# Stage 1 spec — Testing & validation

**Source:** HANDOFF.md §5 Phase 1. **Status:** not started. **Depends on:** package-layout
fix (P0 below). **Blocks:** Stage 2 (skill encodes the schema; schema must be frozen here).

---

## 1. Goal

Stand up a `pytest` suite that pins the engine's behaviour — especially the parts that are
*dormant in Stage A but load-bearing for B2* (the full `decide()` policy ladder, `Policy`
band validation). The suite is the safety net that lets the A→B2 swap stay "mechanical":
if `core.py` / `models.py` / `service.py` are truly stable, these tests pass unchanged
against the Postgres/pgvector backends.

A secondary goal is to **shake out schema tweaks now**, while they are free, before Stage 2
documents the note schema and Stage 3 starts accumulating real data.

## 2. Scope

In scope: automated tests for `core.py`, `models.py`, `dedup_string.py`, `store_git.py`,
`service.py`, and the CLI outcome/exit-code contract. Test infrastructure (fixtures, a stub
`Deduper`, a `tmp_path` git vault). The packaging fix that makes the package importable.
Resolving the idempotency-key decision (§7).

Out of scope: any B2 code, the skill wrapper (Stage 2), CI wiring (note it as follow-up),
changing the architecture or the seams (HANDOFF §3 — do not let a test tempt a core import
of a concrete backend).

## 3. Deliverables

1. **P0 — package layout fix.** Make the engine importable as a package so both the test
   suite and `python -m …cli` work. Pick one, lowest-friction first:
   - Move the nine modules into a `vault_contrib/` directory (matches HANDOFF's
     `python -m vault_contrib.cli` and the zip's original shape), **or**
   - add packaging metadata (`pyproject.toml`) and keep a flat layout, adjusting the
     documented invocation accordingly.
   Recommendation: the `vault_contrib/` directory — it's what every docstring, the HANDOFF
   quick-start, and the relative imports already assume, so it's the smallest reconciling
   change. Confirm with one smoke run of the HANDOFF quick-start afterward.
2. `tests/` package with the cases in §4.
3. `pyproject.toml` (or `pytest.ini`) with pytest config; add `pytest` as a dev dependency
   (keep it out of `requirements.txt` — runtime stays single-dependency `pyyaml`).
4. A short `tests/README` or top-of-file docstring noting which tests are "B2 guard" tests
   (the dormant bands) so a future maintainer doesn't delete them as "testing dead code."
5. Resolution of the idempotency decision (§7), recorded in HANDOFF/CLAUDE.md.

## 4. Test cases (priority order)

### 4.1 `decide()` policy bands — `core.py` (highest value: B2 guard)
Drive with a **stub deduper** (or just hand-built `list[ScoredCandidate]`) so scores are
fixed inputs; `decide()` is pure.

- No similars → `Insert`.
- `Policy(flag_at=0.85)` (the A policy), top score `0.85` and `0.90` → `Flag`; `0.84` →
  `Insert`. Lock the **boundary is inclusive** (`>=`).
- The **independence invariant from HANDOFF §2**: a deduper that *surfaces* a 0.82 match
  while `flag_at=0.85` still yields `Insert`. Encode this as a named test — it's an
  intentional design property, not a bug.
- Full ladder with a B2-style policy `Policy(reject_at=0.97, merge_at=0.93, flag_at=0.85,
  link_at=0.70)`: assert each band's boundary maps to `Reject` / `Merge` / `Flag` / `Link`
  respectively, and below `link_at` → `Insert`.
- `Link` payload: `related_ids` contains exactly the candidates with `score >= link_at`,
  not all similars.
- Ladder is evaluated strongest-first and uses `max(score)`: given mixed similars, the
  **top** score selects the band.

### 4.2 `Policy.__post_init__` — `models.py` (B2 guard)
- Valid: A policy (`flag_at` only); a fully-ordered B2 policy; bands exactly equal
  (`reject_at == merge_at`) is allowed (`>=`, not `>`).
- Raises `ValueError`: out-of-order present bands (e.g. `merge_at=0.80, flag_at=0.85`);
  any band outside `[0,1]`.
- `None` bands are skipped in the ordering check (only "present" bands are compared).

### 4.3 `validate()` — `core.py`
- Empty/whitespace `title` → error; empty/whitespace `body` → error; blank
  `contributed_by` → error.
- Tag rules: a blank tag and a non-string tag each error; duplicate tags error.
- A clean note → `[]`.
- Note `validate()` runs on the *constructed* `Note`, which `.strip()`s fields in
  `Note.create`; build notes via `Note.create` to mirror the real path.

### 4.4 `_normalize()` + dedup paths — `dedup_string.py`
- `_normalize` maps case / surrounding & internal whitespace / punctuation to the same
  key: `"Two-phase TICK updates!!"` and `"two phase tick updates"` normalize equal.
- Exact path (no `fuzzy_threshold`): equal normalized title → `score 1.0`; unrelated →
  no candidate; the candidate never matches itself (`existing.id == candidate.id` skip).
- Fuzzy path (`fuzzy_threshold` set): a near title surfaces with `0 < score < 1.0`;
  titles below the threshold are dropped; output is sorted score-descending.

### 4.5 `GitMarkdownStore` round-trip — `store_git.py`
Use a `tmp_path` vault (`auto_commit=True`, `init_if_missing=True`).
- `insert` → `get` → equal `Note` (all fields); `iter_notes` yields it.
- **Horizontal-rule survival (explicit HANDOFF ask):** a body containing a `---` markdown
  horizontal rule on its own line must round-trip byte-for-byte through write→read. This
  guards the `split(_FRONTMATTER, 2)` `maxsplit=2` contract — lock it with a dedicated test.
- `add_to_review` writes to `review/<id>.md` with `status: flagged` and the
  `flag_reason` / `flag_similars` extra frontmatter keys in the documented shape.
- Each write produces its own git commit with the structured message
  (`vault: insert … by …`, `vault: flag … for review`). Assert via `git log --format=%s`.
- `auto_commit=False` writes the file but creates no commit.
- `update` on a missing note raises `KeyError`.
- A body with unicode survives (`allow_unicode=True` path).

### 4.5a Human contributors (first-class input path)
Human input is an explicitly supported, first-class contribution path — not an
afterthought and not a separate mechanism. The engine is identity-agnostic: `contributed_by`
is a free-form string, so a human contributes through the **same** `contribute()` /
CLI path as an agent and gets the same validation + dedup. Provenance is kept legible by a
**namespacing convention** (`agent:<id>` / `human:<name>`), documented on `Note.contributed_by`
and in the CLI `--by` help. No new schema field and no enforcement in Stage A (instructed,
not gated — B2's auth story formalizes identity).
- Test: a `human:<name>` contribution is accepted and round-trips with that provenance.
- Test: a human re-adding an agent's note is flagged like any other duplicate (humans are
  deduped too).

### 4.6 Outcome & exit-code contract — `service.py` + `cli.py`
Agents branch on these, so pin them:
- `ContributionService.contribute`: clean note → `status="inserted"`; exact-title dup →
  `status="flagged"` (note in `review/`, not `notes/`); empty body → `status="invalid"`
  (no file written, no commit).
- Exit codes (`cli._cmd_contribute`): `0` for `inserted`/`linked`, non-zero otherwise
  (`flagged`, `rejected`, `invalid`). Test via `main([...])` return value.
- `Merge` is `NotImplementedError` and unreachable under the A policy — a small test that
  feeding a `merge_at`-enabled policy + a high score raises it, documenting the deferred
  path rather than leaving it untested.

## 5. Test infrastructure
- `conftest.py`: a `tmp_path`-backed `GitMarkdownStore` fixture; a `StubDeduper` returning
  preset `ScoredCandidate`s for `decide()`/service tests; a `Note` factory.
- Keep the stub deduper conformant to the `Deduper` Protocol (it's `@runtime_checkable` —
  an `isinstance` assertion is a cheap conformance check).
- Tests must not import a concrete backend into anything under test beyond the composition
  root; they may *construct* concrete backends as the system-under-test.

## 6. Acceptance criteria
- `pytest` green on a fresh checkout after `pip install -r requirements.txt && pip install
  pytest`.
- HANDOFF quick-start (the three CLI commands) runs successfully against the fixed layout
  and produces `inserted` then `flagged`.
- Every band of `decide()` and every `Policy` ordering rule has a test (B2 guard coverage
  complete).
- The `---` horizontal-rule round-trip test exists and passes.

## 6a. Implementation status (done)
Stage 1 is implemented and green: **67 tests pass**; the HANDOFF quick-start reproduces
`inserted` → `flagged`; package layout reconstructed under `vault_contrib/`. The idempotency
decision below was resolved as **Option A** (implemented). One behaviour was discovered and
locked rather than changed:

- **`_normalize()` deletes punctuation without substituting a space**, so a hyphenated title
  collapses (`"Two-phase"` → `"twophase"`). Consequence: two titles differing only by a
  hyphen-vs-space do **not** normalize equal. This is a genuine Stage-A crude-dedup limitation
  (the kind semantic dedup fixes in B2), not a bug to patch now — `test_dedup_string.py` pins
  it so the behaviour is explicit. Flagging it as input to the Stage-3 "crude-dedup miss rate"
  signal.

## 7. Open decision — idempotency key — RESOLVED: Option A (implemented)
HANDOFF §5 flags it: `contribute()` mints a fresh `uuid4` per call, so a **retried**
contribution becomes a new note that then flags as a duplicate of the first. Options:
- **A — add an optional client-supplied idempotency key now** (mirrors HSS `client_run_id`):
  `contribute(..., client_run_id: str | None = None)`; if a note with that key exists,
  return the prior result as a no-op. Small, schema-affecting (adds a field), and cheapest
  to do *before* Stage 2 freezes the schema.
- **B — defer to B2**, accept that A-stage retries land in `review/` for manual cleanup.
Recommendation: **A**, because it is a schema change and schema changes are free now and
"annoying after the skill encodes them" (HANDOFF §5/§Phase 2). If chosen, add the field to
`Note` + `to_metadata`/`from_parts`, thread it through `service.contribute`, give it a
dedicated test, and document it in the schema for Stage 2. **This is the one decision in
Stage 1 that needs your sign-off** — it changes the public note schema.

## 8. Notes / risks
- Tests shell out to real `git`; require `git` on PATH in CI — document it.
- Windows: `GitMarkdownStore` uses `subprocess.run(["git", ...])`; verify the suite passes
  on win32 (the dev environment here) as well as POSIX CI.
