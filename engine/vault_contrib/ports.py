"""The seams. These two Protocols are the entire B2 migration surface.

A stage implements them as `StringMatchDeduper` (dedup_string.py) and
`GitMarkdownStore` (store_git.py). B2 implements them as `PgVectorDeduper`
and `PostgresStore` -- new files, same Protocols, zero changes here or in
core.py / service.py. The only edit at migration time is the wiring line in
cli.py (the composition root) that picks which concrete classes to construct.
"""

from __future__ import annotations

from typing import Iterable, Protocol, runtime_checkable

from .models import Note, ScoredCandidate


@runtime_checkable
class Deduper(Protocol):
    """Surfaces existing notes similar to a candidate, with similarity scores.

    A impl  : normalize titles and string-match (no embeddings).
    B2 impl : embed the candidate, then ANN-query a pgvector column.

    Migration note on the transaction boundary: in B2 the *embed* step calls an
    external API and must NOT happen inside a DB transaction. So a B2 deduper
    embeds eagerly inside find_similar() but runs only the cheap ANN query
    there if you split it; the service already calls find_similar() *before*
    any write, so hoisting embedding ahead of a future transaction is a local
    change confined to the deduper + service, not the core logic.
    """

    def find_similar(self, candidate: Note) -> list[ScoredCandidate]:
        ...


@runtime_checkable
class Store(Protocol):
    """Persistence only -- no similarity logic lives here.

    A impl  : markdown files in a git repo, auto-committed.
    B2 impl : rows in Postgres; each method becomes SQL inside the caller's
              transaction. The method *set* is intentionally small so the SQL
              port is mechanical.
    """

    def insert(self, note: Note) -> None: ...

    def get(self, note_id: str) -> Note | None: ...

    def find_by_run_id(self, run_id: str) -> Note | None:
        """Return the note previously written under this idempotency key, if any.

        Supports the service's retry short-circuit. A impl scans the corpus
        (notes + review); B2 impl is an O(1) lookup on a unique-indexed column.
        """
        ...

    def update(self, note: Note) -> None: ...

    def iter_notes(self) -> Iterable[Note]: ...

    def add_to_review(
        self, note: Note, reason: str, similars: list[ScoredCandidate]
    ) -> None: ...
