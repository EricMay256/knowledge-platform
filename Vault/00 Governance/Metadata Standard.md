---
CreatedAt: 2026-06-29T19:08:50Z
LastUpdated: 2026-06-30T16:36:10Z
---
# Metadata Standard

### Universal Properties:

| Property    | Type            | Allowed Values                                   | Applicable to                      | Required when Applicable? |
| ----------- | --------------- | ------------------------------------------------ | ---------------------------------- | ------------------------- |
| Type        | Enum            | Defined in [[Type Dictionary]]                   | All Notes                          | Yes                       |
| Status      | Enum            | Defined by type in [[Status Map]]                | Notes with a meaningful lifecycle  | Yes                       |
| CreatedAt   | DateTime        | ISO-8601                                         | All Notes                          | Yes                       |
| LastUpdated | DateTime        | ISO-8601                                         | All Notes                          | Yes                       |
| tags        | List\<string>   | Freeform                                         | All Notes                          | Optional                  |
| aliases     | List\<string>   | Freeform                                         | All Notes                          | Optional                  |
| ReviewFreq  | Enum            | Daily, Weekly, Monthly, Quarterly, Yearly, Never | Notes intended for periodic review | Optional                  |
| Parent      | List\<WikiLink> | Wikilinked Notes                                 | All Notes                          | No                        |
| DependsOn   | List\<WikiLink> | Wikilinked Notes                                 | All Notes                          | No                        |
| SeeAlso     | List\<WikiLink> | Wikilinked Notes                                 | All Notes                          | No                        |

Note that Obsidian defined properties 'tags' and 'aliases' are not capitalized.

### Type Specific Properties

Some properties are held by only some Types

#### Project

| Property         | Type            | Allowed Values | Required? |
| ---------------- | --------------- | -------------- | --------- |
| Priority         | Enum            |                | Yes       |
| Goal             | Enum            |                | Yes       |
| Area             | WikiLink        |                | No        |
| SourceRepository | URL             |                | No        |
| Owner            | WikiLink        |                | No        |
| Collaborators    | List\<WikiLink> |                | No        |

#### Area

| Property | Type | Allowed Values | Required? |
| -------- | ---- | -------------- | --------- |
| Mission  | enum |                |           |

#### Decision

| Property     | Type | Allowed Values | Required? |
| ------------ | ---- | -------------- | --------- |
| Outcome      |      |                |           |
| Date         | Date |                |           |
| Context      | Enum |                |           |
| Alternatives |      |                |           |
| Consequences |      |                |           |

#### Reference

| Property | Type | Allowed Values                     | Required? |
| -------- | ---- | ---------------------------------- | --------- |
| Subtype  | Enum | Website, Technology, Language, App | Yes       |

#### Resource

| Property     | Type | Allowed Values | Required? |
| ------------ | ---- | -------------- | --------- |
| Subtype      |      |                | No        |
| URL          |      |                | No        |
| Author       |      |                | No        |
| Publisher    |      |                | No        |
| Organization |      |                | No        |

#### Person

| Property     | Type | Allowed Values | Required? |
| ------------ | ---- | -------------- | --------- |
| Role         |      |                |           |
| Organization |      |                |           |
| ContactInfo  |      |                |           |

#### System

| Property   | Type | Allowed Values | Required? |
| ---------- | ---- | -------------- | --------- |
| Purpose    |      |                |           |
| Components |      |                |           |
| Interfaces |      |                |           |
| Owner      |      |                |           |
|            |      |                |           |

#### Summary Notes

| Property  | Type | Allowed Values | Required? |
| --------- | ---- | -------------- | --------- |
| Source    |      |                |           |
| Author    |      |                |           |
| Published |      |                |           |
| URL       |      |                |           |
| DateRead  |      |                |           |

#### Meetings

| Property  | Type | Allowed Values | Required? |
| --------- | ---- | -------------- | --------- |
| Date      |      |                |           |
| Attendees |      |                |           |
| Location  |      |                |           |
| Organizer |      |                |           |

#### Ideas

| Property   | Type | Allowed Values | Required? |
| ---------- | ---- | -------------- | --------- |
| Confidence |      |                |           |

#### Concept

| Property      | Type | Allowed Values | Required? |
| ------------- | ---- | -------------- | --------- |
| Domain        |      |                |           |
| ParentConcept |      |                |           |

#### Agent Note

`Agent/` notes carry the universal properties above (`Type: Agent Note`, `Status`,

`CreatedAt`, `LastUpdated`, `Tags`) **plus** engine-owned plumbing written and read by the

contribution engine. These are **not hand-edited** — the engine assigns and maintains them.

| Property       | Type          | Allowed Values        | Required? | Notes                                            |
| -------------- | ------------- | --------------------- | --------- | ------------------------------------------------ |
| title          | String        | Freeform              | Yes       | The dedup key in Stage A; mirrored by the filename slug. |
| id             | String (hex)  | Engine-assigned       | Yes       | Stable identity; never edit.                     |
| contributed_by | String        | `agent:<id>` / `human:<name>` | Yes | Namespaced provenance; both are first-class.     |
| source         | String        | URL or run id         | No        | Provenance.                                      |
| related_ids    | List\<String> | Engine-assigned ids   | No        | Links surfaced by dedup/linking.                 |
| client_run_id  | String        | Freeform              | No        | Idempotency key; reuse makes a retry a no-op.    |
| schema_version | Integer       | Engine-assigned       | Yes       | Current: 2.                                      |

> The keys above are intentionally lowercase to mark them as engine plumbing, visually
> distinct from the curated TitleCase universal properties. Leave them alone in Obsidian.

### Known non-standard / legacy keys

Notes predating this standard use some keys that are not (yet) part of it. The governance
validator recognizes them and suggests the canonical equivalent rather than reporting a blunt
"unknown property". Prefer the canonical key in new notes.

| Observed key          | Status        | Canonical equivalent                          |
| --------------------- | ------------- | --------------------------------------------- |
| `tags`                | legacy casing | `Tags`                                        |
| `aliases`             | legacy casing | `Aliases`                                     |
| `Review Freq`         | legacy casing | `ReviewFreq`                                  |
| `Related`, `Links`    | non-standard  | `SeeAlso` (or `DependsOn` / `Parent`)         |
| `Category`            | non-standard  | `Subtype` (Reference/Resource) — no universal eq. |
| `Owner/Collaborators` | non-standard  | `Owner` + `Collaborators` (separate keys)     |

### Machine-readable schema

This document is mirrored by machine-readable schemas under `00 Governance/Schemas/`
(`global.yml`, `types.yml`, `folders.yml`), consumed by the `vault_governance` engine package
for inheritance, validation, and linting. When you change a rule here, update the matching
schema file in the same commit. See `00 Governance/Schemas/README.md`.
