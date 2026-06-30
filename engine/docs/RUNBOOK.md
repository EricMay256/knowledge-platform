# Operating runbook — Stage A vault

How to run and curate the knowledge vault day to day. This is the "use" half of Stage 3
(deploy is just: pick where the vault lives — see [specs/stage-3-deploy.md](../specs/stage-3-deploy.md) §3).
Stage A is intentionally manual: the curation loop below is how you *learn the real dedup
policy* before B2 automates it.

## 0. One-time setup

- Install the engine so it runs from any project: `pip install -e .` from this repo
  (`pip install --user -e .` to match a no-venv setup).
- Deploy the skill to user level: `python scripts/sync_skill.py`.
- (Optional) set `KNOWLEDGE_VAULT` to relocate the vault; otherwise it defaults to
  `~/knowledge-vault`, created on first contribution.
- (Optional) add a private git remote to the vault for sync/backup/audit (see §4).

## 1. Contributing (agents and humans, same path)

Retrieve first, then contribute:

1. Search the vault before writing — grep `~/knowledge-vault/notes/` for the topic, or browse
   by tag: `python -m vault_contrib.cli list --tag <tag>` (repeat `--tag` for AND), and
   `… index` to (re)generate a tag-grouped `INDEX.md`. Storage is flat; **tags are the
   organizing axis**. If it's already captured, don't re-add (you'll just get `flagged`).
2. Contribute via CLI (no `--vault` needed — it resolves the central vault):

   ```bash
   python -m vault_contrib.cli contribute \
     --by agent:<id|human:name> --title "…" --body "…" [--tags a,b] [--run-id <key>]
   ```

3. Branch on the result `status` (exit `0` = inserted/linked, non-zero otherwise):
   `inserted`/`linked` → done; `flagged` → a possible dup is queued in `review/` (not a
   failure, don't retry); `invalid` → fix per `errors`; `rejected` → drop/revise.

Non-console browsing: open the vault in **Obsidian** — tags, titles, click to read, no code.
See [browsing-obsidian.md](browsing-obsidian.md).

Clients: local **Codex / Claude Code** are the primary contributors (real FS, live dedup).
Chat/sandbox clients: reads work off a snapshot; for writes use the draft-then-commit bridge
(draft in chat, run `contribute` locally) — see spec §4b.

## 2. Curating `review/` (the core human loop)

`review/` holds notes the dedup flagged as possible duplicates, awaiting a decision. Periodically
(e.g. weekly, or when it grows): for each flagged note, read it and its `flag_similars`, then:

- **Keep** — it's genuinely distinct: move the file from `review/` to `notes/` (drop the
  `flag_*` frontmatter), and commit.
- **Merge by hand** — fold useful content into the existing note's body, edit that note in
  `notes/`, delete the review file, and commit. (No auto-merge in Stage A — silent merges
  corrupt notes.)
- **Delete** — it's a true duplicate that adds nothing: remove the review file and commit.

Guardrails: don't hand-*create* notes in `notes/` (always go through `contribute`); don't
rewrite git history; editing an existing note's body by hand is fine.

## 3. Signals to record (this is the point of the phase)

The git log already timestamps and attributes every contribution and flag — mine it rather
than building telemetry. Track, even roughly:

- **`review/` fill rate** — how often it fills and the adjudication effort.
- **Crude-dedup miss rate** — true dups string-match missed (found by hand). Strongest
  argument for semantic dedup. (Note the known limitation: hyphen-vs-space titles don't match
  — see [specs/stage-1-testing.md](../specs/stage-1-testing.md) §6a.)
- **Concurrent-collision rate** — whether concurrent writes ever actually collide.
- **Human vs agent authorship mix** — `human:` vs `agent:` share of notes and flags.
These are the in-product signals that say when a free user has hit the wall → the A→B2 / paid
trigger. Revisit B2 when a HANDOFF §4 flip condition becomes real *and* the signal justifies
the operational commitment.

## 4. Sync / backup (optional but recommended)

The vault is its own git repo. Add a private remote for free sync + offsite audit:

```bash
git -C ~/knowledge-vault remote add origin <private-repo-url>
git -C ~/knowledge-vault push -u origin <branch>
```

Then push periodically (or via a cron/job). Remote contributors (incl. networked sandboxes)
are possible but carry the auth/consistency caveats in spec §4b.

## 5. Keeping the skill in sync

The repo skill is the source of truth. After editing it:

```bash
python scripts/sync_skill.py            # update deployed copies
python scripts/sync_skill.py --check    # CI/pre-commit: exit 1 on drift
python scripts/sync_skill.py --emit-portable   # text for Codex AGENTS.md / a ChatGPT Custom GPT
```
