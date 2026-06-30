"""Location-implied context and Parent-chain property inheritance."""

from __future__ import annotations

from vault_governance.inheritance import (
    effective_properties,
    parent_links,
    resolve_context,
    resolve_inherited_properties,
)


def test_context_for_human_canonical(gov_schema):
    ctx = resolve_context("Human/03 Projects/Project - Foo.md", gov_schema)
    assert ctx.layer == "human"
    assert ctx.canonical is True
    assert ctx.ai_write == "forbidden"
    assert ctx.default_type == "Project"
    assert ctx.validation_mode == "strict"


def test_context_for_agent_layer(gov_schema):
    ctx = resolve_context("Agent/notes/x.md", gov_schema)
    assert ctx.layer == "agent"
    assert ctx.ai_write == "engine_only"
    assert ctx.allowed_types == ["Agent Note"]
    assert ctx.validation_mode == "agent"


def test_context_inbox_ai_is_writable_and_loose(gov_schema):
    ctx = resolve_context("Human/01 Inbox/AI/proposal.md", gov_schema)
    assert ctx.ai_write == "allowed"
    assert ctx.canonical is False
    assert ctx.validation_mode == "loose"
    assert ctx.purpose == "AI Suggestion"


def test_specific_folder_overrides_parent(gov_schema):
    # Human/01 Inbox/AI overrides the broader Human/01 Inbox forbidden rule.
    ai = resolve_context("Human/01 Inbox/AI/x.md", gov_schema)
    other = resolve_context("Human/01 Inbox/raw.md", gov_schema)
    assert ai.ai_write == "allowed"
    assert other.ai_write == "forbidden"


def test_parent_links_parses_wikilinks():
    meta = {"Parent": ["[[Area - Career]]", "[[Project - Foo|alias]]", "Bare Title"]}
    assert parent_links(meta) == ["Area - Career", "Project - Foo", "Bare Title"]


def test_inherited_properties_union_tags_and_single_domain():
    parents = {
        "Root": {"Tags": ["a", "b"], "Domain": "Backend"},
        "Mid": {"Tags": ["b", "c"], "Parent": ["[[Root]]"]},
    }
    child = {"Tags": ["c", "d"], "Parent": ["[[Mid]]"]}
    inh = resolve_inherited_properties(child, parents)
    assert set(inh["Tags"]) == {"a", "b", "c"}   # unioned across the chain, child excluded
    assert inh["Domain"] == "Backend"            # nearest-setting ancestor


def test_inheritance_is_cycle_safe():
    parents = {
        "A": {"Tags": ["x"], "Parent": ["[[B]]"]},
        "B": {"Tags": ["y"], "Parent": ["[[A]]"]},
    }
    inh = resolve_inherited_properties({"Parent": ["[[A]]"]}, parents)
    assert set(inh["Tags"]) == {"x", "y"}  # terminates despite the A<->B cycle


def test_effective_properties_explicit_wins_tags_union():
    parents = {"P": {"Tags": ["p"], "Domain": "D"}}
    child = {"Tags": ["c"], "Domain": "Own", "Parent": ["[[P]]"]}
    eff = effective_properties(child, parents)
    assert set(eff["Tags"]) == {"p", "c"}
    assert eff["Domain"] == "Own"
