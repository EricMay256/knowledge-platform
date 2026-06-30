# Knowledge Vault — Stage A Handoff

A handoff for continuing this project in Claude Code. Read this first. It captures
**what's built, the decisions behind it, and what NOT to undo** — then lays out the
ordered roadmap: test → wrap as a skill → deploy/use Stage A → eventually upgrade to B2.

---

## 1. What this is

An **agent-contributed knowledge vault**: multiple AI agents both *read from* and
*write to* a shared store of markdown notes, with **deduplication on write** so the
vault doesn't accrete near-duplicates. The contribution path enforces validation and
dedup *before* a note lands.

The project is being built in **two deliberate stages**:

- **Stage A (this handoff):** git + markdown, crude (string/title) dedup. Cheap, no
  hosting, no service to operate. Purpose: prove the vault is worth maintaining before
  paying for the heavier architecture.
- **Stage B2 (eventual):** Postgres + `pgvector` semantic dedup, a single MCP server as
  the enforced write gate, parallel agents writing concurrently with transactional
  safety. We pay for this **only after Stage A demonstrates value.**

The architecture was chosen so the jump from A to B2 is a **localized, mechanical swap**
— not a rewrite. Preserving that property is the single most important thing when
working in this codebase. See §3.

---

## 2. Current state

`vault_contrib/` (in the accompanying zip) is **complete, runnable, and tested through
every code path** (insert / exact-duplicate / fuzzy near-match / unrelated / invalid
input). It is **not yet** packaged as a skill, not deployed, and has **no automated test
suite** — those are Phase 1 and Phase 2 below.

Package contents:

| File | Role | Survives B2? |
|---|---|---|
| `ports.py` | The two Protocols (`Deduper`, `Store`) — the entire B2 migration surface | **Unchanged** |
| `models.py` | Domain types: `Note`, `ScoredCandidate`, `Action` union, `Policy`, result | **Unchanged** |
| `core.py` | Pure logic: `validate()` + `decide()` (the policy ladder) | **Unchanged** |
| `service.py` | `ContributionService` — orchestrates validate→dedup→decide→execute | **~Unchanged** (adds a transaction) |
| `dedup_string.py` | Stage-A deduper: normalized string/title match | **Replaced** by `dedup_pgvector.py` |
| `store_git.py` | Stage-A store: markdown files in a git repo, auto-committed | **Replaced** by `store_postgres.py` |
| `cli.py` | CLI **and composition root** — the one place concrete classes are wired | **2-line edit** |
| `__init__.py` | Public surface | Unchanged |
| `requirements.txt` | One dependency: `pyyaml` | — |

**Verified behaviour (from manual runs):**
- A clean note → `inserted`, written to `notes/<id>.md`, git-committed.
- An exact-title duplicate (case/whitespace/punctuation-insensitive) → `flagged`,
  written to `review/<id>.md` with the matched candidate(s) and reason recorded.
- `--fuzzy 0.6` surfaced a 0.82 near-match but it was still **inserted**, because 0.82
  is below the `flag_at` threshold (0.85). This is correct: the deduper's *surfacing*
  threshold and the policy's *action* threshold are independent. Don't "fix" this.
- Empty body → `invalid` (validation rejects before any write).
- Each contribution is its own git commit with a structured message — **git history is
  the audit log.**

**Quick start to confirm the handoff in a fresh checkout:**

```bash
python -m venv .venv
# bash/zsh:        source .venv/bin/activate
# PowerShell:      .\.venv\Scripts\Activate.ps1
pip install -r vault_contrib/requirements.txt

python -m vault_contrib.cli contribute --vault ./myvault --by agent-1 \
  --title "Two-phase tick updates" \
  --body "Read into a buffer, then commit, so iteration order doesn't bias spread." \
  --tags simulation,determinism

python -m vault_contrib.cli contribute --vault ./myvault --by agent-2 \
  --title "two-phase TICK updates!!" --body "Same idea, different words."   # -> flagged

python -m vault_contrib.cli list --vault ./myvault
```

---

## 3. Architecture & the load-bearing rule

**The package is split along a ports-vs-throwaway line, and that split IS the B2
migration plan.** The filenames encode it: `dedup_string.py` / `store_git.py` are the
Stage-A mechanisms; in B2 you add `dedup_pgvector.py` / `store_postgres.py` as siblings
that satisfy the **same Protocols** in `ports.py`.

```
              ┌───────────────── ports.py (Deduper, Store) ─────────────────┐
              │            the stable contract — DOES NOT CHANGE             │
              └──────▲───────────────────────────────────────────▲──────────┘
                     │ implements                       implements │
   Stage A:  dedup_string.py / store_git.py      B2:  dedup_pgvector.py / store_postgres.py
                     │                                            │
   models.py · core.py · service.py  ── depend only on the Protocols, never the impls ──
                     │
   cli.py (composition root) ── the ONE place that names concrete classes ──
```

> **DO NOT break the seams.** `core.py` and `service.py` must never import a concrete
> store or deduper, reference files/paths/SQL, or branch on "is this string-match or
> vector." If a change tempts you to do that, it belongs in a `Deduper`/`Store`
> implementation or the composition root instead. This abstraction is intentional, not
> incidental over-engineering — it is what makes B2 a swap instead of a rewrite.

**Idiomatic choices to keep:** `typing.Protocol` for the swappable backends and
`match` for `Action` dispatch (both idiomatic modern Python ≥3.10). The one pragmatic
Stage-A shortcut is `StringMatchDeduper` scanning the whole corpus via
`store.iter_notes()` — fine at A-stage scale, and it is exactly what the pgvector
deduper will *not* do (it runs an indexed ANN query). Don't generalize that scan into a
pattern.

---

## 4. Decision history (so future calls are informed)

Compressed rationale, so nobody re-litigates settled choices:

- **Skill vs MCP, originally:** for a clonable markdown repo, a skill + native file
  tools is the right default — the agent already has the "limbs" (grep/read/write); it
  only lacks the "map." MCP earns its place when you need write governance, multi-client
  access, liveness, or scale beyond grep.
- **Why B2 entered the picture:** agents *contribute*, not just retrieve. Write-back is
  the strongest single pull toward a serializing gate.
- **Why parallel forces a real server, not just "MCP":** the dangerous operation is
  *check-dedup-then-write* on shared index state. Git serializes **file** ops, not
  **logical** ones — two agents can both pass a dedup check and both insert distinct
  near-duplicates, and git merges them cleanly while the vault silently degrades. B2's
  value is making that critical section atomic.
- **Why semantic dedup picked the storage model:** real dedup is "notes *about* X," not
  "notes *containing* X" — a vector query. That requires a transactional vector index
  (`pgvector`), which is what lands B2 on Postgres-as-source-of-truth.
- **Why stage through A instead of building B2 now:** B2's cost was never the database
  (that's ~free — see §Phase 4). It's the *server*: the transactional gate, auth,
  embedding integration, and ops. Staging buys an **option** — defer that build/ops cost
  until the vault proves it's worth maintaining. The dedup/validation/schema logic ports,
  so the only throwaway is storage + the dedup mechanism, both isolated behind Protocols.
- **Escape hatch:** the load-bearing requirement is *semantic dedup*. If it ever turns
  out crude dedup is good enough in practice, the whole B2 stack becomes unnecessary and
  Stage A is the finished product.

**Flip conditions — revisit the A→B2 decision when any becomes real:** duplicate
accretion is hurting the vault despite crude dedup; multiple agents are genuinely writing
*concurrently* often enough that git collisions bite; or you need invariants *enforced*
rather than *instructed*.

---

## 5. Roadmap

### Phase 1 — Testing & validation (imminent, do first)

The engine runs but has no automated tests. Build a `pytest` suite. Priority cases:

- **`decide()` bands** (`core.py`): feed a stub deduper fixed scores and assert the
  Action for each band — no-similars→Insert; ≥`flag_at`→Flag; below→Insert; and (with a
  policy that sets them) `reject_at`/`merge_at`/`link_at` boundaries. These bands are
  dormant in A but must be correct for B2 — test them now.
- **`Policy.__post_init__`** rejects out-of-order or out-of-[0,1] bands.
- **`validate()`**: empty title/body, missing `contributed_by`, blank/duplicate tags.
- **`_normalize()`** (`dedup_string.py`): case, whitespace collapse, punctuation
  stripping all map titles together; verify the exact-match and `--fuzzy` paths.
- **`GitMarkdownStore` round-trip**: insert→get→iter equality; `add_to_review` frontmatter
  shape; commit messages; **a body containing a `---` horizontal rule must survive a
  write→read round-trip** (the frontmatter split is `maxsplit=2`, so it should — lock it
  in with a test).
- **Outcome contract**: `ContributionResult.status` and CLI exit codes
  (`0` for inserted/linked, non-zero otherwise) — agents will branch on these.

**Known gap to decide on here:** every `contribute()` mints a fresh `uuid4` id, so a
*retried* contribution becomes a new note that then gets flagged as a duplicate of the
first. If agents may retry, add an **optional client-supplied idempotency key** (mirrors
the `client_run_id` pattern from HSS) so a retry is a no-op rather than a flag. Decide
whether A needs this or whether it can wait for B2.

### Phase 2 — Skill wrapper (`SKILL.md`)

Wrap the engine as a Claude Code skill so agents invoke it idiomatically. The skill is
thin; the engine already does the work. It should teach:

- **The note schema** (`Note` fields: title, body, tags, source, contributed_by) and
  what good tags/titles look like for *this* vault.
- **The contribution procedure**: call the CLI (or import `ContributionService`), and how
  to interpret each `status` — especially that `flagged` means "a human/agent must
  adjudicate later in `review/`," not "failed."
- **The read path**: how agents should *retrieve* before contributing (in A this is
  grep/read over `notes/`; note that B2 will replace this with a query tool).
- **Conventions**: don't hand-edit `review/`; let git history stand as the audit log.

Do **not** change the note schema after the skill documents it without updating both —
schema changes are free now and annoying after the skill encodes them. Shake out schema
tweaks during Phase 1.

### Phase 3 — Deploy & use Stage A

Stage A needs no server. "Deployment" is just: pick where the vault repo lives and let
agents contribute.

- **Vault location**: a git repo (local, or a private GitHub remote the agents push to).
  Git remote = your sync + backup + audit story for free.
- **Concurrency posture (deferred, by design)**: A does **not** serialize writes. At
  small scale, git's optimistic merge absorbs the occasional concurrent contribution;
  rare logical duplicates are caught later by the crude dedup or manual review. This is
  the work B2 buys back — acceptable to live without while proving value.
- **Operating it**: agents run `vault_contrib.cli contribute …`; periodically review the
  `review/` queue and adjudicate (keep / merge by hand / delete). This manual curation
  loop is intentional for A — it's how you *learn the real dedup policy* before
  automating it in B2.
- **Signal to collect for the A→B2 decision**: how often `review/` fills, how many true
  duplicates crude dedup misses, and whether concurrent writes ever actually collide.
  Those numbers decide whether/when B2 is justified.

### Phase 4 — Upgrade to B2 (eventual)

**Trigger:** a flip condition in §4 becomes real, and the collected signal says the vault
is worth the operational commitment.

**The migration is mechanical:**
1. Implement `store_postgres.py` (`PostgresStore`) — each `Store` method becomes SQL.
2. Implement `dedup_pgvector.py` (`PgVectorDeduper`) — embed the candidate, ANN-query a
   `vector(N)` column.
3. In `service.py`, wrap the `find_similar → decide → execute` span in one DB
   transaction, and **hoist embedding to run before the transaction opens** (never hold a
   transaction across the embedding API call — see the migration note in `ports.py`).
4. Change the two wiring lines in `cli.py` (composition root) to construct the Postgres
   implementations.
5. `models.py`, `core.py`, the Protocols, and the policy bands are untouched. Set
   `merge_at` / `link_at` in the `Policy` to light up the dormant bands.
6. Implement the one deferred path: `Merge` in `service.py` (currently
   `NotImplementedError`) — needs a real merge strategy that won't corrupt good notes.

**Hosting decision (already researched — re-verify before committing):**
- `pgvector` is confirmed available on **Heroku Postgres Essential tier** (≈$5/mo,
  pgvector 0.8.0, HNSW + IVFFlat). **Verify it's enabled on the specific HSS Postgres
  plan** before relying on it.
- **Cheapest path (~$0 marginal):** reuse HSS's existing Heroku Postgres (`CREATE
  EXTENSION vector;` + a `notes` table) and fold the MCP server into HSS's existing
  FastAPI app as routes (remote MCP over HTTP) on the always-on dyno. Tradeoff: couples
  the vault to HSS's DB lifecycle/connection pool/blast radius — reversible later via
  `pg:copy` to a separate add-on.
- **Isolated alternative:** separate Heroku Essential-0 Postgres (~$5) + Basic dyno
  (~$7) ≈ $12/mo.
- **Supabase:** Free tier is **not viable** for an agent endpoint (pauses after 7 days
  idle, 20–30s cold wake). The real Supabase price is **Pro, ~$25/mo**, and it still
  doesn't host the MCP server process — you'd host that separately anyway. Heroku-reuse
  dominates on cost for starts-small.

**New design work B2 introduces (not yet specced):** an **auth story** (which agents may
contribute — there was none in A because there was no network surface); the
**transaction/serialization boundary**; the **similarity→action threshold table** tuned
against *real* embedding scores (the §Phase 3 review-queue data is exactly what calibrates
this); and the `Merge` strategy.

---

## 6. Conventions & constraints

- **Python ≥ 3.10** (uses `match` and `X | None`).
- **One dependency:** `pyyaml`.
- **Idioms to preserve:** `Protocol`-based backends; `match` dispatch; pure `core.py`.
- **Deferred on purpose (don't "add" these to A without a reason):** write serialization,
  semantic dedup, auth, the `Merge` path.
- **Don't auto-merge.** Any collision in A goes to `review/` for human/agent adjudication;
  silent merges corrupt notes. Merge waits for B2 + semantic similarity.
- **Humans are first-class contributors.** Both humans and agents contribute via the same
  `contribute()`/CLI path (`--by human:<name>` / `agent:<id>`), getting the same validation +
  dedup. New notes always go through that path — **don't hand-create files in `notes/`**
  (no frontmatter/id, bypasses dedup). Hand-*editing* an existing note body is fine; commit
  it. See specs/stage-3-deploy.md §4a.
- **Don't put vault *data* in a B2 repo.** In B2 the DB is a running service; the repo
  holds server code + schema/migrations, never the data.

---

## 7. Suggested: distill the rules into `CLAUDE.md`

Claude Code auto-loads a `CLAUDE.md` from the project root into context every session.
Consider copying §3's "DO NOT break the seams" rule, §6's conventions, and the note-schema
(once Phase 1 settles it) into a `CLAUDE.md` so those guardrails persist across sessions
without re-reading this whole handoff each time. Keep this file as the full narrative;
let `CLAUDE.md` be the short, always-loaded rules.
