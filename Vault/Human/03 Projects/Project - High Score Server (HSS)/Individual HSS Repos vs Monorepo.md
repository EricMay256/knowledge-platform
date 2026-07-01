---
Type: Decision
Status:
CreatedAt: 2026-07-01T06:25:55Z
LastUpdated: 2026-07-01T06:28:25Z
tags:
aliases:
Parent:
  - "[[Project - High Score Server (HSS)]]"
---
# Decision: Individual HSS Repos vs Monorepo

## Context

HSS consists of four repos - the application itself and three adapters/wrappers. A choice must be made about how to organize the repositories - keep a potentially growing number of individual adapter repos, or consolidate them into one repo that contains multiple distinct adapters for HSS.

## Decision

Many repos with one purpose over one monorepo.

## Rationale

This is industry standard, and costs nothing but discoverability, which isn't a problem at the depth. It's also a good way to demonstrate language and application coverage.

## Consequences

Updating adapters after a HSS update will involve touching multiple, potentially many repos.

Every repo will have commits that closely track only its changes.