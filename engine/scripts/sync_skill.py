#!/usr/bin/env python3
"""Keep the deployed copies of the knowledge-vault skill in sync with the
repo's source of truth, and emit a vendor-neutral version for non-skill contexts.

Source of truth:  .claude/skills/knowledge-vault/SKILL.md  (in this repo)

Managed targets (overwritten on sync -- safe, they are deployment copies):
  - ~/.claude/skills/knowledge-vault/SKILL.md   (Claude Code, user-level -> all projects)
  - ~/.codex/skills/knowledge-vault/SKILL.md    (Codex, user-level -> all projects)

Usage:
  python scripts/sync_skill.py            # sync source -> targets (fix drift)
  python scripts/sync_skill.py --check    # report drift only; exit 1 if any
  python scripts/sync_skill.py --emit-portable   # print a vendor-neutral version
                                                 # (paste into a ChatGPT Custom GPT
                                                 #  or a non-skill AGENTS.md)

Why not auto-manage AGENTS.md/ChatGPT? Their instruction files/fields (a global
AGENTS.md, a Custom GPT's Instructions) usually hold OTHER content too, so this
script never overwrites them -- it only prints the text for you to place.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / ".claude" / "skills" / "knowledge-vault" / "SKILL.md"

# Deployment copies this script keeps identical to SOURCE.
TARGETS = [
    Path.home() / ".claude" / "skills" / "knowledge-vault" / "SKILL.md",
    Path.home() / ".codex" / "skills" / "knowledge-vault" / "SKILL.md",
]


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def _norm(text: str | None) -> str | None:
    # Compare ignoring line-ending differences (Git may store CRLF on Windows).
    return None if text is None else text.replace("\r\n", "\n")


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body) for a `---`-delimited markdown file."""
    if not text.startswith("---"):
        return {}, text
    _, front, body = text.split("---\n", 2)
    return yaml.safe_load(front) or {}, body.lstrip("\n")


def render_portable(source_text: str) -> str:
    """Vendor-neutral guidance for contexts that do not read skill frontmatter:
    drop trigger frontmatter and surface the description as plain context."""
    meta, body = _split_frontmatter(source_text)
    description = " ".join((meta.get("description") or "").split())
    header = (
        "<!-- Generated from .claude/skills/knowledge-vault/SKILL.md by "
        "scripts/sync_skill.py. Do not edit here; edit the source and re-run. -->\n\n"
    )
    when = f"## When to use\n\n{description}\n\n" if description else ""
    return header + when + body


def check() -> int:
    source = _read(SOURCE)
    if source is None:
        print(f"ERROR: source skill not found at {SOURCE}", file=sys.stderr)
        return 2
    drift = []
    for target in TARGETS:
        actual = _read(target)
        if actual is None:
            drift.append((target, "missing"))
        elif _norm(actual) != _norm(source):
            drift.append((target, "out of sync"))
    if drift:
        print("Skill DRIFT detected:")
        for target, why in drift:
            print(f"  - {why}: {target}")
        print("Run `python scripts/sync_skill.py` to fix.")
        return 1
    print(f"In sync: {len(TARGETS)} target(s) match {SOURCE.name}.")
    return 0


def sync() -> int:
    source = _read(SOURCE)
    if source is None:
        print(f"ERROR: source skill not found at {SOURCE}", file=sys.stderr)
        return 2
    changed = 0
    for target in TARGETS:
        if _norm(_read(target)) == _norm(source):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
        print(f"Updated: {target}")
        changed += 1
    print("All targets already in sync." if not changed else f"Synced {changed} target(s).")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Sync / check the knowledge-vault skill.")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true", help="report drift only; exit 1 if any")
    g.add_argument("--emit-portable", action="store_true",
                   help="print a vendor-neutral version for non-Claude agents")
    args = p.parse_args(argv)

    # The skill body contains non-ASCII (arrows, em dashes); make stdout UTF-8 so
    # emission works on Windows consoles defaulting to cp1252.
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

    if args.emit_portable:
        source = _read(SOURCE)
        if source is None:
            print(f"ERROR: source skill not found at {SOURCE}", file=sys.stderr)
            return 2
        sys.stdout.write(render_portable(source))
        return 0
    return check() if args.check else sync()


if __name__ == "__main__":
    sys.exit(main())
