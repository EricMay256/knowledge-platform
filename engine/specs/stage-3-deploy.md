# Stage 3 spec — Deploy & use Stage A

**Source:** HANDOFF.md §5 Phase 3. **Status:** not started. **Depends on:** Stage 1
(tested engine) and Stage 2 (skill) in practice, though the vault location can be chosen
earlier. **Leads to:** the A→B2 decision (Phase 4), which this stage exists to *inform*.

---

## 1. Goal

Put Stage A into real use with **no server**. "Deployment" here is just: choose where the
vault repo lives, let agents contribute through the skill/CLI, run the manual curation loop,
and — most importantly — **collect the signal that decides whether B2 is ever justified**.
Stage A is not a throwaway prototype; per HANDOFF §4's escape hatch, if crude dedup proves
good enough, Stage A *is* the finished product.

## 2. Scope

In scope: picking the vault's git home (local vs private remote), defining the
concurrency posture (explicitly *not* serialized), the operating/curation loop, and the
measurement plan for the A→B2 flip conditions. Optional: the suggested `CLAUDE.md` distilled
from HANDOFF (§7).

Out of scope (deferred **by design** — HANDOFF §6, do not add without a flip condition):
write serialization, semantic dedup, auth, the `Merge` path, any hosted service or DB.

## 3. Deliverables

1. **Vault location decision + setup.** A git repo holding `notes/` and `review/`:
   - **Default central location: `~/knowledge-vault`.** The CLI resolves the vault when
     `--vault` is omitted: `$KNOWLEDGE_VAULT`, else `~/knowledge-vault` (with `~`/env
     expansion). One vault serves every project; set `KNOWLEDGE_VAULT` to relocate it.
     This makes "one vault, all projects" the zero-config default and is the main reason the
     engine is now `pip install -e .`-installable (runs from any directory).
   - Local-only is the simplest start. A **private GitHub remote** is recommended — it
     gives sync, backup, and an offsite audit log for free (HANDOFF §5 Phase 3). Agents
     (or a periodic job) `push`.
   - Decide whether vault data lives in *this* repo or a separate one. (Note for later:
     HANDOFF §6 says B2's repo holds **code + schema only, never data** — so keeping vault
     *data* in its own repo now avoids entangling it with the engine repo at B2.)
     Recommendation: a **separate private repo for vault data**.
   - **Don't let the vault nest inside a consuming repo untracked.** `GitMarkdownStore`
     runs `git init` in the vault root, so the vault is *its own* git repo. If it sits inside
     another project's tree, the outer repo will try to record it as an embedded-repo gitlink
     (`git add -A` → "embedded git repository" warning). The engine can't fix this for you —
     a library can't safely edit a consumer's `.gitignore`. So, in order of preference:
     1. **Keep the vault outside the consuming tree** (sibling dir or `~/…`, via the
        `KNOWLEDGE_VAULT` env var). Nothing to ignore.
     2. **If nested, gitignore its path** in that project (this repo already ignores the
        skill default `/vault/`).
     3. **To ignore it across all your repos automatically**, add the conventional vault dir
        name to your global excludes file:
        `git config --global core.excludesFile ~/.gitignore_global` then add `vault/` (or
        your chosen name) to that file — the closest thing to "ignored wherever it's used."
2. **Operating runbook** (short doc): how an agent contributes (via the Stage-2 skill), how
   often and by whom the `review/` queue is adjudicated, and the keep/merge-by-hand/delete
   decision procedure. Manual curation is intentional here — it's how the *real* dedup
   policy is learned before B2 automates it.
3. **Signal-collection plan** (§5) — the numbers that drive Phase 4.
4. Optional but recommended: a root **`CLAUDE.md`** distilling HANDOFF §3 ("DO NOT break the
   seams"), §6 conventions, and the frozen note schema, so guardrails persist per session
   without re-reading the whole handoff.

## 4. Concurrency posture (state it explicitly)
Stage A does **not** serialize writes, and that is a deliberate, documented trade-off
(HANDOFF §5 Phase 3 / §4):
- At small scale, git's optimistic merge absorbs the occasional concurrent contribution.
- The real hazard is *logical*, not textual: two agents can both pass the dedup check and
  both insert distinct near-duplicates; git merges the two files cleanly while the vault
  quietly degrades. Crude dedup or manual review catches these *after the fact*.
- This is precisely the work **B2 buys back** (an atomic check-dedup-then-write critical
  section). Living without it in A is acceptable *while proving value* — so the runbook
  should treat post-hoc duplicate cleanup as expected, not as a defect.

## 4a. Human input (first-class contributors + curators)
The vault is **explicitly mixed-contributor**: humans and agents both write to it. Two
distinct human entry points, with a clear policy on each:

1. **Contributing new notes — through the CLI**, exactly like an agent:
   `python -m vault_contrib.cli contribute --vault <path> --by human:<name> …`. This is the
   supported path for human-authored notes because it runs the same validation + dedup +
   commit. **Do not hand-create note files in `notes/`** — a hand-written markdown file
   lacks the `id`/frontmatter the store expects (`iter_notes`/`_deserialize` require valid
   frontmatter) and bypasses dedup, so it silently breaks reads or seeds duplicates.
2. **Curating existing content — by hand is allowed and expected:**
   - Editing an existing note's *body* in `notes/<id>.md` for correction/improvement is fine
     (dedup governs *adding*, not editing). Keep the frontmatter intact and commit the change
     so git history stays the audit log.
   - Adjudicating the `review/` queue (keep / merge-by-hand / delete) is *already* a human
     job (§3) — that is the primary human curation loop.

Provenance: tag human contributions `human:<name>` and agent contributions `agent:<id>` (the
convention from `Note.contributed_by`). This keeps the contribution mix measurable — e.g.
"how much of the vault is human- vs agent-authored," and it pre-stages B2's auth story, which
must cover *both* humans and agents (not just "which agents may contribute").

> Note: a richer human UI (web form, editor integration) is intentionally **out of scope for
> Stage A** — markdown + CLI + direct git curation is the whole interface. Revisit only if the
> CLI proves too coarse for human contributors in practice.

## 4b. Remote & sandbox contributors (incl. chat clients)
The natural client for Stage A is a **local coding client** (Codex CLI, Claude Code) operating
on the central `~/knowledge-vault` on disk — real filesystem, live dedup, commit, done. But a
contributor can also reach the vault **over a git remote**: a clone that pushes back is a
legitimate Stage-A contributor — the private remote (§3) *is* that sync path. The engine runs
anywhere Python does, so a sandboxed agent (e.g. a chat client that can clone into its
sandbox) can run `contribute` too. What gates it is not the engine but three properties of
that sandbox:

1. **Outbound network** — to clone and, crucially, `git push` back. Some chat sandboxes are
   network-isolated by default (e.g. ChatGPT's code-interpreter), so they can't clone/push;
   you'd upload a snapshot instead. Newer agent/computer modes may have network. Varies by
   client and mode — verify.
2. **Push credentials** — writing back means giving an ephemeral sandbox a token with write
   access to the vault repo. Stage A has **no per-agent auth** (all-or-nothing repo access),
   so that is a real security decision, not a free default.
3. **Durability** — sandboxes are per-session ephemeral: an unpushed contribution dies with
   the session, and a clone is a point-in-time snapshot that goes stale.

**Consistency caveat:** a sandbox dedups against *its snapshot*, so two sessions can both miss
each other's in-flight notes and create logical duplicates — the documented Stage-A tolerance,
just exercised harder because every clone is a fork.

**Practical patterns:**
- **Reads** work in a chat client even with no network — upload a snapshot (or use the GitHub
  web view) and the agent greps it. Treat it as a stale read cache; the retrieve-before-write
  half of the skill is fully available.
- **Writes from a network-isolated chat client → draft-then-commit bridge:** have the chat
  agent *draft* the note, then run the real `contribute` in your local Codex/Claude Code. Zero
  infra, human-in-the-loop, and it dedups against the *live* vault rather than a snapshot.
- **Writes from a networked sandbox + scoped deploy token** work as a git remote contributor —
  fine at low volume, but you are hand-rolling the auth + write-gate that B2 productizes, and
  you still carry the fork-consistency risk above.
- The clean "any networked client contributes directly" story is **B2's remote endpoint** —
  another concrete pull toward the paid tier (the freemium A→B2 framing).

## 5. Signal to collect (this is the point of Stage 3)
Instrument the curation loop to answer the Phase-4 flip conditions (HANDOFF §4):
- **`review/` fill rate** — how often it fills and how much adjudication effort it costs.
- **Crude-dedup miss rate** — how many *true* duplicates string/title match fails to catch
  (found later by hand). This is the single strongest argument for semantic dedup.
- **Concurrent-collision rate** — whether concurrent writes ever *actually* collide in
  practice, or whether it stays theoretical at your scale.
- **Human vs agent authorship mix** — share of notes (and of `review/` flags) by
  `human:` vs `agent:` provenance. Tells you who the vault is really for and informs B2's
  auth scope.
Capture these as a lightweight running tally (the git log already timestamps and attributes
every contribution and flag — mine it rather than building telemetry). These three numbers,
not intuition, decide whether/when B2 is worth its build + ops cost.

## 6. Acceptance criteria
- A vault repo exists at the chosen location; agents can contribute end-to-end via the
  Stage-2 skill and the result lands in `notes/` or `review/` as expected.
- The runbook is written and a first adjudication pass on `review/` has been done at least
  once (proving the loop works).
- The three signals in §5 are being recorded in some durable, reviewable form.
- If `CLAUDE.md` is added, it contains the seam rule + conventions + schema and nothing that
  contradicts the engine.

## 7. Exit / next step
Stage 3 has no "completion" — it runs until a **flip condition becomes real** (duplicate
accretion hurts despite crude dedup; concurrent writes genuinely bite; or invariants need
to be *enforced* not *instructed*) **and** the collected signal says the vault is worth the
operational commitment. At that point, open Phase 4 (B2): the migration is the mechanical
swap described in HANDOFF §5 Phase 4 — new `store_postgres.py` / `dedup_pgvector.py`
satisfying the same Protocols, a transaction wrapped around `find_similar→decide→execute` in
`service.py`, and the two-line composition-root edit in `cli.py`. Everything tested in
Stage 1 (`models.py`, `core.py`, the Protocols, the policy bands) carries over untouched —
which is the whole reason the staging was set up this way.
