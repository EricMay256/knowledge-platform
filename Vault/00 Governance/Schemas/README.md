# Governance Schemas (machine-readable)

These `*.yml` files are the **machine-readable counterpart** to the prose
governance docs one level up:

| Schema file   | Prose source of truth                          |
| ------------- | ---------------------------------------------- |
| `global.yml`  | `Metadata Standard.md` (universal properties)  |
| `types.yml`   | `Type Dictionary.md` + `Status Map.md`         |
| `folders.yml` | `AI Contribution Policy.md` (write policy)      |

They are consumed by the `vault_governance` engine package
(`engine/vault_governance/`) to drive **property inheritance**, **schema
validation**, and **metadata linting**. They are *not* knowledge notes.

## ⚠️ Markdown-only exception

The Vault is otherwise **markdown-only** so that Obsidian and Syncthing only
ever handle notes (functional code lives in `engine/`). This `Schemas/` folder
is a deliberate, documented exception: the machine schema is kept beside its
prose counterpart instead of in `engine/`.

### Operator follow-up (do this once)

So these `.yml` files don't clutter Obsidian or sync to devices:

1. **Obsidian** — Settings → *Files & Links* → **Excluded files** → add
   `00 Governance/Schemas`. (Optionally also hide non-markdown via the *File
   Explorer*; Obsidian already ignores non-`.md` files in most views.)
2. **Syncthing** — add `00 Governance/Schemas` to the folder's `.stignore`
   if you don't want the schema replicated to phones/tablets. (CI and the
   engine read it from the git checkout regardless, so excluding it from sync
   is safe.)

The files **must stay committed to git** — the validator and CI read them from
the checkout.

## Keeping prose and schema in sync

`engine/tests/test_governance_schema.py` guards against the schemas drifting
out of structural shape. When you change a governance rule, update **both** the
prose doc and the matching schema file in the same commit.
