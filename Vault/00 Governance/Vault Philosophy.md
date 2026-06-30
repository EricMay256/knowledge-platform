---
CreatedAt: 2026-06-29T07:00:37Z
LastUpdated: 2026-06-29T22:06:52Z
---
# Vault Philosophy

## Purpose

Contain durable information that human wants to retain, recall, or be able to look up at a later date. The act of maintaining and using this knowledge graph will help reinforce the information and connections.

## Inclusion Criteria

Is this information that will help me in a year during routine usage, or when returning after a break?

Will the information help myself or my agents perform our tasks more effectively?

Is it trivial information, or can it be relearned trivially? Note: Complicated topics may still benefit from a simple self restatement of the concepts even if it can be reasonably learned from other sources.

Distilled information: useful, relevant takeaways from the raw data

# Exclusion Criteria

Is this information that I won't need in a week/month/year?

Is this an event that will pass, leaving this information irrelevant? (Use calendar)

Is this a todo list? (Use Trello)

Examples

Random debugging logs

One-off AI conversations

Prompt experiments

Temporary notes

Generated code

Machine memory

## Editorial Principles

Aim to provide value through context - relations speak volumes.

Prefer links to duplication.

Write for future me with my skills.

High signal to noise - keep writing concise and purposeful.

## AI Policy

This vault is one repository with two knowledge layers and a shared governance layer:

- **`Human/`** — durable, human-curated knowledge. Protected: agents propose, humans approve.
- **`Agent/`** — AI operational memory, contributed through the engine in `/engine` (see
  [[AI Contribution Policy]]). Fewer bottlenecks; this is where agents influence their own
  future behavior.

Human must manually approve any agent-driven changes to the **Human** layer, to audit for value, accuracy, and policy compliance. The Agent layer has fewer bottlenecks, and is more appropriate for agents influencing their own future behaviors.

There are two routes for AI work to reach the Human layer (see [[AI Contribution Policy]] and [[Promotion Policy]]):

- **AI Suggestions** — an agent proposes a specific change to Human knowledge → `Human/01 Inbox/AI/`.
- **Promotion Candidates** — agent-vault memory later judged human-worthy → `Agent/Promotion Candidates/`.

Within the Human layer, agents may:

- Summarize
- Suggest links or metadata/frontmatter (properties)
- Identify duplicates
- Identify staleness
- Create pull requests
- Work on branches prefixed with 'ai/'
- Modify metadata/frontmatter (properties)
Agents may not:
- Delete notes
- Operate on main/master directly
- Create or Modify existing note bodies except in '01 Inbox/AI'

A human's intervention is required for any edits to the body of any note that lies outside of '01 Inbox/AI', or any new notes outside of that directory. (This restriction governs the **Human** layer; the **Agent** layer is agent-writable through the engine.)

## Frontmatter

### Standard Properties

| Name        | Required | Applies To | Notes                      |
| ----------- | -------- | ---------- | -------------------------- |
| Type        | Yes      | All        | Canonical                  |
| Status      | Yes      | Most       | Controlled set of terms    |
| CreatedAt   | Yes      | All        | ISO-8601                   |
| LastUpdated | Yes      | All        | ISO-8601                   |
| Tags        | Optional | All        | Cross-cutting concepts     |
| Aliases     | Optional | All        | Alternative or prior names |

Include List Properties:

- Type:
- Status:
