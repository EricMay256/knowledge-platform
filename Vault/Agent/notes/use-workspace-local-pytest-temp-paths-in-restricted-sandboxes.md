---
Type: Agent Note
Status: Active
CreatedAt: 2026-06-25T22:16:14.466717+00:00
LastUpdated: 2026-06-25T22:16:14.466717+00:00
tags:
  - pytest
  - windows
  - sandbox
  - testing
  - python
Title: Use workspace-local pytest temp paths in restricted sandboxes
ID: 6d46c9aba5a641bb836e556e60aeab21
ContributedBy: agent:codex
Source:
RelatedIDs: []
ClientRunID: codex-2026-06-25-pytest-workspace-temp
SchemaVersion: 2
---
When pytest fails before test bodies with PermissionError under a user temp directory such as AppData/Local/Temp/pytest-of-..., the product code may be fine: pytest may simply be unable to scan or create its default temp root under the sandbox. Rerun with workspace-local paths, for example python -m pytest --basetemp .pytest-tmp -o cache_dir=.pytest-cache-run, then remove those generated directories after verification.
