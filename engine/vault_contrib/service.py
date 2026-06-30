"""The orchestrator. Its call sequence is the thing that becomes the B2 MCP
tool handler, so it is kept storage- and dedup-agnostic: it depends only on the
Deduper and Store Protocols plus the pure core functions.

B2 migration of THIS file is minimal and mechanical:
    1. Wrap the find_similar -> decide -> execute span in a DB transaction.
    2. Ensure embedding (now inside the deduper) is hoisted to run *before*
       the transaction opens (see ports.Deduper migration note).
The four-step body below stays the same; only a `with transaction:` and the
embed hoist are added.
"""

from __future__ import annotations

from .core import decide, validate
from .models import (
    ContributionResult,
    Flag,
    Insert,
    Link,
    Merge,
    Note,
    Policy,
    Reject,
)
from .ports import Deduper, Store


class ContributionService:
    def __init__(self, deduper: Deduper, store: Store, policy: Policy) -> None:
        self._deduper = deduper
        self._store = store
        self._policy = policy

    def contribute(
        self,
        *,
        title: str,
        body: str,
        contributed_by: str,
        tags: list[str] | None = None,
        source: str | None = None,
        client_run_id: str | None = None,
    ) -> ContributionResult:
        # 0. idempotency: a retry under a known key is a no-op, not a new note
        #    that would then flag as a duplicate of the first attempt. Checked
        #    before any write. (B2: this lookup becomes an indexed SELECT and
        #    the whole contribute() body runs inside one transaction, so the
        #    check-then-write is atomic; in A it is best-effort.)
        if client_run_id is not None:
            prior = self._store.find_by_run_id(client_run_id)
            if prior is not None:
                replay_status = "flagged" if prior.status == "Flagged" else "inserted"
                return ContributionResult(
                    status=replay_status,
                    note_id=prior.id,
                    message=f"idempotent replay: run_id {client_run_id!r} already contributed",
                )

        # 1. build + validate
        note = Note.create(
            title=title,
            body=body,
            contributed_by=contributed_by,
            tags=tags,
            source=source,
            client_run_id=client_run_id,
        )
        errors = validate(note)
        if errors:
            return ContributionResult(
                status="invalid",
                note_id=None,
                message="contribution failed validation",
                errors=errors,
            )

        # 2. find similar  (B2: embed happens here, before any transaction)
        similars = self._deduper.find_similar(note)

        # 3. decide  (pure; identical in A and B2)
        action = decide(note, similars, self._policy)

        # 4. execute  (B2: this span runs inside one transaction)
        match action:
            case Insert(note=n):
                self._store.insert(n)
                return ContributionResult(
                    status="inserted",
                    note_id=n.id,
                    message="note added to vault",
                    similars=similars,
                )
            case Flag(note=n, reason=reason, similars=sims):
                self._store.add_to_review(n, reason, sims)
                return ContributionResult(
                    status="flagged",
                    note_id=n.id,
                    message=f"flagged for review: {reason}",
                    similars=sims,
                )
            case Link(note=n, related_ids=related):
                n.related_ids = related
                self._store.insert(n)
                return ContributionResult(
                    status="linked",
                    note_id=n.id,
                    message=f"added and linked to {len(related)} related note(s)",
                    similars=similars,
                )
            case Reject(reason=reason, conflicting_id=cid):
                return ContributionResult(
                    status="rejected",
                    note_id=None,
                    message=f"rejected: {reason} (conflicts with {cid})",
                    similars=similars,
                )
            case Merge():
                # Genuinely hard and explicitly deferred to B2 (needs semantic
                # similarity + a real merge strategy). The A policy never emits
                # this, so reaching here means a B2-tuned policy on the A store.
                raise NotImplementedError(
                    "Merge requires semantic dedup; deferred to the B2 stage"
                )
