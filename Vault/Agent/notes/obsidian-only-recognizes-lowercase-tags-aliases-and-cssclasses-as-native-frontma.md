---
Type: Agent Note
Status: Active
CreatedAt: 2026-06-30T23:40:26.861922+00:00
LastUpdated: 2026-07-01T00:05:16Z
tags:
  - obsidian
  - frontmatter
  - reference
  - gotcha
Title: Obsidian only recognizes lowercase tags, aliases, and cssclasses as native frontmatter
ID: 163f7b1fd1cc481399750bfeefe209c6
ContributedBy: agent:claude-code
Source:
RelatedIDs: []
ClientRunID: claude-2026-06-30-obsidian-reserved-lowercase-keys
SchemaVersion: 2
---
Obsidian treats only three frontmatter keys as built-in properties, and only when they are lowercase: tags, aliases, and cssclasses. Capitalizing them (Tags, Aliases, CssClasses) demotes them to ordinary custom properties: the tag pane and tag search stop indexing them, alias resolution and `[[` autocomplete stop working, and the cssclasses styling is not applied.

Implication for metadata standards: if a vault standardizes its other frontmatter keys on a different case (e.g. PascalCase), these three must stay lowercase as deliberate, documented exceptions — they are reserved by Obsidian, not stylistic choices. Verify by checking whether the tag pane and alias autocomplete actually pick the value up.
