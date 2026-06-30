"""Client-supplied idempotency key: a retry under the same run_id is a no-op.

The pain this prevents (HANDOFF §5 P1): without a key, every contribute() mints
a fresh uuid, so a retried contribution becomes a *new* note that then flags as
a duplicate of the first. With a key, the second call short-circuits.
"""

from __future__ import annotations

from vault_contrib.models import Policy, ScoredCandidate
from vault_contrib.service import ContributionService

from conftest import StubDeduper


def _service(vault, similars=None):
    return ContributionService(StubDeduper(similars), vault, Policy(flag_at=0.85))


def test_store_finds_note_by_run_id(vault):
    from vault_contrib.models import Note

    note = Note.create(title="Keyed", body="b", contributed_by="a", client_run_id="rid-7")
    vault.insert(note)
    found = vault.find_by_run_id("rid-7")
    assert found is not None and found.id == note.id


def test_find_by_run_id_misses_returns_none(vault):
    assert vault.find_by_run_id("nope") is None


def test_retry_same_run_id_is_noop(vault):
    service = _service(vault)
    first = service.contribute(
        title="Once", body="b", contributed_by="a", client_run_id="rid-1"
    )
    assert first.status == "inserted"

    second = service.contribute(
        title="Once", body="b", contributed_by="a", client_run_id="rid-1"
    )
    assert second.status == "inserted"
    assert second.note_id == first.note_id           # same note, not a new one
    assert "idempotent replay" in second.message
    assert len(list(vault.iter_notes())) == 1         # no second write


def test_retry_finds_prior_flagged_attempt(vault):
    # First attempt flags (a real near-duplicate exists); replay reports flagged
    # and points at the same note rather than creating another.
    sims = [ScoredCandidate(note_id="other", title="Other", score=0.95)]
    service = _service(vault, similars=sims)
    first = service.contribute(
        title="Dup", body="b", contributed_by="a", client_run_id="rid-2"
    )
    assert first.status == "flagged"

    second = service.contribute(
        title="Dup", body="b", contributed_by="a", client_run_id="rid-2"
    )
    assert second.status == "flagged"
    assert second.note_id == first.note_id


def test_distinct_run_ids_do_not_collide(vault):
    service = _service(vault)
    a = service.contribute(title="X", body="b", contributed_by="a", client_run_id="r-a")
    b = service.contribute(title="Y", body="b", contributed_by="a", client_run_id="r-b")
    assert a.note_id != b.note_id
    assert len(list(vault.iter_notes())) == 2


def test_no_run_id_keeps_legacy_behaviour(vault):
    # Without a key, two identical contributions are independent writes; the
    # second flags as a duplicate of the first (the pre-idempotency behaviour).
    from vault_contrib.dedup_string import StringMatchDeduper

    service = ContributionService(
        StringMatchDeduper(vault), vault, Policy(flag_at=0.85)
    )
    first = service.contribute(title="Same title", body="b", contributed_by="a")
    second = service.contribute(title="Same title", body="b", contributed_by="a")
    assert first.status == "inserted"
    assert second.status == "flagged"
