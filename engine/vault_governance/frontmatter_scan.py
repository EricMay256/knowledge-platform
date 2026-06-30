"""Walk the vault, parse note frontmatter, and yield records.

Parsing reuses ``vault_contrib.vault_frontmatter`` so there is exactly one YAML
dialect in the repo. We additionally capture the raw top-level keys in source
order, because PyYAML silently collapses duplicate keys and we want to flag them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator

from vault_contrib import vault_frontmatter as vf

# A top-level YAML key at column 0 (not a list item, not a comment).
_KEY_RE = re.compile(r"^([^\s#:][^:]*):", re.MULTILINE)

# Directories never worth scanning for notes.
_SKIP_DIRS = {".git", ".obsidian", ".trash", "Assets", "Schemas"}


@dataclass
class NoteRecord:
    rel_path: str                 # vault-relative, posix
    abs_path: Path
    text: str                     # original file contents
    meta: dict | None = None      # parsed frontmatter (None if unparseable)
    body: str | None = None
    raw_keys: list[str] = field(default_factory=list)
    error: str | None = None      # parse failure message, if any

    @property
    def has_frontmatter(self) -> bool:
        return self.meta is not None

    @property
    def missing_frontmatter(self) -> bool:
        return self.error is not None and "no leading" in self.error


def parse_note_text(text: str) -> NoteRecord:
    """Parse a note string. `rel_path`/`abs_path` are filled by the caller."""
    rec = NoteRecord(rel_path="", abs_path=Path(), text=text)
    try:
        meta, body = vf.load_note(text)
    except Exception as exc:  # noqa: BLE001 - surface any parse failure as a finding
        rec.error = str(exc)
        return rec
    rec.meta = meta
    rec.body = body
    try:
        raw_yaml, _ = vf.split_frontmatter(text)
        rec.raw_keys = [m.group(1).strip() for m in _KEY_RE.finditer(raw_yaml)]
    except ValueError:
        rec.raw_keys = []
    return rec


def _in_skipped_dir(rel_parts: tuple[str, ...]) -> bool:
    return any(part in _SKIP_DIRS for part in rel_parts[:-1])


def iter_markdown(vault_root: Path) -> Iterator[Path]:
    for path in sorted(vault_root.rglob("*.md")):
        if _in_skipped_dir(path.relative_to(vault_root).parts):
            continue
        yield path


def scan_vault(
    vault_root: Path,
    rel_paths: Iterable[str] | None = None,
) -> Iterator[NoteRecord]:
    """Yield a `NoteRecord` per markdown note under `vault_root`.

    `rel_paths` (vault-relative posix) restricts the scan to specific notes, used
    by ``--changed-only`` and policy checks. Missing/non-markdown paths are
    skipped silently.
    """
    vault_root = Path(vault_root)
    if rel_paths is not None:
        paths = []
        for rp in rel_paths:
            p = vault_root / rp
            if p.suffix == ".md" and p.is_file() and not _in_skipped_dir(Path(rp).parts):
                paths.append(p)
    else:
        paths = list(iter_markdown(vault_root))

    for path in paths:
        rel = path.relative_to(vault_root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            yield NoteRecord(rel_path=rel, abs_path=path, text="", error=f"not UTF-8: {exc}")
            continue
        rec = parse_note_text(text)
        rec.rel_path = rel
        rec.abs_path = path
        yield rec
