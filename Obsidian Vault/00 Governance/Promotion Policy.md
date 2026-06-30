---
CreatedAt: 2026-06-29T21:00:00Z
LastUpdated: 2026-06-29T21:00:00Z
---
# Promotion Policy

How agent-vault memory becomes durable Human knowledge. The companion to
[[AI Contribution Policy]]; see [[Vault Philosophy]] for the editorial bar.

## When to promote

A note belongs in `Agent/Promotion Candidates/` when:

> The content originated as AI operational memory, but may be worth preserving for the
> human long-term.

Examples: a recurring implementation gotcha, a useful debugging lesson, a durable workflow
discovered by agents, a condensed "lesson learned" from task history.

This is distinct from an **AI Suggestion** (Pipeline B), which proposes a specific edit to
existing Human knowledge. Promotion is about elevating agent-learned content into Human
knowledge for the first time.

## Flow

```
Agent/notes (engine memory)
  ↓  an agent or human judges it human-worthy
Agent/Promotion Candidates/
  ↓  human reviews — rewrite, condense, distill (not a blind move)
Human/06 Reference, Human/17 Concepts, Human/03 Projects, …
```

Promotion almost always involves **processing**: rewriting in the human's voice, condensing,
fitting the destination Type's template, and adding links. A promoted note becomes a
first-class Human note under the [[Metadata Standard]] (a real `Type`, `Status`, links),
not a copied agent note.

## Responsibilities

- **Agent / human contributor:** place a candidate in `Agent/Promotion Candidates/` with a
  one-line note on *why* it may deserve promotion. Do not write into `Human/` directly.
- **Human reviewer:** periodically triage the folder. For each candidate: promote (rewrite
  into the right Human area), defer (leave it), or drop (it is not durable). Nothing in
  `Agent/Promotion Candidates/` is canonical until a human promotes it.

## Relationship to the engine

Promotion Candidates is a human-curated queue, **not** an engine-managed store: the engine
owns `Agent/notes/` and `Agent/review/` (dedup, ids, commits). Candidates are staged for
human judgment, so they are kept outside the engine's dedup gate on purpose.
