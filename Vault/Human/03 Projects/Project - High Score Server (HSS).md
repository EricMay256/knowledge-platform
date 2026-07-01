---
Type: Project
Status: Active
CreatedAt: 2026-06-24T06:00:43Z
LastUpdated: 2026-07-01T00:58:32Z
Owner: Me
SeeAlso:
  - "[[Python]]"
  - "[[Databases]]"
  - "[[Area - Career]]"
  - "[[Area - Game Development]]"
  - "[[Unity]]"
  - "[[C-Sharp]]"
  - "[[C++]]"
  - "[[Unreal]]"
SourceRepo: https://github.com/EricMay256/HighScoreServer
tags:
  - json
  - app
aliases:
---
# High Score Server (HSS)

## Outcome

Able to host ranked scores for multiple game modes across multiple games, with multiple options for game mode logic. Supports multiple games in parallel. Includes adapters for [[Unity]], [[C++]], and [[Unreal]]. Built with [[Python]] and [[Databases]]

## Why it matters

This is a common feature that is often offered as a service, which involves vendor lock in and increased dependence on a proprietary ecosystem. A good demonstration of full stack development with APIs and databases.

## Current state

- What is already complete:
	- High score submissions, automatic guest login, upgrading/claiming accounts
	- Multiple scoring logics (highest/lowest is best, cumulative)
	- Basic validation (score < Max)
- What is in progress:
	- Identity management layer with support for steam via steamworks
	- More involving forms of validation
- What is blocked / uncertain:

### Adapters

All currently target target the original release (0.1 - pre-cumulative batch of features)

1. Unity
	1. Demonstrated live via flick fest
2. C++
	1. Exercised by Unreal
3. Unreal
	1. Not currently demonstrated or tested

## Next action

Update HSS Readme to point to existing adapters (Unity, C++, Unreal)

Update adapters for latest changes and features

Implement identity management, including steam identity adapter

## Milestones

- [ ] Milestone 1 — target date if real
- [ ] Milestone 2
- [ ] Milestone 3

## Scope

Included

- High Scores
- Names, renaming, login
- Web view
- API access

Not included

- Async game moves

## Decisions & rationale

| Date | Decision | Why |
|---|---|---|
| YYYY-MM-DD |  |  |

## Risks / open questions

- 
- 

## Notes & useful context

- Key constraints, assumptions, discoveries, or context future-you will need.
- Add links to relevant notes rather than duplicating their contents.

## Activity log

- YYYY-MM-DD —**
