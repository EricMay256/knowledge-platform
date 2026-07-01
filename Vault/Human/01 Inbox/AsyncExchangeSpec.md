---
CreatedAt: 2026-06-28T16:42:05Z
LastUpdated: 2026-07-01T00:54:08Z
Type:
Status:
tags:
aliases:
---
# Async / Asymmetric Exchange System — Implementation Spec

Roadmap #19 (specs-only at this stage). The system that lets players affect each other's

worlds **without playing simultaneously or with identical roles**: left loot caches,

placed structures, ghosts/messages, fulfillable contracts. Written to be executable cold,

in the style of `UBearInventory/Package/Documentation~/NetworkedAuthority.md`.

## 1. Concepts

- **Artifact** — one unit of cross-world influence: a versioned, checksummed payload plus
  routing metadata. Examples: a loot cache (an `InventoryRecord`!), a placed sign, a
  recorded path, a "bring me 5 iron" contract.
- **Exchange** — the store-and-forward backend through which artifacts are published and
  fetched. Never real-time; conflict tolerance comes from artifacts being immutable
  (publish/consume, not edit).
- **Role** — a data-declared capability set: what a participant may publish, fetch, and
  consume. Symmetric play = everyone holds the same role. Asymmetry (a "warden" who
  curates others' artifacts but cannot publish; a "dungeon master" who only places) is a
  different role descriptor, not different code.

## 2. Wire/storage model

```csharp
[Serializable] public class ArtifactEnvelope {
    public int FormatVersion;          // envelope schema
    public string ArtifactId;          // GUID
    public string Kind;                // "loot-cache", "message", "contract" — game vocabulary
    public int KindVersion;            // payload schema version, migratable like save sections
    public string Payload;             // kind-specific JSON (reuse existing records!)
    public string Checksum;            // SHA-256 of Payload (same discipline as saves)
    public ArtifactOrigin Origin;      // account id, character name (display), ruleset
    public ArtifactAudience Audience;  // scope selector, see §4
    public string CreatedUtc;
    public string ExpiresUtc;          // exchanges may garbage-collect
}
```

Payload reuse is the point: a loot cache's payload **is** an `InventoryRecord`; a

contract's reward **is** an `ItemQuantity[]` + `CurrencyEntry[]`. Every serialization

convention (versioned DTOs, checksums, silent-skip-unknown) already exists in this repo.

## 3. Provider interface

```csharp
public interface IArtifactExchange {
    Task<PublishResult> PublishAsync(ArtifactEnvelope artifact);
    Task<FetchResult> FetchAsync(ArtifactQuery query);          // kind, audience, max count, exclude-own
    Task<ConsumeResult> ConsumeAsync(string artifactId);        // claim-once semantics, see §6
    Task<RetractResult> RetractAsync(string artifactId);       // own artifacts only
}
```

Implementations, in build order:

1. **`LoopbackExchange`** — in-memory/local-file, single machine. All gameplay and tests
   run against this; it is also the offline mode.
2. **`FileShareExchange`** *(optional dev tool)* — a shared folder; two editors on one
   LAN exchange artifacts with zero server work. Cheap integration testing.
3. **`HttpExchange`** — small REST backend (publish/fetch/consume/retract + GC). The
   server re-verifies checksums and enforces roles; clients are untrusted.
4. **Steam-adjacent note**: Steam offers no general artifact store. Steam *identities*
   (auth tickets → SteamID64) authenticate against the HTTP exchange — reusing the
   identity model from the networked-authority spec §4 verbatim.

## 4. Identity, audience, ruleset

- Origin identity reuses the networked-authority conventions: `AccountId` = SteamID64,
  ruleset baked in. **Hardcore exchanges only with hardcore** — enforced server-side by
  filtering on `Origin.Ruleset == fetcher.Ruleset`, exactly like the inventory key rule.
- `ArtifactAudience`: `Global | Friends | Guild(id) | Direct(accountId)`. Friends/guild
  resolution is backend-side (Steam friends list via Web API, or game guilds).
- Privacy default: fetches exclude your own artifacts and are rate-limited per account.

## 5. Roles

```csharp
[Serializable] public class RoleDescriptor {
    public string RoleId;                       // "wanderer" (default), "warden", "architect"
    public string[] PublishableKinds;           // empty = none
    public string[] FetchableKinds;
    public string[] ConsumableKinds;
    public bool CanRetractOthers;               // moderation/curation capability
    public int DailyPublishLimit;
}
```

The exchange (server-side for HTTP, locally for loopback) checks every operation against

the caller's role. **The asymmetric-hooks demo requirement is satisfied by flipping one

player's descriptor at runtime and watching capabilities change with zero code edits.**

## 6. Consume-once semantics (the hard rule)

A loot cache taken by two players duplicates items. `ConsumeAsync` is therefore an atomic

claim: the first consumer gets `Claimed` + the payload; later consumers get

`AlreadyClaimed`. Loopback implements it with a dictionary remove; HTTP with a

transactional delete-returning-row. Kinds that are *not* consumable (messages, ghosts)

skip claiming and replicate freely — declared per kind in a `KindPolicy` table

(consumable?, max per fetch, TTL).

## 7. Gameplay integration (prototype scope)

The deliverable prototype is **symmetric with asymmetric hooks**, per specs.md:

1. "Leave cache" — player selects items; client builds an `InventoryRecord` payload via a
   withdraw through the **inventory authority** (items leave the world when published —
   no duplication), publishes a `loot-cache` artifact.
2. "Found a stranger's cache" — on area load, fetch up to N `loot-cache` artifacts, spawn
   pickups (the interaction system's `ItemPickup`); interacting consumes the artifact
   (claim-once) and grants via the authority.
3. Hook demo — flip one client's role to `warden`: their fetch UI gains a "retract"
   affordance, their publish affordance disappears. No code change, one descriptor swap.

Quest synergy for later: a `contract` artifact's completion check is a `QuestSignal`

relay, and its reward grant is a `QuestCompleted` listener — both systems already exist.

## 8. Package plan

```code
com.ericmay256.ubear.exchange
└── Runtime/  UBear.Exchange.asmdef                 (no deps: envelope, query, results, roles, IArtifactExchange, LoopbackExchange, KindPolicy)
    Runtime/InventoryBridge/                        (versionDefines-gated on inventory: cache payload build/consume helpers)
    Tests/    publish/fetch/consume-once/role-gating/ruleset-filter/expiry/checksum tests against LoopbackExchange
Backend/      (separate, non-Unity: minimal HTTP service; defined by an OpenAPI stub in this spec's folder when built)
```

## 9. Phases & acceptance

- **Phase A (offline-complete):** envelope + loopback + roles + kind policies + inventory
  bridge + tests. *Accept:* cache leave/find/claim-once loop runs in the demo scene
  against loopback; duplicate-claim test proves item conservation end to end.
- **Phase B (transport):** HTTP exchange + server-side role/ruleset/checksum enforcement
  + Steam-ticket auth. *Accept:* same demo against a local server instance; tampered
  payloads rejected server-side.
- **Phase C (asymmetry showcase):** warden role, retraction flow, audience selectors.
  *Accept:* role flip changes capabilities live with zero gameplay-code changes.

## 10. Open questions (decide at Phase A start)

- Artifact size cap (suggest 32 KB — an inventory record is far smaller).
- Whether consumed loot-cache items return to the publisher on expiry (roguelike "ghost
  retrieval") — supported by the model (expiry → re-grant via authority), a game-design
  choice, not an architecture one.
- Backend hosting (the smallest viable: one container + SQLite; the interface doesn't care).
