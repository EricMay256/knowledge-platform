# Browsing the vault in Obsidian

[Obsidian](https://obsidian.md) is a free local-markdown app that opens a folder (it calls
them "vaults") and reads YAML frontmatter `tags` — so the knowledge vault works in it with
**no conversion**: your existing notes already populate Obsidian's Tags pane and search.

## Setup (≈1 minute)

1. Install Obsidian (free).
2. **Open folder as vault** → select `~/knowledge-vault` (or wherever `$KNOWLEDGE_VAULT`
   points).
3. Browse by tag: open the **Tags** pane (core plugin), or search `tag:#dedup`. Click a note
   to read it; the frontmatter shows as **Properties**.

That's the whole "non-console browse" — titles, tags, click to open — using a polished app
you don't have to maintain.

## Good to know

- **Obsidian shows the filename (the title slug), not the frontmatter `title`.** Slugs are
  readable (`knowledge-vault-location-and-resolution`). If you want the exact title shown,
  the community plugin **Front Matter Title** displays the `title:` field instead.
- Engine-owned frontmatter (`id`, `status`, `schema_version`, …) appears as Properties —
  harmless; leave it alone.
- The graph view is sparse: notes are linked by **tags**, not `[[wikilinks]]`. That's expected
  — tags are the vault's organizing axis.

## Guardrails (so Obsidian use stays compatible with the engine)

- **Don't create new notes in Obsidian.** Creating a file directly bypasses validation,
  dedup, and id assignment (it lands without frontmatter/id). Always add notes via the
  engine: `vault-contrib contribute …` or the `knowledge-vault` skill.
- **Editing an existing note's body is fine** — keep the frontmatter intact. Obsidian doesn't
  touch git, so commit your edits: `git -C ~/knowledge-vault commit -am "edit: …"`, or install
  the **Obsidian Git** community plugin to auto-commit/sync.
- **Don't hand-edit `review/`** — adjudication is a deliberate curation step (see the runbook).

## Vault hygiene (already applied)

The vault carries a `.gitignore` and `.gitattributes` so Obsidian doesn't pollute the audit
log or churn line endings:

- `.obsidian/` (workspace/config) and `.trash/` are ignored.
- `INDEX.md` (derived by `vault-contrib index`) is ignored — regenerate on demand, or remove
  it from `.gitignore` if you'd rather commit a browsable snapshot.
- `*.md text eol=lf` keeps note line endings as LF regardless of editor, which both stops
  spurious "modified" churn and keeps the frontmatter parser happy.
