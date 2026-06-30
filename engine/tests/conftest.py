"""Shared fixtures.

Kept deliberately small: a real git-backed store over a tmp dir, a Note factory
that mirrors the production construction path (Note.create), and a StubDeduper
that returns preset scores so decide()/service tests control the input precisely.
"""

from __future__ import annotations

import pytest

from vault_contrib.models import Note, ScoredCandidate
from vault_contrib.store_git import GitMarkdownStore


@pytest.fixture
def vault(tmp_path):
    """A fresh git-backed store rooted at a tmp directory."""
    return GitMarkdownStore(tmp_path)


@pytest.fixture
def make_note():
    """Factory building Notes through the real Note.create path."""

    def _make(
        title="A title",
        body="A sufficiently real body.",
        contributed_by="agent-1",
        tags=None,
        source=None,
        client_run_id=None,
    ):
        return Note.create(
            title=title,
            body=body,
            contributed_by=contributed_by,
            tags=tags,
            source=source,
            client_run_id=client_run_id,
        )

    return _make


class StubDeduper:
    """Satisfies the Deduper Protocol; returns a fixed candidate list.

    Lets decide()/service tests feed exact similarity scores without depending
    on the string matcher's behaviour.
    """

    def __init__(self, similars: list[ScoredCandidate] | None = None) -> None:
        self._similars = similars or []

    def find_similar(self, candidate):  # noqa: ARG002 - candidate unused by design
        return list(self._similars)


@pytest.fixture
def stub_deduper():
    return StubDeduper
