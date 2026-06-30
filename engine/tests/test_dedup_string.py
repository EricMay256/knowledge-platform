"""dedup_string: _normalize() + exact/fuzzy find_similar over the corpus."""

from __future__ import annotations

from vault_contrib.dedup_string import StringMatchDeduper, _normalize
from vault_contrib.models import Note


def _seed(store, title, body="body text"):
    note = Note.create(title=title, body=body, contributed_by="seed")
    store.insert(note)
    return note


# --- _normalize --------------------------------------------------------------


def test_normalize_lowercases_and_collapses_internal_whitespace():
    assert _normalize("Two   Phase  Updates") == "two phase updates"


def test_normalize_strips_punctuation_without_inserting_space():
    # Punctuation is deleted, not replaced by a space -- so hyphenated titles
    # collapse ("Two-phase" -> "twophase"). Locks the Stage-A behaviour; two
    # titles that differ only by a hyphen vs. a space do NOT normalize equal.
    assert _normalize("Two-phase TICK updates!!") == "twophase tick updates"
    assert _normalize("Two-phase tick updates") == _normalize("two-phase TICK updates!!")


def test_normalize_strips_surrounding_whitespace():
    assert _normalize("  hello   world  ") == "hello world"


# --- exact path --------------------------------------------------------------


def test_exact_normalized_match_scores_one(vault):
    _seed(vault, "Two-phase tick updates")
    deduper = StringMatchDeduper(vault)
    cand = Note.create(title="two-phase TICK updates!!", body="b", contributed_by="a")
    hits = deduper.find_similar(cand)
    assert len(hits) == 1
    assert hits[0].score == 1.0


def test_unrelated_title_no_hit_without_fuzzy(vault):
    _seed(vault, "Spatial hashing for broadphase")
    deduper = StringMatchDeduper(vault)
    cand = Note.create(title="Completely different topic", body="b", contributed_by="a")
    assert deduper.find_similar(cand) == []


def test_candidate_does_not_match_itself(vault):
    note = _seed(vault, "Self match guard")
    deduper = StringMatchDeduper(vault)
    # Same id as the stored note -> must be skipped.
    assert deduper.find_similar(note) == []


# --- fuzzy path --------------------------------------------------------------


def test_fuzzy_surfaces_near_title_below_one(vault):
    _seed(vault, "Two-phase tick updates")
    deduper = StringMatchDeduper(vault, fuzzy_threshold=0.6)
    cand = Note.create(title="Two phase update ticks", body="b", contributed_by="a")
    hits = deduper.find_similar(cand)
    assert len(hits) == 1
    assert 0.6 <= hits[0].score < 1.0


def test_fuzzy_drops_below_threshold(vault):
    _seed(vault, "Spatial hashing for broadphase collision")
    deduper = StringMatchDeduper(vault, fuzzy_threshold=0.9)
    cand = Note.create(title="Quaternion slerp basics", body="b", contributed_by="a")
    assert deduper.find_similar(cand) == []


def test_results_sorted_score_descending(vault):
    _seed(vault, "Tick update ordering")          # closer
    _seed(vault, "Tick update ordering variant x")  # farther
    deduper = StringMatchDeduper(vault, fuzzy_threshold=0.3)
    cand = Note.create(title="Tick update ordering", body="b", contributed_by="a")
    hits = deduper.find_similar(cand)
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == 1.0
