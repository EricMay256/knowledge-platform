"""Metadata linting.

Answers: *can this note's metadata be normalized safely?* Linting is the
style/normalization counterpart to validation. It is a thin layer over the
canonical serializer in ``vault_contrib.vault_frontmatter`` plus governance-aware
key normalization.

Scope of ``--fix`` honours the AI write policy: it rewrites only Agent-layer and
non-canonical notes. Canonical Human notes (and the governance docs) are
*reported* but never auto-written — a human normalizes those deliberately.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from vault_contrib import vault_frontmatter as vf

from .findings import Finding, Severity
from .frontmatter_scan import NoteRecord, scan_vault
from .inheritance import InheritedContext, resolve_context
from .schema import GovernanceSchema

# Canonical key order for Human-side notes (governance Metadata Standard order).
# Agent notes use the engine's own order (vf.SCHEMA_ORDER).
GOVERNANCE_ORDER = [
    "Type", "Status", "CreatedAt", "LastUpdated",
    "Tags", "Aliases", "ReviewFreq", "Parent", "DependsOn", "SeeAlso",
]


@dataclass
class LintResult:
    rel_path: str
    writable: bool
    changed: bool
    findings: list[Finding] = field(default_factory=list)
    new_text: str | None = None


def is_writable(ctx: InheritedContext) -> bool:
    """`--fix` may rewrite Agent-layer notes and non-canonical Human notes, but
    never canonical Human notes or the governance layer (docs/templates)."""
    if ctx.layer == "agent":
        return True
    return (not ctx.canonical) and ctx.layer != "governance"


def lint_vault(
    vault_root: Path,
    schema: GovernanceSchema,
    fix: bool = False,
    rel_paths: Iterable[str] | None = None,
) -> list[LintResult]:
    results: list[LintResult] = []
    for rec in scan_vault(vault_root, rel_paths):
        res = lint_note(rec, schema)
        if fix and res.changed and res.writable and res.new_text is not None:
            rec.abs_path.write_text(res.new_text, encoding="utf-8")
        results.append(res)
    return results


def lint_note(rec: NoteRecord, schema: GovernanceSchema) -> LintResult:
    ctx = resolve_context(rec.rel_path, schema)
    writable = is_writable(ctx)

    if rec.meta is None or rec.body is None:
        # Nothing to normalize on an unparseable note; validation reports it.
        return LintResult(rec.rel_path, writable, changed=False)

    meta = dict(rec.meta)
    findings: list[Finding] = []
    # Non-writable notes are report-only: surface drift at INFO so --check stays
    # green on the (currently messy) Human back-catalogue until it is cleaned.
    actionable = Severity.WARNING if writable else Severity.INFO

    _normalize_keys(rec.rel_path, meta, schema, findings, actionable)
    _normalize_lists(rec.rel_path, meta, schema, findings, actionable)

    order = vf.SCHEMA_ORDER if ctx.layer == "agent" else GOVERNANCE_ORDER
    new_text = vf.dump_note(meta, rec.body, order=order)
    changed = new_text != rec.text
    if changed and not findings:
        findings.append(Finding(rec.rel_path, Severity.INFO, "reformat",
                               "frontmatter would be reformatted (key order / quoting)"))

    return LintResult(rec.rel_path, writable, changed, findings, new_text if changed else None)


def _normalize_keys(path: str, meta: dict, schema: GovernanceSchema,
                    findings: list[Finding], sev: Severity) -> None:
    """Rewrite legacy/drifted keys to their canonical spelling, in place."""
    for old, new in schema.legacy_renames.items():
        if old not in meta:
            continue
        if new in meta and new != old:
            # Both present — keep the canonical one, drop the legacy duplicate.
            meta.pop(old)
            findings.append(Finding(path, sev, "lint-key-conflict",
                                   f"dropped legacy '{old}' ('{new}' already present)"))
        else:
            meta[new] = meta.pop(old)
            findings.append(Finding(path, sev, "lint-key-rename",
                                   f"renamed '{old}' -> '{new}'"))


def _normalize_lists(path: str, meta: dict, schema: GovernanceSchema,
                     findings: list[Finding], sev: Severity) -> None:
    """Wrap scalars into lists and de-duplicate list values, in place."""
    for key in schema.list_properties:
        if key not in meta:
            continue
        val = meta[key]
        if val is None:
            continue
        if not isinstance(val, (list, tuple)):
            meta[key] = [val]
            findings.append(Finding(path, sev, "lint-list-shape",
                                   f"wrapped scalar '{key}' into a list"))
            continue
        deduped = _dedup(list(val))
        if len(deduped) != len(val):
            meta[key] = deduped
            findings.append(Finding(path, sev, "lint-dedup",
                                   f"removed duplicate values from '{key}'"))


def _dedup(items: list[Any]) -> list[Any]:
    seen, out = set(), []
    for it in items:
        key = it if isinstance(it, (str, int, float, bool)) else repr(it)
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out
