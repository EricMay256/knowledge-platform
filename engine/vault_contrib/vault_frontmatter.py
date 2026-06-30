"""Canonical frontmatter serialization for vault markdown notes.

This is the single source of truth for active-note YAML style in the Stage-A
git/markdown store. It intentionally handles only the scalar/list schema used
by notes; transient review metadata with nested values is serialized separately.
"""

from __future__ import annotations

import re
from typing import Any

import yaml

# Governance-standard keys first (human Metadata Standard order), then the
# engine-owned plumbing the Agent Note type documents as "do not edit".
SCHEMA_ORDER = [
    "Type",
    "Status",
    "CreatedAt",
    "LastUpdated",
    "Tags",
    "title",
    "id",
    "contributed_by",
    "source",
    "related_ids",
    "client_run_id",
    "schema_version",
]

LIST_FIELDS = {"Tags", "related_ids"}


class _VaultLoader(yaml.SafeLoader):
    pass


_VaultLoader.add_constructor(
    "tag:yaml.org,2002:timestamp",
    lambda loader, node: loader.construct_scalar(node),
)

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)\Z", re.DOTALL)
_RESERVED = {"true", "false", "yes", "no", "on", "off", "null", "none", "~", ""}


def split_frontmatter(text: str) -> tuple[str, str]:
    """Return the raw YAML frontmatter and markdown body."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError("note has no leading '---' frontmatter block")
    return match.group(1), match.group(2)


def load_note(text: str) -> tuple[dict[str, Any], str]:
    """Parse a note string into metadata and body, keeping timestamps as strings."""
    raw_yaml, body = split_frontmatter(text)
    meta = yaml.load(raw_yaml, Loader=_VaultLoader) or {}
    if not isinstance(meta, dict):
        raise ValueError("frontmatter did not parse to a mapping")
    return meta, body


def _needs_quote(value: str) -> bool:
    if value == "":
        return False
    if value.lower() in _RESERVED:
        return True
    if value != value.strip():
        return True
    if value[0] in "!&*?|>%@`\"'#,[]{}" or value[:2] in ("- ", "? ", ": "):
        return True
    if ": " in value or value.endswith(":") or " #" in value or '"' in value:
        return True
    if re.fullmatch(r"[+-]?(\d[\d_]*\.?\d*|\.\d+)([eE][+-]?\d+)?", value):
        return True
    return False


def _quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    text = str(value)
    return _quote(text) if _needs_quote(text) else text


def _render_pair(key: str, value: Any) -> str:
    if key in LIST_FIELDS or isinstance(value, (list, tuple)):
        items = list(value or [])
        if not items:
            return f"{key}: []"
        return "\n".join([f"{key}:"] + [f"  - {_scalar(item)}" for item in items])

    rendered = _scalar(value)
    return f"{key}:" if rendered == "" else f"{key}: {rendered}"


def render_frontmatter(meta: dict[str, Any], order: list[str] | None = None) -> str:
    """Render metadata to canonical YAML, without surrounding delimiters.

    `order` lists the keys that should come first, in that order; any remaining
    keys are appended alphabetically. Defaults to the Agent-note SCHEMA_ORDER so
    existing callers are unaffected; the governance linter passes a Human-note
    order instead.
    """
    order = SCHEMA_ORDER if order is None else order
    keys = [key for key in order if key in meta]
    keys += sorted(key for key in meta if key not in order)
    return "\n".join(_render_pair(key, meta[key]) for key in keys)


def dump_note(meta: dict[str, Any], body: str, order: list[str] | None = None) -> str:
    """Serialize metadata and body into a full markdown note."""
    frontmatter = render_frontmatter(meta, order)
    body = body if body.endswith("\n") or body == "" else body + "\n"
    return f"---\n{frontmatter}\n---\n{body}"


def canonicalize(text: str) -> str:
    """Return a canonicalized note string. Idempotent on canonical input."""
    meta, body = load_note(text)
    return dump_note(meta, body)
