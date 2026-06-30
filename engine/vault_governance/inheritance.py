"""Property inheritance: what a note inherits from *where it lives* and from its
declared `Parent`s, without writing any of it into the note's frontmatter.

Two senses of inheritance, both non-destructive:

1. Location-implied context (`resolve_context`): a note's layer, canonicality,
   AI-write policy, default Type, and validation mode follow from its folder.
   This is the workhorse the validator uses. Nothing is materialized — Obsidian
   never sees these fields; they are computed on read.

2. Parent-chain properties (`resolve_inherited_properties`): a note with
   ``Parent: [[X]]`` inherits designated properties (e.g. the union of Tags)
   from its parents. Used to surface "child contradicts/duplicates parent"
   rather than to rewrite notes. The current vault uses `Related` far more than
   `Parent`, so this mostly matters going forward.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .schema import FolderRule, GovernanceSchema

# Properties a child note inherits from its Parent chain. Tags accumulate
# (union); the rest are single-valued and taken from the nearest parent that
# sets them. Conservative on purpose.
INHERITABLE_UNION = ("Tags",)
INHERITABLE_SINGLE = ("Area", "Domain", "ReviewFreq")

_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)")


@dataclass
class InheritedContext:
    """Location-implied context for one note. Derived, never serialized."""

    path: str
    layer: str | None = None
    canonical: bool | None = None
    engine_managed: bool = False
    ai_write: str | None = None
    default_type: str | None = None
    allowed_types: list[str] = field(default_factory=list)
    validation_mode: str = "loose"
    purpose: str | None = None
    # the folder rules that contributed, least- to most-specific (provenance)
    applied_globs: list[str] = field(default_factory=list)


def resolve_context(rel_path: str, schema: GovernanceSchema) -> InheritedContext:
    """Resolve a note's inherited context by overlaying the default rule with
    every matching folder rule, most-specific last (so the deepest folder wins).
    """
    ctx = InheritedContext(path=rel_path)
    _overlay(ctx, schema.folder_default)
    for rule in schema.matching_rules(rel_path):
        _overlay(ctx, rule)
        ctx.applied_globs.append(rule.glob)
    return ctx


def _overlay(ctx: InheritedContext, rule: FolderRule) -> None:
    ctx.layer = rule.layer
    ctx.canonical = rule.canonical
    ctx.engine_managed = rule.engine_managed
    ctx.ai_write = rule.ai_write
    ctx.validation_mode = rule.validation_mode
    # default_type / allowed_types / purpose only override when the rule sets them
    if rule.default_type is not None:
        ctx.default_type = rule.default_type
    if rule.allowed_types:
        ctx.allowed_types = list(rule.allowed_types)
    if rule.purpose is not None:
        ctx.purpose = rule.purpose


def parent_links(meta: dict[str, Any]) -> list[str]:
    """The note titles a note's `Parent` property points at (wikilink targets)."""
    raw = meta.get("Parent")
    if not raw:
        return []
    items = raw if isinstance(raw, (list, tuple)) else [raw]
    out: list[str] = []
    for item in items:
        m = _WIKILINK_RE.search(str(item))
        out.append((m.group(1) if m else str(item)).strip())
    return out


def resolve_inherited_properties(
    meta: dict[str, Any],
    parents_by_title: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Compute the properties `meta` inherits from its Parent chain.

    `parents_by_title` maps a note title to that note's already-resolved
    effective metadata, so the walk is a single lookup per parent (callers
    resolve bottom-up). Cycles are broken by the visited set.
    """
    inherited: dict[str, Any] = {}
    union: dict[str, list] = {key: [] for key in INHERITABLE_UNION}
    visited: set[str] = set()

    stack = list(parent_links(meta))
    while stack:
        title = stack.pop(0)
        if title in visited:
            continue
        visited.add(title)
        pmeta = parents_by_title.get(title)
        if pmeta is None:
            continue
        for key in INHERITABLE_UNION:
            for v in _as_list(pmeta.get(key)):
                if v not in union[key]:
                    union[key].append(v)
        for key in INHERITABLE_SINGLE:
            if key not in inherited and pmeta.get(key) not in (None, "", []):
                inherited[key] = pmeta[key]
        stack.extend(parent_links(pmeta))

    for key, vals in union.items():
        if vals:
            inherited[key] = vals
    return inherited


def effective_properties(
    meta: dict[str, Any],
    parents_by_title: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """A note's own properties overlaid on what it inherits (explicit wins;
    Tags are unioned). Read-time view only."""
    inherited = resolve_inherited_properties(meta, parents_by_title)
    eff = dict(inherited)
    for key, val in meta.items():
        if key in INHERITABLE_UNION:
            merged = list(inherited.get(key, []))
            for v in _as_list(val):
                if v not in merged:
                    merged.append(v)
            eff[key] = merged
        elif val not in (None, "", []):
            eff[key] = val
    return eff


def _as_list(val: Any) -> list:
    if val is None:
        return []
    return list(val) if isinstance(val, (list, tuple)) else [val]
