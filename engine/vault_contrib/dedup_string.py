"""A-stage deduper: crude string/title matching. THROWAWAY at B2.

Replaced wholesale by a `PgVectorDeduper` that embeds the candidate and runs an
ANN query. Nothing else in the package references this class by name except the
composition root (cli.py), so swapping it is a one-line change there.

Default behaviour is exact-normalized-title match only (score 1.0 or nothing),
which is all the A stage needs. An optional `fuzzy_threshold` enables a cheap
difflib ratio so you can exercise the policy's mid-range bands (Flag/Link)
before real embeddings exist -- useful for testing decide() end to end.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from .models import Note, ScoredCandidate
from .ports import Store

_PUNCT = re.compile(r"[^\w\s]")
_WS = re.compile(r"\s+")


def _normalize(title: str) -> str:
    t = _PUNCT.sub("", title)
    t = _WS.sub(" ", t)
    return t.strip().lower()


class StringMatchDeduper:
    """Satisfies the Deduper Protocol using only the local note corpus.

    Note this scans every existing note via store.iter_notes(). That is fine at
    the small scale the A stage targets and is precisely the part that does NOT
    port -- the B2 deduper never iterates the corpus; it issues an indexed ANN
    query instead.
    """

    def __init__(self, store: Store, fuzzy_threshold: float | None = None) -> None:
        self._store = store
        self._fuzzy_threshold = fuzzy_threshold

    def find_similar(self, candidate: Note) -> list[ScoredCandidate]:
        cand_norm = _normalize(candidate.title)
        out: list[ScoredCandidate] = []
        for existing in self._store.iter_notes():
            if existing.id == candidate.id:
                continue
            existing_norm = _normalize(existing.title)
            if existing_norm == cand_norm:
                score = 1.0
            elif self._fuzzy_threshold is not None:
                score = SequenceMatcher(None, cand_norm, existing_norm).ratio()
                if score < self._fuzzy_threshold:
                    continue
            else:
                continue
            out.append(
                ScoredCandidate(
                    note_id=existing.id, title=existing.title, score=score
                )
            )
        out.sort(key=lambda c: c.score, reverse=True)
        return out
