"""Domain types for the knowledge-vault contribution engine.

Everything in this module is pure data with no I/O and no knowledge of *how*
notes are stored or *how* similarity is computed. That is deliberate: these
types are the stable core that survives the eventual migration from the A
stage (git + string-match dedup) to the B2 stage (Postgres + pgvector).

B2 mapping:
    Note.to_metadata()  -> a row's columns (jsonb for tags/related_ids, or
                           join tables); `body` -> a text column; the
                           embedding becomes an extra `vector(N)` column the
                           PgVector deduper owns.
    Action variants     -> the set of operations the transactional write path
                           dispatches on. Identical types; only the executor
                           (store) changes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

SCHEMA_VERSION = 2

# The single note Type agent-vault notes carry, per the shared governance
# Type Dictionary. The engine produces only this type; the human vault's other
# types (Project, Concept, ...) are authored on the Human side.
AGENT_NOTE_TYPE = "Agent Note"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


@dataclass
class Note:
    """A single vault note. `body` is markdown; everything else is metadata."""

    id: str
    title: str
    body: str
    # Provenance of the contributor. Free-form, but namespaced by convention so
    # human and agent contributions are distinguishable: "agent:<id>" or
    # "human:<name>". Both are first-class -- humans and agents use the same
    # contribution path (validate -> dedup -> decide). Not enforced in Stage A
    # (instructed, not gated); B2's auth story turns this into a real identity.
    contributed_by: str
    created_at: str
    updated_at: str
    tags: list[str] = field(default_factory=list)
    source: str | None = None
    related_ids: list[str] = field(default_factory=list)
    # Governance Status (see Status Map -> Agent Note): "Active" | "Flagged".
    status: str = "Active"
    # Governance Type. Fixed for engine-produced notes (see AGENT_NOTE_TYPE).
    note_type: str = AGENT_NOTE_TYPE
    # Optional caller-supplied idempotency key. A retried contribution that
    # reuses the same key is a no-op (the service short-circuits) instead of
    # minting a fresh uuid that then flags as a duplicate of the first write.
    # B2 maps this to a unique-indexed column for an O(1) lookup.
    client_run_id: str | None = None
    schema_version: int = SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        title: str,
        body: str,
        contributed_by: str,
        tags: list[str] | None = None,
        source: str | None = None,
        client_run_id: str | None = None,
    ) -> "Note":
        now = _now_iso()
        return cls(
            id=_new_id(),
            title=title.strip(),
            body=body.strip(),
            contributed_by=contributed_by.strip(),
            created_at=now,
            updated_at=now,
            tags=list(tags or []),
            source=source,
            client_run_id=client_run_id,
        )

    def to_metadata(self) -> dict:
        """Everything except the body. Becomes frontmatter now, columns in B2.

        Governance-standard keys (Type, Status, CreatedAt, LastUpdated, Tags) are
        TitleCase to match the human vault's Metadata Standard; engine-owned
        plumbing (title, id, contributed_by, source, related_ids, client_run_id,
        schema_version) is documented under the Agent Note type as "do not edit".
        """
        return {
            "Type": self.note_type,
            "Status": self.status,
            "CreatedAt": self.created_at,
            "LastUpdated": self.updated_at,
            "Tags": self.tags,
            "title": self.title,
            "id": self.id,
            "contributed_by": self.contributed_by,
            "source": self.source,
            "related_ids": self.related_ids,
            "client_run_id": self.client_run_id,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_parts(cls, metadata: dict, body: str) -> "Note":
        # Read the governance-standard keys, tolerating the pre-migration
        # lowercase keys (created_at/tags/status) so a stray legacy note still
        # loads. created_at falls back for LastUpdated when older notes lack it.
        created = metadata.get("CreatedAt") or metadata.get("created_at") or _now_iso()
        return cls(
            id=metadata["id"],
            title=metadata["title"],
            body=body,
            contributed_by=metadata.get("contributed_by", "unknown"),
            created_at=created,
            updated_at=metadata.get("LastUpdated") or metadata.get("updated_at") or created,
            tags=list(metadata.get("Tags") or metadata.get("tags") or []),
            source=metadata.get("source"),
            related_ids=list(metadata.get("related_ids") or []),
            status=metadata.get("Status") or metadata.get("status") or "Active",
            note_type=metadata.get("Type") or metadata.get("note_type") or AGENT_NOTE_TYPE,
            client_run_id=metadata.get("client_run_id"),
            schema_version=metadata.get("schema_version", SCHEMA_VERSION),
        )


@dataclass
class ScoredCandidate:
    """A potential near-duplicate the deduper surfaced, with its similarity."""

    note_id: str
    title: str
    score: float  # 0.0 .. 1.0, higher = more similar


# --- Actions: the tagged union decide() returns and the store executes. ------
# All five variants are defined so they port to B2 untouched. Under the A
# policy only Insert and Flag are ever emitted (Merge/Link need real semantic
# similarity; Reject is opt-in via Policy.reject_at).


@dataclass
class Insert:
    note: Note


@dataclass
class Flag:
    note: Note
    reason: str
    similars: list[ScoredCandidate]


@dataclass
class Link:
    note: Note
    related_ids: list[str]


@dataclass
class Merge:
    into_id: str
    note: Note


@dataclass
class Reject:
    reason: str
    conflicting_id: str


Action = Insert | Flag | Link | Merge | Reject


@dataclass
class Policy:
    """Similarity thresholds -> action. This IS the vault's curation policy.

    Bands are checked high score -> low. A `None` band is disabled. The A stage
    sets only `flag_at`; the others stay None and activate for free once a
    semantic deduper produces meaningful mid-range scores in B2.

    Required ordering when set: reject_at >= merge_at >= flag_at >= link_at.
    """

    flag_at: float = 0.85
    reject_at: float | None = None
    merge_at: float | None = None
    link_at: float | None = None

    def __post_init__(self) -> None:
        bands = [
            ("reject_at", self.reject_at),
            ("merge_at", self.merge_at),
            ("flag_at", self.flag_at),
            ("link_at", self.link_at),
        ]
        present = [(n, v) for n, v in bands if v is not None]
        for (n1, v1), (n2, v2) in zip(present, present[1:]):
            if v1 < v2:
                raise ValueError(
                    f"Policy bands out of order: {n1}={v1} must be >= {n2}={v2}"
                )
        for n, v in present:
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"Policy.{n}={v} must be in [0, 1]")


@dataclass
class ContributionResult:
    """Structured outcome handed back to the caller (agent / CLI / B2 tool)."""

    status: str  # "inserted" | "flagged" | "linked" | "rejected" | "invalid"
    note_id: str | None
    message: str
    similars: list[ScoredCandidate] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
