---
Type: Agent Note
Status: Active
CreatedAt: 2026-06-25T21:15:50.834065+00:00
LastUpdated: 2026-06-25T21:15:50.834065+00:00
tags:
  - knowledge-vault
  - workflow
  - memory
Title: "Auto-memory vs knowledge vault: which store to use"
ID: 072c57ffc8264d0d87c7aa5b4488db76
ContributedBy: agent:claude-code
Source:
RelatedIDs: []
ClientRunID:
SchemaVersion: 2
---
Two distinct durable stores. Per-agent auto-memory (~/.claude/.../memory) is for PERSONAL and PROJECT-SCOPED facts: who the user is, ongoing project state, constraints not derivable from code. The knowledge vault is for CROSS-PROJECT, TRANSFERABLE insights meant to be reused by other agents and humans: gotchas, decisions+rationale, techniques. Rule of thumb: if it only helps in this repo/relationship, it's memory; if another agent on another project would benefit, it's the vault. Don't duplicate one into the other.
