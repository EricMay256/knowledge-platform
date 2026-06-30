---
CreatedAt: 2026-06-28T16:42:05Z
LastUpdated: 2026-06-29T22:06:52Z
---
# Spec: `RoomGraphStage` shape/corridor knobs + destructible-terrain passability

**Audience:** Claude Code (implementation handoff).

**Goal:** Three coordinated changes that, together, let a recipe author a faithful RotMG

*Snake Pit* — circular rooms linked by hallways filled with **load-bearing destructible**

blocks — without a new structure generator.

1. `RoomGraphStage`: add an **`Ellipse`** room shape (circular rooms of varying size).
2. `RoomGraphStage`: add a **`CorridorTile`** parameter (carve corridors as a chosen tile, e.g. a breakable block, instead of floor).
3. **Destructible terrain**: promote palette passability to a 3-value class
   (`Impassable | Passable | Breakable`) and add a runtime `DestructibleTileBehaviour`
   that turns a `Breakable` cell into floor when destroyed.

These mirror the existing house conventions: pure-C# `UBear.WorldGenSystem` stages, a

matching `*StageAsset` wrapper, `ComputeHash`-stable determinism, fixed-order RNG, and a

closing `ConnectivityGuardStage`.

---

## 0. Hard constraints (apply to every change)

- **Backward compatibility is a gate.** Every new field defaults to its *current* behavior
  (`RoomShape.Rectangular`, `CorridorTile = -1`). After these changes the existing Sewers,
  Badlands, and (DrunkardWalk) Snake Pit recipes and **all existing EditMode/PlayMode tests
  must stay green with no edits**, and generated maps for those recipes must be byte-identical
  (`ComputeHash()` unchanged). If a golden-hash test exists, it must not move.
- **Determinism.** No RNG is added for shape (it's pure geometry). Any iteration that affects
  writes stays fixed-order — never `HashSet`/`Dictionary` enumeration.
- **One commit per change** (matches the repo's "one feature per commit, headless-tested" cadence),
  with the new EditMode tests in the same commit as the code they cover.
- **Confirm before you rename serialized fields** (see §3.1 migration).

---

## 1. `RoomGraphStage` — `Ellipse` room shape

**Files:**

- `UBearWorldGen/Package/Runtime/Core/Stages/RoomGraphStage.cs`
- `UBearWorldGen/Package/Runtime/Unity/RoomGraphStageAsset.cs`
- `UBearWorldGen/Package/README.md` + `Docs/WorldGenStages.md` (document the new param)

**What exists today** (verified): `RoomGraphStage.Apply` carves each room as a filled rectangle

via `CarveRoom(grid, rect)` and records the full rectangle via `RecordRoomArea(...)`. Corridors

are L-paths from `rect.Center` to `rect.Center`, carved by `CarveBrush`.

### 1.1 Core change

Add an enum and a field:

```csharp
public enum RoomShape { Rectangular, Ellipse }

// new public field on RoomGraphStage; default preserves current behavior
public RoomShape Shape = RoomShape.Rectangular;
```

Append it to the constructor as an **optional trailing parameter** so existing positional/named

calls keep compiling:

```csharp
public RoomGraphStage(
    int floorTile,
    RoomGraphLayout layout = RoomGraphLayout.Branching,
    int roomCountMin = 8, int roomCountMax = 14,
    int minRoomSize = 4, int maxRoomSize = 9,
    int extraLoopEdges = 0, int corridorWidth = 1,
    int doorTile = -1, string roomTag = "room",
    RoomShape shape = RoomShape.Rectangular,
    int corridorTile = -1)            // §2
```

Factor the shape test out so **carving and area-recording use the same predicate** (otherwise a

recorded `room/i` cell could land on a wall and break spawn placement):

```csharp
// True if (x,y) is inside the room under the active shape.
private bool IsInsideRoom(in RoomRect r, int x, int y)
{
    if (Shape == RoomShape.Rectangular)
        return true; // caller already iterates the rect bounds

    // Inscribed ellipse: touches each rect edge at its midpoint.
    // Degenerate (width or height == 1) -> keep the full line.
    if (r.Width <= 1 || r.Height <= 1) return true;

    double cx = r.X + (r.Width  - 1) / 2.0;
    double cy = r.Y + (r.Height - 1) / 2.0;
    double ax = (r.Width  - 1) / 2.0;
    double ay = (r.Height - 1) / 2.0;
    double nx = (x - cx) / ax;
    double ny = (y - cy) / ay;
    return nx * nx + ny * ny <= 1.0 + 1e-9; // epsilon so edge-midpoints are inside
}
```

Apply it in both `CarveRoom` and `RecordRoomArea`:

```csharp
// CarveRoom
for (int y = room.Y; y <= room.Bottom; y++)
for (int x = room.X; x <= room.Right; x++)
    if (grid.InBounds(x, y) && IsInsideRoom(room, x, y))
        grid[x, y] = FloorTile;

// RecordRoomArea — identical guard, so the area matches the carved shape exactly
```

### 1.2 Why corridors still connect (correctness note — verify, don't assume)

Corridors run **axis-aligned from `rect.Center`**. An inscribed ellipse touches the bounding rect

at the *midpoint of each side*, which is exactly where a horizontal or vertical ray from the

center exits — so the corridor meets the room's floor with no 1-cell gap. This should hold, but

it is the one place an ellipse could regress connectivity. The closing `ConnectivityGuardStage`

in the acceptance recipe (§4) is the backstop; if it ever fails for `Ellipse`, the fix is to clamp

the corridor's room-side endpoint to the nearest carved cell rather than `rect.Center`.

### 1.3 Asset + docs

- `RoomGraphStageAsset`: add `[SerializeField] private RoomShape _roomShape = RoomShape.Rectangular;`
  and thread it into `CreateStage()`.
- Document `Shape` in the README param block and the `WorldGenStages.md` `RoomGraphStage` table.

### 1.4 "Circular" vs "elliptical" — recipe-level, no extra code

`Ellipse` inscribed in a non-square room reads as an **oval**. True circles are the square special

case, so the recipe gets circular rooms by using a near-square size range

(`minRoomSize ≈ maxRoomSize`); the natural variation in placed-room size still yields *varying*

circle radii. **Do not** add a separate `Disc` mode in this task — it's a trivial follow-on

(`radius = min(w,h)/2` centered in the rect) if guaranteed circles regardless of rect aspect are

ever wanted. Note this in the docs and stop.

### 1.5 Per‑room shape variation

To support the mixed circular‑and‑square geometry of the original Snake Pit, this change introduces an optional per‑room shape mode. A new field

public RoomShapeMode ShapeMode = RoomShapeMode.Uniform;

controls how RoomGraphStage selects shapes. In Uniform mode (default), all rooms use the stage‑level Shape value, preserving current behavior and all existing recipe hashes. In PerRoom mode, each room’s shape is chosen by a fixed, deterministic rule (no RNG), e.g. alternating rectangular/ellipse by room index or selecting ellipses only for sufficiently large bounding rects. This enables mixed‑shape dungeons without affecting backward compatibility, serialization, or golden tests. Recipes opt into mixed geometry by setting ShapeMode = PerRoom and choosing an appropriate Shape baseline; the deterministic rule ensures stable ComputeHash() output and fixed‑order carving.

---

## 2. `RoomGraphStage` — `CorridorTile` parameter (decision B1)

**Same files as §1.**

### 2.1 Core change

Add `public int CorridorTile = -1;` (`-1` ⇒ carve corridors as `FloorTile`, the current behavior).

The only subtlety: the L-path **starts at `rect.Center`, i.e. inside the room**, so a naive brush

would stamp `CorridorTile` over room-interior floor. Guard against clobbering already-carved floor:

```csharp
private void CarveBrush(MapGrid grid, int cx, int cy)
{
    int tile = (CorridorTile >= 0) ? CorridorTile : FloorTile;
    int half = CorridorWidth / 2;
    for (int dy = 0; dy < CorridorWidth; dy++)
    for (int dx = 0; dx < CorridorWidth; dx++)
    {
        int x = cx - half + dx, y = cy - half + dy;
        if (!grid.InBounds(x, y)) continue;

        // Never overwrite room-interior floor with a corridor tile.
        if (tile != FloorTile && grid[x, y] == FloorTile) continue;

        grid[x, y] = tile;
    }
}
```

`DoorTile` stamping is unchanged. The `RoomEdge` door chokepoint is still recorded — for the Snake

Pit the recipe sets `DoorTile = -1` (the whole hallway is breakable; there's no separate door tile),

but the chokepoint stays available for lock/boss logic.

### 2.2 Interaction with `BossArenaStage`

`BossArenaStage` seals the approach door "floor only — never overwrites a lock." When the approach

corridor is `Breakable` rather than floor, sealing is effectively a no-op (it won't overwrite the

breakable tile), which is **correct for the Snake Pit** — the player breaks into the boss room.

No change needed; just confirm `BossArenaStage` doesn't throw when the approach isn't floor.

### 2.3 Asset + docs

- `RoomGraphStageAsset`: add `[SerializeField] private int _corridorTile = -1;`, thread into `CreateStage()`.
- Document in README + `WorldGenStages.md`.

---

## 3. Destructible terrain

Implements `WorldGenStages.md §0.2` and `WorldStructureSpec.md` G.11. Two parts: a generation/data

change (passability becomes 3-valued) and a runtime behaviour. **The connectivity guard needs no

code change** — `ConnectivityGuardStageAsset` already builds its predicate from a `_passableTiles`

list, so *soft* connectivity = include the breakable tile id in that list.

### 3.1 Passability → 3-value class

**Files:**

- `TilePaletteAsset` (palette stores `tile id → name + colour + passability + optional prefab`).
- `TilemapMapBuilder` (impassable palette entries merge into `TilemapCollider2D` + `CompositeCollider2D`).
- Any other reader of the current passability `bool` — **grep for it first** (e.g. `passab`, the
  field name on the palette entry, `MapBuilderBehaviour`). I have *not* seen every reader; enumerate
  them before editing.

Introduce:

```csharp
public enum Passability { Impassable, Passable, Breakable }
```

**Migration (do this carefully — Unity serialization will silently drop a renamed field):**

- The demo palettes are code-generated in `DemoSceneBuilder.CreateTilePalette`, so regenerated
  assets are fine. The risk is *hand-authored* `.asset` palettes. **Grep the repo for palette
  `.asset` files** before changing the field.
- Prefer adding the enum field while preserving the old `bool` via `[FormerlySerializedAs]` or an
  `ISerializationCallbackReceiver.OnAfterDeserialize` that maps the legacy bool
  (`true → Passable`, `false → Impassable`) into the enum when the enum is still at its default.
  Do **not** do a bare rename.
- Update `CreateTilePalette` (and any code-side palette construction) to pass `Passability` instead
  of `bool`. A `Breakable` entry is authored exactly like an `Impassable` one but with the new value.

**Collider semantics:** in `TilemapMapBuilder`, **`Breakable` generates collision like `Impassable`**

(it blocks movement until destroyed). Only `Passable` is walkable at build time.

**Connectivity semantics (config, not code):** for a load-bearing-destructible recipe, the closing

`ConnectivityGuardStageAsset._passableTiles` list **includes the breakable tile id** (soft

connectivity: floor ∪ breakable). This guarantees the dungeon is *completable*, not that it's

traversable untouched. `GridConnectivity.FloodFill` already takes the predicate; nothing else changes.

### 3.2 Runtime: `DestructibleTileBehaviour`

**Mirror the existing tile-tag component pattern.** G.11 says runtime needs nothing beyond the

`TOXIC`/`ICE` pattern (a game-side component that reads a palette tag). **I have not seen the TOXIC/ICE

component source — grep for it** (`Toxic`, `Ice`, `IDamageOnStand`, whatever the slow/damage component

is) and follow that structure so this is consistent with the codebase rather than a new idiom.

Contract:

- Identifies `Breakable` cells (via palette passability == `Breakable`).
- Tracks per-cell HP. Default **1–2 hits** to match "easily destructible." HP source/config: a field
  on the behaviour or a palette-driven value — match how TOXIC carries its damage value.
- Takes damage from player projectiles. **Wire to the existing combat/projectile hit path** — grep
  for where projectiles resolve hits against walls/tiles; do not invent a parallel system.
- On destroy: swap the cell to `FLOOR` in the build result, **repaint the Tilemap cell**, **rebuild
  the affected `CompositeCollider2D` region**, and **raise a tile-changed event**.

### 3.3 Runtime: `TilemapMapBuilder` mutation API + event

Add a minimal mutation seam (also the future minimap/binder hook):

```csharp
// Repaint one cell to a new tile id and refresh collision.
public void SetCell(int x, int y, int tileId);

// Convenience used by DestructibleTileBehaviour.
public void BreakCell(int x, int y); // SetCell(x, y, floorTileId) + collider refresh

// Fired after any cell mutation (minimap, audio, binders).
public event Action<int /*x*/, int /*y*/, int /*newTileId*/> CellChanged;
```

`SetCell` must mark the `CompositeCollider2D` dirty (or rebuild the affected chunk) so the broken

cell stops colliding the same frame. If the composite is large, prefer a chunked/region rebuild over

a full regenerate for perf, but a full `Generate()` is acceptable for a first pass — note it as a TODO.

### 3.4 Explicit non-goal: seed-determinism of breaks

Broken cells are **runtime state**, not regenerated from the seed (this is the one piece of geometry

that doesn't derive from the seed — `WorldStructureSpec.md` D.1). **Do not** try to make destruction

seed-deterministic or persist it through regeneration. Multiplayer replication of break-diffs is a

separate, deferred task (gated on the FishNet port). Single-player only here.

---

## 4. Acceptance criteria

### 4.1 Existing tests unchanged

All current EditMode + PlayMode tests pass with **no edits**; Sewers/Badlands/Snake-Pit recipe

hashes are unchanged. This is the backward-compat gate.

### 4.2 New EditMode tests

- **Ellipse determinism & shape:** same seed ⇒ identical grid; for an `Ellipse` room, every recorded
  `room/i` cell satisfies `IsInsideRoom`, the carved set ⊆ the rect, and corner cells of a
  sufficiently large room are *walls* (proves it's not still rectangular).
- **Ellipse connectivity:** a `RoomGraph(Linear, Ellipse)` map passes a hard `ConnectivityGuardStage`
  over floor (proves corridors meet ellipse rooms).
- **CorridorTile:** with `CorridorTile = B`, corridor cells read `B`, room-interior floor is untouched
  (no `B` inside rooms); with `CorridorTile = -1`, output is identical to pre-change (golden).
- **Passability migration:** a palette authored with the legacy bool deserializes to the correct
  `Passability` enum value.

### 4.3 Fuzz test (house convention: 25 seeds)

Build the acceptance recipe below across 25 seeds and assert, each seed:

- the build succeeds (soft guard reaches `boss`);
- `boss` is reachable over **floor ∪ breakable**;
- `boss` is **NOT** reachable over **floor only** — this proves the destructible corridors are
  genuinely *load-bearing*, not decorative.

### 4.4 PlayMode test (optional but recommended)

Spawn the acceptance map, `BreakCell` a breakable corridor cell, assert: tile becomes floor,

`CellChanged` fires, and the cell no longer collides.

### 4.5 Acceptance recipe (test fixture — not the shipped themed dungeon)

```csharp
// Tile ids for the fixture
const int WALL = 0, FLOOR = 1, BREAKABLE = 2;

var fill   = new FillStage(WALL);
var rooms  = new RoomGraphStage(
                 floorTile: FLOOR,
                 layout: RoomGraphLayout.Linear,
                 roomCountMin: 7, roomCountMax: 7,   // start + 5 + boss
                 minRoomSize: 6, maxRoomSize: 7,     // near-square => circular
                 corridorWidth: 1,                   // narrow => the 1-tile-gap tech
                 doorTile: -1,
                 shape: RoomShape.Ellipse,           // §1
                 corridorTile: BREAKABLE);           // §2 (load-bearing)
var entrance = new EntranceStage(/* NearEdge, pocket */);
var distance = new DistanceFieldStage(passable: t => t == FLOOR || t == BREAKABLE); // include breakable
var boss   = new BossArenaStage(/* Pick = TerminalRoom, BossTag = "boss" */);
var guard  = new ConnectivityGuardStage(
                 passable: t => t == FLOOR || t == BREAKABLE, // SOFT
                 requiredTags: new[] { "boss" },
                 onFail: GuardFailAction.Throw);

// recipe = fill -> rooms -> entrance -> distance -> boss -> guard, MaxRerolls > 0
```

(The themed Snake Pit — palette/grates/treasure-room/Stheno binders — is a **separate task**; this

fixture only proves the three engine changes compose.)

---

## 5. Files-to-touch checklist

- [ ] `Core/Stages/RoomGraphStage.cs` — `RoomShape` enum, `Shape` + `CorridorTile` fields, ctor
      params, `IsInsideRoom`, `CarveRoom`/`RecordRoomArea`/`CarveBrush` updates.
- [ ] `Unity/RoomGraphStageAsset.cs` — `_roomShape`, `_corridorTile`, thread into `CreateStage()`.
- [ ] `TilePaletteAsset` (+ palette entry type) — `Passability` enum + migration.
- [ ] `DemoSceneBuilder.CreateTilePalette` (+ any code-side palette builders) — pass `Passability`.
- [ ] `TilemapMapBuilder` — treat `Breakable` as colliding; `SetCell`/`BreakCell`/`CellChanged`.
- [ ] `Runtime/.../DestructibleTileBehaviour.cs` (new) — mirror TOXIC/ICE pattern.
- [ ] README.md + `Docs/WorldGenStages.md` — document `Shape`, `CorridorTile`, the passability class.
- [ ] EditMode tests (§4.2), fuzz test (§4.3), optional PlayMode test (§4.4).

## 6. Out of scope / follow-ups

- Themed Snake Pit recipe + palette + Snake-Grate continuous spawner + treasure-room button trap +
  Stheno `BossBinder` (separate content task).
- Minimap (strongly recommended for this dungeon — corridors are invisible until broken).
- Multiplayer break-diff replication (deferred to the FishNet port; see §3.4 / D.1).
- A guaranteed-circle `Disc` shape mode (trivial follow-on; see §1.4).
