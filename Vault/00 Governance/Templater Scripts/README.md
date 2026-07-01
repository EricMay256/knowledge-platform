---
Type: Note
Status:
CreatedAt:
LastUpdated: 2026-07-01T19:06:50Z
tags:
aliases:
---
# Templater Scripts (machine-readable)

JavaScript **user scripts** for the [Templater](https://github.com/SilentVoid13/Templater)

community plugin. Templater's *User Scripts folder* points here

(`Settings → Templater → User Scripts folder = 00 Governance/Templater Scripts`),

which exposes each exported function as `tp.user.<name>` inside a template.

They live in `00 Governance/` for the same reason the machine schemas do: this is

shared machinery that templates and the `vault_governance` engine both depend on,

kept beside the governance rules it reads rather than off in `engine/`.

| Script         | Purpose                                                                    | Needs `require` |
| -------------- | -------------------------------------------------------------------------- | --------------- |
| `newNote.js`   | Orchestrates a creation template: title → Status → optional props → CreatedAt | no            |
| `vaultType.js` | Reads `Schemas/types.yml` → a type's Status list, home folder, recommended props | no          |
| `pickProps.js` | Multi-select of optional properties (checkbox modal, or native ✓ Done picker) | falls back    |

Every note-creation template in `Templates/` is a thin shell: it calls

`tp.user.newNote(tp, "<Type>")`, prints the returned values into frontmatter, and

files the note. Type-specific behavior (statuses, home folder, recommended props)

comes entirely from `types.yml`, so adding or changing a type needs no edit here.

## Loading & mobile

Templater scans this folder **once, at plugin load**. After adding/renaming a

script, **reload Templater** (toggle it off/on in Community plugins, or restart

Obsidian) so the new `tp.user.*` functions register. To confirm they loaded:

`Settings → Templater → User Script Functions` lists the detected functions.

`newNote.js` and `vaultType.js` are `require`-free, so the core creation flow works

on **desktop and mobile**. `pickProps.js` prefers Obsidian's `Modal`/`Setting`

(`require("obsidian")`) for a real checkbox modal, but where that isn't reachable

(mobile, or desktop builds without `window.require`) it automatically falls back to

a native repeated `tp.system.suggester` picker — no `require`, works everywhere.

## ⚠️ Markdown-only exception

Like `Schemas/`, this folder is a deliberate exception to the Vault's

markdown-only rule. The `.js` files **must stay committed to git** so Templater

loads them, but you may exclude the folder from Obsidian's file explorer

(Settings → *Files & Links* → Excluded files) and from Syncthing (`.stignore`).

## Single source of truth

`vaultType.js` reads the same `Schemas/types.yml` that drives the validator, so a

creation template can never offer a Status or recommended property the schema

doesn't define. Add or rename a type/status/property in `types.yml` and the

templates pick it up with no change here.
