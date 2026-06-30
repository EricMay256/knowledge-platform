---
CreatedAt: 2026-06-29T21:00:00Z
LastUpdated: 2026-06-29T21:00:00Z
---
# AI Contribution Policy

How agents (and humans acting through the same tools) contribute to this repository.
See [[Vault Philosophy]] for the why, [[Metadata Standard]] for note shape, and
[[Promotion Policy]] for moving agent memory into Human knowledge.

## The two layers

| Layer       | Who curates it | How content lands                                              |
| ----------- | -------------- | ------------------------------------------------------------- |
| `Human/`    | Humans         | Authored by the human; agents may only *propose* (see below). |
| `Agent/`    | The engine     | Written through the contribution engine in `/engine`.         |

`00 Governance/` is shared by both and is not duplicated inside either layer.

## Where AI may write

```
AI may write to:
  Agent/                        (via the engine — validate → dedup → decide → write)
  Human/01 Inbox/AI/            (proposals only; nothing here is canonical)

AI may NOT directly write to:
  Human/03 Projects/  Human/04 Areas/  Human/05 Decisions/
  Human/06 Reference/ Human/07 People/ Human/08 Resources/
  Human/02 Daily/     Human/17 Concepts/  (and any other canonical Human area)
```

Within the Human layer, agents work on `ai/*` branches and open pull requests; a human
reviews and merges. Agents may suggest links, metadata, and duplicate/staleness findings
anywhere, but may only create or edit **note bodies** inside `Human/01 Inbox/AI/`.

> Later: a Git hook can *enforce* this write policy on `ai/*` branches. Until then it is
> instructed, not gated.

## The two AI → Human routes

**Pipeline A — Promotion Candidates** (`Agent/Promotion Candidates/`): agent-vault memory
that later proves worth preserving for the human long-term. Origin is operational; the
human reviews, rewrites/condenses, and promotes into `Human/`. See [[Promotion Policy]].

**Pipeline B — AI Suggestions** (`Human/01 Inbox/AI/`): an agent proposing a *specific
change* to Human knowledge (a new Concept draft, a backlink, a metadata fix, a merge of
duplicates). Each proposal states what change is suggested and why.

```
Promotion Candidate = "This AI memory may be human-worthy."
AI Suggestion       = "This is a proposed change to the Human vault."
```

## Contributing to the Agent layer (the engine)

The `Agent/` layer is managed by the contribution engine in `/engine` — never hand-create
files in `Agent/notes/`. Every contribution passes one gate: **validate → dedup → decide →
write**, so the vault does not accrete near-duplicates.

- Point the engine at this layer: set `KNOWLEDGE_VAULT` to
  `<repo>/Vault/Agent`, or pass `--vault "<repo>/Vault/Agent"`.
- Retrieve before contributing: grep `Agent/notes/`, or `list --tag <tag>` / `index`.
- Contribute: `python -m vault_contrib.cli contribute --by agent:<id> --title … --body …`.
- Agent notes follow the [[Metadata Standard]] (`Type: Agent Note`) and are flat +
  tag-organized; tags are the organizing axis, not folders.

Humans are first-class contributors to the Agent layer too, via `--by human:<name>`.

## Procedure (agent checklist)

1. Read governance (this doc, [[Metadata Standard]], [[Promotion Policy]]).
2. Retrieve: search existing notes before writing.
3. Decide destination: Agent memory · Agent Promotion Candidate · Human AI Suggestion.
4. Deduplicate (the engine does this for `Agent/`; do it by hand for proposals).
5. Validate metadata against the standard.
6. Write only to an allowed location.
7. Leave a clear review trail (commit message / proposal rationale).
