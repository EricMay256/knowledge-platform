"""Load the machine-readable governance schemas and expose them as typed objects.

The YAML lives in ``<vault>/00 Governance/Schemas/`` (global.yml, types.yml,
folders.yml). This module is the only place that knows that layout; everything
else takes a `GovernanceSchema`.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SCHEMAS_SUBDIR = ("00 Governance", "Schemas")


@dataclass(frozen=True)
class TypeSchema:
    name: str
    folder_globs: list[str] = field(default_factory=list)
    statuses: list[str] = field(default_factory=list)
    required: list[str] = field(default_factory=list)
    recommended: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)

    @property
    def has_lifecycle(self) -> bool:
        return bool(self.statuses)


@dataclass(frozen=True)
class FolderRule:
    glob: str
    layer: str = "human"
    canonical: bool = False
    ai_write: str = "restricted"
    engine_managed: bool = False
    default_type: str | None = None
    allowed_types: list[str] = field(default_factory=list)
    validation_mode: str = "loose"
    purpose: str | None = None

    @property
    def specificity(self) -> int:
        """Length of the literal prefix before the first wildcard.

        Used to order overlapping rules most-specific-last so the deepest rule
        wins on conflicts (e.g. ``Human/01 Inbox/AI/**`` over ``Human/**``).
        """
        idx = self.glob.find("*")
        return len(self.glob) if idx == -1 else idx


def _glob_to_regex(glob: str) -> re.Pattern[str]:
    """Translate a vault-relative glob to a regex. ``**`` spans path separators,
    ``*`` and ``?`` do not."""
    out: list[str] = ["^"]
    i = 0
    while i < len(glob):
        c = glob[i]
        if c == "*":
            if glob[i : i + 2] == "**":
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(c))
        i += 1
    out.append("$")
    return re.compile("".join(out))


@dataclass
class GovernanceSchema:
    universal_properties: dict[str, dict]
    list_properties: set[str]
    datetime_properties: set[str]
    engine_owned_properties: set[str]
    legacy_renames: dict[str, str]
    known_extra_keys: dict[str, str | None]
    types: dict[str, TypeSchema]
    folder_default: FolderRule
    folder_rules: list[FolderRule]
    # alias (lowercased) -> canonical type name
    _type_aliases: dict[str, str] = field(default_factory=dict)
    _folder_regexes: dict[str, re.Pattern[str]] = field(default_factory=dict)

    # ---- loading ---------------------------------------------------------

    @classmethod
    def load(cls, vault_root: Path) -> "GovernanceSchema":
        schemas_dir = Path(vault_root).joinpath(*SCHEMAS_SUBDIR)
        return cls.from_dir(schemas_dir)

    @classmethod
    def from_dir(cls, schemas_dir: Path) -> "GovernanceSchema":
        glob_cfg = _read_yaml(schemas_dir / "global.yml")
        types_cfg = _read_yaml(schemas_dir / "types.yml")
        folders_cfg = _read_yaml(schemas_dir / "folders.yml")
        return cls.from_dicts(glob_cfg, types_cfg, folders_cfg)

    @classmethod
    def from_dicts(cls, glob_cfg: dict, types_cfg: dict, folders_cfg: dict) -> "GovernanceSchema":
        types: dict[str, TypeSchema] = {}
        aliases: dict[str, str] = {}
        for name, spec in (types_cfg.get("types") or {}).items():
            spec = spec or {}
            ts = TypeSchema(
                name=name,
                folder_globs=list(spec.get("folder_globs") or []),
                statuses=list(spec.get("statuses") or []),
                required=list(spec.get("required") or []),
                recommended=list(spec.get("recommended") or []),
                aliases=list(spec.get("aliases") or []),
            )
            types[name] = ts
            for alias in ts.aliases:
                aliases[alias.lower()] = name

        default_spec = folders_cfg.get("default") or {}
        folder_default = FolderRule(glob="(default)", **_folder_kwargs(default_spec))
        folder_rules = [
            FolderRule(glob=g, **_folder_kwargs(spec or {}))
            for g, spec in (folders_cfg.get("folders") or {}).items()
        ]
        folder_rules.sort(key=lambda r: r.specificity)

        return cls(
            universal_properties=dict(glob_cfg.get("universal_properties") or {}),
            list_properties=set(glob_cfg.get("list_properties") or []),
            datetime_properties=set(glob_cfg.get("datetime_properties") or []),
            engine_owned_properties=set(glob_cfg.get("engine_owned_properties") or []),
            legacy_renames=dict(glob_cfg.get("legacy_renames") or {}),
            known_extra_keys=dict(glob_cfg.get("known_extra_keys") or {}),
            types=types,
            folder_default=folder_default,
            folder_rules=folder_rules,
            _type_aliases=aliases,
            _folder_regexes={r.glob: _glob_to_regex(r.glob) for r in folder_rules},
        )

    # ---- type resolution -------------------------------------------------

    def canonical_type(self, raw: str | None) -> str | None:
        """Map a raw `Type` value to a canonical type name (resolving aliases),
        or None if it is neither a known type nor a known alias."""
        if not raw:
            return None
        if raw in self.types:
            return raw
        return self._type_aliases.get(raw.lower())

    def is_alias(self, raw: str | None) -> bool:
        return bool(raw) and raw not in self.types and raw.lower() in self._type_aliases

    def suggest_type(self, raw: str | None) -> str | None:
        """Best-effort 'did you mean' for an unknown Type."""
        if not raw:
            return None
        alias = self._type_aliases.get(raw.lower())
        if alias:
            return alias
        names = list(self.types)
        match = difflib.get_close_matches(raw, names, n=1, cutoff=0.6)
        return match[0] if match else None

    def type_for(self, name: str | None) -> TypeSchema | None:
        canon = self.canonical_type(name)
        return self.types.get(canon) if canon else None

    # ---- folder resolution ----------------------------------------------

    def matching_rules(self, rel_path: str) -> list[FolderRule]:
        """All folder rules whose glob matches `rel_path`, least-specific first."""
        return [r for r in self.folder_rules if self._folder_regexes[r.glob].match(rel_path)]


def _folder_kwargs(spec: dict) -> dict:
    return {
        "layer": spec.get("layer", "human"),
        "canonical": bool(spec.get("canonical", False)),
        "ai_write": spec.get("ai_write", "restricted"),
        "engine_managed": bool(spec.get("engine_managed", False)),
        "default_type": spec.get("default_type"),
        "allowed_types": list(spec.get("allowed_types") or []),
        "validation_mode": spec.get("validation_mode", "loose"),
        "purpose": spec.get("purpose"),
    }


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"governance schema not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"schema {path.name} did not parse to a mapping")
    return data
