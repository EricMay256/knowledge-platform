"""Schema validation: severities, modes, and the specific rules."""

from __future__ import annotations

from vault_governance.findings import Severity, has_errors
from vault_governance.frontmatter_scan import parse_note_text
from vault_governance.validate import validate_note, validate_vault


def _rec(rel_path: str, text: str):
    rec = parse_note_text(text)
    rec.rel_path = rel_path
    return rec


def _rules(findings):
    return {f.rule for f in findings}


def _by_rule(findings, rule):
    return [f for f in findings if f.rule == rule]


# --- Agent Note (agent mode) ---------------------------------------------

GOOD_AGENT = """---
Type: Agent Note
Status: Active
CreatedAt: 2026-06-25T22:16:45+00:00
LastUpdated: 2026-06-25T22:16:45+00:00
tags:
  - x
Title: A note
ID: d636f2fe799c4caa8d9147e38e76641a
ContributedBy: agent:codex
RelatedIDs: []
SchemaVersion: 2
---
body
"""


def test_valid_agent_note_has_no_errors(gov_schema):
    findings = validate_note(_rec("Agent/notes/a.md", GOOD_AGENT), gov_schema)
    assert not has_errors(findings)


def test_agent_note_wrong_type_and_missing_id_are_errors(gov_schema):
    text = GOOD_AGENT.replace("Type: Agent Note", "Type: Concept").replace(
        "ID: d636f2fe799c4caa8d9147e38e76641a\n", "")
    findings = validate_note(_rec("Agent/notes/a.md", text), gov_schema)
    assert has_errors(findings)
    assert "agent-type" in _rules(findings)
    assert "agent-missing-field" in _rules(findings)


# --- Human canonical (strict mode) ---------------------------------------

def test_engine_field_on_human_note_is_error(gov_schema):
    text = """---
Type: Concept
Status: Seed
CreatedAt: 2026-06-25T00:00:00Z
LastUpdated: 2026-06-25T00:00:00Z
ID: deadbeefdeadbeefdeadbeefdeadbeef
ContributedBy: agent:codex
SchemaVersion: 2
---
copied agent body
"""
    findings = validate_note(_rec("Human/17 Concepts/x.md", text), gov_schema)
    assert has_errors(findings)
    assert "engine-field-in-human" in _rules(findings)


def test_missing_type_warns_with_folder_default(gov_schema):
    text = """---
Status:
CreatedAt: 2026-06-25T00:00:00Z
LastUpdated: 2026-06-25T00:00:00Z
---
body
"""
    findings = validate_note(_rec("Human/03 Projects/p.md", text), gov_schema)
    f = _by_rule(findings, "missing-type")
    assert f and f[0].severity is Severity.WARNING
    assert "Project" in f[0].message


def test_drifted_type_and_invalid_status(gov_schema):
    text = """---
Type: Daily Note
Status: Bogus
CreatedAt: 2026-06-25T00:00:00Z
LastUpdated: 2026-06-25T00:00:00Z
---
body
"""
    findings = validate_note(_rec("Human/02 Daily/2026-06-25.md", text), gov_schema)
    assert "drifted-type" in _rules(findings)     # 'Daily Note' -> 'Daily'
    assert "invalid-status" in _rules(findings)   # 'Bogus' not in Daily statuses


def test_unknown_type_suggests(gov_schema):
    text = """---
Type: Referense
CreatedAt: 2026-06-25T00:00:00Z
LastUpdated: 2026-06-25T00:00:00Z
---
body
"""
    findings = validate_note(_rec("Human/06 Reference/r.md", text), gov_schema)
    f = _by_rule(findings, "unknown-type")
    assert f and "Reference" in f[0].message


def test_titlecase_tags_key_warns(gov_schema):
    # Post-standardization, lowercase `tags` is canonical and TitleCase `Tags`
    # is the legacy drift.
    text = """---
Type: Reference
CreatedAt: 2026-06-25T00:00:00Z
LastUpdated: 2026-06-25T00:00:00Z
Tags:
  - language
---
body
"""
    findings = validate_note(_rec("Human/06 Reference/r.md", text), gov_schema)
    assert "legacy-key" in _rules(findings)


def test_scalar_in_list_field_and_bad_datetime(gov_schema):
    text = """---
Type: Reference
CreatedAt: not-a-date
LastUpdated: 2026-06-25T00:00:00Z
tags: justone
---
body
"""
    findings = validate_note(_rec("Human/06 Reference/r.md", text), gov_schema)
    assert "list-shape" in _rules(findings)
    assert "bad-datetime" in _rules(findings)


def test_type_not_allowed_in_agent_folder_is_error(gov_schema):
    # A non-Agent-Note type under Agent/notes violates allowed_types via the
    # agent-mode Type check.
    text = GOOD_AGENT.replace("Type: Agent Note", "Type: Project")
    findings = validate_note(_rec("Agent/notes/a.md", text), gov_schema)
    assert "agent-type" in _rules(findings)


def test_universal_types_exempt_from_folder_rules(gov_schema):
    # Note/MoC declare folder_globs ['**'] -> allowed in any folder, exempt from
    # both allowed_types (error) and default_type mismatch (warning).
    def _fm(typ):
        return (f"---\nType: {typ}\nCreatedAt: 2026-06-25T00:00:00Z\n"
                f"LastUpdated: 2026-06-25T00:00:00Z\n---\nbody\n")

    # An allowed_types folder: a universal type is not an error...
    note_in_projects = validate_note(_rec("Human/03 Projects/x.md", _fm("Note")), gov_schema)
    assert "type-not-allowed" not in _rules(note_in_projects)
    # ...but a non-universal, non-listed type still is (regression guard).
    person_in_projects = validate_note(_rec("Human/03 Projects/y.md", _fm("Person")), gov_schema)
    assert "type-not-allowed" in _rules(person_in_projects)

    # A default_type-only folder: a universal type raises no folder mismatch.
    moc_in_reference = validate_note(_rec("Human/06 Reference/z.md", _fm("MoC")), gov_schema)
    assert "type-folder-mismatch" not in _rules(moc_in_reference)


# --- loose mode -----------------------------------------------------------

def test_loose_mode_skips_governance_drift(gov_schema):
    # An inbox AI proposal with a junk Type should NOT raise type/status drift
    # (loose mode), only structural issues.
    text = """---
Type: Whatever
Status: Whenever
CreatedAt: 2026-06-25T00:00:00Z
LastUpdated: 2026-06-25T00:00:00Z
SomeRandomKey: ok
---
body
"""
    findings = validate_note(_rec("Human/01 Inbox/AI/x.md", text), gov_schema)
    assert "unknown-type" not in _rules(findings)
    assert "invalid-status" not in _rules(findings)
    assert "unknown-key" not in _rules(findings)


def test_no_frontmatter_severity_depends_on_canonicality(gov_schema):
    canon = validate_note(_rec("Human/06 Reference/r.md", "just a body, no frontmatter"), gov_schema)
    loose = validate_note(_rec("Human/01 Inbox/AI/x.md", "just a body, no frontmatter"), gov_schema)
    assert _by_rule(canon, "no-frontmatter")[0].severity is Severity.WARNING
    assert _by_rule(loose, "no-frontmatter")[0].severity is Severity.INFO


def test_templates_dir_is_skipped(temp_vault, gov_schema):
    # Templates carry {{date}}/<% %> placeholders that are not valid frontmatter
    # until a plugin expands them; the scan layer must skip them entirely so they
    # never produce findings (here: an unparseable-YAML {{date}} value).
    vault, write = temp_vault
    write("Templates/Daily.md",
          "---\nType: Daily\nCreatedAt: {{date:YYYY-MM-DD}}T00:00:00Z\n---\n# {{date}}\n")
    findings = validate_vault(vault, gov_schema)
    assert not any(f.path.startswith("Templates/") for f in findings)


# --- whole-vault integration ---------------------------------------------

def test_validate_real_vault_has_no_errors(gov_schema):
    from tests.conftest import REPO_VAULT

    findings = validate_vault(REPO_VAULT, gov_schema)
    errors = [f for f in findings if f.severity is Severity.ERROR]
    assert errors == [], f"unexpected errors: {[ (e.path, e.rule) for e in errors ]}"
