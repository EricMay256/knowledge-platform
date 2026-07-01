---
CreatedAt: 2026-06-28T16:42:05Z
LastUpdated: 2026-07-01T00:54:36Z
Type:
Status:
tags:
aliases:
---

# UBear WorldGen — Stage Reference

The parameter-level spec for the generation stages named in

[WorldStructureSpec §A.5](WorldStructureSpec.md). Each stage is an `IMapStage` in

`UBear.WorldGenSystem` — pure C#, deterministic, headless-testable — with a matching

`*StageAsset` for authoring. This document fleshes each into **effective tools + parameters**:

what it does, the knobs that shape the result, the algorithm, what it reads/writes, and the

invariant it keeps. Status tags match the catalog (✅ ships · 📐 proposed · ➕ gap).

Nothing here is implemented beyond the ✅ stages; this is the build spec.

---

## 0. Conventions every stage follows

- **Tiles are recipe-defined ints.** Stages take tile-id parameters (`WallTile`, `FloorTile`,
  `HazardTile`…); what an id *means* is the palette/theme's business. Common legend used in
  examples: `WALL=0, FLOOR=1, DOOR=2, HAZARD=3, BREAKABLE=4, STAIRS=5`.
- **All randomness flows through `context.Rng`** (`MapRng`): `NextInt(maxExcl)`,
  `Range(min, maxExcl)`, `NextFloat()` ∈ [0,1), `Chance(p)`. Iterate grids in fixed order.
  This is the determinism contract — same seed ⇒ same map ⇒ same `ComputeHash()`.
- **Stages compose in list order** over one `MapBuildContext`. A recipe is a stage list.
- **Spawn areas** are tagged cell lists (`context.Area("boss")`) that binders consume.
- **Parameters** below show `name : type = default` and the effective range / what it *tunes*.
  Constructors default sensibly; assets expose the same fields.

### 0.1 The context blackboard (the one core addition)

Annotator stages publish data later stages and binders read. Add a small typed bag to

`MapBuildContext` plus a parallel-layer type:

```csharp
// MapBuildContext
public void Set<T>(string key, T value);
public bool TryGet<T>(string key, out T value);

// Well-known keys (ContextKeys.*):
//   Entrance      → GridPoint
//   RoomGraph     → RoomGraph     (rooms[] + adjacency + entrance/terminal indices)
//   DistanceField → MapLayer      (BFS depth per cell; -1 = unreachable)
//   RegionMap     → MapLayer + RegionInfo[]   (per-cell region id + {centroid, area, biome})

// MapLayer: an int[width*height] parallel to MapGrid, for per-cell metadata (depth, region
// id, biome id) kept OFF the terrain grid so collision/pathing stays a single clean layer.
```

Terrain stays one `MapGrid`; depth/region/decoration ride alongside as layers/annotations,

rendered as separate tilemaps. This is the only non-trivial core change — the stages are leaf

code on top of it.

### 0.2 Passability (for guards / soft connectivity)

The palette's passability becomes a 3-value class: `Impassable`, `Passable`, **`Breakable`**.

Guards take a predicate; *hard* connectivity counts only `Passable`, *soft* counts

`Passable ∪ Breakable` (required-destructible dungeons — see WorldStructureSpec G.11).

---

## 1. Foundation (✅ shipped)

### `FillStage` ✅

Fills the whole grid with one tile — the usual first stage.

| Param | Type | Default | Tunes |
|---|---|---|---|
| `Tile` | int | 0 | The canvas (usually `WALL` for carve-based, `FLOOR` for additive). |

### `BorderStage` ✅

Solid frame around the rim — the wall that keeps everything in.

| Param | Type | Default | Tunes |
|---|---|---|---|
| `Tile` | int | — | Rim tile (`WALL`). |
| `Thickness` | int | 1 | 1–3; thicker rims for set-piece edges. |

---

## 2. Structure generators (the dungeon's shape)

### `RoomsAndCorridorsStage` ✅

Non-overlapping rooms + L-corridors chaining each to the previous (connectivity by construction).

| Param | Type | Default | Tunes |
|---|---|---|---|
| `FloorTile` | int | — | Carve tile. |
| `RoomAttempts` | int | 30 | 15–60; more attempts ⇒ denser layouts. |
| `MinRoomSize` / `MaxRoomSize` | int | 4 / 9 | Room scale. |
| `SpawnAreaTag` | string | null | Records interiors (e.g. `"room"`). |

### `CellularCaveStage` ✅

Random wall-fill + automaton smoothing (5+ wall neighbours ⇒ wall; OOB = wall, sealing the rim).

| Param | Type | Default | Tunes |
|---|---|---|---|
| `WallTile` / `FloorTile` | int | — | — |
| `WallChance` | float | 0.45 | 0.40–0.50; higher ⇒ tighter, more broken caverns. |
| `Iterations` | int | 4 | 3–6; more ⇒ smoother blobs. |

> Cellular caves strand pockets — always follow with `ConnectComponentsStage`.

### `DrunkardWalkStage` 📐 — agent tunneling (organic)

One or more diggers random-walk, carving `FloorTile` through `WallTile`. The snake-pit look.

| Param | Type | Default | Tunes |
|---|---|---|---|
| `WallTile` / `FloorTile` | int | — | Fill + carve. |
| `CarveFraction` | float | 0.40 | 0.20–0.60; target carved fraction (stop condition) = openness. |
| `Walkers` | int | 1 | 1–4; >1 strands pockets unless children start on carved cells. |
| `TurnChance` | float | 0.25 | 0–1; per-step direction re-roll. Low = long straight tunnels, high = wiggly. |
| `BranchChance` | float | 0.0 | 0–0.25; spawn a child walker (forking caves). |
| `BrushRadius` | int | 0 | 0 = 1-wide, 1 = 3-wide. **Tunnel width = a difficulty knob** (tight tunnels brutalize bullet-hell). |
| `MaxSteps` | int | w·h·4 | Safety cap. |
| `StartTag` / `EndTag` | string | null | Spawn areas at the start cell and the farthest-from-start cell (the boss). |

**Algorithm:** fill `WallTile`; seed walker(s) at center; each step carve a brush, step in the

current direction (re-roll on `TurnChance` or at a border), branch on `BranchChance`; track the

farthest carved cell from start; stop at `CarveFraction` or `MaxSteps`.

**Writes:** tiles; `StartTag`/`EndTag` spawn areas. **Invariant:** single walker connected by

construction; otherwise run `ConnectComponentsStage`.

### `RoomGraphStage` ✅ — rooms as an explicit graph

Generalizes RoomsAndCorridors with a layout policy and a published adjacency graph.

| Param | Type | Default | Tunes |
|---|---|---|---|
| `FloorTile` / `DoorTile` | int | —/0 | Carve + optional door cells at junctions. |
| `Layout` | enum | `Branching` | `Linear` (chain), `Branching` (random spanning tree), `HubAndSpoke` (central hub → all), `Looped` (tree + extra edges), `BSP` (binary-partition → room per leaf). The dungeon's *shape*. |
| `RoomCountMin/Max` | int | 8 / 14 | Size of the dungeon. |
| `MinRoomSize/MaxRoomSize` | int | 4 / 9 | — |
| `ExtraLoopEdges` | int | 0 | `Looped` only; 1–4 non-tree edges = anti-backtracking flow. |
| `CorridorWidth` | int | 1 | 1–3. |
| `RoomTag` | string | `"room"` | Records `room/0…room/n` spawn areas. |

**Algorithm:** place non-overlapping rooms; build edges per `Layout`; carve corridors along

edges; pick entrance + terminal rooms.

**Writes:** tiles; `room/i` areas; **publishes `RoomGraph`** to the blackboard (consumed by

PrefabRoom, LockAndKey, BossArena). **Invariant:** spanning tree ⇒ all rooms connected.

### `MazeStage` ✅ — perfect / braided maze

| Param | Type | Default | Tunes |
|---|---|---|---|
| `WallTile` / `FloorTile` | int | — | — |
| `CellSize` | int | 2 | Maze-cell = N×N tiles, so walls have thickness (corridor width). |
| `Algorithm` | enum | `RecursiveBacktracker` | vs `Wilson` (unbiased, less "long corridor" bias). |
| `BraidChance` | float | 0.3 | 0 = perfect maze (one path between any two cells); higher removes dead-ends ⇒ loops, less tedium, better for combat. |
| `DeadEndTag` | string | null | Records remaining dead-ends (natural treasure spots). |

**Determinism caveat:** neighbour-visit order + the backtracker stack must be RNG-/fixed-order

(never `HashSet` enumeration). **Invariant:** perfect maze fully connected by construction.

### `TemplateAssemblyStage` ✅ — socketed modular rooms

Authored room templates with **typed door sockets**, stitched into varied layouts.

| Param | Type | Default | Tunes |
|---|---|---|---|
| `Templates` | RoomTemplate[] | — | Pool of authored rooms; each has edge sockets (door width/type). |
| `Policy` | enum | `Sprawl` | `Spine` (guaranteed linear critical path + optional rib rooms), `HubAndSpoke`, `Sprawl` (organic). |
| `RoomCountMin/Max` | int | 6 / 12 | — |
| `AllowRotation` / `AllowMirror` | bool | true / true | Layout variety from one template (apply transforms in canonical order for determinism). |
| `StartTemplate` / `BossTemplate` | tag | — | Forced first/terminal rooms. |
| `MaxAttempts` | int | 200 | Backtracking budget. |

**Algorithm:** place start template; repeatedly match an open socket to a compatible socket of a

new (optionally transformed) template, tracking an occupancy mask, backtracking on overlap; stop

at `RoomCount`. **Writes:** tiles; room graph. **Invariant:** connected (attach only via sockets).

### `PrefabRoomStage` ✅ — fill graph slots with authored rooms

| Param | Type | Default | Tunes |
|---|---|---|---|
| `TemplatePool` | RoomTemplate[] | — | Authored interiors (vault, library, miniboss arena). |
| `SlotTag` | string | — | Which `RoomGraph` rooms to fill. |
| `MatchTile` | int | `FLOOR` | Only stamp where the footprint matches. |
| `RecordTag` | string | null | e.g. `"loot-vault"`. |

Consumes the `RoomGraph`; stamps a random fitting template into each tagged room.

---

## 3. Connectivity & repair (guards)

### `ConnectComponentsStage` 📐 (guard + writer)

| Param | Type | Default | Tunes |
|---|---|---|---|
| `Passable` | predicate | `t==FloorTile` | What counts as walkable. |
| `Mode` | enum | `BridgeOrDiscard` | `KeepLargest` (wall-fill the rest), `Bridge` (tunnel nearest cells between components), `BridgeOrDiscard` (bridge big pockets, discard tiny). |
| `MinComponentSize` | int | 8 | Pockets smaller than this are discarded (wall-filled). |
| `BridgeTile` | int | `FloorTile` | Carve tile for bridges. |

**The cave fixer.** Cellular/multi-walker output is reconciled into one reachable space.

### `ConnectivityGuardStage` 📐 (guard) — *every recipe ends with this*

| Param | Type | Default | Tunes |
|---|---|---|---|
| `Passable` | predicate | `Passable` only | Hard vs **soft** (`Passable ∪ Breakable`) — pick soft for required-destructible dungeons. |
| `RequiredTags` | string[] | `["boss"]` | Spawn areas that MUST be reachable from `Entrance` (boss, keys, exit). |
| `OnFail` | enum | `Throw` | `Throw` (CI/tests), `BridgeToEntrance` (prod self-heal). |

**Algorithm:** flood from `Entrance` over `Passable`; assert every floor cell and every

`RequiredTags` marker is reached. The non-negotiable invariant; in the **seed-fuzz CI** this

throws on a bad seed before it ever ships to players.

---

## 4. Anchors & progression

### `EntranceStage` ➕ (writer + annotator)

| Param | Type | Default | Tunes |
|---|---|---|---|
| `Mode` | enum | `NearEdge` | `NearEdge`, `Center`, `Random` — where players spawn in. |
| `PocketRadius` | int | 2 | Carves a safe starting pocket. |
| `Tag` | string | `"spawn-entry"` | Spawn area for the player start. |

Picks a floor cell, carves a safe pocket, **publishes `Entrance` (GridPoint)** + the spawn area.

Prerequisite for DistanceField, LockAndKey, and "deepest room" boss selection.

### `DistanceFieldStage` ➕ (annotator)

| Param | Type | Default | Tunes |
|---|---|---|---|
| `From` | key/tag | `Entrance` | Source of the BFS. |
| `Passable` | predicate | `FLOOR` | — |

BFS depth-from-entrance into a `MapLayer`. **The depth metric** that lets scatter/binders scale

enemy tier and loot *by distance into the dungeon*, and that BossArena uses to find the deepest room.

### `BossArenaStage` ✅ (writer + annotator)

| Param | Type | Default | Tunes |
|---|---|---|---|
| `Pick` | enum | `Deepest` | `Deepest` (max distance-field), `TerminalRoom` (graph leaf), `Tagged`. |
| `ArenaRadius` | int | 0 | >0 clears/enlarges a fighting arena. |
| `SealTile` | int | `DOOR` | Seals the entrance (the boss door). |
| `BossTag` | string | `"boss"` | Single-cell area at the arena center. |

### `LockAndKeyStage` ✅ (writer + annotator)

| Param | Type | Default | Tunes |
|---|---|---|---|
| `LockCount` | int | 1 | 1–3; puzzle depth. |
| `DoorTile` | int | `DOOR` | Locked-door tile. |
| `KeyTag` | string | `"key"` | Key spawn markers. |
| `GateMode` | enum | `Item` | `Item` (UBearInventory key) or `Switch` (ability-gated). |
| `KeyItem` | string | null | Item id for `Item` mode. |

**Algorithm:** walk the `RoomGraph` spanning tree from `Entrance`; lock `LockCount` edges

(prefer edges gating the path to the boss); place each key in a room **upstream of its lock**.

**Invariant (asserted):** solvable — flood over `Passable ∪ openable-with-keys-collected-so-far`

reaches the boss. A "boss key" is the same mechanism one level up (the realm).

### `StairLinkStage` ✅ (annotator) — multi-floor

| Param | Type | Default | Tunes |
|---|---|---|---|
| `FloorIndex` | int | — | Which floor of the `DungeonInstance` this is. |
| `DownTile` / `UpTile` | int | `STAIRS` | — |
| `LinkMode` | enum | `Teleport` | `Teleport` (paired markers) or `Aligned` (stacked floors). |

Places + records paired stairs so a multi-floor `DungeonInstance` (WorldStructureSpec G.4) can

move between floors; each floor is its own `MapGrid` from a sub-seed.

---

## 5. Population & decoration

### `ScatterSpawnPointsStage` ✅ (annotator)

Tagged spawn cells on matching tiles with minimum spacing — "the forest spawns wolves" as data.

| Param | Type | Default | Tunes |
|---|---|---|---|
| `Tag` | string | — | Spawn-area tag. |
| `OnTile` | int | — | Tile the points must sit on. |
| `Count` | int | — | How many points. |
| `MinSpacing` | float | 0 | Keeps spawners apart. |

*Extension:* a `DepthWeight` curve reading the distance-field would bias counts/tier deeper in.

### `DecorationScatterStage` ✅ (writer)

| Param | Type | Default | Tunes |
|---|---|---|---|
| `DecorTile` | int | — | Prop tile (or palette prefab: torch, rubble, pillar). |
| `OnTile` | int | `FLOOR` | Eligible base. |
| `Placement` | enum | `OpenFloor` | `AgainstWall` (torches), `OpenFloor` (rubble), `RoomCenter` (pillars/braziers). |
| `Density` | float | 0.05 | 0–0.3 per eligible cell. |
| `MinSpacing` | float | 0 | — |

Non-spawn visual clutter with adjacency rules — what makes a generated room read as *built*.

### `SetPieceStage` ✅ (writer)

Stamps authored patterns (ruins, shrines, nests) where the footprint matches; `-1` cells transparent.

| Param | Type | Default | Tunes |
|---|---|---|---|
| `Piece` | SetPiece | — | Char-row authored stamp. |
| `Count` | int | — | Placements. |
| `MatchTile` | int | -1 | Footprint must be this (-1 = anywhere). |
| `SpawnAreaTag` | string | null | Records each footprint. |

---

## 6. Hazard & terrain

### `HazardFloodStage` ✅ (writer)

| Param | Type | Default | Tunes |
|---|---|---|---|
| `HazardTile` | int | — | TOXIC / LAVA / deep WATER. |
| `Mask` | enum | `LowNoise` | `Edges` (rim channels), `LowNoise` (organic pools), `RandomBlobs`. |
| `Coverage` | float | 0.25 | 0–0.5 target fraction flooded. |
| `KeepConnected` | bool | true | Recede the flood / carve a catwalk if it would island the map. |
| `MinDryWidth` | int | 1 | Guaranteed dry path width. |

**Algorithm:** flood `HazardTile` per `Mask` toward `Coverage`; flood-fill walkable; if a region

islands, recede or carve a dry catwalk; re-assert connectivity. The sewer's toxic channels.

Runtime effect (damage/slip) is a game-side component reading the palette tag, not this stage.

---

## 7. Biome / overworld

### `NoiseRegionsStage` ✅ (writer)

Smooth value noise → biome tiles through ascending thresholds (water/grass/forest/mountain).

| Param | Type | Default | Tunes |
|---|---|---|---|
| `Scale` | float | — | Cells per noise unit — bigger = broader biomes. |
| `Thresholds` | (upTo, tile)[] | — | The biome bands. |

### `BiomeMatrixStage` 📐 (writer)

| Param | Type | Default | Tunes |
|---|---|---|---|
| `TempScale` / `MoistureScale` | float | — | Two noise fields. |
| `BiomeTable` | tile[ , ] | — | temperature × moisture → biome tile (Whittaker-style bands). |

### `MaskedSubStage` ✅ (writer / decorator)

| Param | Type | Default | Tunes |
|---|---|---|---|
| `SubStages` | IMapStage[] | — | Stages to run masked. |
| `MaskTiles` | int[] | — | Writes confined to cells currently of these tiles. |

"Scatter trees only on forest, rocks only on mountain" — biome detail without bespoke stages.

### `BiomeBlendStage` ✅ (writer)

| Param | Type | Default | Tunes |
|---|---|---|---|
| `Transitions` | (a, b, edgeTile)[] | — | e.g. water↔grass ⇒ beach; mountain↔grass ⇒ scree. |
| `Width` | int | 1 | Edge band thickness. |

Softens hard biome seams so adjacency reads naturally.

### `RegionMapStage` ✅ (annotator)

| Param | Type | Default | Tunes |
|---|---|---|---|
| `SameRegion` | predicate | same tile | What groups a region. |
| `MinRegionSize` | int | 16 | Ignore noise specks. |

Flood-fills contiguous regions → `RegionMap` layer + `RegionInfo[]` (centroid, area, biome).

Consumed by the realm layer (quadrants), minimaps, and region-scaled spawn density.

### `PathStage` / `RiverStage` / `RoadStage` ✅ (writer)

*Shipped as one versatile `PathStage`: rivers and roads are configurations (cost field + carve tile + mode), not separate classes. Modes: Single / SourceToSink / Network(MST).*

| Param | Type | Default | Tunes |
|---|---|---|---|
| `FromTag` / `ToTag` | string | — | Endpoints (mountain→sea for rivers; POI→POI for roads). |
| `CarveTile` | int | — | RIVER / ROAD. |
| `Width` | int | 1 | 1–3. |
| `Meander` | float | 0.2 | 0–1 wiggle off the straight path. |
| `CostField` | layer | null | Optional (elevation → rivers flow downhill; terrain cost → roads route around). |

Pathfinds (A*/greedy) a connected linear feature and carves it. Overworlds feel dead without

rivers/roads; in dungeons a forced "main corridor" is the same stage.

---

## 8. Composition / symmetry

### `MirrorStage` ✅ (writer)

| Param | Type | Default | Tunes |
|---|---|---|---|
| `Axis` | enum | `Vertical` | `Vertical`, `Horizontal`, `Both`. |
| `Source` | enum | `LeftHalf` | Which half to reflect. |

Reflects the source half (canonical order for determinism) for authored grandeur (temples,

castles). **Place spawn/loot tags *after* mirroring** (or mirror them) so the halves aren't

identical encounters.

---

## 9. Composing into map types (effective recipes)

Stages compose head-to-tail; these are real parameterizations. (Full archetype list:

WorldStructureSpec Part G.)

**Snake Pit** — tight organic single-boss:

```code
Fill(WALL)
DrunkardWalk(WALL, FLOOR, CarveFraction 0.35, TurnChance 0.30, BrushRadius 0, EndTag "boss")
Entrance(NearEdge, PocketRadius 2)
DistanceField(from Entrance)
BossArena(Pick Deepest, ArenaRadius 2, SealTile DOOR)
ScatterSpawnPoints("snakes", FLOOR, Count 12, MinSpacing 6)
ConnectComponents(KeepLargest)          // single walker, but cheap insurance
ConnectivityGuard(Required ["boss"])
Border(WALL, 2)
```

**Toxic Sewers** — connected rooms, hazard, lock/key, boss:

```code
Fill(WALL)
RoomGraph(FLOOR, Layout Looped, RoomCount 10..14, ExtraLoopEdges 2)
Entrance(NearEdge)  ·  DistanceField(from Entrance)
PrefabRoom(pool=[pump, grate-vault], SlotTag "room", RecordTag "loot-vault")
HazardFlood(TOXIC, Mask Edges, Coverage 0.3, KeepConnected true)
LockAndKey(LockCount 2, GateMode Item, KeyItem "sewer-valve")
BossArena(Pick TerminalRoom)
ScatterSpawnPoints("slimes", FLOOR, Count 20, MinSpacing 4)
ConnectivityGuard(Required ["boss","key"])
Border(WALL, 2)
```

**Overworld quadrant** — biome surface with connective features:

```code
BiomeMatrix(TempScale 28, MoistureScale 22, BiomeTable …)
BiomeBlend([(water,grass,BEACH),(mountain,grass,SCREE)], Width 1)
MaskedSub([ScatterSpawnPoints("trees",…)], MaskTiles [FOREST])
River(FromTag "peak", ToTag "sea", Width 2, Meander 0.4)
Road(FromTag "town", ToTag "nexus", Width 1)
RegionMap(MinRegionSize 24)
ScatterSpawnPoints("portal-sites", on=CLEARING, Count 4)
```

---

## 10. Build & test discipline (per stage)

- **Pure core, one asset, one test file** per stage — `ComputeHash()` determinism + the stage's
  invariant (connectivity, key-before-lock, min area, no orphan markers).
- **Seed-fuzz** each shipping recipe in CI: N seeds, assert `ConnectivityGuard` passes + the
  archetype's specific invariants. A bad seed in multiplayer hits *everyone* (geometry replicates
  by seed), so fuzzing matters more here than single-player.
- Annotator stages depend on the §0.1 blackboard landing first; it's the single prerequisite.
