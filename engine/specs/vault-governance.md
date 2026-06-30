# Vault Governance layer (`vault_governance`)

Whole-vault metadata correctness, sitting **beside** the contribution engine, not inside it.

```
vault_contrib     contributions INTO Agent/notes:   validate -> dedup -> decide -> write
vault_governance  correctness ACROSS the whole Vault: inheritance -> validate -> lint -> policy
```

`vault_contrib` owns the Stage-A/B2 migration seams and is untouched. `vault_governance` reuses
exactly one thing from it — `vault_frontmatter` (the canonical YAML serializer) — so there is a
single YAML dialect in the repo. It never imports the contribution engine's storage or dedup.

## Source of truth

Rules live as machine-readable YAML under `Vault/00 Governance/Schemas/`
(`global.yml`, `types.yml`, `folders.yml`), mirroring the prose governance docs. This is a
documented exception to the Vault's markdown-only rule (see `Schemas/README.md`); the schema is
config, kept beside its prose counterpart. Paths in the schema are **vault-root-relative**
(`Human/03 Projects/**`), so they don't hard-code where the vault is checked out.

## The three features

### 1. Property inheritance (`inheritance.py`) — non-destructive

- **Location-implied context** (`resolve_context`): a note's `layer`, `canonical`, `ai_write`,
  `default_type`, `allowed_types`, and `validation_mode` follow from its folder. Computed on
  read; never written into frontmatter (keeps YAML clean, never edits Human notes).
- **Parent-chain properties** (`resolve_inherited_properties` / `effective_properties`): a note
  with `Parent: [[X]]` inherits the union of `Tags` and nearest-ancestor `Area`/`Domain`/
  `ReviewFreq`. Used to reason about notes, not to rewrite them.

### 2. Automated schema validation (`validate.py`)

Graduated severity so it runs against the existing, pre-enforcement vault:

| Severity  | Fails a run? | Examples |
| --------- | ------------ | -------- |
| `ERROR`   | yes          | unparseable frontmatter, engine field on a Human note, type not allowed in folder, malformed Agent Note |
| `WARNING` | no           | missing/unknown/drifted Type, invalid Status, lowercase `tags`, scalar-where-list, non-ISO date |
| `INFO`    | no           | known non-standard keys (`Related`, `Category`, …) |

Three per-folder modes (`folders.yml`): `strict` (canonical Human), `agent` (engine-shape
enforcement on `Agent/`), `loose` (inboxes/templates/governance — structural checks only).

### 3. Metadata linting (`lint.py`)

Normalization over the canonical serializer: legacy key → canonical casing, scalar → list,
de-duplicate list values, governance key order. **`--fix` only rewrites Agent-layer and
non-canonical notes**; canonical Human notes (and the governance layer) are *reported* but never
auto-written, honoring the AI write policy.

### Bonus: AI write-policy gate (`policy.py`)

`check-policy` closes the "instructed, not gated" gap from the migration report: on an `ai/*`
branch it flags any diff touching a forbidden canonical Human area, reusing the same
`folders.yml` so doc, validator, and gate cannot disagree.

## CLI

```bash
python -m vault_governance.cli validate                 # exits 1 on ERROR
python -m vault_governance.cli lint --check             # exits 1 on fixable drift
python -m vault_governance.cli lint --fix               # rewrites fixable notes
python -m vault_governance.cli check-policy --base origin/master --head HEAD
# --vault defaults to the repo's Vault/; --changed-only limits to the git diff; --format json
```

## Integration

- **CI:** `.github/workflows/vault-governance.yml` runs the suite + `lint --check` + `validate`
  on every push/PR, and `check-policy` on PRs (a no-op unless the head branch is `ai/*`).
- **Git hooks:** `.githooks/` (`pre-commit` = validate + lint --check; `pre-push` = check-policy).
  Enable with `git config core.hooksPath .githooks` (or `python engine/scripts/install_hooks.py`).

## Calibration note (deliberate, not a bug)

`types.yml` marks type-specific properties as `recommended`, not `required`, and the validator
treats Type/Status drift as warnings. This is because the current vault predates the standard
(32% of Human notes have no `Type`; statuses like `Ongoing` and an unedited template placeholder
appear). The tool is therefore **green on `ERROR` today** and ratchets: as the back-catalogue is
cleaned, promote `recommended` → `required` and warnings → errors. Run
`vault-governance lint --fix` over the Agent layer and `... validate` to triage Human drift.
