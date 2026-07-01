---
CreatedAt: 2026-06-24T07:37:45Z
LastUpdated: 2026-07-01T03:06:29Z
Type: Idea
Status:
tags:
aliases:
---
# Claude as Overseer

I didn’t think this was possible.

r/ClaudeCode - I didn’t think this was possible.

Basically, I gave Claude access to the MiniMax and Kimi API subscriptions and told it to use them as executors while Claude itself acted as the manager/coordinator. It massively increased Claude’s capabilities.

UPD:

I built a small setup for running multiple AI coding agents in parallel against Linear tasks.

The idea is simple:

- Claude acts as the manager.

- MiniMax and Kimi act as worker agents.

- Linear is the task pool.

- tmux is the control room.

Claude plans the work → creates clear Linear tasks → assigns work between MiniMax and Kimi → launches the grid → agents solve tasks → Claude reviews results → cycle repeats.

How it works

dwh-launch-grid.sh

├─ cleans old locks and logs

├─ checks how many Linear tasks are ready

├─ opens a tmux grid with N panes

└─ starts one autonomous agent per pane

Each pane runs dwh-auto-agent.sh.

The agent loop:

pick task from Linear

→ create lock

→ move task to In Progress

→ collect context

→ run AI coding agent

→ test / commit

→ parse result

→ update Linear

→ release lock

→ take next task

The workflow

I don’t manually manage every agent. I just tell Claude to:

- Generate the tasks

- Create / update the task pool in Linear

- Assign tasks between MiniMax and Kimi

- Run dwh-launch-grid

- Wait until the grid finishes

- Do a quick screening of the results

- Check that nothing obvious broke

- Continue the cycle

Claude is basically the orchestrator/reviewer.

MiniMax handles lighter tasks well: small fixes, cleanup, simple scripts, documentation, minor refactors.

Kimi is closer to a Sonnet Medium-level worker for heavier coding tasks: deeper refactors, more context-heavy changes, debugging, and implementation work.

The key part is not just the models. It is the quality of task specification.

Claude writes very clear task briefs: goal, context, constraints, files to check, expected output, DoD, and what not to touch. Because of that, even smaller agents become much more effective. They don’t need to guess the architecture or invent the plan — they just execute a precise task.

Why locks are needed

The main issue with parallel agents is duplicate work.

Without locking, two agents can grab the same task.

So each task gets a lock file:

.agent-locks/DWH-168.lock

If another agent sees the lock, it skips that task and takes another one.

If an agent crashes, old locks expire after 1 hour and the task is moved back from In Progress to Todo.

What I like about this approach

It is not a complex orchestrator. It is mostly shell scripts, tmux, Linear statuses, lock files, logs, and clear conventions.

Each layer has a simple role:

Claude = manager / reviewer

Linear = source of truth

tmux = live control room

MiniMax = lightweight worker

Kimi = stronger coding worker

locks = duplicate protection

logs = audit trail

status updates = progress tracking

The result feels like a lightweight multi-agent coding grid rather than a big framework.

I also ask the agents to create Obsidian Vault Docs in the filesystem, so they have a clear reference point and better understanding of what to do.

UPD 2:

If I keep it short: the company I work for originally wanted to build analytics for all of their websites, but later refused to hire additional people for the team. Honestly, that situation burned me out a bit and made me start thinking about leaving eventually.

The problem is scale. They have an absurd number of products and websites — around 100 sites, no joke. As the workload kept growing, I gradually started using AI agents to speed up my work.

Over time I realized I didn’t just want “AI assistance.” I wanted a system where I could start a workflow in the morning, let multiple agents work in parallel for hours, and focus myself on higher-level problems where agents are still weak.

After a lot of experimentation, I finally found a setup that fits me perfectly. It can run for hours during the day, continuously processing tasks while I handle architecture, reviews, communication, and other things that still require human judgment.

**
