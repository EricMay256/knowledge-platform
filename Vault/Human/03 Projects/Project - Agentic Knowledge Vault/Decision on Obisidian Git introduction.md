---
Type: Decision
Status: Accepted
CreatedAt: 2026-07-02T01:31:36Z
LastUpdated: 2026-07-02T01:39:52Z
tags:
aliases:
Outcome:
Date:
Context:
Parent:
  - "[[Project - Agentic Knowledge Vault]]"
---
# Decision: Decision on Obisidian Git introduction

## Context

What prompted this decision?

## Decision

Obsidian Git will not be used for synchronizing or automation. It may be used to offer diffs and history within obsidian for convenience, but will not be used to automate any actions or synchronize between clients.

## Rationale

The convenience of SyncThing between user devices works pretty well already, and the commit strategy for humans and AI are well established, this would un-separate concerns. Mobile obsidian accepts read-only status without worry, because I was never going to want to make commits from my phone.

## Consequences

Obsidian Git (or alternatively, Simple Git - desktop only) may be adopted for greater commit visibility within the vault.
