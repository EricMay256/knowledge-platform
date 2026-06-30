---
Type: Agent Note
Status: Active
CreatedAt: 2026-06-25T21:15:34.340057+00:00
LastUpdated: 2026-06-25T21:15:34.340057+00:00
tags:
  - knowledge-vault
  - dedup
  - gotcha
Title: Knowledge vault Stage-A dedup keys on title only
ID: 8afd4672c7a34c129cb3c0ada734bd2c
ContributedBy: agent:claude-code
Source:
RelatedIDs: []
ClientRunID:
SchemaVersion: 2
---
The contribution engine's automatic dedup compares normalized TITLES, not bodies, in Stage A. So two notes expressing the same insight under different titles both insert cleanly — the engine will not flag them. The manual grep-over-notes/ retrieve-first step is therefore the ONLY body-level duplicate check available; treat it as mandatory, not optional. (This changes when the planned query/MCP tool replaces grep retrieval.)
