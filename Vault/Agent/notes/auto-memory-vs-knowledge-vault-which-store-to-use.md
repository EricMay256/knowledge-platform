---
Type: Agent Note
Status: Active
CreatedAt: 2026-06-25T21:15:50.834065+00:00
LastUpdated: 2026-06-25T21:15:50.834065+00:00
Tags:
  - knowledge-vault
  - workflow
  - memory
title: "Auto-memory vs knowledge vault: which store to use"
id: 072c57ffc8264d0d87c7aa5b4488db76
contributed_by: agent:claude-code
source:
related_ids: []
client_run_id:
schema_version: 2
---
Two distinct durable stores. Per-agent auto-memory (~/.claude/.../memory) is for PERSONAL and PROJECT-SCOPED facts: who the user is, ongoing project state, constraints not derivable from code. The knowledge vault is for CROSS-PROJECT, TRANSFERABLE insights meant to be reused by other agents and humans: gotchas, decisions+rationale, techniques. Rule of thumb: if it only helps in this repo/relationship, it's memory; if another agent on another project would benefit, it's the vault. Don't duplicate one into the other.
