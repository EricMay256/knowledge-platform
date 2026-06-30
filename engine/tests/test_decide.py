"""core.decide() — the policy ladder.

B2 GUARD: only Insert and Flag are ever emitted under the Stage-A policy, but
the Reject/Merge/Link bands must already be correct so B2 lights them up by
setting thresholds with zero change to core.py. Do not delete these as tests of
unreachable code -- that is exactly what they protect.
"""

from __future__ import annotations

import pytest

from vault_contrib.core import decide
from vault_contrib.models import (
    Flag,
    Insert,
    Link,
    Merge,
    Note,
    Policy,
    Reject,
    ScoredCandidate,
)

A_POLICY = Policy(flag_at=0.85)
B2_POLICY = Policy(reject_at=0.97, merge_at=0.93, flag_at=0.85, link_at=0.70)


def _note():
    return Note.create(title="t", body="b", contributed_by="agent-1")


def _sim(score, note_id="other"):
    return ScoredCandidate(note_id=note_id, title="x", score=score)


# --- Stage-A policy: collapses to dup -> Flag, else Insert -------------------


def test_no_similars_inserts():
    assert isinstance(decide(_note(), [], A_POLICY), Insert)


def test_flag_boundary_is_inclusive():
    action = decide(_note(), [_sim(0.85)], A_POLICY)
    assert isinstance(action, Flag)


def test_above_flag_flags():
    assert isinstance(decide(_note(), [_sim(0.90)], A_POLICY), Flag)


def test_just_below_flag_inserts():
    assert isinstance(decide(_note(), [_sim(0.84)], A_POLICY), Insert)


def test_surfacing_threshold_independent_of_action_threshold():
    """HANDOFF §2: a deduper may surface a 0.82 match while flag_at=0.85; that
    candidate is still Inserted. The deduper's *surfacing* threshold and the
    policy's *action* threshold are independent -- this is a design property."""
    assert isinstance(decide(_note(), [_sim(0.82)], A_POLICY), Insert)


# --- Full B2 ladder ----------------------------------------------------------


@pytest.mark.parametrize(
    "score,expected",
    [
        (0.97, Reject),  # >= reject_at
        (0.96, Merge),   # >= merge_at, < reject_at
        (0.93, Merge),   # merge boundary inclusive
        (0.92, Flag),    # >= flag_at, < merge_at
        (0.85, Flag),    # flag boundary inclusive
        (0.84, Link),    # >= link_at, < flag_at
        (0.70, Link),    # link boundary inclusive
        (0.69, Insert),  # below everything
    ],
)
def test_full_ladder_bands(score, expected):
    assert isinstance(decide(_note(), [_sim(score)], B2_POLICY), expected)


def test_top_score_selects_band():
    """Mixed similars: the max score picks the band, not the first."""
    sims = [_sim(0.10), _sim(0.95, note_id="winner"), _sim(0.50)]
    action = decide(_note(), sims, B2_POLICY)
    assert isinstance(action, Merge)
    assert action.into_id == "winner"


def test_link_collects_only_candidates_at_or_above_link_at():
    sims = [_sim(0.80, "a"), _sim(0.72, "b"), _sim(0.40, "c")]
    action = decide(_note(), sims, B2_POLICY)
    assert isinstance(action, Link)
    assert set(action.related_ids) == {"a", "b"}  # 0.40 excluded


def test_reject_reports_conflicting_id():
    action = decide(_note(), [_sim(0.99, "boom")], B2_POLICY)
    assert isinstance(action, Reject)
    assert action.conflicting_id == "boom"
