"""Shared fixtures.

Kept deliberately small: a real git-backed store over a tmp dir, a Note factory
that mirrors the production construction path (Note.create), and a StubDeduper
that returns preset scores so decide()/service tests control the input precisely.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from vault_contrib.models import Note, ScoredCandidate
from vault_contrib.store_git import GitMarkdownStore

# --- governance fixtures --------------------------------------------------

REPO_VAULT = Path(__file__).resolve().parents[2] / "Vault"
REPO_SCHEMAS = REPO_VAULT / "00 Governance" / "Schemas"


@pytest.fixture
def gov_schema():
    """The real governance schema loaded from the repo's Vault."""
    from vault_governance.schema import GovernanceSchema

    if not REPO_SCHEMAS.exists():
        pytest.skip("repo Vault schemas not found")
    return GovernanceSchema.load(REPO_VAULT)


@pytest.fixture
def temp_vault(tmp_path):
    """An empty temp Vault with the real Schemas copied in, plus a note writer.

    Returns (vault_root, write) where write(rel_path, text) creates a note and
    returns its absolute Path.
    """
    vault = tmp_path / "Vault"
    schemas_dst = vault / "00 Governance" / "Schemas"
    schemas_dst.parent.mkdir(parents=True)
    shutil.copytree(REPO_SCHEMAS, schemas_dst)

    def write(rel_path: str, text: str) -> Path:
        p = vault / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    return vault, write


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
