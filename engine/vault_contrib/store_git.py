"""A-stage store: markdown files in a git repo. THROWAWAY at B2.

Replaced by a `PostgresStore` whose methods become SQL inside the caller's
transaction. Git is the A stage's history / rollback / audit layer and its
(optimistic) concurrency story: parallel contributions are not serialized here
-- that's the deferred work B2 buys back. At A-stage scale, git's merge
behaviour absorbs the occasional concurrent write.

Layout under the vault root:
    notes/<title-slug>.md     active notes
    review/<title-slug>.md    flagged possible-duplicates awaiting adjudication
Files are named from the note *title* so the vault is human-browsable (the whole
point of the markdown stage). The frontmatter `id` remains the real identity:
filenames are a cosmetic, scan-resolved lookup key, and two notes that slugify
the same are disambiguated with a `-2`, `-3`, ... suffix. Each file is YAML
frontmatter (the note metadata) followed by the markdown body.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable

import yaml

from .models import Note, ScoredCandidate
from . import vault_frontmatter as vf

_SLUG_MAX = 80
# Names Windows refuses for a file (case-insensitive, with or without extension).
_WIN_RESERVED = {"con", "prn", "aux", "nul"} | {
    f"{p}{n}" for p in ("com", "lpt") for n in range(1, 10)
}


def _slugify(title: str) -> str:
    """Filesystem-safe, human-readable slug from a title.

    Lowercase; any run of non-alphanumeric characters (incl. the Windows-illegal
    set < > : " / \\ | ? * and whitespace) collapses to a single hyphen. Unicode
    letters are kept (str.isalnum is script-aware), so non-ASCII titles stay
    readable. Falls back to "untitled" when nothing survives.
    """
    out: list[str] = []
    prev_hyphen = False
    for ch in title.strip().lower():
        if ch.isalnum():
            out.append(ch)
            prev_hyphen = False
        elif not prev_hyphen:
            out.append("-")
            prev_hyphen = True
    slug = "".join(out).strip("-")[:_SLUG_MAX].strip("-")
    if not slug:
        return "untitled"
    if slug in _WIN_RESERVED:
        return f"{slug}-note"
    return slug


def _serialize(note: Note) -> str:
    return vf.dump_note(note.to_metadata(), note.body)


def _serialize_review(note: Note, reason: str, similars: list[ScoredCandidate]) -> str:
    meta = {
        **note.to_metadata(),
        "flag_reason": reason,
        "flag_similars": [
            {"note_id": c.note_id, "title": c.title, "score": round(c.score, 4)}
            for c in similars
        ],
    }
    front = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)
    return f"---\n{front}---\n{note.body}\n"


def _deserialize(text: str) -> Note:
    # Tolerate CRLF: editors on Windows (Obsidian, Notepad, VS Code) may save the
    # file with \r\n, which would otherwise defeat the "---\n" frontmatter split.
    text = text.replace("\r\n", "\n")
    meta, body = vf.load_note(text)
    return Note.from_parts(meta, body.strip())


class GitMarkdownStore:
    """Satisfies the Store Protocol over a git working directory."""

    def __init__(
        self,
        root: str | Path,
        *,
        auto_commit: bool = True,
        init_if_missing: bool = True,
    ) -> None:
        self.root = Path(root)
        self.notes_dir = self.root / "notes"
        self.review_dir = self.root / "review"
        self.auto_commit = auto_commit
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.review_dir.mkdir(parents=True, exist_ok=True)
        # Only initialize a repo when the vault is NOT already inside one. When
        # the vault lives under a larger repo (e.g. Vault/Agent inside
        # the knowledge-platform monorepo), initializing here would create a
        # nested repo; instead we let git auto-commit against the enclosing repo.
        if init_if_missing and self._enclosing_git_root() is None:
            self._git("init", "-q")
            # Local identity so commits work in a fresh sandbox / CI.
            self._git("config", "user.email", "vault-agent@example.com")
            self._git("config", "user.name", "vault-agent")

    def _enclosing_git_root(self) -> Path | None:
        """The nearest ancestor (incl. self.root) that holds a `.git`, if any."""
        for parent in (self.root, *self.root.parents):
            if (parent / ".git").exists():
                return parent
        return None

    # --- filename helpers ----------------------------------------------------

    def _new_path(self, directory: Path, note: Note) -> Path:
        """A free title-slug path in `directory`, suffixed -2/-3 on collision."""
        base = _slugify(note.title)
        candidate = directory / f"{base}.md"
        n = 2
        while candidate.exists():
            candidate = directory / f"{base}-{n}.md"
            n += 1
        return candidate

    def _path_by_id(self, directory: Path, note_id: str) -> Path | None:
        """Locate a note's file by its frontmatter id (names are slug-based, so
        the path can't be computed from the id -- scan, fine at A-stage scale)."""
        for path in sorted(directory.glob("*.md")):
            if _deserialize(path.read_text(encoding="utf-8")).id == note_id:
                return path
        return None

    # --- Store protocol ------------------------------------------------------

    def insert(self, note: Note) -> None:
        path = self._new_path(self.notes_dir, note)
        path.write_text(_serialize(note), encoding="utf-8")
        self._commit(path, f'vault: insert {note.id} "{note.title}" by {note.contributed_by}')

    def update(self, note: Note) -> None:
        # Rewrite in place under the existing filename (kept stable even if the
        # title changed) -- the id, not the name, identifies the note.
        path = self._path_by_id(self.notes_dir, note.id)
        if path is None:
            raise KeyError(f"cannot update missing note {note.id}")
        path.write_text(_serialize(note), encoding="utf-8")
        self._commit(path, f"vault: update {note.id}")

    def get(self, note_id: str) -> Note | None:
        path = self._path_by_id(self.notes_dir, note_id)
        if path is None:
            return None
        return _deserialize(path.read_text(encoding="utf-8"))

    def find_by_run_id(self, run_id: str) -> Note | None:
        # Scan both active and review notes: a prior attempt under this key may
        # have landed in either. A-stage scale makes the linear scan fine; B2
        # replaces it with a unique-indexed SQL lookup.
        for directory in (self.notes_dir, self.review_dir):
            for path in sorted(directory.glob("*.md")):
                note = _deserialize(path.read_text(encoding="utf-8"))
                if note.client_run_id == run_id:
                    return note
        return None

    def iter_notes(self) -> Iterable[Note]:
        for path in sorted(self.notes_dir.glob("*.md")):
            yield _deserialize(path.read_text(encoding="utf-8"))

    def add_to_review(
        self, note: Note, reason: str, similars: list[ScoredCandidate]
    ) -> None:
        flagged = Note(**{**note.__dict__, "status": "Flagged"})
        path = self._new_path(self.review_dir, flagged)
        path.write_text(_serialize_review(flagged, reason, similars), encoding="utf-8")
        self._commit(path, f'vault: flag {note.id} "{note.title}" for review')

    # --- git plumbing --------------------------------------------------------

    def _commit(self, path: Path, message: str) -> None:
        if not self.auto_commit:
            return
        rel = path.relative_to(self.root)
        self._git("add", str(rel))
        self._git("commit", "-q", "-m", message)

    def _git(self, *args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        )
