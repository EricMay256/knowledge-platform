# Migration Report — merging the agentic engine into the Obsidian vault

Consolidation of three previously independent repos into one `knowledge-platform` monorepo
with strong internal separation (markdown vault vs. functional code). Dated 2026-06-29.

## What was moved / renamed

- **`agentic_knowledge_vault/` → `engine/`.** The Python contribution engine (`vault_contrib`,
  tests, scripts, specs, docs, HANDOFF, skill source) now lives beside the vault, not inside
  it. Functional code is kept out of the synced markdown vault by design.
- **Live agent vault data → `Vault/Agent/notes/`.** The 9 notes from the standalone
  `~/knowledge-vault` repo were migrated in and rewritten to the new governance schema (see
  below). `Agent/review/` and `Agent/Promotion Candidates/` were scaffolded.
- **`Vault/Tools/`** (empty placeholder) was removed — the spec's `Tools/` was the
  engine, which is now `engine/`.

## What was rewritten

- **Engine note schema → human governance schema (`schema_version` 1 → 2).** Agent notes now
  carry governance-standard TitleCase frontmatter (`Type: Agent Note`, `Status` ∈
  {`Active`,`Flagged`}, `CreatedAt`, `LastUpdated`, `Tags`) plus lowercase engine plumbing
  (`title`, `id`, `contributed_by`, `source`, `related_ids`, `client_run_id`,
  `schema_version`). Changed `models.py`, `vault_frontmatter.py`, `store_git.py`,
  `service.py`, and the test suite. **97/97 tests pass.**
- **Engine is now monorepo-aware.** `GitMarkdownStore` no longer inits a nested git repo when
  the vault is inside an existing repo; it auto-commits against the enclosing repo. (New
  `_enclosing_git_root()`, covered behavior verified against `Vault/Agent/`.)
- **Governance reconciled:** `Vault Philosophy.md` AI policy corrected (`00 Inbox/AI` →
  `01 Inbox/AI`) and expanded with the two-layer / two-pipeline model; `Type Dictionary`,
  `Status Map`, and `Metadata Standard` gained the `Agent Note` type; new
  `AI Contribution Policy.md` and `Promotion Policy.md` describe the pipelines and write rules.
- **Skill/doc fixes:** `AGENTS.md` `.Codex` → `.claude` typo fixed; `SKILL.md`, `CLAUDE.md`,
  `AGENTS.md` updated for the new vault location and schema; deployed skill copies re-synced.

## Git topology

All three repos were collapsed into the single top-level repo (the pre-existing empty
`knowledge-platform/.git`). Nested `.git` dirs were removed. Full histories are preserved as
bundles (outside the tree) at:
`…/scratchpad/history-bundles/{obsidian-vault,engine,live-knowledge-vault}.bundle`
(the Obsidian vault's history also remains on its GitHub remote). Restore any with
`git clone <bundle>`.

## What was left behind / assumptions

- **`~/knowledge-vault` (the old standalone vault) was left intact**, not deleted — its notes
  are now mirrored under `Agent/`. You can archive/remove it once satisfied. **Set
  `KNOWLEDGE_VAULT="<repo>/Vault/Agent"`** so the engine writes to the new location.
- **Two migrated notes are now content-stale** (they describe the old vault location / engine
  layout): `knowledge-vault-location-and-resolution` and
  `knowledge-vault-stage-a-dedup-keys-on-title-only`. Bodies were not auto-edited (agents
  don't rewrite note bodies without review) — refresh or re-flag them when convenient.

## TODO (operator decisions, intentionally not done)

- **Remote + Syncthing:** re-establish on the `Vault/` subfolder (not the repo root)
  so engine code isn't replicated to devices. Decide whether to push the combined repo to the
  existing `obsidian-vault` GitHub remote or a fresh one.
- **Governance still to finalize (your call):** the human vault's own `Tags`-vs-`tags`
  frontmatter drift (Metadata Standard says `Tags`; several human notes use lowercase `tags`);
  `Tag Dictionary` is a stub; some Type-specific property tables are placeholders.
- **Enforcement:** the AI write policy is currently instructed, not gated — a future `ai/*`
  pre-commit/CI hook can enforce it (`engine/Tools`-style hook, deferred per non-goals).
