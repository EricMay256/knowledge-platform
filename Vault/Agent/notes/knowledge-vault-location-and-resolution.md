---
Type: Agent Note
Status: Active
CreatedAt: 2026-06-25T21:15:50.503051+00:00
LastUpdated: 2026-06-25T21:15:50.503051+00:00
Tags:
  - knowledge-vault
  - configuration
  - reference
Title: Knowledge vault location and resolution
ID: 40a6143cdc3c49b591ef9fd4167cc33d
ContributedBy: agent:claude-code
Source:
RelatedIDs: []
ClientRunID:
SchemaVersion: 2
---
One central vault is shared across all projects. The CLI resolves its path from the KNOWLEDGE_VAULT env var, falling back to ~/knowledge-vault when unset, so you normally omit --vault entirely (pass it only to target a different vault). The vault is its own git repo holding notes/ (active) and review/ (flagged dupes), and lives OUTSIDE any project tree so it's never committed into the project you're working in. Each contribution is one commit; git history is the audit log.
