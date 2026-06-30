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

Property keys are **PascalCase** by convention. The exceptions are the three Obsidian-reserved
keys — `tags`, `aliases`, and `cssclasses` — which stay lowercase so Obsidian's native handling
recognizes them.

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
`CreatedAt`, `LastUpdated`, `tags`) **plus** engine-owned plumbing written and read by the
contribution engine. These are **not hand-edited** — the engine assigns and maintains them.

| Property      | Type          | Allowed Values        | Required? | Notes                                            |
| ------------- | ------------- | --------------------- | --------- | ------------------------------------------------ |
| Title         | String        | Freeform              | Yes       | The dedup key in Stage A; mirrored by the filename slug. |
| ID            | String (hex)  | Engine-assigned       | Yes       | Stable identity; never edit.                     |
| ContributedBy | String        | `agent:<id>` / `human:<name>` | Yes | Namespaced provenance; both are first-class.     |
| Source        | String        | URL or run id         | No        | Provenance.                                      |
| RelatedIDs    | List\<String> | Engine-assigned ids   | No        | Links surfaced by dedup/linking.                 |
| ClientRunID   | String        | Freeform              | No        | Idempotency key; reuse makes a retry a no-op.    |
| SchemaVersion | Integer       | Engine-assigned       | Yes       | Current: 2.                                      |

> All property keys are **PascalCase**, including this engine plumbing. The only exceptions are
> the three Obsidian-reserved keys — `tags`, `aliases`, `cssclasses` — which stay lowercase so
> Obsidian's native handling recognizes them. The plumbing above is engine-owned: leave it
> alone in Obsidian.

### Known non-standard / legacy keys

Notes predating this standard use some keys that are not (yet) part of it. The governance
validator recognizes them and suggests the canonical equivalent rather than reporting a blunt
"unknown property". Prefer the canonical key in new notes.

| Observed key            | Status        | Canonical equivalent                          |
| ----------------------- | ------------- | --------------------------------------------- |
| `Tags`                  | legacy casing | `tags` (Obsidian-reserved, lowercase)         |
| `Aliases`               | legacy casing | `aliases` (Obsidian-reserved, lowercase)      |
| `Review Freq`           | legacy casing | `ReviewFreq`                                  |
| lowercase plumbing (`id`, `title`, `schema_version`, …) | legacy casing | PascalCase (`ID`, `Title`, `SchemaVersion`, …) |
| `Related`, `Links`      | non-standard  | `SeeAlso` (or `DependsOn` / `Parent`)         |
| `Category`              | non-standard  | `Subtype` (Reference/Resource) — no universal eq. |
| `Owner/Collaborators`   | non-standard  | `Owner` + `Collaborators` (separate keys)     |

### Machine-readable schema

This document is mirrored by machine-readable schemas under `00 Governance/Schemas/`
(`global.yml`, `types.yml`, `folders.yml`), consumed by the `vault_governance` engine package
for inheritance, validation, and linting. When you change a rule here, update the matching
schema file in the same commit. See `00 Governance/Schemas/README.md`.
