---
Type:
Status:
CreatedAt: 2026-06-28T16:42:05Z
LastUpdated: 2026-07-01T00:54:43Z
tags: []
aliases:
---

# World Structure — Dungeons, Overworld, and Realm Control

A design document and forward spec for building **dungeons** (RotMG-style snake pits,

toxic sewers, …), a **multi-biome overworld**, and the **realm-level arrangement and

control mechanics** (a four-quadrant biome realm with boss gates, dropped portal items,

and other progression locks) on top of the existing `UBearWorldGen` pipeline — sized for

a **local or small server-hosted co-op game (4–6 players)**.

This is written in the same spirit as [NetworkedAuthority.md](../UBearInventory/Package/Documentation~/NetworkedAuthority.md)

and [AsyncExchangeSpec.md](AsyncExchangeSpec.md): grounded in what ships today, explicit

about what is new, and pick-up-able cold. Nothing here is implemented yet — it is the plan.

---

## 0. What already ships (the substrate this builds on)

[`UBearWorldGen`](../UBearWorldGen/Package/README.md) gives us a seeded, composable tile

pipeline. The pieces this document leans on:

| Primitive | What it is | Why it matters here |
|---|---|---|
| `MapGenerator.Generate(w, h, seed, stages)` | Runs an `IMapStage` list over a fresh `MapGrid` | **A dungeon *kind* is a recipe (stage list). A realm is a tree of recipes.** |
| `MapRng` (xorshift64*) | The pipeline's only randomness | **Same seed ⇒ byte-for-byte identical map on every platform.** The whole multiplayer model rests on this. |
| `MapGrid.ComputeHash()` (FNV-1a) | Fingerprint of the tile field | Determinism assertion *and* the server↔client desync check. |
| `MapBuildContext.SpawnAreas` (tagged cell lists) | Stages record "where things go" | Boss cells, portal cells, loot-vault cells, enemy spawns — all just tags. |
| `IMapStage` library | Fill, Border, NoiseRegions, CellularCave, RoomsAndCorridors, SetPiece, ScatterSpawnPoints | The dungeon/overworld vocabulary. We add a handful of new stages, not a new engine. |
| `GridConnectivity.AreAllConnected` | Flood-fill reachability | "Every floor reachable / key reachable before its lock" is a generation invariant we assert. |
| `TilemapMapBuilder` (Tilemap bridge) | Production renderer: chunked tilemap + merged composite collider, themed `TileBase` legend, prefab-per-cell for props | Renders any recipe; **themes are palette + tile-set assets, so "snake pit" vs "sewer" is mostly art swap over shared stages.** |
| `MapBuilderBehaviour.Built` event + `GetSpawnPoints(tag)` | The seam | `SpawnAreaBinder` (Enemies pkg) already plants spawners on tagged cells. Boss/portal binders are the same pattern. |

**The thesis:** we already have the level *generator*. What's missing is (1) a few

dungeon-shaped stages, (2) a **realm composition layer** above single maps that owns

biome arrangement and zone graph, and (3) a **server-authoritative control/progression

layer** that decides which zones exist, who can enter, and when they unlock. Items 2 and 3

are new packages; item 1 is new stages in the existing one.

---

## Part A — Dungeons as recipes

### A.1 The model: a dungeon kind = recipe + theme + encounter bindings

Three orthogonal authoring assets compose a dungeon, mirroring the existing

recipe/palette/binder split:

- **Recipe** (`MapRecipeAsset`, exists) — the *shape*: stage list, size, seed policy.
  "Snake Pit" and "Toxic Sewers" can share a recipe and differ only in theme, or use
  different recipes when their layout genuinely differs (winding tunnels vs. room
  clusters).
- **Theme** = `TilePaletteAsset` + `TilemapTileSetAsset` (exist) — the *look*: tile id →
  color/passability and id → authored `TileBase`. The same `WALL`/`FLOOR`/`HAZARD` tile
  ids render as cave rock, sewer brick, or jungle vines per theme. **This is why one
  recipe yields many dungeons.**
- **Encounter binding** (`SpawnAreaBinder`, exists; + new `BossBinder`) — the
  *population*: tag → spawner/boss/loot prefab.

A dungeon is therefore *data*, not a scene. The same `MapBuilderBehaviour` /

`TilemapMapBuilder` plays any of them; only the three assets change.

### A.2 New stages needed

Each is an `IMapStage` in `UBear.WorldGenSystem`, pure-C#, unit-tested against

`ComputeHash()` and connectivity assertions, with a matching `*StageAsset`

(`Create → UBear → World Generation → …`) — exactly like the shipped stages.

1. **`DrunkardWalkStage`** — carves winding tunnels by a seeded random walk that tunnels
   `FLOOR` through `WALL`, with branch probability and target carved-fraction. *The snake
   pit's signature organic corridors.* Records the walk endpoints as a spawn area so the
   boss lands at the far end.

2. **`RoomGraphStage`** — generalizes `RoomsAndCorridorsStage` into an explicit **room
   graph** with a layout policy: `Linear`, `Branching` (tree), `HubAndSpoke`, `Looped`
   (tree + a few extra edges for non-backtracking flow). Records each room as a spawn area
   (`room/0`, `room/1`, …) and exposes the adjacency graph on the context so downstream
   stages can reason about it. Connectivity-by-construction is preserved.

3. **`PrefabRoomStage`** — like `SetPieceStage` but room-sized and drawn from a *pool* of
   authored room templates (entrance hall, treasure vault, puzzle room, miniboss arena),
   placed into `RoomGraphStage` slots by tag. Vault rooms record a `loot-vault` area.

4. **`LockAndKeyStage`** — consumes the room graph: walks the spanning tree from the
   entrance, designates some edges as **locked doors** (write a `DOOR_locked` tile) and
   places the matching **key** spawn marker in a room that is *upstream of the lock on the
   path from entrance* (so the dungeon is always solvable — an asserted invariant, tested
   via `GridConnectivity` over "passable ∪ openable-with-keys-held-so-far"). Keys/doors
   may be literal items (UBearInventory) or ability-gated (a switch). Generalizes to the
   realm: a "boss key" is the same mechanism one level up.

5. **`BossArenaStage`** — selects the graph's terminal/deepest room (or a tagged
   `PrefabRoomStage` arena), optionally enlarges/clears it, seals its entrance with a
   `DOOR_boss` tile, and records a single-cell `boss` spawn area at its center. Pairs with
   a new `BossBinder` (Enemies pkg, §A.4) and the existing `UBearProjectiles` warlord-style
   patterns.

6. **`HazardFloodStage`** — flood-fills a chosen tile (toxic sludge, lava, deep water)
   into low/edge regions or a noise mask, leaving guaranteed dry paths (re-checks
   connectivity over walkable tiles, backs off the flood if it would sever the map). *The
   sewer's toxic channels.*

7. **`MazeStage`**, **`TemplateAssemblyStage`**, **`ConnectComponentsStage`**, **`MirrorStage`**
   — more structural generators introduced by the deep-dive archetypes (true mazes, modular
   template assembly, cellular-cave component reconciliation, symmetric reflection). See
   [Part G](#part-g--dungeon-generation-deep-dive-twelve-archetypes). (Traversal-modifying or
   destructible tiles — ice slip, toxic damage, breakable crystal — are game-side components
   reading palette tags, not stages. The one generator-side caveat: a *required* breakable
   wall must be a recognized **passability class** so the connectivity check counts it as
   traversable — see G.11.)

> None of these need engine types; they read/write `MapGrid` and append to
> `SpawnAreas`/the context graph. They stay in the pure core and are CI-tested headless.

### A.3 Worked examples

The Snake Pit and Toxic Sewers are written out as full stage lists — alongside five more

archetypes chosen to exercise *different* generation techniques — in

[Part G: Dungeon generation deep dive](#part-g--dungeon-generation-deep-dive-twelve-archetypes).

The pattern is always the same: one recipe + one theme + one binder row set. **Add a

dungeon kind without touching code.**

### A.4 Encounter & boss wiring (Enemies/Combat/Projectiles, mostly existing)

- `SpawnAreaBinder` (ships) handles ambient spawns on tagged areas with population caps.
- **New `BossBinder`** (Enemies pkg, WorldGen bridge): single spawn on the `boss` area, a
  phase/enrage hook (the demo Warlord already does half-health enrage via `UBearCombat`
  statuses + `UBearProjectiles` patterns), and a `BossDefeated` event. That event is the
  control signal the realm layer (§C) and `UBearQuests` consume.
- Loot: rolled **server-side only** (per NetworkedAuthority §6) — `LootDropper` on the
  boss/loot-vault area. Dungeon-completion rewards (the next portal key) drop here.

### A.5 The stage catalog (consolidated)

The stages scattered through A.2 and Part G, gathered. **Kind:** *writer* mutates tiles,

*annotator* computes metadata / spawn areas (little or no tile change), *guard* asserts or

repairs an invariant. **Status:** ✅ ships today · 📐 proposed above · ➕ gap surfaced by this

review. A well-rounded *dungeon* recipe is roughly: a writer for the shape, `EntranceStage` +

`BossArenaStage` to anchor the ends, `DistanceFieldStage` for depth, scatter / decoration /

hazard / lock passes, then a connectivity guard to close. A well-rounded *biome*: a macro

writer, `MaskedSubStage` detail, `BiomeBlendStage` edges, `PathStage` connective features,

`RegionMapStage` naming. Each stage below is fleshed out with parameters, algorithms, and

feel-knobs in the **[WorldGen stage reference](WorldGenStages.md)**.

| Stage | Kind | Status | For | Purpose |
|---|---|---|---|---|
| `FillStage`, `BorderStage` | writer | ✅ | both | Canvas + rim. |
| `NoiseRegionsStage` | writer | ✅ | biome | Noise → biome tiles by threshold. |
| `CellularCaveStage` | writer | ✅ | dungeon | Organic caverns. |
| `RoomsAndCorridorsStage` | writer | ✅ | dungeon | Rooms + L-corridors. |
| `SetPieceStage` | writer | ✅ | both | Stamp authored patterns. |
| `ScatterSpawnPointsStage` | annotator | ✅ | both | Tagged spawn cells w/ spacing. |
| `DrunkardWalkStage` | writer | 📐 | dungeon | Winding agent tunnels. |
| `RoomGraphStage` | writer | 📐 | dungeon | Room graph + layout policy (Linear/Branching/HubAndSpoke/Looped/BSP). |
| `PrefabRoomStage` | writer | 📐 | dungeon | Authored room templates from a pool. |
| `TemplateAssemblyStage` | writer | 📐 | dungeon | Socketed modular assembly (spine/hub). |
| `MazeStage` | writer | 📐 | dungeon | Perfect / braided maze. |
| `HazardFloodStage` | writer | 📐 | both | Toxic/lava/water flood w/ connectivity guard. |
| `MirrorStage` | writer | 📐 | both | Symmetric reflection for authored grandeur. |
| `MaskedSubStage` | writer | 📐 | both | Run sub-stages masked to a tile set (biome detail). |
| `LockAndKeyStage` | writer + annotator | 📐 | dungeon | Locked doors + key markers; solvability invariant. |
| `BossArenaStage` | writer + annotator | 📐 | dungeon | Terminal arena + `boss` marker. |
| `ConnectComponentsStage` | guard + writer | 📐 | dungeon | Flood-fill components; keep largest / bridge / discard. |
| `RegionMapStage` | annotator | 📐 | biome | Name contiguous regions + metadata (centroid, area, biome). |
| `BiomeMatrixStage` | writer | 📐 | biome | Two-axis (temperature × moisture) biome lookup. |
| `EntranceStage` | writer + annotator | ➕ | dungeon | Carve a safe entry pocket; record `spawn-entry`. *Every dungeon needs a defined start; today it's implicit.* |
| `DistanceFieldStage` | annotator | ➕ | both | BFS depth-from-entrance per cell — the metric that lets scatter/binders scale difficulty & loot **by depth**. |
| `DecorationScatterStage` | writer | ➕ | both | Non-spawn props/clutter (torches, rubble, pillars) with adjacency rules (against-wall, in-room, density). Visual life. |
| `PathStage` / `RiverStage` / `RoadStage` | writer | ➕ | both | Carve *connected linear features*: rivers mountain→sea, roads between POIs, a guaranteed main corridor. Overworlds feel dead without them. |
| `BiomeBlendStage` | writer | ➕ | biome | Soften biome seams (beaches between water/grass, scree at mountain feet). |
| `StairLinkStage` | annotator | ➕ | dungeon | Place + pair stairs-up/down across floors (multi-floor, G.4). |
| `ConnectivityGuardStage` | guard | ➕ | both | Generic "all required cells reachable" assertion, choosing the hard/soft predicate (incl. `Breakable`); the stage every recipe ends with. |

**The one core change that makes the annotator stages possible.** `MapBuildContext` today

carries Grid + Rng + SpawnAreas. The richer stages publish data *other stages and binders

consume* — the room graph (RoomGraph), a distance field (DistanceField), region/biome ids

(RegionMap), the entrance cell (Entrance). Add a small typed **annotation blackboard** to the

context (named parallel arrays + a `T Get<T>(key)` bag) rather than overloading the single

tile grid with non-terrain meaning. Terrain stays one `int[]` grid (collision/pathing); depth,

region, and decoration ride alongside as annotations, rendered as separate tilemaps. This is

the only non-trivial *core* addition — the stages themselves are leaf code on top of it.

---

## Part B — The overworld (multi-biome surface)

### B.1 Single-map biomes (works today, extend lightly)

`NoiseRegionsStage` already paints water/grass/forest/mountain by octaved value noise

through ascending thresholds. For an overworld:

- **Sub-biome detail recipes** — after the macro biome pass, run per-biome detail stages
  masked to that biome's tiles (scatter trees in forest, rocks in mountain, reeds at water
  edges). Add a **`MaskedSubStage`** decorator: "run these stages, but only write where the
  current tile ∈ {forest}". Keeps biome detail composable without bespoke stages.
- **Named regions** — add a `RegionMapStage` that flood-fills contiguous same-biome blobs,
  names them, and records each as a spawn area + metadata (centroid, area, biome). The
  realm layer and minimap consume this; spawn density scales by region.
- **Portal placement** — `ScatterSpawnPointsStage(tag="portal-sites", on=<biome floor>)`
  plus biome rules ("dungeon portals only in forest clearings"). Portal *sites* are
  candidate cells; whether a portal is *active* is realm state (§C), not geometry.

### B.2 The biome adjacency question

Pure noise gives blobby, sometimes-incoherent adjacency. Two upgrades, choose per game:

- **Whittaker-style two-axis biome lookup** — generate two noise fields (a
  "temperature" and a "moisture" octave set, both already expressible with the existing
  lattice noise) and look the pair up in a 2-D biome table. Cheap, gives believable
  biome bands. A `BiomeMatrixStage`.
- **Region-first (recommended for the four-quadrant realm, §C)** — *don't* leave biome
  placement to noise at all. Partition the map deterministically into regions (quadrants,
  Voronoi cells from seeded sites, or a grid) and assign each a biome from an authored
  palette, then run that biome's recipe *inside* the region with a derived sub-seed. This
  is the bridge from "one noisy map" to "a structured realm," and it is what the control
  mechanics need.

---

## Part C — Realm progression & control (Nexus, biomes, completion)

This is the **composition layer above single maps** and the heart of the request: how a

party chooses what to fight, how progress accrues, and how the realm reaches a climax. It

replaces "walk between fixed quadrants" with **agency over biome selection**, gated by

**unlocking** and paced by a **completion** meta-currency that culminates in a dropped

**Challenge map**.

### C.1 The loop

```code
HUB TOWN ──[Portal Nexus]── party selects an UNLOCKED biome ──► party DUNGEON instance
   ▲                                                                      │
   │                                                           clear it → COMPLETION
   │                                                       (tougher biome = more, faster)
   │                                                                      │
   │                                               accrues into the REALM CHALLENGE bar
   │                                                                      │
   └─────── capstone cleared ◄── [Portal Nexus] ◄── CHALLENGE MAP drops when bar charges
                (cycle resets, favored biome rotates)
```

1. **Open at the hub.** The party gathers at a fixed **Portal Nexus** in town and selects a
   biome to run — no field-dropped portals. One social, server-friendly instancing point,
   and the natural home for the selection UI.
2. **Run the biome.** A party-shared dungeon instance (Part A geometry) opens for the chosen
   biome. Agency: you pick the bosses and loot you'll face.
3. **Earn completion.** Clearing grants **Completion** toward the realm's **Challenge bar**.
   **Tougher biomes grant completion faster** (§C.3) — the core risk/reward lever.
4. **Charge the Challenge.** When the bar fills, a one-use **Challenge map** drops to the
   party (claimable at the Nexus).
5. **Climax & reset.** Using the Challenge map opens the capstone (realm boss / gauntlet,
   §C.4). Win or lose, the cycle resets — optionally rotating the *favored* biome (bonus
   completion) so the meta varies. A roguelite/seasonal cadence that gives a small server a
   shared reason to log in.

Two distinct map-drop layers — don't conflate them:

- **Biome keys/maps** — let you *open a chosen biome* at the Nexus (dropped or bought). The
  agency currency.
- **The Challenge map** — produced by the completion bar; opens the *capstone*. The climax.

### C.2 Biome roster & unlocking (the agency surface)

A **`BiomeRosterAsset`** lists the realm's biomes; each is a **`BiomeDefinitionAsset`**:

```csharp
[CreateAssetMenu(menuName = "UBear/World Generation/Biome Definition")]
public sealed class BiomeDefinitionAsset : ScriptableObject
{
    public string BiomeId;              // stable id (save/unlock state, keys)
    public MapRecipeAsset[] Recipes;    // pool — one rolled per run (variety)
    public ThemeRef Theme;              // palette + tile set
    public int Tier;                    // difficulty band (1..N)
    public float CompletionValue;       // meta-charge per clear (scales with Tier)
    public UnlockRule Unlock;           // how it becomes selectable (below)
    public EnemyTierTable EnemyScaling; // archetype tiers + density by tier
    public LootTableRef Loot;           // biome-flavored drops + sibling biome keys
    public BossRef[] Bosses;
}
```

**Unlock schemes** (mix freely):

| Rule | Mechanism | Feel |
|---|---|---|
| Tier-gate | clear any tier-N biome → tier-(N+1) selectable | A guaranteed difficulty ladder. |
| Key-drop | a biome boss drops the key to a *sibling/secret* biome | Discovery; optional content off the main path. |
| Completion-gate | reach X cumulative completion → unlock a bracket of biomes | Rewards investment, not just one clear. |
| Purchase | buy access at the Nexus (`UBearEconomy`) | A currency sink and pity-unlock for unlucky parties. |

> **Recommendation:** a short linear *spine* (tier-gated) so every party has a path, plus a
> few *branch* biomes behind key-drops/purchase for discovery and build variety. The
> selection UI lists unlocked biomes with tier, expected loot, and completion-per-clear, so
> the trade-off is legible at the point of choice.

### C.3 Completion as the risk/reward lever

Completion is the meta-currency; the Challenge bar fills from it. The design promise:

**tougher biomes charge the realm much faster, so a strong party can rush the capstone via

hard content while a cautious party grinds safe content — both valid.**

| Tier | Rel. difficulty | Completion / clear | Clears to charge bar |
|---|---|---|---|
| 1 (starter) | 1× | 1.0 | ~20 |
| 2 | ~2× | 2.5 | ~8 |
| 3 | ~4× | 5.0 | ~4 |
| 4 | ~7× | 9.0 | ~3 |
| 5 (brutal) | ~12× | 16.0 | ~1–2 |

(Illustrative — tune in `UBearDataTables`.) Completion-per-clear rises *faster* than

clear-time, so high tiers are strictly more *time-efficient* but carry wipe risk — and under

the **hardcore ruleset** (already first-class in the inventory authority), that risk is

permanent character loss. That's the whole tension: efficiency vs. survival.

Guardrails so the roster stays varied instead of degenerate:

- Optional **per-biome diminishing returns or a soft daily cap**, so the single most
  efficient biome isn't the only correct choice.
- The **favored biome** each cycle (§C.4) grants bonus completion, nudging rotation.
- Higher **loot quality** (not just charge speed) on higher tiers, so the choice is also
  "what do we want to farm," not only "what charges fastest."

### C.4 The Challenge (capstone) as a map drop

When the bar charges, the server issues a **Challenge map** item to the party (or marks it

claimable at the Nexus). It is one-use; using it at the Nexus opens the **capstone instance**

— the realm boss or a multi-stage gauntlet (e.g. the curated boss-rush of Part G.7; the worked

capstone is Part G.12, Oryx's Castle). On a

small server this is the *event beat*: everyone online can join the capstone window.

Resolution resets the cycle (full or partial bar reset — see open questions) and rotates the

favored biome. It's the RotMG "realm closes → Oryx" rhythm, generalized and player-paced.

### C.5 Server-authoritative state & control verbs

`RealmState` is server-owned, replicated as small id/flag/number payloads, and persisted as a

versioned `UBearSaves` section — **separately per ruleset** (hardcore progression is its own

track):

```csharp
public sealed class RealmState
{
    public int RealmSeed;
    public int CycleNumber;                              // bumps each capstone resolution
    public HashSet<string> UnlockedBiomes;
    public float ChallengeCharge;                        // 0..1 toward the Challenge map
    public Dictionary<string, float> CompletionByBiome;  // for caps / diminishing returns
    public string FavoredBiome;                          // bonus completion this cycle
    public bool ChallengeMapIssued;
    public List<DungeonInstance> ActiveInstances;        // open party dungeons + their seeds
}
```

A **`WorldDirector`** host (new `UBearWorldDirector`-style package, or the demo to start)

owns it: validates Nexus open-requests against `UnlockedBiomes` + key items, rolls each run's

sub-seed and recipe, opens/closes instances, and — on server-side completion signals — adds

`CompletionValue × modifiers`, charges the bar, and issues the Challenge map. **Completion

accrual is server-side only; a client can't forge progress.** It routes these **control

verbs** (each an existing package event) into unlocks, completion charge, or the capstone:

| Verb | Source event | Typically drives |
|---|---|---|
| Boss kill | `BossBinder.BossDefeated` | completion charge; sibling-biome key unlock |
| Objective / collection | `UBearQuests` objective complete | biome unlock; capstone gate |
| Altar offering | `UBearInteraction` altar consumes an item | summon an optional super-boss; unlock a secret biome |
| Switch / lever | in-dungeon interactables (`LockAndKeyStage` doors) | intra-dungeon gating |
| World event / timer | `WorldDirector` schedule | favored-biome rotation; timed capstone window |

`UBearQuests` signals are the glue throughout, exactly as the demo already relays kills.

### C.6 What happens to the four-quadrant overworld?

The Nexus + roster + completion *is* the control layer now; the fixed four-quadrant geography

from the first draft becomes **optional presentation** — two ways to take it:

- **Nexus-only (leanest — recommended start):** no persistent overworld; the town hub + the
  Portal Nexus, everything else an instance. Minimal server footprint, fastest to ship.
- **Hub + shared overworld (add later if wanted):** keep a persistent four-quadrant surface
  as a shared zone for ambient play and **biome-key farming** — field content and events
  there drop the keys you spend at the Nexus. The quadrants then express the *starter* biomes
  spatially, while the roster/Nexus still drives structured progression.

Either way the geometry-from-seed and authority models in Part D are unchanged.

---

## Part D — Multiplayer (4–6 player local/hosted) considerations

The target is co-op on a **listen server or small dedicated server**, FishNet + Steam (the

stack [NetworkedAuthority.md](../UBearInventory/Package/Documentation~/NetworkedAuthority.md)

already commits to). Worldgen is unusually friendly to this because of determinism.

### D.1 Geometry replicates as a seed, not as tiles

This is the headline. Because `MapGenerator` is byte-for-byte reproducible from

`(width, height, seed, recipe)`, **the server never ships tile data**. It sends:

```code
ZoneOpen { zoneId, recipeId, themeId, width, height, subSeed, tier, partySize }
```

…and every client regenerates the identical `MapGrid` locally. A 256×256 map is one small

message instead of 64 KB+. On open, both sides compute `MapGrid.ComputeHash()`; the server

includes its hash in `ZoneOpen` and **clients that mismatch fall back to a full tile

snapshot and log a desync** (the safety net for any residual nondeterminism — see D.5).

`partySize` is itself a **generation input** (larger maps / more spawns for a 6-party), so a

zone is reproducible from `(subSeed, partySize)` and both feed the hash — fix party size at

open time, don't vary it mid-instance.

**The one mutable exception: destroyed terrain.** Seed-derived geometry is static; *broken*

tiles are not. If a recipe has destructible tiles (G.11), which cells are currently destroyed

is server-authoritative per-instance runtime state — replicated as a small **destroyed-cells

delta** layered on the seed-derived base grid (the same regenerate-base-then-apply-deltas

pattern as enemies and loot), with each client rebuilding the affected collider chunk on

apply. The base grid and its hash still come from the seed; only the delta rides the wire, so

required-breakable dungeons cost a handful of cell ids per break, not a tile snapshot.

### D.2 Authority split

| Concern | Owner | Notes |
|---|---|---|
| Realm seed, sub-seeds, `RealmState`, gate unlocks | **Server** | Replicated as small id/flag payloads; persists in a save section. |
| Map *geometry* | **Both** (regenerated from seed) | Server keeps it too (collision/AI queries); no per-tile sync. |
| Enemy spawns from spawn areas | **Server only** | ⚠️ Today `SpawnAreaBinder`/`DemoBadlandsDirector` `Instantiate` locally on `Built`. In MP they must run **server-side** and spawn **networked** enemies; clients get replicated `NetworkObject`s, not locally-spawned ones. This is the main port. |
| Boss state / phases / `BossDefeated` | **Server** | Drives gate unlocks; clients see replicated boss + effects. |
| Loot rolls, portal-item creation, key/door state | **Server** | Per NetworkedAuthority §2/§6: clients never roll loot or forge items; opening a portal is a gameplay RPC the server validates. |
| Dungeon instance lifecycle | **Server** | Open on validated portal use; close on empty + grace timer or completion. |

### D.3 Instancing & zone lifecycle

- **Overworld is persistent and shared** — one realm, all online players in it. Small
  (quadrants are bounded), cheap to keep resident.
- **Dungeons are instances.** For 4–6 players, default to **party-shared instances**
  (whole group opens a run at the hub Portal Nexus together) rather than per-player —
  simpler, more social, and avoids N copies of AI. Cap concurrent instances (e.g. ≤ a
  handful) so a tiny server's CPU/RAM stays bounded; each instance is a server-side
  `MapGrid` + its networked agents.
- **Multi-floor / sub-area dungeons** (Part G.4) make one instance own *several* grids plus
  per-area cleared/looted state; the server holds all floors, clients regenerate the active
  floor from its sub-seed on each transition (still seed-only on the wire).
- **Scene strategy:** additive-load a lightweight dungeon scene per active instance, or
  keep a single scene and offset instances spatially / use scene-per-instance. Tear down
  on close to reclaim the tilemap, colliders, and agents.
- **Late join / reconnect:** send realm seed + `RealmState` + the set of open `ZoneOpen`
  messages for zones the joiner is in; they regenerate geometry and reconcile enemies/loot
  through the existing replication layer. Same heal path as a desync.

### D.4 Performance & memory budget (small server)

- **Map memory is `int[w*h]`** — a 512×512 zone is ~1 MB server-side, trivial; clients hold
  the same plus the rendered tilemap (chunked by `TilemapMapBuilder`, with one merged
  `CompositeCollider2D` — already the cheap path).
- **Keep zones small and few.** Bound quadrant size, bound concurrent dungeon instances,
  despawn distant/empty instances. The four-quadrant model exists partly to keep this
  bounded by design.
- **AI is the real cost, not tiles.** Population caps already exist on spawners
  (`MaxAlive`, respawn timers). Budget total live networked agents across all instances,
  not per-spawner. Consider server-side agent sleep when no player is near an instance.
- **Generation cost** is a one-time CPU spike per zone open; run it off the main thread on
  the server if a large zone stalls the tick (the core is engine-free, so it can run on a
  worker thread — only the Unity tilemap emission must be on the main thread, and that's
  client-side render only).

### D.5 Determinism caveats to verify (don't assume — test)

- `MapRng` is pure integer math → deterministic across platforms by construction.
- **`NoiseRegionsStage` uses `float` smoothstep.** IEEE-754 float results *should* match
  across platforms for the same ops, but this is the classic cross-platform determinism
  trap (x86 vs ARM, fused-multiply-add, compiler flags). **The `ComputeHash` handshake in
  D.1 makes this safe regardless** — a mismatch just triggers the snapshot fallback — but
  add a CI test that generates each shipping recipe on the build agents you actually target
  and asserts a pinned hash. If you want hard guarantees, port the noise to fixed-point /
  integer math (the lattice is simple enough).
- New stages (`DrunkardWalkStage`, `LockAndKeyStage`, …) must draw **all** randomness from
  `context.Rng` and iterate grids in a fixed order — never from `UnityEngine.Random`, wall
  time, or hash-set enumeration order. Enforce with the existing hash-determinism test
  pattern.

### D.6 Persistence (UBearSaves) & rulesets

- `RealmState` (seed, unlocked zones, gate progress) is a versioned save section — the
  realm survives restarts; a fresh seed = "new world."
- Dungeon instances are **ephemeral**: not persisted; re-derivable from a portal item's
  sub-seed if you want "save and resume a dive."
- **Hardcore/normal ruleset** (already a first-class concept in the inventory authority)
  extends here: keep separate realm progression per ruleset, and gate hardcore players to
  hardcore instances — the access-policy seam already carries `Ruleset`.

---

## Part E — Build order (proposed)

Dependency-ordered, each step independently testable, matching the house "one commit per

feature, headless-tested" cadence:

1. **Dungeon stages in `UBearWorldGen`** — `DrunkardWalkStage`, `RoomGraphStage`,
   `LockAndKeyStage`, `BossArenaStage`, `HazardFloodStage`, `PrefabRoomStage`,
   `MaskedSubStage`, then `MazeStage`, `TemplateAssemblyStage`, `ConnectComponentsStage`.
   Pure core + assets + per-recipe **seed-fuzz tests** (connectivity, boss reachable,
   key-before-lock, min area). *Yields the Part G archetypes as content, single-player.*
2. **`BossBinder`** (Enemies/WorldGen bridge) + a demo dungeon scene that opens a Snake Pit.
   Proves the encounter loop end-to-end offline.
3. **Multi-floor `DungeonInstance`** — generalize an instance to own ≥1 `MapGrid` + per-area
   cleared/looted state + sub-seed lineage (Part G.4). Unlocks tombs/towers and is the
   substrate the realm layer instantiates.
4. **Biome roster + Nexus + completion** (new `UBearWorldDirector`-style package) —
   `BiomeDefinitionAsset`/`BiomeRosterAsset`, the Portal Nexus open-flow, `RealmState`
   (unlocks, completion, Challenge bar), unlock rules (start tier-gate + key-drop),
   completion accrual on server-side clear signals, the Challenge-map drop + capstone open.
   **The headline feature, fully playable offline** (single-player or listen host).
5. **Overworld extensions (optional)** — `RegionMapStage`, biome sub-stages, the portal/key
   farming surface, *if* you want the hub + shared overworld variant (§C.6) over Nexus-only.
6. **Networking port** — gated on the FishNet timeline (alongside NetworkedAuthority
   Phase 1+): seed-based `ZoneOpen` replication + hash handshake, **server-side
   spawn/boss/loot authority** (the `SpawnAreaBinder` port), instance lifecycle, `RealmState`
   replication, late-join/reconnect. Acceptance: 4–6 client soak — identical geometry from
   seed across all clients (hashes match), one party clears a Nexus-opened dungeon,
   completion charges only server-side, no enemy/loot dup across a forced disconnect.

Steps 1–4 deliver the full experience **locally**; step 6 makes it co-op without touching the

gameplay/content built before it — the same "gameplay code doesn't change" promise the

inventory networking spec keeps.

---

## Part F — Open questions

- **Instance sharing** — *resolved:* party-shared, opened at the hub Portal Nexus. Still to
  pin: max party size in one instance, and whether a second party can open the same biome
  concurrently as its own instance (assumed yes).
- **Completion economy tuning** — the tier→completion curve (§C.3 table is illustrative);
  whether to add per-biome diminishing returns / daily caps; how big the Challenge bar is
  relative to a session. Owns the whole pacing feel — tune in `UBearDataTables`.
- **Unlock topology** — how much linear spine vs. branch/secret biomes; are any biomes
  purchase-only; does completion-gating unlock *brackets* or single biomes.
- **Capstone reset behavior** — on win *and* on wipe, does the Challenge bar fully reset,
  partially reset, or persist? Does the favored biome rotate every cycle? (Decides whether
  the loop feels seasonal or grindy.)
- **Map/key economy** — are biome keys and the Challenge map tradeable (touches the
  async-exchange + inventory-authority specs), bound-on-pickup, or consumed-on-use only?
  Hardcore vs normal separation is already implied by per-ruleset `RealmState`.
- **Overworld or Nexus-only** (§C.6) — ship lean (Nexus-only) first, or build the shared
  four-quadrant farming surface up front?
- **Multi-floor resume** — are partially-cleared multi-floor dungeons resumable (persist the
  instance sub-seed + per-floor progress) or always fresh on re-open?
- **Noise determinism** — accept the hash-handshake fallback, or invest in fixed-point noise
  for hard cross-platform guarantees? (Recommendation: ship the handshake + pinned-hash CI
  test; port to fixed-point only if mismatches actually appear.)

---

## Part G — Dungeon generation deep dive: twelve archetypes

**G.1–G.7** each foreground a *different* generation technique and surface a *different*

consideration — together they map the spectrum from "geometry fully emergent" to "geometry

fixed, only content rolls." **G.8–G.12** are concrete RotMG-flavored dungeons that *compose*

those techniques, each adding one wrinkle; the G.13 cross-cutting rules apply to all. Every

one is still recipe + theme + binders over the shipped pipeline.

### G.1 Snake Pit — agent-based tunneling (organic)

**Feel:** claustrophobic winding tunnels, egg nests, a queen at the dead end.

**Technique:** `FillStage(WALL)` → `DrunkardWalkStage`: one or more "diggers" do a weighted

random walk carving `FLOOR`, biased to keep heading (snaky, not blobby), spawning child

diggers at `branchChance`, stopping at a target carved fraction (~0.30–0.40). A carve *brush*

radius sets tunnel width. Track the farthest-from-start carved cell → `BossArenaStage` widens

it; scatter nests on `FLOOR`.

**Consideration — connectivity vs. organic feel.** A *single* walker is connected by

construction. *Multiple* walkers can strand pockets unless each new digger starts from an

already-carved cell (recommended) or you run `GridConnectivity` and bridge afterward. Tunnel

width is a deliberate **difficulty knob**: tight corridors make `UBearProjectiles` patterns

brutal (the real snake pit's signature) — generation params *are* combat-design params. When

the *required* path runs through destructible blocks (RotMG's pits do this), carve those

segments as a `BREAKABLE` tile rather than `FLOOR` and assert **soft** connectivity (floor ∪

breakable) — the mechanics of that live in G.11.

### G.2 Toxic Sewers — room graph + hazard + lock/key (layered post-passes)

**Feel:** connected chambers, toxic channels, a valve puzzle, a boss room.

**Technique:** `RoomGraphStage(Looped)` → `PrefabRoomStage` (pump room, grate vault) →

`HazardFloodStage(TOXIC)` → `LockAndKeyStage(keyItem="sewer-valve", locks=2)` → scatter →

`BossArenaStage(pick='boss-room')`. Theme makes `TOXIC` an animated, damage-on-stand sludge

tile (a game-side component reads the palette tag, like the demo warlord's slow).

**Consideration — each post-pass re-validates the invariant it could break.** Hazard flood

must not sever the map: flood, then flood-fill *walkable*; if a room islands, recede the

hazard or carve a catwalk. Locks must stay solvable: place each key in a room *upstream of

its lock* on the entrance spanning tree, asserted by flood-fill over "passable ∪

openable-with-keys-collected-so-far." Build additively; every layer that can violate

connectivity proves it didn't.

### G.3 The Labyrinth — true maze (braided)

**Feel:** a maze of corridors, dead-end treasure, a minotaur.

**Technique:** new `MazeStage` — recursive backtracker (or Wilson's for unbiased) over a

maze-cell lattice where each cell is a 2–3 tile block so walls have thickness. A *perfect*

maze has exactly one path between any two points; **braid it** by knocking out a fraction of

dead-ends to add loops. Record dead-end cells as a `loot` area.

**Consideration — mazes are determinism-sensitive and easily tedious.** The backtracker's

neighbor-visit order and stack must be RNG-/fixed-order (never `HashSet` enumeration). A

textbook perfect maze is miserable for ranged combat (no sightlines, lots of backtracking):

**braiding + occasional rooms beats a pure maze almost always**, and a minimap becomes

near-mandatory.

### G.4 The Sunken Tomb — multi-floor vertical stack (instance with state)

**Feel:** descend several floors by stairs, deeper = deadlier, a crypt boss at the bottom.

**Technique:** the dungeon is an **ordered list of `MapGrid`s**, each generated from a

sub-seed derived from `(instanceSeed, floorIndex)`, each placing `stairs-down`/`stairs-up`

markers in connected rooms (teleport-linked, or spatially aligned if floors render

adjacently).

**Consideration — this breaks "one `MapGrid` = one instance."** You need a `DungeonInstance`

that owns *several* grids, the current floor, and **per-floor persistent state** (cleared

enemies, opened chests) so backtracking up doesn't respawn the world. In MP the server holds

all floors; clients regenerate the active floor on transition (seed-only, cheap). This is the

template for *any* dungeon with sub-areas, and why step 3 of the build order exists.

### G.5 The Modular Keep — template assembly (modular rooms)

**Feel:** authored rooms (great hall, armory, secret study) stitched into varied keeps —

high authored quality, randomized layout.

**Technique:** new `TemplateAssemblyStage` — rooms are authored templates with **typed door

sockets** on their edges; a seeded graph walk matches an open socket of a placed room to a

compatible socket of a new room (optionally rotating/mirroring), tracking an occupancy mask

and backtracking on overlap. The Spelunky-room / modular-dungeon / WFC-lite approach.

**Consideration — socket matching + transforms are the hard part.** Define a connector

vocabulary (door width/type), forbid overlaps, cap attempts with backtracking, and apply

rotations/mirrors in a canonical order for determinism. Connectivity is free (you only attach

via sockets). Trade-off: more curated control, less emergent surprise — ideal when you want

set-piece quality *with* layout variety.

### G.6 The Infested Hollow — cellular caves + component reconciliation

**Feel:** big organic caverns with pockets, fungal chambers, a brood boss.

**Technique:** `CellularCaveStage` (ships) → new `ConnectComponentsStage` (flood-fill all

walkable components; keep the largest, then either wall-fill small pockets or tunnel the

nearest cells between components) → place chambers in large open regions by area-threshold

detection → scatter + boss.

**Consideration — cellular automata almost always strand pockets.** Unlike room graphs,

connectivity is *not* free; you must detect components and reconcile (discarding wastes space;

bridging can look artificial — tune). And placing *meaningful* rooms in noise is harder with

no slots to fill — region-area thresholds are how you find "a cavern big enough to matter."

### G.7 The Gauntlet — curated geometry, rolled content (boss rush)

**Feel:** a fixed linear chain of arenas; each rolls its encounter; a final boss. Minimal

geometric randomness.

**Technique:** `TemplateAssemblyStage` forced to a **linear** policy over a few arena

templates (or a fully authored scene); the procgen lives in the **content** — seeded rolls

pick each arena's archetype mix and modifiers ("frenzied", "shielded", hazard variant) from

weighted tables scaled by biome tier and party size. A natural capstone (§C.4).

**Consideration — procgen is a dial, not a mandate.** Boss fights want deliberate arenas;

fixed geometry + rolled encounters often beats random layout for pacing and readability. This

sample anchors the far end of the spectrum from G.1: **most good dungeons sit somewhere

between fully-emergent and fully-authored — choose the mix per the experience you want.**

**Reference dungeons (RotMG-flavored).** G.8–G.12 compose the G.1–G.7 techniques into named

dungeons, each with one new wrinkle; the G.13 rules still apply to every one.

### G.8 Haunted Manor — hub-and-spoke, parallel bosses, gated finale

**Feel:** a grand entrance hall opening onto several haunted wings, each ending in a restless

mini-boss ("the Immortals"); clear enough wings to break the seal on the master's chamber.

**Technique:** `TemplateAssemblyStage(HubAndSpoke)` (G.5's socket assembly in a hub topology)

— a central hall with *K* wing sockets, each wing a short template chain ending in a

`boss/wing-N` arena. A `LockAndKeyStage` variant where the "keys" are *mini-boss kills*, not

items: the finale door opens when ≥ *M* of *K* `wing-cleared` signals fire (server-tracked).

**Consideration — parallel, any-order objectives with a completion gate.** Unlike G.2's

linear lock/key, progression is a *set*, not a *sequence*: a 4–6 party splits up or picks an

order, and "M of K cleared" is a natural divide-and-conquer beat. Generation only has to

guarantee each wing is independently reachable from the hub (free by socket construction) and

the finale only through the gate. It is G.5's template assembly + a graph topology + a

multi-boss binder.

### G.9 Mountain Temple — authored spine, symmetry, guaranteed critical path

**Feel:** a stately, dangerous ascent — a long ceremonial corridor through arena chambers to

a summit boss; you can't get lost, but you can die.

**Technique:** `TemplateAssemblyStage` forced to a **spine** policy — a guaranteed critical

path of arena templates end to end, with optional *rib* rooms (side reward pockets) hung off

it. Author the grandeur with **mirror symmetry**: generate one half along the spine axis and

reflect it (a new `MirrorStage`) so it reads as built, not grown. Boss at the spine terminus.

**Consideration — controlled linearity and the critical-path guarantee.** The opposite pole

from the maze (G.3): the point is that there *is* one obvious way forward, branches strictly

optional. Symmetry is the wrinkle — it needs a canonical reflection order to stay

deterministic, and spawn/loot tags must be placed *after* mirroring (or mirrored too) so the

two halves aren't identical encounters. Pace by spine length, not room count.

### G.10 Haunted Cemetery — open arena, the encounter script is the dungeon

**Feel:** a moonlit graveyard, no corridors — fight waves among the tombstones, then summon

and down a sequence of bosses by activating graves in order.

**Technique:** geometry is almost trivial — an open field (`NoiseRegionsStage` for

paths/mud/fences, `SetPieceStage` tombstones/crypts, a few `loot` pockets, one big `arena`

area). The dungeon lives in a **server-side encounter sequencer**: wave 1 → on clear, enable

summon-altar A (an `UBearInteraction` grave) → boss A → altar B → … → final. The §C.5 control

verbs (altar offering, world event) applied *inside* a single instance.

**Consideration — when the geometry is trivial and the encounter script is the dungeon.** The

far end of the dial from G.1: the map barely matters; the challenge is sequencing,

telegraphing, and arena spacing for bullet-hell readability. It is a trap to over-generate

here — a legible open space + a tight server-driven script beats clever layout. The sequencer

is server-authoritative (clients see replicated waves/bosses) — the Part D split exactly.

### G.11 Icy Caverns — traversal-modifying tiles + destructible terrain (a cave re-skin)

**Feel:** glittering caverns where the floor is slick and momentum slides you into the

bullets; some ice walls shatter to open shortcuts.

**Technique:** reuse G.6's `CellularCaveStage` + `ConnectComponentsStage` wholesale, then

re-skin the tile *semantics*: an `ICE` floor tile carries a **slip/friction modifier** (a

game-side movement component reads the palette tag, like `TOXIC` damage in G.2), and a

`CRYSTAL` wall tile is **destructible** for bonus shortcuts/loot.

**Consideration — tiles that change the rules of traversal, and dynamic terrain.** Two

wrinkles: (1) slippery floors change the *effective* difficulty of a given spacing — tune

spawn spacing and tunnel width knowing players slide, so `UBearProjectiles` pacing differs

from a dry cave; (2) destructible walls come in two flavors, and the difference is a

*generation* decision, not a runtime one. **Bonus** destructibles (Icy Caverns' shortcuts)

assert connectivity over the *non*-destructible tiles (`GridConnectivity` ignoring `CRYSTAL`),

so a party that breaks nothing still finishes. **Load-bearing** destructibles (a Snake Pit

whose required path runs through breakable blocks) instead promote breakable to a third

**passability class** and assert *soft* connectivity — floor ∪ breakable counts as

traversable — which guarantees the dungeon is *completable*, not that it's traversable

untouched. A load-bearing breakable is a `LockAndKeyStage` in disguise: if breaking is a

universal action (any shot dents a wall) it needs no key; if it needs a specific tool, the

generator must place the tool upstream of the wall or the run soft-locks. The *same* generator

(G.6) becomes a wholly different dungeon through tile semantics alone — feel is data, not new

code.

> **What's actually new, minimally.** Runtime behavior needs nothing beyond the ICE/TOXIC
> pattern: a `DestructibleTileBehaviour` (HP → on-destroy swap the cell to `FLOOR`, raise a
> tile-changed event, rebuild the affected collider chunk). The *only* first-class promotion
> is in the **passability model** — today it's binary passable/impassable; add a `Breakable`
> value so a recipe can choose hard- vs soft-connectivity. `GridConnectivity` already takes an
> arbitrary predicate, so the core barely changes. See D.1 for the multiplayer wrinkle (broken
> cells are the one bit of geometry that *doesn't* derive from the seed).

### G.12 Oryx's Castle — the capstone (authored grandeur + scripted boss + special lifecycle)

**Feel:** the realm's climax — a grand symmetric castle to the throne, then a multi-phase duel

with Oryx; opened only by the Challenge map (§C.4), a server-wide event everyone piles into.

**Technique:** mostly **authored** — `TemplateAssemblyStage(spine)` + `MirrorStage` (G.9) for

ceremonial halls, an authored throne `arena`, optionally **multi-floor** (G.4: Castle →

Chamber → Cellar) as a `DungeonInstance` of stacked grids. The fight is a multi-phase

`BossBinder` (the demo Warlord's enrage, scaled up — transitions swap `UBearProjectiles`

patterns and summon adds). Light procedural variation (which wings/patterns this cycle) keeps

repeats fresh without redesigning the climax.

**Consideration — the capstone is a special case on every axis.** Geometry leans authored (a

climax wants deliberate staging, not a random layout); the boss is heavily scripted and

server-authoritative; and the **instance lifecycle is unique** — not Nexus-selectable but

*issued* by the completion bar as the Challenge map, a time-boxed event the whole server can

join, and resolving it **resets the realm cycle** and rotates the favored biome (§C.4). Parts

A, C, D, and G.4/G.9 all converge here — the worked example of the realm's whole loop closing.

### G.13 Cross-cutting considerations

- **Connectivity is universal but earned differently** — by construction (room-graph,
  template) or by post-pass (cave reconciliation, multi-walker bridging). Always assert with
  `GridConnectivity`; it is the one non-negotiable invariant.
- **Separate structure from population.** Structure stages only *tag* cells (`boss`, `loot`,
  `room/N`, `stairs`, `key`); binders decide what spawns there. That separation is what lets
  one recipe be reskinned and re-tiered as pure data.
- **Difficulty is data; geometry is shape.** The biome tier scales enemy tiers, density,
  modifiers, and loot through binders — the *same* recipe serves tier 1 and tier 5. Scale map
  size and boss health with `partySize`, fed in as a generation input so the map stays reproducible from
  `(seed, partySize)` (§D.1).
- **Determinism per generator.** Maze neighbor order, template transform order, component
  iteration — all RNG- or fixed-order, never `Dictionary`/`HashSet` enumeration or
  `UnityEngine.Random`. **Fuzz every shipping recipe in CI:** generate N seeds and assert
  connectivity + boss reachable + key-before-lock + min walkable area + no orphaned loot. A
  bad seed in MP hits *everyone*, so fuzzing matters more here than single-player.
- **Sub-areas need stateful instances** (G.4) — generalize `DungeonInstance` to own ≥1 grid
  plus per-area cleared/looted flags; the sub-seed lineage keeps every area reproducible.
- **Regenerate, don't replicate.** Map size barely matters on the wire (§D.1), so a maze or
  a multi-floor tomb costs the same bandwidth as a one-room pit. Render cost is the limiter —
  lean on `TilemapMapBuilder` chunking + the merged composite collider.
- **Budget the clear time.** Target ~8–15 min for a 4–6 party; tune via carve fraction / room
  count / floor count / arena count, and validate the average through the fuzz harness (count
  walkable cells, rooms, path length) rather than by eyeballing seeds.

---

## Part H — Single-player first: realistic, if you stub the seams now

**Verdict: yes, and more safely than most co-op games — because of two things this project

already has.** (1) Geometry replicates as a seed (§D.1), so the part of a world game that is

usually *hardest* to network is here nearly free. (2) The inventory system already shipped its

**Phase 0 seam prep** before any networking — async surface, revision counters, replication

hooks — proving the house can build "host-authoritative, single client" and drop the network

in later without touching gameplay/UI. Apply that same discipline to worldgen and SP→MP stays

a *port*, not a *rewrite*.

**The failure mode to avoid** is SP code that bakes in client authority — spawning,

simulating, and rolling loot wherever the code happens to run. The fix is *not* to network

early (transport stays correctly deferred to the FishNet timeline); it's to **stub the seams

during the SP build** so the authoritative implementation has a socket to drop into. Five

seams, all cheap now and expensive to retrofit:

1. **Spawn / agent seam — the biggest one.** `SpawnAreaBinder` and `DemoBadlandsDirector` today
   call `Instantiate` directly in `OnBuilt` (and `MapBuilderBehaviour.EmitTiles` likewise).
   Introduce an `IAgentSpawner` the binders call instead; locally it wraps `Instantiate`,
   networked it wraps `ServerManager.Spawn`. Without this, every binder is rewritten at MP time.
2. **Authority from day one.** Write `WorldDirector` / `RealmState` (completion, unlocks,
   instance open/close, gate logic) as *the authority*, SP simply being "I am the host" — the
   same trick as `LocalInventoryAuthority` completing async ops synchronously. Loot rolls,
   completion accrual, and boss-defeat → unlock all run there, never in a client `Update()`.
3. **Mutable state as serializable deltas.** Broken tiles (§D.1), opened doors, looted chests,
   cleared rooms — model them as records/deltas over the seed-derived base from the start (the
   project's "everything persistent is a versioned record" convention), not as ad-hoc scene
   mutations. The replication layer and the save sections then reuse one representation.
4. **Determinism enforced from the first new stage.** All randomness through `MapRng`, fixed
   iteration order, per-recipe `ComputeHash` CI tests. Note `MapBuilderBehaviour.Build()` seeds
   a 0-recipe from `Environment.TickCount` — fine for SP, but in MP the **server** picks and
   broadcasts the seed; route random-seed selection through the authority, not local wall time.
5. **`Breakable` passability class** (from the destructibles discussion) — add the third
   passability value while the palette/connectivity code is young; retrofitting a binary model
   later touches every recipe's connectivity assertion.

Build these as you build SP and step 6 of Part E is genuinely just transport + replication,

exactly as the inventory networking spec scopes it. Everything *worldgen-specific* about

multiplayer — the hard part elsewhere — is already solved by determinism; what remains is the

universal co-op work (networked agents, server authority, latency UX) the project is already

structured to take on.
