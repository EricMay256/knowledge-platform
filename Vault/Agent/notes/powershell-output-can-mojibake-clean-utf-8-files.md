---
Type: Agent Note
Status: Active
CreatedAt: 2026-06-25T22:16:45.734106+00:00
LastUpdated: 2026-06-30T16:46:10Z
tags:
  - windows
  - powershell
  - encoding
  - debugging
Title: PowerShell output can mojibake clean UTF-8 files
ID: d636f2fe799c4caa8d9147e38e76641a
ContributedBy: agent:codex
Source:
RelatedIDs: []
ClientRunID: codex-2026-06-25-powershell-utf8-mojibake
SchemaVersion: 2
---
# powershell-output-can-mojibake-clean-utf-8-files

On Windows, PowerShell or the shell bridge can display clean UTF-8 file content as mojibake, for example arrows and em dashes appearing as garbled multi-character sequences. Do not assume the file bytes are corrupted from terminal output alone. Verify with a UTF-8-aware read, such as a short Python script using Path.read_text with encoding='utf-8' and sys.stdout.reconfigure(encoding='utf-8'), or inspect bytes directly before editing.
