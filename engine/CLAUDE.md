# CLAUDE.md — knowledge-vault engine (always-loaded rules)

Short, load-bearing rules for working **on this engine**. Full narrative and rationale live
in [HANDOFF.md](HANDOFF.md) and `specs/`. This is **Stage A** (the free tier): git + markdown
+ crude string/title dedup. Stage B2 (paid) swaps the storage + dedup behind the same ports.

> **Two packages, one job each.** `vault_contrib` = contributions INTO `Agent/notes`
> (validate → dedup → decide → write). `vault_governance` = metadata correctness ACROSS the
> whole `Vault/` (inheritance → validation → linting → ai/* policy). The governance package
> reuses only `vault_frontmatter` from here; **do not merge it into `vault_contrib`** — keeping
> it separate is what protects the B2 seams. See `specs/vault-governance.md`.

## The one rule that must not break: keep the seams
The package is split along a ports-vs-throwaway line, and **that split is the B2 migration
plan** (HANDOFF §3):
- `ports.py` (`Deduper`, `Store` Protocols), `models.py`, `core.py` — **stable**, never touch
  for storage/dedup reasons.
- `dedup_string.py` / `store_git.py` — Stage-A throwaway impls; B2 adds `dedup_pgvector.py` /
  `store_postgres.py` as siblings satisfying the **same** Protocols.
- `cli.py` is the **composition root** — the *only* place concrete impls are named.

> `core.py` and `service.py` must depend **only on the Protocols**. They must never import a
> concrete store/deduper, reference files/paths/SQL, or branch on "string-match vs vector."
> If a change tempts you to, it belongs in a `Deduper`/`Store` impl or the composition root.

## Conventions
- Python ≥ 3.10 (`match`, `X | None`). **One runtime dep:** `pyyaml`. Dev: `pytest`.
- Idioms to preserve: `Protocol` backends, `match` dispatch on `Action`, pure `core.py`.
- **Deferred on purpose — don't add to A without a flip condition** (HANDOFF §4/§6): write
  serialization, semantic dedup, auth, the `Merge` path.
- **Don't auto-merge.** Collisions go to `review/` for human/agent adjudication.
- **Humans are first-class contributors**, same path as agents; `contributed_by` is namespaced
  `agent:<id>` / `human:<name>`.
- **Don't hand-create files in `notes/`** (no frontmatter/id, bypasses dedup). Hand-editing an
  existing note body is fine — keep frontmatter intact and commit it.
- **Git history is the audit log** — one commit per contribution; don't rewrite it.

## Note schema (frozen — change here AND the skill together)
Agent notes follow the human vault's governance (`00 Governance/Metadata Standard.md`,
type `Agent Note`). Frontmatter keys are PascalCase (`Type`, `Status` [`Active`/`Flagged`],
`CreatedAt`, `LastUpdated`, `Title`, `ID`, `ContributedBy`, `Source`, `RelatedIDs`,
`ClientRunID`, `SchemaVersion`) — except the Obsidian-reserved `tags`/`aliases`/`cssclasses`,
which stay lowercase. (Python field / CLI names below are unchanged.)
Settable: `title`, `body`, `contributed_by`, `tags` (non-empty, no dups), `source` (optional),
`client_run_id` (optional idempotency key — reuse on retries to make them no-ops).
Engine-owned, never set by a caller: `id`, `created_at`/`updated_at`, `status`, `note_type`,
`related_ids`, `schema_version` (currently 2).

## Vault location
The Agent layer lives **inside the knowledge-platform monorepo** at `Vault/Agent/`
(siblings `notes/`, `review/`, `Promotion Candidates/`). Point the engine there via
`$KNOWLEDGE_VAULT=<repo>/Vault/Agent` or `--vault`; the CLI still falls back to
`~/knowledge-vault` when neither is set. The store is **monorepo-aware**: it auto-commits
against the enclosing repo and never inits a nested one.

## Commands
```bash
pytest                                   # run the test suite
python -m vault_contrib.cli contribute --by agent:me --title … --body …   # --vault optional
python -m vault_contrib.cli list
python scripts/sync_skill.py [--check|--emit-portable]   # keep deployed skill copies in sync
```
The skill source of truth is `.claude/skills/knowledge-vault/SKILL.md`; deployed copies are
synced by `scripts/sync_skill.py`.
