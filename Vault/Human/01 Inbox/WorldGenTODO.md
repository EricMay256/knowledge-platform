---
CreatedAt: 2026-06-28T16:42:05Z
LastUpdated: 2026-07-01T00:54:39Z
Type:
Status:
tags:
aliases:
---

# UBear WorldGen — Implementation TODO

Tracks building out the generation system specced in

[WorldGenStages.md](WorldGenStages.md) and [WorldStructureSpec.md](WorldStructureSpec.md).

Stage parameters/algorithms live in the stage reference; this doc is the *build order +

status + acceptance*. Each stage is pure-C# `UBear.WorldGenSystem`, deterministic

(`ComputeHash`-stable), and headless-tested.

**Status:** `[x]` done · `[ ]` open. Batches are ordered by leverage/dependency.

---

## Done

- [x] **Context blackboard** — `MapBuildContext.Set/TryGet<T>` + `ContextKeys` *(e8f2261)*
- [x] **`MapLayer`** — parallel int field for per-cell metadata
- [x] **`DrunkardWalkStage`** — organic tunnels; tags start/boss; connected by construction
- [x] **`EntranceStage`** — publishes the start cell + safe pocket
- [x] **`DistanceFieldStage`** — BFS depth layer from the entrance
- [x] **`ConnectComponentsStage`** — KeepLargest / Bridge / BridgeOrDiscard
- [x] **`ConnectivityGuardStage`** — asserts passable + required cells reachable
- [x] **Snake Pit recipe** — fuzz-verified solvable across 25 seeds (test)

---

## Batch 1 — Room-based dungeon chain ✅

Unlocks the Toxic Sewers archetype and everything graph-driven.

*Done: 376 EditMode tests green, zero CS warnings (was 322 + 54 new cases).*

- [x] **`RoomGraph` type + `RoomGraphStage`** — rooms + adjacency + entrance/terminal indices,
      published at `ContextKeys.RoomGraph`. Layouts: Linear / Branching / HubAndSpoke / Looped
      (`ExtraLoopEdges`) / BSP. Rich edges carry a door chokepoint cell for locks. *Tested:*
      determinism + grid/graph `AreAllConnected` per layout; `room/i` areas; loop edges.
- [x] **`BossArenaStage`** — `Pick` Deepest (distance field) / TerminalRoom (graph) / Tagged;
      `ArenaRadius`; seals the approach door (floor only — never overwrites a lock); records `boss`.
- [x] **`LockAndKeyStage`** — locks `LockCount` spanning-tree edges along the entrance→terminal
      path; each key in a room upstream of its lock. *Asserted:* key-aware fixpoint flood reaches
      `boss`. Stamped `LockTile` is a logical gate (the closing guard counts it passable).
- [x] **`RoomTemplate` type + `PrefabRoomStage`** — `FromRows` char-grid authoring; stamps a
      fitting template into graph rooms (entrance/terminal preserved); records `loot-vault`.
- [x] **Toxic Sewers recipe + fuzz test** — `RoomGraph(Looped) → PrefabRoom → LockAndKey →
      BossArena → ConnectivityGuard(boss,key)`, solvable across 25 seeds. *Note:* `HazardFlood`
      slots in after PrefabRoom but is a **Batch 3** stage, so it's omitted here.

## Batch 2 — Authoring assets (editor-usable) ✅

The stages are core-only today; this makes them usable from `MapRecipeAsset` in the editor.

*Done: 384 EditMode + 2 PlayMode tests green, zero CS warnings.*

- [x] **`*StageAsset` wrappers** for every implemented stage (DrunkardWalk, Entrance,
      DistanceField, ConnectComponents, ConnectivityGuard, RoomGraph, BossArena, LockAndKey,
      PrefabRoom). The `Func<int,bool>` stages take a **passable tile-set** and build the predicate;
      PrefabRoom authors templates as char-rows + legend. *Tested:* each `CreateStage` returns its
      stage and a composed `MapRecipeAsset` builds via `Generate()` (room dungeon + lock chain).
- [x] **`Validate(List<string>)`** on each asset — incl. LockAndKey rejecting a lock tile that's
      in the passable set (it could never gate), and tile-set/room-count/template sanity.
- [x] **Demo dungeon** — a "Sewers" recipe asset (graph-driven chain: RoomGraph(Looped) → Prefab
      vault → LockAndKey → BossArena → Guard, seed 7) built into `PlaygroundDemo` as a worldgen
      region reached by a **portal** (`DemoPortal` + `DemoSpawnAnchor` land the hero on the
      generated entrance). Reuses the badlands enemy archetypes; a PlayMode smoke test asserts it
      builds and records boss/key/loot-vault. *(Showcases the graph chain rather than the simpler
      Snake Pit, which only exercises BossArena.)*

## Batch 3 — Remaining structure / terrain stages ✅

*Done: 417 EditMode + 2 PlayMode tests green, zero CS warnings. Each stage has a `*StageAsset`.*

- [x] **`MazeStage`** — recursive-backtracker / Wilson; `BraidChance` knocks dead-ends into loops;
      `DeadEndTag` records the rest. Connected by construction; fixed-order/RNG determinism.
- [x] **`RoomTemplate` sockets + `TemplateAssemblyStage`** — typed edge sockets + rotation/mirror
      transforms (direction derived from the position transform); Spine / HubAndSpoke / Sprawl with
      occupancy + backtracking; publishes a `RoomGraph`, connected by construction.
- [x] **`MirrorStage`** — Vertical / Horizontal / Both reflection (pure geometric copy, no RNG).
- [x] **`HazardFloodStage`** — Edges / LowNoise / RandomBlobs mask toward Coverage; `KeepConnected`
      carves dry catwalks via BFS over floor∪hazard so it never tunnels through walls. Wired into the
      demo Sewers recipe (toxic channels, placed before the anchors so they stay dry).
- [x] **`DecorationScatterStage`** — AgainstWall / OpenFloor / RoomCenter props with density + spacing.
- [x] **`StairLinkStage` + multi-floor `DungeonInstance`** — paired up/down stairs (down deepest, up
      at the entrance); `DungeonInstance` stacks per-floor grids from reproducible sub-seeds and pairs
      the stairs between floors.

## Batch 4 — Biome / overworld stages

*Direction (2026-06-15): the elevation-banded biome model you want — deep water → beach → lowlands

→ forest → mountains by ascending thresholds — is already `NoiseRegionsStage` (shipped). So Batch 4

leads with that + `RegionMapStage`; the matrix / blend / river stages below are **optional** extras,

not required for the elevation model.*

- [x] **`RegionMapStage`** — flood-fills contiguous regions → `RegionMap` (id layer + `RegionInfo[]`
      with area/centroid/biome), drops sub-`MinRegionSize` specks. *Core: realm quadrants, minimaps,
      region-scaled spawn density.*
- [x] **`MaskedSubStage`** — runs sub-stages but reverts net tile writes outside a mask tile-set
      (trees on forest, rocks on mountain). *Core: biome detail over the elevation bands.*
- [x] **`BiomeBlendStage`** — directional edge bands (grass→beach near water, mountain→scree near
      grass) within `Width`; transitions read the original biome snapshot so they're independent.
- [x] **`PathStage`** (rivers / roads / corridors — one versatile stage) — A* between tagged points
      (POIs), optional cost-field bias (low-ground rivers / avoid-terrain roads), `Width` + `Meander`,
      and Single / SourceToSink / Network(MST completeness) modes. Rivers/roads are configurations,
      not separate classes.
- [ ] **`BiomeMatrixStage`** — temperature × moisture lookup. *(optional — Minecraft-style climate space; the only Batch 4 item left, and the one you flagged as not needed)*

## Cross-cutting

- [x] **Reroll-on-fail** — `MapGenerator.GenerateWithRetry` + `MapRecipeAsset` *MaxRerolls*: catch the
      guard's throw and retry the next seed (the RotMG "just reroll" move). The demo Sewers recipe uses
      it instead of a pinned seed.
- [ ] **Seed-fuzz CI harness** — per shipping recipe, generate N seeds and assert
      `ConnectivityGuard` + archetype invariants (boss reachable, key-before-lock, min walkable
      area, no orphan markers). A bad seed in MP hits everyone — make this part of the headless run.
- [ ] **`ScatterSpawnPointsStage` depth weighting** — optional curve reading the distance field
      to bias enemy count/tier deeper in.

---

## Deferred / gated (tracked in their own specs)

- [ ] **`SpawnAreaBinder` server-authoritative port + seed-based `ZoneOpen` replication** —
      WorldStructureSpec Part D/H. *Gated on the FishNet timeline.*
- [ ] **Realm layer** — `BiomeRoster` / Portal Nexus / `RealmState` / `WorldDirector` +
      completion + Challenge-map capstone — WorldStructureSpec Part C. *Game-shell, after the stages.*
- [ ] **Required-breakable passability class** — palette `Breakable` + soft-connectivity guard
      (WorldStructureSpec G.11), once a recipe needs load-bearing destructibles.
- [ ] **Weapon damage model** (roll min/max + Atk) — not worldgen, but the piece that makes
      character classes *feel* distinct; tracked alongside the class system.
