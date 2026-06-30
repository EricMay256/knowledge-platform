"""ContributionService — the outcome contract agents branch on."""

from __future__ import annotations

import pytest

from vault_contrib.models import Policy, ScoredCandidate
from vault_contrib.service import ContributionService

from conftest import StubDeduper


def _service(vault, similars=None, policy=None):
    return ContributionService(
        StubDeduper(similars), vault, policy or Policy(flag_at=0.85)
    )


def test_clean_note_inserted(vault):
    res = _service(vault).contribute(
        title="Fresh", body="real body", contributed_by="agent-1"
    )
    assert res.status == "inserted"
    assert vault.get(res.note_id) is not None


def test_duplicate_flagged_to_review(vault):
    sims = [ScoredCandidate(note_id="other", title="Other", score=0.95)]
    res = _service(vault, similars=sims).contribute(
        title="Dup", body="b", contributed_by="agent-1"
    )
    assert res.status == "flagged"
    # Lives in review/ (by title slug), not notes/.
    assert vault.get(res.note_id) is None
    assert (vault.review_dir / "dup.md").exists()


def test_invalid_note_writes_nothing(vault):
    res = _service(vault).contribute(title="No body", body="   ", contributed_by="a")
    assert res.status == "invalid"
    assert res.note_id is None
    assert res.errors
    assert list(vault.iter_notes()) == []


def test_human_contributor_uses_same_path(vault):
    # Human input is first-class: a "human:<name>" contributor flows through the
    # same validate -> dedup -> decide path and lands as a normal note.
    res = _service(vault).contribute(
        title="Hand-written insight", body="A human wrote this.",
        contributed_by="human:yarom",
    )
    assert res.status == "inserted"
    assert vault.get(res.note_id).contributed_by == "human:yarom"


def test_human_contribution_is_deduped_like_an_agent(vault):
    # Humans get dedup too: a human re-adding what an agent already wrote flags.
    sims = [ScoredCandidate(note_id="agent-note", title="Existing", score=0.95)]
    res = _service(vault, similars=sims).contribute(
        title="Existing", body="b", contributed_by="human:yarom",
    )
    assert res.status == "flagged"


def test_merge_band_is_not_implemented(vault):
    # A B2-tuned policy on the A store reaching the Merge band must raise the
    # documented NotImplementedError rather than silently mis-handling it.
    sims = [ScoredCandidate(note_id="x", title="X", score=0.95)]
    service = _service(vault, similars=sims, policy=Policy(merge_at=0.93, flag_at=0.85))
    with pytest.raises(NotImplementedError):
        service.contribute(title="Merge me", body="b", contributed_by="a")
