# Stage 2 spec — Skill wrapper (`SKILL.md`)

**Source:** HANDOFF.md §5 Phase 2. **Status:** not started. **Depends on:** Stage 1
(schema must be frozen, incl. the idempotency decision). **Blocks:** nothing hard, but it's
how agents are *meant* to use the vault in Stage 3.

---

## 1. Goal

Wrap the existing engine as a Claude Code skill so agents invoke contribution and retrieval
idiomatically — by triggering a skill, not by reverse-engineering the CLI. The skill is
**thin**: the engine already does validation, dedup, and the policy ladder. The skill's job
is to teach *the map*, not re-implement the limbs: the note schema, the contribution
procedure, how to read each `status`, and the retrieve-before-write path.

## 2. Scope

In scope: a `SKILL.md` (with front-matter `name`/`description` for triggering), guidance
content, and worked examples that call the **already-built** CLI / `ContributionService`.
Optionally a tiny convenience wrapper *only if* it removes real friction — default is to
call the CLI directly.

Out of scope: changing the engine, the schema (frozen in Stage 1), or the CLI surface;
B2's query tool; any server. If writing the skill reveals a needed schema tweak, that is a
signal to **go back to Stage 1**, fix it there, then resume — do not let the skill and the
engine document divergent schemas (HANDOFF §5 Phase 2: "do not change the note schema after
the skill documents it without updating both").

## 3. Deliverables

1. `SKILL.md` with:
   - YAML front-matter: `name` (e.g. `knowledge-vault`) and a `description` written for
     **trigger accuracy** — fire when an agent wants to record a durable, reusable insight
     into the shared vault, or retrieve prior vault knowledge before solving something; do
     **not** fire for ordinary file edits or scratch notes.
   - The body content in §4.
2. At least two worked examples (a clean insert; a near-duplicate that returns `flagged`),
   showing the exact CLI invocation and the JSON the agent should parse.
3. A short "interpreting results" table mapping every `status` → what the agent should do.

## 4. Content the skill must teach

### 4.1 The note schema (authoritative, mirrors `models.Note`)
Document the contributable fields and what "good" looks like *for this vault*:
- `title` — short, specific, the searchable handle; titles are the dedup key in Stage A, so
  near-identical titles will flag.
- `body` — markdown; the durable insight, self-contained enough to be useful out of context.
- `tags` — non-empty, de-duplicated; establish a small house vocabulary (e.g.
  `simulation`, `determinism`, …) and tell agents to prefer existing tags.
- `contributed_by` — the contributor's id (required; validation rejects blank). **Both
  agents and humans contribute** through this same path; namespace by convention as
  `agent:<id>` or `human:<name>` so provenance stays legible. A skill-driven agent sets its
  own `agent:` id; a human running the CLI sets a `human:` id.
- `source` — optional provenance (URL / run id).
- If Stage 1 added the **idempotency key**, document it here and tell agents to pass a
  stable key on retries.
- Fields agents do **not** set (engine-owned): `id`, `created_at`, `status`,
  `related_ids`, `schema_version`.

### 4.2 The contribution procedure
- The canonical call: `python -m vault_contrib.cli contribute --vault <path> --by <agent>
  --title … --body … [--tags a,b] [--source …]` (use the layout/invocation finalized in
  Stage 1). Note `--by`, `--title`, `--body` are required.
- Parse the emitted JSON (`status`, `note_id`, `message`, `errors`, `similars`).
- Importing `ContributionService` directly is the alternative for in-process agents; the
  CLI is the default and simpler path.

### 4.3 Interpreting `status` (the critical teaching point)
A table the agent branches on. **`flagged` is not a failure** — HANDOFF §5 Phase 2 calls
this out explicitly:
| status | meaning | agent action |
|---|---|---|
| `inserted` | added to `notes/` | done |
| `linked` | added + linked (B2 only today) | done |
| `flagged` | possible duplicate; lives in `review/` for later human/agent adjudication | **do not retry or rewrite**; surface that it needs adjudication; consider reading the `similars` to decide if your note adds anything |
| `rejected` | near-identical (only if a `reject_at` policy is set; not Stage A default) | drop or revise |
| `invalid` | failed validation | fix per `errors` and retry |
Also map CLI exit codes (`0` = inserted/linked, non-zero otherwise) for shell-driven agents.

### 4.4 The read path (retrieve before contributing)
- In Stage A, retrieval is **grep/read over `notes/`** — the agent already has these tools.
  Teach: search the vault for the topic before writing, to avoid creating obvious dupes and
  to build on existing notes.
- State plainly that **B2 will replace this with a query/MCP tool**; the skill's retrieval
  section is the part most likely to change at B2, so keep it isolated and clearly labelled.

### 4.5 Conventions / guardrails (from HANDOFF §6)
- Don't hand-edit `review/`; adjudication is a deliberate human/agent curation step.
- Git history **is** the audit log — don't squash or rewrite it; each contribution is one
  commit.
- Don't auto-merge duplicates; collisions go to `review/`.

### 4.6 Human contributors
The skill itself is agent-facing, but the *vault* is shared by humans and agents. State that
humans contribute through the **same CLI** (`contribute … --by human:<name>`), getting the
same validation and dedup — so an agent reading the vault should expect human-authored notes
alongside agent ones and treat them identically. Human-specific *workflow* (hand-curation,
review-queue adjudication, direct body edits) is operator guidance and lives in the Stage 3
runbook, not the skill — but the skill should not imply the vault is agent-only.

## 5. Acceptance criteria
- The schema documented in `SKILL.md` matches `models.Note` field-for-field (including any
  Stage-1 idempotency field) — verify against the frozen schema, not from memory.
- Following the skill's procedure verbatim reproduces the Stage-1 behaviours: a clean note
  → `inserted`; a near-identical title → `flagged`.
- The description triggers on "record this for other agents / check the vault first" and
  does **not** trigger on ordinary editing — sanity-check phrasing against the
  skill-creator guidance.
- No instruction in the skill contradicts the engine (e.g. it must not tell agents to set
  engine-owned fields, or treat `flagged` as an error).

## 5a. Implementation status (done)
Implemented at `.claude/skills/knowledge-vault/SKILL.md`; the skill registers and is
discoverable. Acceptance verified: schema matches `models.Note` field-for-field
(incl. `--run-id` ↔ `client_run_id`); the documented commands reproduce `inserted` (clean
note) and `flagged` (near-identical title) from a fresh vault; no instruction contradicts
the engine. Vault location is referenced as the `KNOWLEDGE_VAULT` env var (fallback
`./vault`) pending the Stage-3 decision.

## 5b. Deployment & cross-vendor sync
The repo skill (`.claude/skills/knowledge-vault/SKILL.md`) is the **single source of truth**;
deployed copies are kept in sync by `scripts/sync_skill.py`:
- `python scripts/sync_skill.py` — copy source → managed targets (currently the user-level
  Claude skill `~/.claude/skills/knowledge-vault/`, so it reaches every project).
- `--check` — report drift only, exit 1 if any (suitable for a pre-commit/CI gate).
- `--emit-portable` — print a **vendor-neutral** rendering (Claude trigger frontmatter
  dropped, the `description` surfaced as a "When to use" section) for agents that don't read
  `SKILL.md`.

**Non-Claude agents.** There is no shared cross-vendor skill location — `SKILL.md` is
Claude-specific. Reach others by *placing* the `--emit-portable` output:
- **OpenAI Codex CLI** reads `AGENTS.md` (repo-root, plus a merged global `~/.codex/AGENTS.md`).
  Pipe the portable output into one of those.
- **ChatGPT app / Custom GPT** uses UI-configured *Custom Instructions* / *Instructions* —
  paste the portable output there.
The script deliberately does **not** auto-write those: a global `AGENTS.md` or a Custom GPT's
instructions usually hold other content, so overwriting them would be destructive. (Verify
each vendor's convention against your installed version — they move fast.)

## 6. Open decisions — RESOLVED
- **Skill name / trigger phrasing** → named `knowledge-vault`; description written with
  explicit positive triggers ("save this to the vault" / "check the vault") and negatives
  (no ordinary edits / scratch notes / TODOs). A formal `skill-creator` eval pass is still
  available if trigger precision needs tightening once real usage data exists — not run yet.
- **Convenience wrapper vs raw CLI** → **raw CLI** (no wrapper added). Revisit only if
  Stage-3 usage shows the raw invocation is error-prone.
