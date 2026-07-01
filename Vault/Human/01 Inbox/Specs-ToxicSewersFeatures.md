---
CreatedAt: 2026-06-28T16:42:05Z
LastUpdated: 2026-07-01T00:54:33Z
Type:
Status:
tags:
aliases:
---

# Spec: Toxic Sewers — walkable hazards + the `HazardProfile` flavor system

**Audience:** Claude Code (implementation handoff).

**Goal:** Make a faithful RotMG *Toxic Sewers* buildable, which means fixing one wrong

assumption and adding one general system:

- **Correction:** sludge is **walkable terrain that applies a lingering status on stand**, not an
  impassable blocker. The demo currently marks the toxic tile impassable (`SewerToxic` ⇒
  `passable: false`), turning it into a wall. Flip it to passable + give it an on-stand effect.
- **General system:** a hazard tile's *flavor* (passability, on-stand status/damage, directional
  force, cosmetic twin) is a **bundle of orthogonal axes**. Encode them declaratively in a
  `HazardProfile` rather than implicitly (a passability bool here, a hardcoded component there).
  Toxic Sewers alone needs three sludge flavors from one sprite: damaging room-center river,
  inert hallway water, cosmetic floor stain.

Companion to `snake-pit-roomgraph-destructible-spec.md`. **Shared prerequisite:** the 3-value

`Passability { Impassable, Passable, Breakable }` class from that spec. If it hasn't landed, do it

once here; do not duplicate it.

---

## 0. Hard constraints

- **Backward compatibility gate.** Every new param defaults to current behavior
  (`HazardMask` keeps `Edges/LowNoise/RandomBlobs` working unchanged; `PrefabRoomStage` with no
  slot targeting behaves exactly as today). Existing Sewers/Badlands/Snake-Pit recipes and all
  current tests stay green with **no edits**; their `ComputeHash()` is unchanged.
- **Determinism.** Fixed-order iteration; any added RNG draws from `context.Rng`. Flow assignment
  must be deterministic per seed.
- **Layering.** Worldgen stays pure-C# with no engine/game types. `HazardProfile` and the runtime
  effect components are **game-side** (they reference combat/status types). The worldgen palette
  must NOT gain a dependency on combat — see §3.5 for where each axis lives.
- **One commit per logical change**, tests in the same commit.

---

## 1. The recipe (stages used)

In `CreateMapRecipe` order. Tile ids illustrative; `SLUDGE` is the corrected walkable hazard.

| # | Stage | Status (see §2) | Key params for this dungeon |
|---|---|---|---|
| 1 | `FillStage(WALL)` | reuse | gray-brick canvas |
| 2 | `RoomGraphStage(Branching)` | reuse | room count tuned so entrance→boss depth ≈ 8–10; narrow `corridorWidth`; publishes `RoomGraph` |
| 3 | `EntranceStage` | reuse | `NearEdge`; publishes `Entrance` |
| 4 | `DistanceFieldStage` | reuse + **config** | `passable = floor ∪ sludge` — sludge counts as walkable |
| 5 | `HazardFloodStage(RoomCenter)` | **modify** | new `RoomCenter` mask + `EdgeMargin`; `keepConnected = false` (walkable sludge needs no dry catwalk); consumes `RoomGraph` |
| 6 | `FlowFieldStage` | **add** | assigns per-cell flow direction to a subset of sludge rooms → `MapLayer` |
| 7 | `PrefabRoomStage` (start / treasure / boss) | **improve** | slot-targeted: small-square start at entrance, rounded sludge+walkway boss at terminal, rare treasure in an interior slot |
| 8 | `ScatterSpawnPointsStage` | reuse | ambient enemies on floor/edge; a low-rate `golden-rat` roamer marker |
| 9 | `DecorationScatterStage` | reuse | wall-face variants, **cosmetic** sludge stains, machinery props |
| 10 | `BossArenaStage(Tagged)` | reuse + **config** | targets the boss prefab from step 7 (or `TerminalRoom`); records `boss` |
| 11 | `ConnectivityGuardStage` | reuse + **config** | `passable = floor ∪ sludge ∪ door`, `required = {boss}` — **soft over walkable sludge** (the correction) |

Plus, outside the recipe: the **palette** flips sludge to `Passable` (§3.1), and the game-side

**`HazardProfileSet`** declares the sludge flavors (§3.5).

---

## 2. Stage assessment — modify / improve / add

### Reuse as-is (no code change)

- `FillStage`, `RoomGraphStage` (core), `EntranceStage`, `ScatterSpawnPointsStage`,
  `DecorationScatterStage`.

### Reuse, but the *config* is the correction (no code change, just recipe authoring)

- **`DistanceFieldStage`** and **`ConnectivityGuardStage`** must include `SLUDGE` in their passable
  predicate. With the old impassable toxic this was wrong-by-design ("the dry route is the
  assertion"); with walkable sludge the guard asserts solvability *over* sludge. This single config
  change is the heart of the fix — verify there's a regression test (§4) proving the boss is
  reachable on a path that crosses sludge.

### Needs **modification**

- **`HazardFloodStage` → add a `RoomCenter` mask + `EdgeMargin`.** Today's masks
  (`Edges/LowNoise/RandomBlobs`) all distribute hazard globally; none floods *per room center with a
  safe rim*, which is the Toxic Sewers signature ("river of sludge in the center, normal tiles on
  the edges"). New mask consumes the `RoomGraph`, floods each room's interior inset by `EdgeMargin`
  cells, leaving a dry walkable rim. For walkable sludge, recipes set `keepConnected = false` (the
  dry-catwalk machinery is moot — and harmful, since carving "dry" floor through a walkable-sludge
  pool just removes hazard for no connectivity reason). *Alternative (a1):* a continuous
  `PathStage(RIVER)` through room centers — rejected as primary because the source hazard is
  per-room, not one winding river, but keep it documented for a "single river" aesthetic.

### Needs **improvement**

- **`PrefabRoomStage` → slot targeting.** Currently it stamps random pool templates into non-
  entrance/non-terminal rooms (`skipEntranceAndTerminal = true`) with no way to say "this template
  at the entrance" or "that one at the terminal." Toxic Sewers has *role-specific* rooms: a small-
  square **start**, a rounded sludge **boss** at the terminal, and a rare **treasure**. Add optional
  `entranceTemplate` / `terminalTemplate` bindings (placed at those exact graph rooms), leaving the
  existing pool behavior for interior slots and the existing default (both null) byte-identical.
- **`BossArenaStage` → confirm it composes with a prefab arena.** The `Tagged` pick is documented as
  selecting "a tagged `PrefabRoomStage` arena." Verify that path works end to end (prefab tags the
  terminal room; `BossArena(Tagged)` finds it and records `boss` without overwriting the authored
  sludge/walkway interior). If `Tagged` is unimplemented, either implement it or use
  `TerminalRoom` + the terminal-targeted prefab from the improvement above. This is a verify-or-small-fix, not a redesign.

### Needs **adding (net-new)**

- **`FlowFieldStage`** (worldgen): writes a per-cell flow direction into a `MapLayer` for a
  deterministic subset of sludge rooms (so "some rivers flow"). Pure data; runtime conveyor reads it.
- **`HazardProfile` + `HazardProfileSet`** (game-side): the declarative flavor system (§3.5).
- **`HazardEffectBehaviour`** (game-side runtime): applies on-stand status/damage with linger (§3.6).
- **`ConveyorBehaviour`** (game-side runtime): directional push from the flow `MapLayer` (§3.6).
- **Authored content (separate follow-up, not this commit):** start/treasure/boss templates;
  sludge palette flavors; Gulpord + 3-slime `BossBinder`; Master Rat treasure binder; Golden Rat
  roamer binder.

### Carry-over dependency

- **`Passability` 3-value class** (Snake Pit spec). Required so sludge can be `Passable` *and* carry
  an effect. **`RoomShape.Ellipse`** (Snake Pit spec) is *optional-but-handy* for the "rounded
  square" boss room, though a prefab can author the rounding instead — no hard dependency.

---

## 3. Detailed specs

### 3.1 Palette correction — sludge becomes `Passable`

**Files:** `DemoSceneBuilder.CreateSewersPalette` (and any authored sewer palette `.asset` — grep),

`TilemapMapBuilder`.

- Change the sludge entry from impassable to **`Passability.Passable`** (was `false`). Update the
  `SewerToxic` comment ("impassable toxic channel" is now wrong).
- Confirm `TilemapMapBuilder` gives `Passable` sludge **no collider** (it merges only impassable
  entries into the composite). Walkable sludge should render and be walked on.
- The damage/status is **not** here — passability stays a pure collision/render concern. The effect
  lives in the `HazardProfileSet` (§3.5). This split is deliberate (layering).

### 3.2 `HazardFloodStage` — `RoomCenter` mask + `EdgeMargin`

**Files:** `Core/Stages/HazardFloodStage.cs`, `Unity/HazardFloodStageAsset.cs`, docs.

```csharp
public enum HazardMask { Edges, LowNoise, RandomBlobs, RoomCenter } // append RoomCenter

// new field; only meaningful for RoomCenter
public int EdgeMargin = 1; // dry rim width left around each room (1–3)
```

`RoomCenter` algorithm: read the published `RoomGraph`; for each room, flood floor cells whose

distance-to-room-edge `> EdgeMargin` (i.e., the interior minus a rim), up to a per-room cap derived

from `Coverage`. Skip the entrance and terminal rooms by default (the start is a safe square; the

boss room's sludge is authored by its prefab) — make that a bool so the recipe can opt in.

Deterministic, fixed-order over rooms. When `RoomGraph` is absent, no-op (don't throw).

Recipes using walkable sludge pass `keepConnected = false`. The existing masks and the

`keepConnected`/catwalk path are untouched.

### 3.3 `FlowFieldStage` (new)

**Files:** `Core/Stages/FlowFieldStage.cs`, `Unity/FlowFieldStageAsset.cs`, docs.

- Reads the sludge tile id and the `RoomGraph`. For a deterministic subset of sludge rooms
  (`FlowRoomFraction`, default ~0.4), pick a flow direction (4- or 8-dir) and write a direction code
  into a `MapLayer` (the existing per-cell metadata field) for that room's sludge cells. Non-flowing
  sludge cells get the "none" code.
- Publish the layer under a context key (e.g. `ContextKeys.FlowField`) for the runtime to read after
  build.
- Pure data, no tile writes. Deterministic. No-op without a `RoomGraph` or sludge cells.

*Design choice:* a separate stage (not a flag on `HazardFloodStage`) keeps "where is sludge" and

"which sludge flows" independently tunable and testable. Fold them only if that separation proves

pointless.

### 3.4 `PrefabRoomStage` — slot targeting (improvement)

**Files:** `Core/Stages/PrefabRoomStage.cs`, `Unity/PrefabRoomStageAsset.cs`, docs.

Add optional, default-null bindings:

```csharp
public string EntranceTemplate; // tag of a template to stamp into the entrance room (null = leave it)
public string TerminalTemplate; // tag of a template to stamp into the terminal room (null = leave it)
```

When set, stamp that specific template into the entrance/terminal graph room (overriding

`skipEntranceAndTerminal` for those two slots only); the rest of the pool fills interior slots as

today. Both null + `skipEntranceAndTerminal = true` ⇒ **identical to current behavior** (the

back-compat gate). Record areas as today (boss prefab should record/permit a `boss` tag for

`BossArena(Tagged)`).

### 3.5 `HazardProfile` + `HazardProfileSet` (new, game-side) — the flavor system

This is the precise answer to "how do I indicate what flavor each hazard cell is." Flavor

decomposes into orthogonal axes, and each axis lives in exactly one place:

| Axis | Lives in | Read by |
|---|---|---|
| Passability (Impassable/Passable/Breakable) | **palette** (worldgen) | `TilemapMapBuilder` colliders |
| On-stand status (+ duration, linger) & flat damage | **`HazardProfileSet`** (game) | `HazardEffectBehaviour` |
| Directional force (flow) | **`MapLayer`** (per-cell, from `FlowFieldStage`) | `ConveyorBehaviour` |
| Cosmetic twin (same art, no effect) | a **separate tile id** sharing the `TileBase`, with no/inert profile | n/a |

`HazardProfile` (ScriptableObject), game-side so it may reference combat status types:

```csharp
public sealed class HazardProfile : ScriptableObject
{
    public StatusEffect OnStandStatus;     // match UBearCombat's status enum/type — GREP, do not invent
    public float StatusRefreshSeconds = 1; // re-apply cadence while standing
    public float LingerSeconds = 3;        // kept after leaving (the "still sickened a few seconds" rule)
    public float DamagePerSecond = 0;      // flat DoT (0 = none)
    public bool  UsesFlow = false;         // if true, ConveyorBehaviour pushes per the flow layer
    public float ForceStrength = 0;        // push speed when UsesFlow
}
```

`HazardProfileSet` (ScriptableObject): a `tileId → HazardProfile` map (parallel to the palette,

not merged into it — keeps worldgen free of combat deps). Runtime components look up the cell's

tile id in this set; a tile id with no entry has no effect (that's the cosmetic/inert twin).

Map the three RotMG sludge flavors:

- `SLUDGE_SICK` → `{Passable (palette), SkullSick, linger 3s}` — room-center river.
- `SLUDGE_FLOW` → same as above + `UsesFlow=true, ForceStrength=…` — the flowing rivers.
- `SLUDGE_INERT` → **no profile entry**, shares the sprite — hallway water + stains.

*(Whether flowing-vs-still is a distinct tile id or the same id gated by the flow layer is a minor

call — I'd use one `SLUDGE` id with `UsesFlow` true and let the flow layer decide per cell, so you

don't fork the sprite. Implementer's discretion.)*

### 3.6 Runtime: `HazardEffectBehaviour` + `ConveyorBehaviour` (new, game-side)

**Mirror the existing tile-tag component pattern** — grep for how the warlord/`UBearCombat` applies

statuses; do not build a parallel status system.

- `HazardEffectBehaviour`: each tick, for the cell each player occupies, look up its `HazardProfile`
  in the `HazardProfileSet`. If `OnStandStatus != none`, apply/refresh it; track `LingerSeconds` so
  it persists after the player leaves. If `DamagePerSecond > 0`, apply DoT. Reads the build result
  (cell→tileId) + the set.
- `ConveyorBehaviour`: for cells whose profile has `UsesFlow`, read the flow `MapLayer` direction and
  add `ForceStrength` to the player's velocity that frame.
- Both are **server-authoritative** in the eventual MP port (clients receive the resulting status/
  velocity) — out of scope here; single-player now. Flag inline so no one bakes client authority in.

### 3.7 Guard / DistanceField config

Recipe-level only: `DistanceFieldStage` and `ConnectivityGuardStage` predicates include `SLUDGE`.

`ConnectivityGuardStageAsset._passableTiles` gains the sludge id; no code change (it already builds

the predicate from the list).

---

## 4. Acceptance criteria

### 4.1 Backward-compat gate

All existing tests green, untouched; Sewers/Badlands/Snake-Pit hashes unchanged. `HazardMask`'s

three original values behave identically; `PrefabRoomStage` with null slot bindings is byte-identical.

### 4.2 The correction (regression tests — these are the point)

- **Sludge is walkable:** build a `RoomCenter`-flooded map; the soft `ConnectivityGuard`
  (`floor ∪ sludge`, `required={boss}`) passes, and there exists an entrance→boss path that **passes
  through at least one sludge cell** (proves you walk *through* it, not around).
- **No dry-catwalk dependency:** the same map passes with `keepConnected = false` (sludge walkability,
  not dry routing, is what makes it solvable).

### 4.3 New-stage tests

- **`RoomCenter` mask:** every flooded room has sludge in its interior **and** a dry rim of width
  ≥ `EdgeMargin`; entrance/terminal skipped by default; deterministic per seed; no-op without a graph.
- **`FlowFieldStage`:** deterministic; flowing rooms' sludge cells have a defined direction code,
  non-flowing cells read "none"; `FlowRoomFraction` roughly honored.
- **`PrefabRoomStage` slot targeting:** `entranceTemplate`/`terminalTemplate` land in the entrance/
  terminal rooms; pool still fills interiors; null bindings unchanged.

### 4.4 Flavor-system tests

- **Profile lookup:** a `SLUDGE_SICK` cell resolves to the SkullSick profile; an inert cell resolves
  to none.
- **(PlayMode)** standing on damaging sludge applies SkullSick and keeps it `LingerSeconds` after
  leaving; standing on a flowing cell nudges player velocity in the flow direction.

### 4.5 Acceptance recipe (test fixture — not the shipped themed dungeon)

```csharp
const int WALL = 0, FLOOR = 1, SLUDGE = 2, DOOR = 3;

var fill     = new FillStage(WALL);
var rooms    = new RoomGraphStage(FLOOR, RoomGraphLayout.Branching,
                   roomCountMin: 12, roomCountMax: 14, corridorWidth: 1, doorTile: -1);
var entrance = new EntranceStage(/* NearEdge */);
var distance = new DistanceFieldStage(passable: t => t == FLOOR || t == SLUDGE); // sludge walkable
var sludge   = new HazardFloodStage(FLOOR, SLUDGE, HazardMask.RoomCenter,
                   coverage: 0.35f, keepConnected: false /*, edgeMargin: 1 */);
var flow     = new FlowFieldStage(/* sludgeTile: SLUDGE, flowRoomFraction: 0.4f */);
var prefab   = new PrefabRoomStage(/* pool…, terminalTemplate: "boss-sludge-ring",
                   entranceTemplate: "start-square" */);
var boss     = new BossArenaStage(/* Pick = Tagged ("boss") or TerminalRoom */);
var guard    = new ConnectivityGuardStage(
                   passable: t => t == FLOOR || t == SLUDGE || t == DOOR, // SOFT over walkable sludge
                   requiredTags: new[] { "boss" },
                   onFail: GuardFailAction.Throw);

// recipe = fill → rooms → entrance → distance → sludge → flow → prefab → boss → guard, MaxRerolls > 0
```

Run across 25 seeds (house convention): build succeeds, boss reachable over `floor ∪ sludge`, and

the cross-sludge-path assertion (§4.2) holds.

---

## 5. Files-to-touch checklist

- [ ] `Core/Stages/HazardFloodStage.cs` + `Unity/HazardFloodStageAsset.cs` — `RoomCenter`, `EdgeMargin`.
- [ ] `Core/Stages/FlowFieldStage.cs` + asset — new.
- [ ] `Core/Stages/PrefabRoomStage.cs` + asset — `entranceTemplate`/`terminalTemplate`.
- [ ] Palette: flip sludge to `Passability.Passable` (`DemoSceneBuilder` + grep authored palettes).
- [ ] `TilemapMapBuilder` — verify Passable sludge gets no collider (likely already true).
- [ ] Game-side: `HazardProfile.cs`, `HazardProfileSet.cs`, `HazardEffectBehaviour.cs`, `ConveyorBehaviour.cs`.
- [ ] `Passability` 3-value class — only if the Snake Pit spec hasn't landed it (shared prerequisite).
- [ ] Docs: `WorldGenStages.md` + README (RoomCenter mask, FlowFieldStage, PrefabRoom slots);
      a short note on the HazardProfile axes split.
- [ ] Tests per §4.

## 6. Out of scope / follow-ups

- Themed recipe asset + palette flavors + Gulpord/3-slime `BossBinder` + Master Rat + Golden Rat
  roamer (content task).
- Compound **L/U-shaped rooms** ("count as one room"): use authored L/U prefabs for now; a true
  rectangle-merging compound-room generator is a deferred, larger feature.
- Multiplayer server-authority + replication for statuses and flow (gated on the FishNet port).
- `PathStage` single-winding-river variant (a1) if a different sludge aesthetic is ever wanted.
