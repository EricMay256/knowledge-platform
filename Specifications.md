# Spec: knowledge-platform — one repo, human + agent knowledge with shared governance

**Status:** agreed and executed (2026-06-29). See `MIGRATION-REPORT.md` for what changed and
the remaining operator TODOs. This document is the corrected spec; it supersedes the original
"merge agentic-knowledge-vault into Obsidian Vault" draft, which assumed the two sides were
symmetric and folded executable code into the synced vault.

## Goal

Combine a mature human Obsidian vault and a working agent-contribution engine into **one
repository with clear separation of responsibility** — without collapsing the distinction
between human-curated knowledge and AI operational memory, and without polluting the synced
markdown vault with functional code.

## Architecture

```
knowledge-platform/                 # one git repo
  Vault/                            # markdown only — Obsidian opens this; Syncthing syncs this
    00 Governance/                  # shared rules for humans AND agents
    Human/                          # durable, human-curated knowledge (protected)
      01 Inbox/AI/                  #   Pipeline B: AI Suggestions (not canonical)
    Agent/                          # AI operational memory (engine-managed)
      notes/  review/              #   flat, tag-organized, dedup-gated
      Promotion Candidates/        #   Pipeline A: staged for human promotion
    Templates/  Assets/
  engine/                           # the Python contribution engine (kept OUT of the vault)
```

Markdown remains the canonical source of truth for knowledge. The engine is tooling that
operates on the `Agent/` layer; it is not part of the vault's synced surface.

## Layers and responsibility

1. **Governance (`00 Governance/`)** — one shared layer consumed by humans, agents, and the
   engine. Not duplicated inside `Human/` or `Agent/`. Defines the Metadata Standard, Type
   Dictionary, Status Map, Vault Philosophy, and the AI Contribution / Promotion policies.
2. **Human (`Human/`)** — durable, human-authored or human-approved knowledge. Agents may
   read it and *propose* changes, but may not directly edit canonical Human notes. Agent
   bodies are allowed only in `Human/01 Inbox/AI/`. Agent work happens on `ai/*` branches via
   pull request.
3. **Agent (`Agent/`)** — AI operational memory and working material, contributed through the
   engine under the same governance (type `Agent Note`). Lower editorial bar than Human, but
   structured (validated + deduped) so it stays reusable.
4. **Engine (`engine/`)** — scripts, validators, the contribution CLI, the skill, tests. Lives
   beside the vault, never inside it.

## The two AI → Human pipelines

- **Pipeline A — Promotion Candidates** (`Agent/Promotion Candidates/`): agent memory later
  judged worth preserving for the human. Human reviews, rewrites/distills, and promotes into
  `Human/`. *"This AI memory may be human-worthy."*
- **Pipeline B — AI Suggestions** (`Human/01 Inbox/AI/`): an agent proposing a specific change
  to Human knowledge (new Concept draft, backlink, metadata fix, duplicate merge). *"This is a
  proposed change to the Human vault."*

## Write policy

```
AI may write to:        Agent/  (via the engine)  and  Human/01 Inbox/AI/  (proposals)
AI may NOT write to:    any canonical Human area (Projects, Areas, Decisions, Reference,
                        People, Resources, Daily, Concepts, …)
```

Enforced by convention now; a future `ai/*` Git hook can gate it. Full rules in
`00 Governance/AI Contribution Policy.md`.

## Schema

Agent notes adopt the human vault's Metadata Standard (type `Agent Note`): governance-standard
TitleCase keys (`Type`, `Status` ∈ {`Active`,`Flagged`}, `CreatedAt`, `LastUpdated`, `Tags`)
plus lowercase engine plumbing (`title`, `id`, `contributed_by`, `source`, `related_ids`,
`client_run_id`, `schema_version`). The engine assigns and maintains the plumbing; it is not
hand-edited. `schema_version` is 2.

## Engine integration

- The engine is **monorepo-aware**: it auto-commits agent contributions against this repo and
  never inits a nested repo. Git history is the audit log (one commit per contribution).
- Point it at the layer with `KNOWLEDGE_VAULT="<repo>/Vault/Agent"` (or `--vault`).
- Contribution gate is unchanged: **validate → dedup → decide → write**; `flagged` dupes go to
  `Agent/review/` for human/agent adjudication. The ports remain clean for the eventual
  Postgres/pgvector + MCP swap (`engine/HANDOFF.md`).

## Non-goals (unchanged)

No MCP server yet; no database indexer yet; no UUID/auth work yet; agents never directly edit
canonical Human notes; Agent and Human content stay in separate layers; don't over-normalize
schemas before governance stabilizes.

## Acceptance criteria — all met

- One shared Governance layer; one git repo. ✓
- Human knowledge protected and curated; agents propose without applying. ✓
- Agent memory has a clear, engine-managed home, browsable in Obsidian. ✓
- Both AI→Human routes exist and are documented. ✓
- Existing engine value (retrieve-before-contribute, dedup, review queue, idempotency,
  validation, the skill) preserved; 97/97 tests pass. ✓
- Functional code separated from the synced vault. ✓
- Clear places for future linting, Git hooks, MCP access, and indexing. ✓
