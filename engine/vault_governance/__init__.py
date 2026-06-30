"""Whole-vault governance enforcement: property inheritance, schema validation,
and metadata linting.

This package sits *beside* ``vault_contrib`` (the Agent-note contribution engine)
and is deliberately separate from it:

    vault_contrib    -> contributions INTO Agent/notes (validate -> dedup ->
                        decide -> write). Owns the B2 migration seams; untouched.
    vault_governance -> metadata correctness ACROSS the whole Vault/
                        (inheritance -> validation -> linting -> policy).

It reuses ``vault_contrib.vault_frontmatter`` as the single canonical YAML
serializer rather than parsing notes a second way, but never reaches into the
contribution engine's storage/dedup internals.

Governance rules are read from machine-readable schemas under
``Vault/00 Governance/Schemas/`` (see that folder's README), which mirror the
prose governance docs.
"""

from __future__ import annotations

from .findings import Finding, Severity
from .schema import GovernanceSchema

__all__ = ["Finding", "Severity", "GovernanceSchema"]
