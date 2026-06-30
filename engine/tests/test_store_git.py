"""GitMarkdownStore: round-trip fidelity, review shape, commit behaviour."""

from __future__ import annotations

import subprocess

import pytest

from vault_contrib.models import Note, ScoredCandidate
from vault_contrib.store_git import GitMarkdownStore, _deserialize, _serialize, _slugify
from vault_contrib import vault_frontmatter as vf


def _git_log_subjects(root):
    # check=False: `git log` exits 128 on a repo with no commits yet (the
    # auto_commit=False case), which legitimately means "zero subjects".
    out = subprocess.run(
        ["git", "log", "--format=%s"],
        cwd=root, capture_output=True, text=True, check=False,
    )
    return [line for line in out.stdout.splitlines() if line]


def test_insert_get_roundtrip_all_fields(vault):
    note = Note.create(
        title="Round trip", body="hello", contributed_by="agent-1",
        tags=["a", "b"], source="http://x", client_run_id="rid-1",
    )
    vault.insert(note)
    got = vault.get(note.id)
    assert got == note


def test_iter_notes_yields_inserted(vault):
    n1 = Note.create(title="One", body="b1", contributed_by="a")
    n2 = Note.create(title="Two", body="b2", contributed_by="a")
    vault.insert(n1)
    vault.insert(n2)
    ids = {n.id for n in vault.iter_notes()}
    assert ids == {n1.id, n2.id}


def test_get_missing_returns_none(vault):
    assert vault.get("does-not-exist") is None


def test_horizontal_rule_in_body_survives_roundtrip(vault):
    """A '---' markdown horizontal rule must survive write->read. Guards the
    _deserialize split(_FRONTMATTER, maxsplit=2) contract (HANDOFF §5 P1)."""
    body = "Intro paragraph.\n\n---\n\nSection after a horizontal rule."
    note = Note.create(title="Has HR", body=body, contributed_by="a")
    vault.insert(note)
    assert vault.get(note.id).body == body


def test_serialize_deserialize_unit_with_rule():
    note = Note.create(title="t", body="above\n\n---\n\nbelow", contributed_by="a")
    assert _deserialize(_serialize(note)).body == note.body


def test_deserialize_tolerates_crlf():
    # A Windows editor (e.g. Obsidian) may rewrite the file with CRLF; the
    # frontmatter must still parse rather than raising "missing frontmatter".
    note = Note.create(title="CRLF note", body="line one\nline two", contributed_by="a")
    crlf = _serialize(note).replace("\n", "\r\n")
    out = _deserialize(crlf)
    assert out.title == "CRLF note"
    assert out.body == "line one\nline two"


def test_unicode_body_survives(vault):
    note = Note.create(title="Unicode", body="naïve café — 日本語 ✓", contributed_by="a")
    vault.insert(note)
    assert vault.get(note.id).body == note.body


def test_add_to_review_shape(vault):
    note = Note.create(title="Dup", body="b", contributed_by="a")
    sims = [ScoredCandidate(note_id="other", title="Other", score=0.91)]
    vault.add_to_review(note, reason="possible duplicate of other", similars=sims)

    # Filename is the title slug, in review/ not notes/.
    review_path = vault.review_dir / "dup.md"
    assert review_path.exists()
    assert list(vault.notes_dir.glob("*.md")) == []

    import yaml
    text = review_path.read_text(encoding="utf-8")
    _, front, _ = text.split("---\n", 2)
    meta = yaml.safe_load(front)
    assert meta["Status"] == "Flagged"
    assert meta["flag_reason"] == "possible duplicate of other"
    assert meta["flag_similars"][0]["note_id"] == "other"
    assert meta["flag_similars"][0]["score"] == 0.91


def test_commits_have_structured_messages(vault):
    note = Note.create(title="Committed", body="b", contributed_by="agent-1")
    vault.insert(note)
    vault.add_to_review(note, reason="r", similars=[])
    subjects = _git_log_subjects(vault.root)
    assert any(s.startswith(f"vault: insert {note.id}") for s in subjects)
    assert any(s.startswith(f"vault: flag {note.id}") for s in subjects)


def test_no_commit_writes_file_but_no_commit(tmp_path):
    store = GitMarkdownStore(tmp_path, auto_commit=False)
    note = Note.create(title="No commit", body="b", contributed_by="a")
    store.insert(note)
    assert (store.notes_dir / "no-commit.md").exists()
    assert _git_log_subjects(tmp_path) == []  # nothing committed


def test_update_missing_raises(vault):
    ghost = Note.create(title="Ghost", body="b", contributed_by="a")
    with pytest.raises(KeyError):
        vault.update(ghost)


def test_update_existing_rewrites(vault):
    note = Note.create(title="Original", body="b", contributed_by="a")
    vault.insert(note)
    note.title = "Edited"
    vault.update(note)
    assert vault.get(note.id).title == "Edited"


def test_engine_output_stays_canonical_after_update(vault):
    note = Note.create(
        title="Auto-memory vs knowledge vault: which store to use",
        body="Body.",
        contributed_by="agent:codex",
        tags=["knowledge-vault"],
    )
    vault.insert(note)
    note.tags.append("serialization")
    vault.update(note)

    path = vault.notes_dir / "auto-memory-vs-knowledge-vault-which-store-to-use.md"
    text = path.read_text(encoding="utf-8")
    assert vf.canonicalize(text) == text
    assert 'Title: "Auto-memory vs knowledge vault: which store to use"\n' in text
    assert "  - serialization\n" in text


# --- title-slug filenames ----------------------------------------------------


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Two-phase tick updates", "two-phase-tick-updates"),
        ("Auto-memory vs vault: which store?", "auto-memory-vs-vault-which-store"),
        ("  Spaces   collapse  ", "spaces-collapse"),
        ("!!!", "untitled"),            # nothing survives -> fallback
        ("CON", "con-note"),            # Windows-reserved device name
        ("café déjà 日本語", "café-déjà-日本語"),  # unicode letters preserved
    ],
)
def test_slugify(title, expected):
    assert _slugify(title) == expected


def test_slugify_truncates_long_titles():
    slug = _slugify("word " * 50)
    assert len(slug) <= 80
    assert not slug.endswith("-")


def test_insert_uses_title_slug_filename(vault):
    note = Note.create(title="Spatial Hashing for Broadphase", body="b", contributed_by="a")
    vault.insert(note)
    assert (vault.notes_dir / "spatial-hashing-for-broadphase.md").exists()
    # The id is unchanged and still resolves the note.
    assert vault.get(note.id).id == note.id


def test_same_slug_notes_get_suffixed(vault):
    a = Note.create(title="Same Title", body="one", contributed_by="x")
    b = Note.create(title="same   title", body="two", contributed_by="y")  # slugs identical
    vault.insert(a)
    vault.insert(b)
    names = {p.name for p in vault.notes_dir.glob("*.md")}
    assert names == {"same-title.md", "same-title-2.md"}
    # Both remain independently retrievable by their distinct ids.
    assert vault.get(a.id).body == "one"
    assert vault.get(b.id).body == "two"


def test_filename_stable_when_title_edited(vault):
    note = Note.create(title="First Title", body="b", contributed_by="a")
    vault.insert(note)
    note.title = "Completely Different"
    vault.update(note)
    # Filename keeps the original slug; the frontmatter title is updated.
    assert (vault.notes_dir / "first-title.md").exists()
    assert vault.get(note.id).title == "Completely Different"
