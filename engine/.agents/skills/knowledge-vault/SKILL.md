---
name: knowledge-vault
description: >-
  Contribute durable, reusable insights to the shared knowledge vault (validation
  and deduplication happen automatically) and retrieve what the vault already knows
  before solving a problem. Use when you want to record a learning, decision,
  gotcha, or technique for other agents and humans to reuse, "save this to the
  vault," or "check the vault" for prior knowledge on a topic. Do NOT use for
  ordinary file edits, scratch notes, transient TODOs, or anything not meant to
  outlive the current task.
---

# Knowledge Vault

A shared store of markdown notes that both agents and humans read from and write to.
Every contribution goes through one gate — **validate → dedup → decide → write** — so
the vault doesn't accrete near-duplicates. You don't implement any of that; you call the
contribution engine and interpret its result.

This is **Stage A**: a git repo of markdown files with crude (normalized-title) dedup.
The read path below (grep/read) is Stage-A specific and will be replaced by a query tool
in a later stage — everything else is stable.

## Where the vault lives

There is **one shared Agent vault**: the `Agent/` layer of the knowledge-platform repo — a
directory holding `notes/` (active) and `review/` (flagged dupes awaiting adjudication),
browsable in Obsidian alongside the human notes. Point the engine at it with the
`KNOWLEDGE_VAULT` environment variable set to `<repo>/Vault/Agent`, or pass
`--vault "<repo>/Vault/Agent"`. (With neither set the CLI falls back to
`~/knowledge-vault`.)

The vault lives **inside the knowledge-platform monorepo**, so the engine is monorepo-aware:
each contribution auto-commits against that repo (git history is the audit log) and it never
creates a nested git repo. Agent notes follow the repo's governance — type `Agent Note`,
flat and tag-organized (see `00 Governance/`).

Prerequisites: Python ≥ 3.10 and the engine installed (`pip install -e .` from the engine
repo, one dep `pyyaml`). Once installed, `python -m vault_contrib.cli …` runs from any
directory; an equivalent `vault-contrib …` console command also exists if the install's
scripts dir is on your PATH.

## Step 1 — Retrieve before you contribute (Stage A: grep/read)

Always check what the vault already holds before adding, to build on existing notes and
avoid obvious duplicates:

- Find the vault path: `$KNOWLEDGE_VAULT`, else `~/knowledge-vault`.
- Search titles and bodies: grep the topic over `<vault>/notes/`.
- Browse by tag — `tags` are the vault's organizing axis (storage is flat):
  `python -m vault_contrib.cli list --tag <tag>` filters; `… index` (re)writes a tag-grouped
  `INDEX.md` at the vault root for click-through browsing.
- Read the promising matches. If an existing note already captures your insight, **don't
  contribute** — at best you'd be flagged as a duplicate.
- Glance at `<vault>/review/` too; the idea may already be queued for adjudication.

> This grep/read step is the part most likely to change later (a query/MCP tool replaces
> it). Treat the *contribution* path below as the stable interface.

## Step 2 — Contribute

Write one self-contained insight per note. Call the CLI and parse the JSON it prints:

```bash
python -m vault_contrib.cli contribute \
  --by agent:my-id \
  --title "Two-phase tick updates" \
  --body "Read into a buffer, then commit, so iteration order doesn't bias spread." \
  --tags simulation,determinism
```
(No `--vault` — it resolves to the central vault. Add `--vault <path>` only to override.)

### Note schema (what you set)

| field | required | notes |
|---|---|---|
| `--title` | yes | Short, specific, searchable. **Titles are the dedup key in Stage A** — a near-identical title flags. |
| `--body` | yes | Markdown. The durable insight, self-contained enough to be useful out of context. |
| `--by` | yes | Contributor id, namespaced: `agent:<id>` for an agent, `human:<name>` for a person. Both are first-class. |
| `--tags` | no | Comma-separated, non-empty, no duplicates. **Tags are how the vault is organized** (storage is flat) — tag thoughtfully and prefer the existing vocabulary over inventing new tags. |
| `--source` | no | Provenance — a URL or run id. |
| `--run-id` | no | Idempotency key. Pass a **stable** value when you may retry, so a retry is a no-op instead of a second note that flags as a duplicate of the first. |

Engine-owned — **do not try to set these**: `id`, `created_at`, `status`, `related_ids`,
`schema_version`.

## Step 3 — Interpret the result

The CLI prints JSON (`status`, `note_id`, `message`, `errors`, `similars`) and sets an
exit code: **`0`** for a write outcome (`inserted`/`linked`), **non-zero** otherwise.

| status | meaning | what you do |
|---|---|---|
| `inserted` | added to `notes/` | done |
| `linked` | added and linked to related notes (later stages only) | done |
| `flagged` | possible duplicate; the note was written to `review/` for a human/agent to adjudicate later | **Not a failure, and not yours to retry or rewrite.** Read `similars`; if your note genuinely adds nothing, drop it. Otherwise leave it for adjudication. |
| `rejected` | near-identical to an existing note (only if a reject policy is configured; not the Stage-A default) | drop or substantially revise |
| `invalid` | failed validation | fix per `errors` and retry (a `--run-id` retry is safe) |

### Worked example — a near-duplicate flags

```bash
python -m vault_contrib.cli contribute \
  --by agent:other --title "two-phase TICK updates!!" --body "Same idea, different words."
```
```json
{
  "status": "flagged",
  "note_id": "b27d16e1…",
  "message": "flagged for review: possible duplicate of 87cd5835… (score=1.000)",
  "errors": [],
  "similars": [{ "note_id": "87cd5835…", "title": "Two-phase tick updates", "score": 1.0 }]
}
```
Exit code is non-zero. `flagged` means "queued for review," not "failed."

## Listing

```bash
python -m vault_contrib.cli list
```

## Conventions

- **Retrieve first.** Don't contribute what the vault already has.
- **`flagged` ≠ failed.** It's a deferred decision in `review/`; never auto-retry it.
- **Don't hand-edit `review/`** — adjudication is a deliberate curation step.
- **Don't hand-create files in `notes/`** — always go through the CLI so you get validation,
  dedup, an id, and a commit. (Editing an existing note's body by hand is fine; keep the
  frontmatter intact and commit it.)
- **Git history is the audit log** — each contribution is one commit; don't rewrite it.
- **Humans contribute too**, through this same CLI (`--by human:<name>`). Expect human- and
  agent-authored notes side by side and treat them identically.
