"""Schema loading, type/alias resolution, and folder glob matching."""

from __future__ import annotations

from vault_governance.schema import GovernanceSchema


def test_real_schema_loads_and_reconciles_concept(gov_schema):
    # The Type Dictionary's plural 'Concepts' was reconciled to singular
    # 'Concept'; the plural must survive only as an alias.
    assert "Concept" in gov_schema.types
    assert "Concepts" not in gov_schema.types
    assert gov_schema.canonical_type("Concepts") == "Concept"
    assert gov_schema.is_alias("Concepts")


def test_alias_and_fuzzy_suggestions(gov_schema):
    assert gov_schema.canonical_type("Daily Note") == "Daily"      # explicit alias
    assert gov_schema.canonical_type("Agent Note") == "Agent Note"  # exact
    assert gov_schema.canonical_type("Nonsense") is None
    # fuzzy: a near-miss on a real type name
    assert gov_schema.suggest_type("Referense") == "Reference"


def _schema(folders):
    return GovernanceSchema.from_dicts(
        {"list_properties": ["Tags"], "datetime_properties": ["CreatedAt"]},
        {"types": {"Project": {"folder_globs": ["Human/03 Projects/**"],
                               "statuses": ["Active"]}}},
        {"default": {"layer": "human", "validation_mode": "loose"},
         "folders": folders},
    )


def test_glob_matching_double_star_spans_separators():
    s = _schema({"Human/03 Projects/**": {"default_type": "Project"}})
    assert s.matching_rules("Human/03 Projects/Foo.md")
    assert s.matching_rules("Human/03 Projects/Sub/Bar.md")
    assert not s.matching_rules("Human/04 Areas/Baz.md")


def test_single_star_does_not_span_separators():
    s = _schema({"Human/*": {"default_type": "X"}})
    assert s.matching_rules("Human/file.md")
    assert not s.matching_rules("Human/sub/file.md")


def test_rules_sorted_least_specific_first():
    s = _schema({
        "Human/**": {"layer": "human"},
        "Human/03 Projects/**": {"default_type": "Project"},
    })
    matches = s.matching_rules("Human/03 Projects/Foo.md")
    # least-specific first, so the deepest rule (with default_type) is last
    assert matches[0].glob == "Human/**"
    assert matches[-1].glob == "Human/03 Projects/**"
    assert matches[-1].default_type == "Project"
