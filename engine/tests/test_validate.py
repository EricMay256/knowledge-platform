"""core.validate() — field-level validation on the constructed Note."""

from __future__ import annotations

from vault_contrib.core import validate
from vault_contrib.models import Note


def _note(**over):
    base = dict(title="Title", body="Body text", contributed_by="agent-1")
    base.update(over)
    return Note.create(**base)


def test_clean_note_has_no_errors():
    assert validate(_note()) == []


def test_empty_title_errors():
    # Note.create strips, so a whitespace title becomes empty.
    errs = validate(_note(title="   "))
    assert any("title" in e for e in errs)


def test_empty_body_errors():
    errs = validate(_note(body="   "))
    assert any("body" in e for e in errs)


def test_blank_contributor_errors():
    errs = validate(_note(contributed_by="  "))
    assert any("contributed_by" in e for e in errs)


def test_blank_tag_errors():
    errs = validate(_note(tags=["ok", "  "]))
    assert any("invalid tag" in e for e in errs)


def test_duplicate_tags_error():
    errs = validate(_note(tags=["dup", "dup"]))
    assert any("duplicate tags" in e for e in errs)


def test_non_string_tag_errors():
    # Bypass create() to inject a non-string tag directly.
    note = _note()
    note.tags = ["ok", 5]  # type: ignore[list-item]
    errs = validate(note)
    assert any("invalid tag" in e for e in errs)
