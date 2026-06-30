#!/usr/bin/env python3
"""One-time migration: rename existing vault files from `<id>.md` to title slugs.

New contributions already get title-based names; this fixes notes written under
the old `<uuid>.md` scheme. Renames are done with `git mv` so history follows the
file, and committed as one migration commit. The frontmatter `id` is untouched —
only the filename changes.

Usage:
  python scripts/reslug_vault.py            # dry run: print the planned renames
  python scripts/reslug_vault.py --apply    # perform the renames + commit
  python scripts/reslug_vault.py --vault <path> [--apply]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from vault_contrib.cli import _resolve_vault
from vault_contrib.store_git import _deserialize, _slugify


def _plan(directory: Path) -> list[tuple[Path, Path]]:
    """Renames needed in one directory, with stable -N suffixing for slug clashes."""
    items = []
    for path in directory.glob("*.md"):
        note = _deserialize(path.read_text(encoding="utf-8"))
        items.append((path, note))
    # created_at order makes collision suffixes deterministic across runs.
    items.sort(key=lambda pn: (pn[1].created_at, pn[1].id))

    taken: set[str] = set()
    renames: list[tuple[Path, Path]] = []
    for path, note in items:
        base = _slugify(note.title)
        name, n = f"{base}.md", 2
        while name in taken:
            name, n = f"{base}-{n}.md", n + 1
        taken.add(name)
        if path.name != name:
            renames.append((path, directory / name))
    return renames


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vault", default=None, help="vault path (default: $KNOWLEDGE_VAULT or ~/knowledge-vault)")
    p.add_argument("--apply", action="store_true", help="perform renames (default: dry run)")
    args = p.parse_args(argv)

    vault = _resolve_vault(args.vault)
    if not vault.exists():
        print(f"No vault at {vault}", file=sys.stderr)
        return 2

    renames: list[tuple[Path, Path]] = []
    for sub in ("notes", "review"):
        d = vault / sub
        if d.is_dir():
            renames.extend(_plan(d))

    if not renames:
        print(f"Nothing to rename — {vault} already uses title-based filenames.")
        return 0

    print(f"{'Renaming' if args.apply else 'Would rename'} {len(renames)} file(s) in {vault}:")
    for old, new in renames:
        print(f"  {old.relative_to(vault).as_posix()}  ->  {new.relative_to(vault).as_posix()}")

    if not args.apply:
        print("\nDry run. Re-run with --apply to perform the renames.")
        return 0

    for old, new in renames:
        subprocess.run(
            ["git", "-C", str(vault), "mv", old.relative_to(vault).as_posix(),
             new.relative_to(vault).as_posix()],
            check=True, capture_output=True, text=True,
        )
    subprocess.run(
        ["git", "-C", str(vault), "commit", "-q", "-m",
         "vault: rename notes to title-based filenames"],
        check=True, capture_output=True, text=True,
    )
    print(f"\nRenamed and committed {len(renames)} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
