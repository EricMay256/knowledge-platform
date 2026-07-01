---
Type: Project
Status: Active
CreatedAt: 2026-06-25T05:49:08Z
LastUpdated: 2026-07-01T02:36:10Z
tags:
  - data
  - skill
aliases:
Owner: Me
SeeAlso:
  - "[[AI or LLMs]]"
  - "[[Agent Skills]]"
  - "[[Databases]]"
---
# Agentic Knowledge Vault

## Related

[[Personal Project INDEX]],

## Outcome

What “done” looks like, in one or two concrete sentences.

## Why it matters

As frontier models solve problems, they often find effective solutions, and by documenting the knowledge and universal truths they work with as they go they can inform other agents of what they have learned without the inference cost, organized effectively so that a scanning of file names gives a reliable indicator of their contents.

## Current state

- What is already complete:
	- Roadmap: First a github repo/file based system wrapped in a skill, then a postgres database
	- Proof of concept for primary github repo version
- What is in progress:
	- Generating thorough data on the skill
	- Iteration on the skill to improve performance
	- Diagnose fail states, causes, and remedies
	- Through usage, establish what should be placed into skill (consider refactoring logic)
- What is blocked / uncertain:
	- Will it cohost nicely alongside HSS

## Next action

Continue generating diverse data for the database, and check the skill's performance and behavior

## Milestones

- [ ] Milestone 1 - Polished Version "A" (local access through shared local vault)
- [ ] Milestone 2 - Version "B2" - HTTP exposing postgres backend containing notes
	- Supports concurrency (~10 concurrent agents) and remote providers better
	- Hosting requirement
- [ ] Milestone 3 - Introduce significant overhaul for deduplication of entries
	- Involved with creating/searching entries ("Find entries related to X")

## Scope

Included
-

Not included
-

## Decisions & rationale

| Date       | Decision | Why |
| ---------- | -------- | --- |
| YYYY-MM-DD |          |     |

## Risks / open questions

- 

- 

## Notes & useful context

- Titles/filenames holding functional summaries is vital
- Flat directory of notes with tagging preferred
	- Users can probably set their own folder structure without too much issue

## Activity log

- 2026-06-25 — Implemented version A with local knowledge vault created
