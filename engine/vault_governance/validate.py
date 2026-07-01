"""Automated schema validation.

Answers: *is this note structurally allowed where it lives?* Severity is
graduated so the tool is usable against the existing (pre-enforcement) vault:

    ERROR   structural breakage or a hard policy violation
            (unparseable frontmatter, engine field on a Human note, a type that
            isn't allowed in its folder, a malformed Agent Note).
    WARNING governance drift worth fixing but safe to ship
            (missing/unknown Type, invalid Status, lowercase `tags`,
            non-standard keys, scalar where a list is expected).
    INFO    advisory.

Validation runs in one of three modes, chosen per folder in ``folders.yml``:
    strict  canonical Human notes — full checks.
    agent   Agent/notes & Agent/review — engine-shape enforcement.
    loose   inboxes, governance, promotion queue — structural only.

`Templates/` and `Schemas/` are not notes and are skipped entirely at the scan
layer (see ``frontmatter_scan._SKIP_DIRS``), so template placeholders never
produce findings.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .findings import Finding, Severity
from .frontmatter_scan import NoteRecord, scan_vault
from .inheritance import InheritedContext, resolve_context
from .schema import GovernanceSchema

AGENT_NOTE_TYPE = "Agent Note"
_AGENT_STATUSES = {"Active", "Flagged"}


def validate_vault(
    vault_root: Path,
    schema: GovernanceSchema,
    rel_paths: Iterable[str] | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    for rec in scan_vault(vault_root, rel_paths):
        findings.extend(validate_note(rec, schema))
    return findings


def validate_note(rec: NoteRecord, schema: GovernanceSchema) -> list[Finding]:
    ctx = resolve_context(rec.rel_path, schema)
    out: list[Finding] = []

    # --- parse failures ---------------------------------------------------
    if rec.meta is None:
        if rec.missing_frontmatter:
            # Only canonical-knowledge modes (strict/agent) treat a missing
            # frontmatter block as drift; loose areas (governance docs, inbox,
            # templates) have legitimate frontmatter-free files (READMEs).
            sev = Severity.WARNING if ctx.validation_mode in ("strict", "agent") else Severity.INFO
            out.append(Finding(rec.rel_path, sev, "no-frontmatter",
                               "note has no YAML frontmatter block"))
        else:
            out.append(Finding(rec.rel_path, Severity.ERROR, "unparseable-frontmatter",
                               rec.error or "could not parse frontmatter"))
        return out

    meta = rec.meta

    # --- duplicate keys (any mode) ---------------------------------------
    dupes = _duplicates(rec.raw_keys)
    for key in dupes:
        out.append(Finding(rec.rel_path, Severity.WARNING, "duplicate-key",
                           f"frontmatter key '{key}' appears more than once"))

    # --- structural checks (any mode) ------------------------------------
    out.extend(_check_shapes(rec.rel_path, meta, schema))

    # --- mode-specific ----------------------------------------------------
    if ctx.validation_mode == "agent":
        out.extend(_check_agent_note(rec.rel_path, meta, ctx, schema))
    elif ctx.validation_mode == "strict":
        out.extend(_check_human_canonical(rec.rel_path, meta, ctx, schema))
    # loose: structural checks only.

    return out


# --------------------------------------------------------------------------
# Structural (mode-independent)
# --------------------------------------------------------------------------

def _check_shapes(path: str, meta: dict, schema: GovernanceSchema) -> list[Finding]:
    out: list[Finding] = []
    for key in schema.list_properties:
        val = meta.get(key)
        if val is not None and not isinstance(val, (list, tuple)):
            out.append(Finding(path, Severity.WARNING, "list-shape",
                               f"'{key}' should be a list, found a scalar ({val!r})"))
    for key in schema.datetime_properties:
        val = meta.get(key)
        if val not in (None, "") and not _is_iso8601(val):
            out.append(Finding(path, Severity.WARNING, "bad-datetime",
                               f"'{key}'={val!r} is not an ISO-8601 datetime"))
    return out


# --------------------------------------------------------------------------
# Agent Note mode (engine-managed)
# --------------------------------------------------------------------------

def _check_agent_note(path: str, meta: dict, ctx: InheritedContext,
                      schema: GovernanceSchema) -> list[Finding]:
    out: list[Finding] = []
    note_type = meta.get("Type")
    if note_type != AGENT_NOTE_TYPE:
        out.append(Finding(path, Severity.ERROR, "agent-type",
                           f"Agent layer note must be Type '{AGENT_NOTE_TYPE}', found {note_type!r}"))

    status = meta.get("Status")
    if status not in _AGENT_STATUSES:
        out.append(Finding(path, Severity.ERROR, "agent-status",
                           f"Agent Note Status must be one of {sorted(_AGENT_STATUSES)}, found {status!r}"))

    ts = schema.types.get(AGENT_NOTE_TYPE)
    for key in (ts.required if ts else []):
        if meta.get(key) in (None, ""):
            out.append(Finding(path, Severity.ERROR, "agent-missing-field",
                               f"engine field '{key}' is required on an Agent Note"))

    note_id = meta.get("ID")
    if note_id and not _looks_hex(note_id):
        out.append(Finding(path, Severity.WARNING, "agent-id",
                           f"ID {note_id!r} does not look like an engine hex id"))

    cb = meta.get("ContributedBy")
    if cb and not (str(cb).startswith("agent:") or str(cb).startswith("human:")):
        out.append(Finding(path, Severity.WARNING, "agent-provenance",
                           f"ContributedBy {cb!r} should be namespaced 'agent:<id>' or 'human:<name>'"))

    sv = meta.get("SchemaVersion")
    if sv is not None and sv != 2:
        out.append(Finding(path, Severity.WARNING, "agent-schema-version",
                           f"SchemaVersion is {sv!r}; current engine schema is 2"))
    return out


# --------------------------------------------------------------------------
# Human canonical mode (strict)
# --------------------------------------------------------------------------

def _check_human_canonical(path: str, meta: dict, ctx: InheritedContext,
                           schema: GovernanceSchema) -> list[Finding]:
    out: list[Finding] = []

    # Engine plumbing must never appear on a canonical Human note — that means an
    # Agent note was copied in verbatim instead of being rewritten (Promotion
    # Policy). This is a hard error.
    leaked = [k for k in schema.engine_owned_properties if k in meta]
    if leaked:
        out.append(Finding(path, Severity.ERROR, "engine-field-in-human",
                           f"engine-owned field(s) {leaked} on a canonical Human note; "
                           "promoted Agent memory must be rewritten as a Human note, not copied"))

    raw_type = meta.get("Type")
    canon = schema.canonical_type(raw_type)

    # Type presence / validity
    if raw_type in (None, ""):
        hint = f"; folder default is '{ctx.default_type}'" if ctx.default_type else ""
        out.append(Finding(path, Severity.WARNING, "missing-type",
                           f"canonical note has no Type{hint}"))
    elif canon is None:
        sugg = schema.suggest_type(raw_type)
        tail = f"; did you mean '{sugg}'?" if sugg else ""
        out.append(Finding(path, Severity.WARNING, "unknown-type",
                           f"Type {raw_type!r} is not in the Type Dictionary{tail}"))
    elif schema.is_alias(raw_type):
        out.append(Finding(path, Severity.WARNING, "drifted-type",
                           f"Type {raw_type!r} is a drifted spelling of '{canon}'"))

    # Type vs folder. Universal types (folder_globs ['**'], e.g. Note/MoC) may
    # live in any folder, so they are exempt from allowed_types / default_type.
    canon_ts = schema.types.get(canon) if canon else None
    if canon and not (canon_ts and canon_ts.universal):
        if ctx.allowed_types and canon not in ctx.allowed_types:
            out.append(Finding(path, Severity.ERROR, "type-not-allowed",
                               f"Type '{canon}' is not allowed in this folder "
                               f"(allowed: {ctx.allowed_types})"))
        elif ctx.default_type and canon != ctx.default_type and canon not in ctx.allowed_types:
            out.append(Finding(path, Severity.WARNING, "type-folder-mismatch",
                               f"Type '{canon}' does not match the folder's default '{ctx.default_type}'"))

    # Status valid for type
    ts = schema.type_for(raw_type)
    status = meta.get("Status")
    if ts and ts.has_lifecycle and status not in (None, ""):
        if status not in ts.statuses:
            out.append(Finding(path, Severity.WARNING, "invalid-status",
                               f"Status {status!r} is not valid for Type '{ts.name}' "
                               f"(allowed: {ts.statuses})"))

    # Key hygiene: legacy spellings, known-but-nonstandard keys, unknown keys.
    out.extend(_check_keys(path, meta, ts, schema))
    return out


def _check_keys(path: str, meta: dict, ts, schema: GovernanceSchema) -> list[Finding]:
    out: list[Finding] = []
    known = set(schema.universal_properties)
    if ts:
        known.update(ts.required)
        known.update(ts.recommended)
    for key in meta:
        if key in known or key in schema.engine_owned_properties:
            continue
        if key in schema.legacy_renames:
            out.append(Finding(path, Severity.WARNING, "legacy-key",
                               f"'{key}' is a legacy/drifted key; standard key is "
                               f"'{schema.legacy_renames[key]}'"))
        elif key in schema.known_extra_keys:
            sugg = schema.known_extra_keys[key]
            tail = f"; consider standard '{sugg}'" if sugg else ""
            out.append(Finding(path, Severity.INFO, "nonstandard-key",
                               f"'{key}' is a known non-standard key{tail}"))
        else:
            out.append(Finding(path, Severity.WARNING, "unknown-key",
                               f"'{key}' is not a recognized property"))
    return out


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _duplicates(keys: list[str]) -> list[str]:
    seen, dupes = set(), []
    for k in keys:
        if k in seen and k not in dupes:
            dupes.append(k)
        seen.add(k)
    return dupes


def _is_iso8601(value: Any) -> bool:
    if isinstance(value, datetime):
        return True
    if not isinstance(value, str):
        return False
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        datetime.fromisoformat(text)
        return True
    except ValueError:
        # tolerate a bare date already covered by fromisoformat; anything else fails
        return False


def _looks_hex(value: Any) -> bool:
    s = str(value)
    return len(s) >= 8 and all(c in "0123456789abcdefABCDEF" for c in s)
