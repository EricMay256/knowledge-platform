"""Metadata linting: normalization rules, writability scope, and --fix."""

from __future__ import annotations

from vault_contrib import vault_frontmatter as vf
from vault_governance.frontmatter_scan import parse_note_text
from vault_governance.lint import GOVERNANCE_ORDER, lint_note, lint_vault
from vault_governance.schema import GovernanceSchema


def _rec(rel_path: str, text: str):
    rec = parse_note_text(text)
    rec.rel_path = rel_path
    return rec


def _rules(findings):
    return {f.rule for f in findings}


def test_canonical_agent_note_is_unchanged(gov_schema):
    # Render exactly what the engine would, then confirm lint sees no drift.
    meta = {
        "Type": "Agent Note", "Status": "Active",
        "CreatedAt": "2026-06-25T00:00:00+00:00", "LastUpdated": "2026-06-25T00:00:00+00:00",
        "tags": ["x"], "Title": "T", "ID": "deadbeef", "ContributedBy": "agent:me",
        "Source": None, "RelatedIDs": [], "ClientRunID": None, "SchemaVersion": 2,
    }
    text = vf.dump_note(meta, "body\n")
    res = lint_note(_rec("Agent/notes/a.md", text), gov_schema)
    assert res.changed is False
    assert res.new_text is None


def test_legacy_keys_renamed_on_writable_note(gov_schema):
    text = """---
Type: Agent Note
status: Active
created_at: 2026-06-25T00:00:00Z
tags:
  - a
title: t
id: deadbeef
contributed_by: agent:me
schema_version: 2
---
body
"""
    res = lint_note(_rec("Agent/notes/a.md", text), gov_schema)
    assert res.writable is True
    assert res.changed is True
    assert "lint-key-rename" in _rules(res.findings)
    # renamed keys appear with canonical casing in the rewritten text
    assert "Status: Active" in res.new_text
    assert "CreatedAt:" in res.new_text
    assert "Title: t" in res.new_text
    assert "tags:" in res.new_text          # reserved-lowercase, unchanged


def test_dedup_and_list_shape(gov_schema):
    text = """---
Type: Reference
CreatedAt: 2026-06-25T00:00:00Z
LastUpdated: 2026-06-25T00:00:00Z
tags:
  - a
  - a
  - b
aliases: solo
---
body
"""
    # Reference notes live in a canonical (non-writable) folder; use a writable
    # location so the findings are actionable (WARNING) and a rewrite is offered.
    res = lint_note(_rec("Agent/Promotion Candidates/c.md", text), gov_schema)
    assert "lint-dedup" in _rules(res.findings)
    assert "lint-list-shape" in _rules(res.findings)


def test_canonical_human_note_is_reported_not_writable(gov_schema):
    text = """---
Type: Reference
CreatedAt: 2026-06-25T00:00:00Z
LastUpdated: 2026-06-25T00:00:00Z
Tags:
  - language
---
body
"""
    res = lint_note(_rec("Human/06 Reference/r.md", text), gov_schema)
    assert res.writable is False
    assert res.changed is True          # TitleCase Tags is drift -> would become tags
    # but it is only reported (INFO), never auto-written
    assert all(f.severity.value == "info" for f in res.findings)


def test_human_note_uses_governance_key_order(gov_schema):
    text = """---
Tags:
  - a
Status: Active
Type: Project
CreatedAt: 2026-06-25T00:00:00Z
LastUpdated: 2026-06-25T00:00:00Z
---
body
"""
    res = lint_note(_rec("Agent/Promotion Candidates/p.md", text), gov_schema)
    fm, _ = vf.split_frontmatter(res.new_text)
    keys = [line.split(":")[0] for line in fm.splitlines() if line and not line.startswith(" ")]
    # Type/Status/CreatedAt/LastUpdated come first, in governance order
    assert keys[: 4] == GOVERNANCE_ORDER[: 4]


def test_fix_writes_only_writable_notes(gov_schema, temp_vault):
    vault, write = temp_vault
    agent = write("Agent/Promotion Candidates/c.md",
                  "---\nType: Note\nTags:\n  - a\n---\nbody\n")
    human = write("Human/06 Reference/r.md",
                  "---\nType: Reference\nTags:\n  - a\n---\nbody\n")

    schema = GovernanceSchema.load(vault)
    lint_vault(vault, schema, fix=True)

    assert "tags:" in agent.read_text(encoding="utf-8")        # writable -> fixed to lowercase
    assert "Tags:" in human.read_text(encoding="utf-8")        # canonical Human -> untouched
    assert "tags:" not in human.read_text(encoding="utf-8")
