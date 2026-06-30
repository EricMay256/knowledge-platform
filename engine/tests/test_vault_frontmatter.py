"""Regression guard for canonical frontmatter rendering."""

from vault_contrib import vault_frontmatter as vf

CANON_PLAIN_TITLE = (
    "---\n"
    "Type: Agent Note\n"
    "Status: Active\n"
    "CreatedAt: 2026-06-25T22:16:14.466717+00:00\n"
    "LastUpdated: 2026-06-25T22:16:14.466717+00:00\n"
    "tags:\n"
    "  - pytest\n"
    "  - windows\n"
    "Title: Use workspace-local pytest temp paths in restricted sandboxes\n"
    "ID: 6d46c9aba5a641bb836e556e60aeab21\n"
    "ContributedBy: agent:codex\n"
    "Source:\n"
    "RelatedIDs: []\n"
    "ClientRunID: codex-2026-06-25-pytest-workspace-temp\n"
    "SchemaVersion: 2\n"
    "---\n"
    "Body stays verbatim.\n"
)

CANON_QUOTED_TITLE = (
    "---\n"
    "Type: Agent Note\n"
    "Status: Active\n"
    "CreatedAt: 2026-06-25T21:15:50.834065+00:00\n"
    "LastUpdated: 2026-06-25T21:15:50.834065+00:00\n"
    "tags:\n"
    "  - knowledge-vault\n"
    'Title: "Auto-memory vs knowledge vault: which store to use"\n'
    "ID: 072c57ffc8264d0d87c7aa5b4488db76\n"
    "ContributedBy: agent:claude-code\n"
    "Source:\n"
    "RelatedIDs: []\n"
    "ClientRunID:\n"
    "SchemaVersion: 2\n"
    "---\n"
    "Body.\n"
)


def test_canonical_input_is_byte_stable():
    for fixture in (CANON_PLAIN_TITLE, CANON_QUOTED_TITLE):
        assert vf.canonicalize(fixture) == fixture


def test_idempotent_on_noncanonical_input():
    pyyaml_style = (
        "---\n"
        "Type: Agent Note\n"
        "Status: Active\n"
        "CreatedAt: '2026-06-25T21:15:50.834065+00:00'\n"
        "LastUpdated: '2026-06-25T21:15:50.834065+00:00'\n"
        "tags:\n"
        "- a\n"
        "- b\n"
        "Title: 'Has: a colon'\n"
        "ID: x\n"
        "Source: null\n"
        "RelatedIDs: []\n"
        "SchemaVersion: 2\n"
        "---\n"
        "Body.\n"
    )
    once = vf.canonicalize(pyyaml_style)
    assert vf.canonicalize(once) == once
    assert "  - a" in once
    assert "Source:\n" in once
    assert 'Title: "Has: a colon"' in once
    assert "CreatedAt: 2026-06-25T21:15:50.834065+00:00\n" in once


def test_quoting_rules():
    out = vf.render_frontmatter({"title": 'He said "hi" \\o/'})
    assert out == 'title: "He said \\"hi\\" \\\\o/"'
    assert vf.render_frontmatter({"title": "null"}) == 'title: "null"'
    assert vf.render_frontmatter({"title": "true"}) == 'title: "true"'
    assert vf.render_frontmatter({"title": "- leading dash"}) == 'title: "- leading dash"'
    assert vf.render_frontmatter({"title": "123"}) == 'title: "123"'
    assert (
        vf.render_frontmatter({"title": "perfectly normal title"})
        == "title: perfectly normal title"
    )


def test_empty_scalar_is_bare_and_empty_list_is_flow():
    out = vf.render_frontmatter({"Source": None, "RelatedIDs": []})
    assert out == "Source:\nRelatedIDs: []"


def test_unknown_field_preserved_deterministically():
    out = vf.render_frontmatter({"zeta": "z", "ID": "x", "alpha": "a"})
    # schema-ordered keys first (ID), then unknown keys sorted (alpha, zeta)
    assert out == "ID: x\nalpha: a\nzeta: z"
