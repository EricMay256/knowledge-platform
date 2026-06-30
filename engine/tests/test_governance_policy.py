"""AI write-policy gating on ai/* branches (real git integration)."""

from __future__ import annotations

import shutil
import subprocess

import pytest

from vault_governance.findings import Severity
from vault_governance.policy import check_policy, is_ai_branch
from vault_governance.schema import GovernanceSchema

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not available")


def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True,
                   capture_output=True, text=True)


def _init_repo(root):
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t.test")
    _git(root, "config", "user.name", "Test")
    _git(root, "checkout", "-q", "-b", "master")


def test_is_ai_branch():
    assert is_ai_branch("ai/foo")
    assert not is_ai_branch("master")


def test_ai_branch_blocked_on_human_allowed_on_inbox(temp_vault):
    vault, write = temp_vault
    root = vault.parent
    # seed both files on master so the diff is a *modification*
    write("Human/03 Projects/p.md", "---\nType: Project\n---\nv1\n")
    write("Human/01 Inbox/AI/s.md", "---\nType: Idea\n---\nv1\n")
    _init_repo(root)
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "seed")

    _git(root, "checkout", "-q", "-b", "ai/work")
    write("Human/03 Projects/p.md", "---\nType: Project\n---\nv2 edited\n")   # forbidden
    write("Human/01 Inbox/AI/s.md", "---\nType: Idea\n---\nv2 edited\n")     # allowed
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "ai edits")

    schema = GovernanceSchema.load(vault)
    findings = check_policy(root, vault.name, schema, base="master", head="HEAD", branch="ai/work")

    rules = {(f.path, f.severity) for f in findings}
    assert ("Human/03 Projects/p.md", Severity.ERROR) in rules
    assert not any(f.path == "Human/01 Inbox/AI/s.md" for f in findings)


def test_non_ai_branch_is_unconstrained(temp_vault):
    vault, write = temp_vault
    root = vault.parent
    write("Human/03 Projects/p.md", "---\nType: Project\n---\nv1\n")
    _init_repo(root)
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "seed")
    _git(root, "checkout", "-q", "-b", "feature/x")
    write("Human/03 Projects/p.md", "---\nType: Project\n---\nv2\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "edit")

    schema = GovernanceSchema.load(vault)
    findings = check_policy(root, vault.name, schema, base="master", head="HEAD", branch="feature/x")
    assert findings == []
