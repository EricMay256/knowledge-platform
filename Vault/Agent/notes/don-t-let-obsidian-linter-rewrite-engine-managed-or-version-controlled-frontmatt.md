---
Type: Agent Note
Status: Active
CreatedAt: 2026-06-30T23:40:16.310532+00:00
LastUpdated: 2026-06-30T23:40:16.310532+00:00
tags:
  - obsidian
  - frontmatter
  - gotcha
  - configuration
Title: Don't let Obsidian Linter rewrite engine-managed or version-controlled frontmatter
ID: b88c80597b674e2a97c88cb506099fcc
ContributedBy: agent:claude-code
Source:
RelatedIDs: []
ClientRunID: claude-2026-06-30-obsidian-linter-frontmatter
SchemaVersion: 2
---
Obsidian's Linter plugin, with "Lint on file change" / "Lint on save" enabled, rewrites a note's YAML frontmatter whenever you open or save it. In a git- or Syncthing-backed vault this causes two distinct failures:

1. Timestamp churn on mere access. If the YAML Timestamp rule sources the modified date from the file system (mtime), the linter writes the OS modification time into the note. Git operations (checkout, branch switch, pull, stash) and sync tools constantly rewrite mtimes, so just opening a note rewrites its modified-date property and nothing else — endless one-line diffs. Fix: set the modified-date "source of truth" to frontmatter / "user or Linter edits", not "file system", and disable "Lint on file change".

2. Corrupting machine-managed notes. If an external engine writes notes with specific frontmatter keys, a linter rule (key casing/sort/etc.) will rename or strip them — e.g. PascalCasing id->ID, title->Title — and the engine then crashes reading them (KeyError). Fix: add engine-managed folders to the linter's "Folders to ignore". Treat machine-owned frontmatter as code, not prose.

General rule: never point an auto-formatter at frontmatter that another program owns, or that lives under version control, unless its trigger and date-source are configured to change only on genuine edits.
