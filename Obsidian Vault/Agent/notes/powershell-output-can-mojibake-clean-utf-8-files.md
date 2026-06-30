---
Type: Agent Note
Status: Active
CreatedAt: 2026-06-25T22:16:45.734106+00:00
LastUpdated: 2026-06-25T22:16:45.734106+00:00
Tags:
  - windows
  - powershell
  - encoding
  - debugging
title: PowerShell output can mojibake clean UTF-8 files
id: d636f2fe799c4caa8d9147e38e76641a
contributed_by: agent:codex
source:
related_ids: []
client_run_id: codex-2026-06-25-powershell-utf8-mojibake
schema_version: 2
---
On Windows, PowerShell or the shell bridge can display clean UTF-8 file content as mojibake, for example arrows and em dashes appearing as garbled multi-character sequences. Do not assume the file bytes are corrupted from terminal output alone. Verify with a UTF-8-aware read, such as a short Python script using Path.read_text with encoding='utf-8' and sys.stdout.reconfigure(encoding='utf-8'), or inspect bytes directly before editing.
