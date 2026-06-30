"""CLI status JSON + exit-code contract.

Agents shell out and branch on the exit code: 0 for a write outcome
(inserted/linked), non-zero otherwise (flagged/rejected/invalid).
"""

from __future__ import annotations

import json

from pathlib import Path

from vault_contrib.cli import _resolve_vault, main, render_index
from vault_contrib.models import Note


def _contribute(vault, capsys, **extra):
    argv = [
        "contribute", "--vault", str(vault),
        "--by", "agent-1", "--title", extra.pop("title", "A title"),
        "--body", extra.pop("body", "A body"),
    ]
    for k, v in extra.items():
        argv += [f"--{k.replace('_', '-')}", v]
    code = main(argv)
    payload = json.loads(capsys.readouterr().out)
    return code, payload


def test_insert_exit_zero(tmp_path, capsys):
    code, payload = _contribute(tmp_path, capsys)
    assert code == 0
    assert payload["status"] == "inserted"
    assert payload["note_id"]


def test_duplicate_exit_nonzero(tmp_path, capsys):
    _contribute(tmp_path, capsys, title="Same")
    code, payload = _contribute(tmp_path, capsys, title="Same")
    assert code != 0
    assert payload["status"] == "flagged"


def test_invalid_exit_nonzero(tmp_path, capsys):
    code, payload = _contribute(tmp_path, capsys, body="   ")
    assert code != 0
    assert payload["status"] == "invalid"
    assert payload["errors"]


def test_run_id_retry_exit_zero(tmp_path, capsys):
    _contribute(tmp_path, capsys, title="Keyed", run_id="rid-1")
    code, payload = _contribute(tmp_path, capsys, title="Keyed", run_id="rid-1")
    assert code == 0
    assert payload["status"] == "inserted"
    assert "idempotent replay" in payload["message"]


def test_resolve_vault_explicit_path_wins(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_VAULT", "/env/vault")
    assert _resolve_vault("/explicit") == Path("/explicit")


def test_resolve_vault_uses_env_var(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_VAULT", "/env/vault")
    assert _resolve_vault(None) == Path("/env/vault")


def test_resolve_vault_default_expands_home(monkeypatch):
    monkeypatch.delenv("KNOWLEDGE_VAULT", raising=False)
    resolved = _resolve_vault(None)
    # Falls back to ~/knowledge-vault with ~ expanded (no literal "~" segment).
    assert resolved == Path.home() / "knowledge-vault"
    assert "~" not in str(resolved)


def test_contribute_uses_env_var_when_vault_omitted(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_VAULT", str(tmp_path / "central"))
    code = main(["contribute", "--by", "agent:x", "--title", "T", "--body", "B"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0 and payload["status"] == "inserted"
    assert (tmp_path / "central" / "notes").is_dir()


def test_list_command(tmp_path, capsys):
    _contribute(tmp_path, capsys, title="Listed note")
    capsys.readouterr()
    code = main(["list", "--vault", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert "Listed note" in out


def test_list_tag_filter(tmp_path, capsys):
    _contribute(tmp_path, capsys, title="Alpha", tags="x,y")
    _contribute(tmp_path, capsys, title="Beta", tags="y,z")
    capsys.readouterr()
    main(["list", "--vault", str(tmp_path), "--tag", "x"])
    out = capsys.readouterr().out
    assert "Alpha" in out and "Beta" not in out

    # Repeated --tag is AND.
    main(["list", "--vault", str(tmp_path), "--tag", "y", "--tag", "z"])
    out = capsys.readouterr().out
    assert "Beta" in out and "Alpha" not in out


def test_index_command_writes_grouped_file(tmp_path, capsys):
    _contribute(tmp_path, capsys, title="Note One", tags="a,b")
    _contribute(tmp_path, capsys, title="Note Two", tags="b")
    capsys.readouterr()
    code = main(["index", "--vault", str(tmp_path)])
    assert code == 0
    index = (tmp_path / "INDEX.md").read_text(encoding="utf-8")
    assert "## a (1)" in index and "## b (2)" in index
    # Links point at the title-slug files.
    assert "(notes/note-one.md)" in index


def test_normalize_check_reports_offenders(tmp_path, capsys):
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "old-style.md").write_text(
        "---\n"
        "Type: Agent Note\n"
        "Status: Active\n"
        "CreatedAt: '2026-06-25T21:15:50.834065+00:00'\n"
        "LastUpdated: '2026-06-25T21:15:50.834065+00:00'\n"
        "Tags:\n"
        "- a\n"
        "title: 'Has: a colon'\n"
        "id: x\n"
        "source: null\n"
        "related_ids: []\n"
        "schema_version: 2\n"
        "---\n"
        "Body.\n",
        encoding="utf-8",
    )

    code = main(["normalize", "--vault", str(tmp_path), "--check"])
    out = capsys.readouterr().out
    assert code == 1
    assert "old-style.md" in out


def test_normalize_rewrites_notes_only(tmp_path, capsys):
    notes = tmp_path / "notes"
    review = tmp_path / "review"
    notes.mkdir()
    review.mkdir()
    noncanonical = (
        "---\n"
        "Type: Agent Note\n"
        "Status: Active\n"
        "CreatedAt: '2026-06-25T21:15:50.834065+00:00'\n"
        "LastUpdated: '2026-06-25T21:15:50.834065+00:00'\n"
        "Tags:\n"
        "- a\n"
        "title: 'Has: a colon'\n"
        "id: x\n"
        "source: null\n"
        "related_ids: []\n"
        "schema_version: 2\n"
        "---\n"
        "Body.\n"
    )
    note_path = notes / "old-style.md"
    review_path = review / "old-style.md"
    note_path.write_text(noncanonical, encoding="utf-8")
    review_path.write_text(noncanonical, encoding="utf-8")

    code = main(["normalize", "--vault", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0
    assert "rewrote 1 note(s)" in out
    assert 'title: "Has: a colon"\n' in note_path.read_text(encoding="utf-8")
    assert review_path.read_text(encoding="utf-8") == noncanonical

    code = main(["normalize", "--vault", str(tmp_path), "--check"])
    assert code == 0


def test_render_index_multi_tag_and_untagged():
    a = Note.create(title="Tagged", body="b", contributed_by="x", tags=["t1", "t2"])
    b = Note.create(title="Bare", body="b", contributed_by="x")
    out = render_index([("notes/tagged.md", a), ("notes/bare.md", b)])
    # A note appears under every tag it carries (no single-hierarchy lock-in).
    assert out.count("[Tagged]") == 2
    assert "## (untagged) (1)" in out
    assert "[Bare](notes/bare.md)" in out
