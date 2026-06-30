"""AI write-policy enforcement on ``ai/*`` branches.

The AI Contribution Policy says agents may write only to ``Agent/`` (via the
engine) and ``Human/01 Inbox/AI/`` (proposals), and must never directly edit
canonical Human areas. That rule has been *instructed, not gated*. This module
gates it: given a git diff, it flags any change an ``ai/*`` branch makes to a
forbidden path.

It shells out to git (the repo is the audit log) and reuses the same folder
policy the validator does, so doc, validator, and gate cannot disagree.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .findings import Finding, Severity
from .schema import GovernanceSchema

# ai_write values that an ai/* branch may modify.
_ALLOWED_AI_WRITE = {"allowed", "engine_only"}


def current_branch(repo_root: Path) -> str:
    return _git(repo_root, "rev-parse", "--abbrev-ref", "HEAD").strip()


def is_ai_branch(branch: str) -> bool:
    return branch.startswith("ai/")


def changed_files(repo_root: Path, base: str, head: str) -> list[str]:
    """Repo-relative paths changed between `base` and `head` (added/modified)."""
    out = _git(repo_root, "diff", "--name-only", f"{base}...{head}")
    return [line.strip() for line in out.splitlines() if line.strip()]


def check_policy(
    repo_root: Path,
    vault_dirname: str,
    schema: GovernanceSchema,
    base: str,
    head: str,
    branch: str | None = None,
) -> list[Finding]:
    """Return policy violations for the diff. Empty == clean (or not an ai/* branch)."""
    branch = branch if branch is not None else current_branch(repo_root)
    findings: list[Finding] = []
    if not is_ai_branch(branch):
        return findings  # policy only constrains ai/* branches

    prefix = vault_dirname.rstrip("/") + "/"
    for path in changed_files(repo_root, base, head):
        if not path.startswith(prefix):
            # Outside the vault (e.g. engine/ code). Not governed here.
            continue
        rel = path[len(prefix):]
        ctx_rules = schema.matching_rules(rel)
        # Most-specific rule wins (matching_rules is least-specific-first).
        ai_write = ctx_rules[-1].ai_write if ctx_rules else schema.folder_default.ai_write
        if ai_write in _ALLOWED_AI_WRITE:
            continue
        sev = Severity.ERROR if ai_write == "forbidden" else Severity.WARNING
        findings.append(Finding(rel, sev, "ai-write-policy",
                               f"ai/* branch '{branch}' modifies '{path}' "
                               f"(ai_write: {ai_write}) — not an AI-writable location"))
    return findings


def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


# Raised by the CLI when git invocation itself fails (not a policy violation).
GitError = subprocess.CalledProcessError
