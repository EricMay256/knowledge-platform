"""CLI for the vault governance layer.

    python -m vault_governance.cli validate --vault ../Vault
    python -m vault_governance.cli lint     --vault ../Vault --check
    python -m vault_governance.cli lint     --vault ../Vault --fix
    python -m vault_governance.cli check-policy --base origin/master --head HEAD

``--vault`` defaults to the ``Vault/`` folder of the enclosing knowledge-platform
repo, so the commands work from inside ``engine/`` with no arguments.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

from .findings import Finding, Severity, has_errors, sort_key
from .frontmatter_scan import parse_note_text, scan_vault
from .lint import LintResult, lint_vault
from .moc import render_moc
from .policy import check_policy
from .schema import GovernanceSchema
from .validate import validate_vault


def default_vault() -> Path | None:
    # engine/vault_governance/cli.py -> parents[2] == repo root.
    repo_root = Path(__file__).resolve().parents[2]
    candidate = repo_root / "Vault"
    return candidate if candidate.exists() else None


def _resolve_vault(arg: str | None) -> Path:
    vault = Path(arg).resolve() if arg else default_vault()
    if vault is None or not vault.exists():
        sys.exit("error: could not locate the Vault; pass --vault <path>")
    return vault


def _changed_vault_paths(repo_root: Path, vault_dirname: str, base: str | None) -> list[str]:
    """Vault-relative paths changed in the working tree (or vs `base`)."""
    prefix = vault_dirname.rstrip("/") + "/"
    try:
        if base:
            names = _git(repo_root, "diff", "--name-only", f"{base}...HEAD").splitlines()
        else:
            # staged + unstaged + untracked, de-duplicated
            names = _git(repo_root, "diff", "--name-only", "HEAD").splitlines()
            names += _git(repo_root, "ls-files", "--others", "--exclude-standard").splitlines()
    except subprocess.CalledProcessError:
        # e.g. a repo with no commits yet (no HEAD); nothing to diff.
        names = []
    rel = []
    seen = set()
    for n in names:
        n = n.strip()
        if n.startswith(prefix) and n.endswith(".md") and n not in seen:
            seen.add(n)
            rel.append(n[len(prefix):])
    return rel


def _git(repo_root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(repo_root),
        capture_output=True, text=True, check=True,
    ).stdout


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def _emit(findings: list[Finding], as_json: bool, summary: str | None = None,
          quiet: bool = False) -> None:
    if as_json:
        print(json.dumps([f.to_dict() for f in findings], indent=2))
        return
    for f in sorted(findings, key=sort_key):
        if quiet and f.severity is Severity.INFO:
            continue
        print(f.format_line())
    counts = {s: sum(1 for f in findings if f.severity is s) for s in Severity}
    line = (f"\n{counts[Severity.ERROR]} error(s), "
            f"{counts[Severity.WARNING]} warning(s), "
            f"{counts[Severity.INFO]} info")
    if summary:
        line += f"  --  {summary}"
    print(line)


# --------------------------------------------------------------------------
# subcommands
# --------------------------------------------------------------------------

def cmd_validate(args: argparse.Namespace) -> int:
    vault = _resolve_vault(args.vault)
    schema = GovernanceSchema.load(vault)
    rel = None
    if args.changed_only:
        rel = _changed_vault_paths(vault.parent, vault.name, args.base)
    findings = validate_vault(vault, schema, rel_paths=rel)
    _emit(findings, args.format == "json", quiet=args.quiet)
    return 1 if has_errors(findings) else 0


def cmd_lint(args: argparse.Namespace) -> int:
    vault = _resolve_vault(args.vault)
    schema = GovernanceSchema.load(vault)
    rel = None
    if args.changed_only:
        rel = _changed_vault_paths(vault.parent, vault.name, args.base)
    results = lint_vault(vault, schema, fix=args.fix, rel_paths=rel)

    findings = [f for r in results for f in r.findings]
    writable_changed = [r for r in results if r.changed and r.writable]
    report_only = [r for r in results if r.changed and not r.writable]

    if args.fix:
        summary = f"fixed {len(writable_changed)} note(s); {len(report_only)} report-only note(s) left untouched"
    else:
        summary = f"{len(writable_changed)} fixable, {len(report_only)} report-only (Human/governance)"
    _emit(findings, args.format == "json", summary, quiet=args.quiet)

    if args.fix:
        return 0
    if args.check:
        # Fail only on drift the linter is actually allowed to fix.
        return 1 if writable_changed else 0
    return 0


def cmd_check_policy(args: argparse.Namespace) -> int:
    vault = _resolve_vault(args.vault)
    repo_root = vault.parent
    schema = GovernanceSchema.load(vault)
    try:
        findings = check_policy(
            repo_root, vault.name, schema,
            base=args.base, head=args.head, branch=args.branch,
        )
    except subprocess.CalledProcessError as exc:
        sys.exit(f"error: git failed: {exc.stderr or exc}")
    _emit(findings, args.format == "json", quiet=args.quiet)
    return 1 if has_errors(findings) else 0


def cmd_moc(args: argparse.Namespace) -> int:
    vault = _resolve_vault(args.vault)
    rel = args.path.strip("/\\").replace("\\", "/")
    target = vault / rel
    if not target.is_dir():
        sys.exit(f"error: not a folder: {target}")

    out = Path(args.out).resolve() if args.out else (target / "INDEX.md")
    try:
        out_rel = out.relative_to(vault.resolve()).as_posix()
    except ValueError:
        out_rel = None

    prefix = rel + "/"
    records = [
        rec for rec in scan_vault(vault)
        if rec.rel_path.startswith(prefix)
        and "INDEX" not in PurePosixPath(rec.rel_path).name
        and rec.rel_path != out_rel
    ]

    # Preserve an existing index's CreatedAt so only LastUpdated churns.
    created = None
    if out.exists():
        prev = parse_note_text(out.read_text(encoding="utf-8"))
        if prev.meta:
            created = prev.meta.get("CreatedAt") or None

    text = render_moc(rel, records, created=created)
    if args.dry_run:
        print(text)
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"Wrote {out} ({len(records)} notes).")
    return 0


# --------------------------------------------------------------------------
# parser
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    # Shared options, accepted on every subcommand (before or after it).
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--vault", help="path to the Vault folder (default: repo's Vault/)")
    common.add_argument("--format", choices=["text", "json"], default="text")
    common.add_argument("--quiet", action="store_true",
                        help="suppress INFO findings in the listing (counts still shown)")

    p = argparse.ArgumentParser(prog="vault-governance", description=__doc__,
                                parents=[common])
    sub = p.add_subparsers(dest="command", required=True)

    v = sub.add_parser("validate", parents=[common], help="schema/policy validation")
    v.add_argument("--changed-only", action="store_true",
                   help="only notes changed in the working tree (or vs --base)")
    v.add_argument("--base", help="git ref to diff against for --changed-only")
    v.set_defaults(func=cmd_validate)

    l = sub.add_parser("lint", parents=[common], help="metadata normalization")
    l.add_argument("--fix", action="store_true", help="rewrite fixable notes in place")
    l.add_argument("--check", action="store_true",
                   help="exit non-zero if fixable drift exists (no writes)")
    l.add_argument("--changed-only", action="store_true")
    l.add_argument("--base", help="git ref to diff against for --changed-only")
    l.set_defaults(func=cmd_lint)

    c = sub.add_parser("check-policy", parents=[common],
                       help="enforce AI write policy on ai/* branches")
    c.add_argument("--base", default="origin/master", help="merge base (default: origin/master)")
    c.add_argument("--head", default="HEAD")
    c.add_argument("--branch", help="branch name (default: current)")
    c.set_defaults(func=cmd_check_policy)

    m = sub.add_parser("moc", parents=[common],
                       help="generate a Map-of-Content index note for a folder")
    m.add_argument("--path", default="Human",
                   help="vault-relative folder to index (default: Human)")
    m.add_argument("--out", help="output file (default: <path>/INDEX.md)")
    m.add_argument("--dry-run", action="store_true",
                   help="print the index instead of writing it")
    m.set_defaults(func=cmd_moc)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
