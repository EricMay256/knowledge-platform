#!/usr/bin/env python3
"""Point this repo's git hooks at `.githooks/` and mark them executable.

    python engine/scripts/install_hooks.py

Equivalent to `git config core.hooksPath .githooks`, plus a chmod so the hooks
run on Linux/CI. Idempotent. Run `git config --unset core.hooksPath` to undo.
"""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

HOOKS_DIRNAME = ".githooks"


def main() -> int:
    repo_root = Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    )
    hooks_dir = repo_root / HOOKS_DIRNAME
    if not hooks_dir.is_dir():
        sys.exit(f"error: {hooks_dir} not found")

    subprocess.run(
        ["git", "config", "core.hooksPath", HOOKS_DIRNAME],
        cwd=repo_root, check=True,
    )

    for hook in hooks_dir.iterdir():
        if hook.is_file():
            mode = hook.stat().st_mode
            hook.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"installed: core.hooksPath -> {HOOKS_DIRNAME}")
    print("hooks:", ", ".join(sorted(p.name for p in hooks_dir.iterdir() if p.is_file())))
    print("undo with: git config --unset core.hooksPath")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
