# Governance runbook — validate, lint, enforce

Day-to-day operations for the **`vault_governance`** layer: schema validation, metadata
linting, property inheritance, and the AI write-policy gate. For the *contribution* side
(adding/curating Agent notes) see [RUNBOOK.md](RUNBOOK.md); for the design, see
[../specs/vault-governance.md](../specs/vault-governance.md).

> All commands below assume your shell is in the `engine/` directory. `--vault` is **optional**
> after `pip install -e .` — it defaults to the repo's `Vault/`. When in doubt, pass it
> explicitly: `--vault ../Vault`.

---

## 0. Quick reference

| I want to…                                            | Command |
| ----------------------------------------------------- | ------- |
| Check the vault for schema/policy problems            | `python -m vault_governance.cli validate` |
| See only errors + warnings (hide INFO)                | `python -m vault_governance.cli validate --quiet` |
| Check only what I've changed                          | `python -m vault_governance.cli validate --changed-only` |
| See what linting *would* normalize (no writes)        | `python -m vault_governance.cli lint --check` |
| Auto-fix metadata where allowed                       | `python -m vault_governance.cli lint --fix` |
| Gate an `ai/*` branch against the write policy        | `python -m vault_governance.cli check-policy --base origin/master --head HEAD` |
| Machine-readable output                               | add `--format json` to any command |
| List Agent notes / regenerate the index              | `python -m vault_contrib.cli list` · `… index` |
| Install the git hooks                                 | `python scripts/install_hooks.py` |

One-time setup: `pip install -e ".[dev]"` (installs the engine + `pytest`; one runtime dep,
`pyyaml`). After that the console scripts `vault-governance` and `vault-contrib` work from any
directory too.

---

## 1. Validation — *is the vault structurally correct?*

```bash
python -m vault_governance.cli validate --vault ../Vault
```

Validation reads the machine-readable schemas in `Vault/00 Governance/Schemas/`
(`global.yml`, `types.yml`, `folders.yml`) and reports findings at three severities:

| Severity  | Fails the run? | Examples |
| --------- | -------------- | -------- |
| **ERROR** | **yes** (exit 1) | unparseable frontmatter; an engine field (`ID`, `Title`, …) on a canonical Human note; a Type not allowed in its folder; a malformed Agent Note |
| WARNING   | no (exit 0)      | missing/unknown/drifted `Type`; invalid `Status` for the type; TitleCase `Tags` (should be lowercase); a scalar where a list is expected; a non-ISO date |
| INFO      | no               | known non-standard keys (`Related`, `Category`, …) |

**Exit code:** `0` unless there is at least one ERROR. That's what CI and the pre-commit hook
key off — the vault can carry warnings indefinitely without blocking you.

Useful flags:

```bash
python -m vault_governance.cli validate --quiet           # hide INFO lines (counts still shown)
python -m vault_governance.cli validate --changed-only    # only notes changed in the working tree
python -m vault_governance.cli validate --changed-only --base origin/master   # …vs a ref
python -m vault_governance.cli validate --format json      # one object per finding, for scripts
```

Triage a specific rule with JSON, e.g. list every invalid Status:

```bash
python -m vault_governance.cli validate --format json \
  | python -c "import sys,json;[print(f['path']) for f in json.load(sys.stdin) if f['rule']=='invalid-status']"
```

### Validation modes (per folder, from `folders.yml`)
- **strict** — canonical Human notes (`Human/03 Projects`, `…/17 Concepts`, …): full checks.
- **agent** — `Agent/notes` & `Agent/review`: enforces the engine note shape (ERROR-level).
- **loose** — inboxes, templates, governance docs, promotion queue: structural checks only.

---

## 2. Linting — *can the metadata be normalized?*

Linting is the style/normalization counterpart to validation: it renames legacy/drifted keys
to canonical (`Tags`→`tags`, `created_at`→`CreatedAt`, lowercase plumbing → PascalCase),
de-duplicates list values, wraps stray scalars into lists, and fixes key order.

```bash
python -m vault_governance.cli lint --check     # report drift, write nothing, exit 1 if fixable drift exists
python -m vault_governance.cli lint --fix       # rewrite the notes it is allowed to touch
python -m vault_governance.cli lint             # report only, always exit 0
```

**Scope of `--fix` (important):** it rewrites **only Agent-layer and non-canonical notes**.
Canonical Human notes and the governance layer are *reported but never auto-written* — that
honors the AI write policy (agents don't edit canonical Human knowledge). To normalize a Human
note, edit it yourself (the report tells you exactly what would change).

`--check` only fails on drift in notes it could actually fix, so it stays green while the Human
back-catalogue still has cosmetic drift. Combine with `--changed-only` in hooks/CI.

---

## 3. Property inheritance

Inheritance is **non-destructive and computed on read** — there is no command that writes
inherited values into notes. It powers validation in two ways you'll see in the output:

- **Location-implied context:** a note's layer, canonicality, AI-write policy, default Type,
  and validation mode come from its folder (`folders.yml`). This is why a Reference note placed
  under `17 Concepts/` is flagged `type-folder-mismatch`.
- **`Parent`-chain properties:** a note with `Parent: [[X]]` inherits the union of `tags` and
  the nearest ancestor's `Area`/`Domain`/`ReviewFreq`, used to reason about notes (not rewrite
  them).

If you want to use it programmatically:

```python
from pathlib import Path
from vault_governance.schema import GovernanceSchema
from vault_governance.inheritance import resolve_context
schema = GovernanceSchema.load(Path("../Vault"))
print(resolve_context("Human/17 Concepts/SOLID.md", schema))
```

---

## 4. AI write-policy gate (`ai/*` branches)

```bash
python -m vault_governance.cli check-policy --base origin/master --head HEAD
```

On an `ai/*` branch this flags any diff that touches a forbidden canonical Human area
(`Human/03 Projects`, `…/05 Decisions`, etc.). It is a **no-op on any other branch**, so it's
safe to wire into CI/hooks unconditionally. Override the branch name with `--branch <name>`.

---

## 5. Contribution engine (Agent notes)

These live in `vault_contrib` (separate package); full loop in [RUNBOOK.md](RUNBOOK.md).

```bash
python -m vault_contrib.cli list                       # list Agent notes
python -m vault_contrib.cli list --tag windows         # filter by tag (repeat --tag for AND)
python -m vault_contrib.cli index                      # (re)write Agent/INDEX.md (gitignored)
python -m vault_contrib.cli contribute --by agent:me --title "…" --body "…" --tags a,b
```

The engine writes notes in canonical form (PascalCase plumbing, lowercase `tags`) — so a fresh
contribution is already validation- and lint-clean.

---

## 6. CI

`.github/workflows/vault-governance.yml` runs on every push/PR:

```
pytest  →  lint --check  →  validate  →  check-policy (PRs only; no-op unless head is ai/*)
```

It fails on a test failure, fixable lint drift, a validation **error**, or an `ai/*` write-policy
violation — never on warnings/INFO.

---

## 7. Git hooks (local, opt-in)

```bash
python scripts/install_hooks.py        # sets core.hooksPath -> .githooks (reversible)
git config --unset core.hooksPath      # undo
```

- **pre-commit** — runs `validate` + `lint --check` on the notes in your commit (`--changed-only`).
  Blocks the commit on an error or fixable drift.
- **pre-push** — on `ai/*` branches only, runs `check-policy` against `origin/master`.

Bypass once with `git commit --no-verify` (or `git push --no-verify`). Hooks no-op cleanly if
Python isn't on `PATH`.

---

## 8. Changing the rules (schemas)

The schemas in `Vault/00 Governance/Schemas/` are the machine-readable mirror of the prose
governance docs. **Change both in the same commit:**

| Edit this prose doc                  | …and this schema |
| ------------------------------------ | ---------------- |
| `Metadata Standard.md` (properties)  | `global.yml` |
| `Type Dictionary.md` / `Status Map.md` | `types.yml` |
| `AI Contribution Policy.md` (write policy) | `folders.yml` |

After editing, run `python -m vault_governance.cli validate` to confirm the vault still parses
and you didn't introduce new errors. `engine/tests/test_governance_schema.py` guards the
schemas' structural shape.

Reminder: property keys are **PascalCase**, except the three Obsidian-reserved keys `tags`,
`aliases`, `cssclasses`, which stay lowercase.

---

## 9. Gotchas & troubleshooting

- **Never let the Obsidian Linter touch `Agent/`.** Those notes are engine-managed; linting
  them renames/strips the engine plumbing and breaks `vault_contrib`. Keep `Agent` in the
  Linter's *Folders to ignore*. (If it already happened, re-canonicalize: load each note and
  re-serialize through the engine — see the migration snippet in git history / PR #1.)
- **`vault_contrib` raises `KeyError: 'id'`** → an Agent note's keys were mangled (e.g. by the
  Linter). Run `validate` to find them; they'll show `agent-missing-field` errors.
- **`error: could not locate the Vault`** → run from `engine/`, or pass `--vault <path>`.
- **`check-policy` says git failed** → it needs history; in CI use `fetch-depth: 0` and fetch
  the base branch first.
- **Lots of WARNINGs, zero ERRORs** → expected. Warnings are the pre-existing Human-note drift
  backlog (missing `Type`, TitleCase `Tags`, invalid `Status`); clean at your own pace. The
  gates only care about errors and fixable drift.
