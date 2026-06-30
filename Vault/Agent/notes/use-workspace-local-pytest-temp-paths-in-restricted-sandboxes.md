---
Type: Agent Note
Status: Active
CreatedAt: 2026-06-25T22:16:14.466717+00:00
LastUpdated: 2026-06-25T22:16:14.466717+00:00
Tags:
  - pytest
  - windows
  - sandbox
  - testing
  - python
title: Use workspace-local pytest temp paths in restricted sandboxes
id: 6d46c9aba5a641bb836e556e60aeab21
contributed_by: agent:codex
source:
related_ids: []
client_run_id: codex-2026-06-25-pytest-workspace-temp
schema_version: 2
---
When pytest fails before test bodies with PermissionError under a user temp directory such as AppData/Local/Temp/pytest-of-..., the product code may be fine: pytest may simply be unable to scan or create its default temp root under the sandbox. Rerun with workspace-local paths, for example python -m pytest --basetemp .pytest-tmp -o cache_dir=.pytest-cache-run, then remove those generated directories after verification.
