"""Pure decision logic: validate() and decide(). No I/O, ports to B2 verbatim.

These are the functions you most want to get right and least want to rewrite,
so they are deliberately free of any storage or embedding concerns. decide()
takes a candidate plus whatever the deduper surfaced and returns an Action; it
neither knows nor cares whether the scores came from string matching or cosine
distance.
"""

from __future__ import annotations

from .models import (
    Action,
    Flag,
    Insert,
    Link,
    Merge,
    Note,
    Policy,
    Reject,
    ScoredCandidate,
)

MIN_BODY_CHARS = 1


def validate(note: Note) -> list[str]:
    """Return a list of human-readable validation errors (empty == valid)."""
    errors: list[str] = []
    if not note.title.strip():
        errors.append("title must not be empty")
    if len(note.body.strip()) < MIN_BODY_CHARS:
        errors.append("body must not be empty")
    if not note.contributed_by.strip():
        errors.append("contributed_by must be set (which agent is writing?)")
    for tag in note.tags:
        if not isinstance(tag, str) or not tag.strip():
            errors.append(f"invalid tag: {tag!r} (tags must be non-empty strings)")
    if len(note.tags) != len(set(note.tags)):
        errors.append("duplicate tags are not allowed")
    return errors


def decide(
    candidate: Note,
    similars: list[ScoredCandidate],
    policy: Policy,
) -> Action:
    """Map the top similarity score to an Action via the policy bands.

    Bands are evaluated strongest-match-first. Disabled (None) bands are
    skipped, so the A policy -- which sets only `flag_at` -- collapses to:
    exact-ish duplicate -> Flag, otherwise -> Insert. Setting merge_at /
    link_at in B2 lights up those branches with no change here.
    """
    if not similars:
        return Insert(note=candidate)

    top = max(similars, key=lambda c: c.score)
    s = top.score

    if policy.reject_at is not None and s >= policy.reject_at:
        return Reject(
            reason=f"near-identical to existing note (score={s:.3f})",
            conflicting_id=top.note_id,
        )

    if policy.merge_at is not None and s >= policy.merge_at:
        return Merge(into_id=top.note_id, note=candidate)

    if s >= policy.flag_at:
        return Flag(
            note=candidate,
            reason=f"possible duplicate of {top.note_id} (score={s:.3f})",
            similars=similars,
        )

    if policy.link_at is not None and s >= policy.link_at:
        related = [c.note_id for c in similars if c.score >= policy.link_at]
        return Link(note=candidate, related_ids=related)

    return Insert(note=candidate)
