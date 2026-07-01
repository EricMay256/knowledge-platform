<%*
if (!tp.user || typeof tp.user.newNote !== "function") {
  throw new Error("Templater user scripts not loaded — reload Templater "
    + "(see '00 Governance/Templater Scripts/README').");
}
const n = await tp.user.newNote(tp, "Project");
%>---
Type: Project
Status: <% n.status %>
CreatedAt: <% n.created %>
LastUpdated: <% n.created %>
tags:
aliases:
<% n.extraProps %>---
# <% n.title %>

## Outcome

What “done” looks like, in one or two concrete sentences.

## Why it matters

The problem, opportunity, or personal reason this is worth doing.

## Current state

- What is already complete:
- What is in progress:
- What is blocked / uncertain:

## Next action

**One physical, specific action**

Example: “Write the first-pass outline for the project case study.”

## Milestones

- [ ] Milestone 1 — target date if real
- [ ] Milestone 2
- [ ] Milestone 3

## Scope

Included
-

Not included
-

## Decisions & rationale

| Date       | Decision | Why |
| ---------- | -------- | --- |
| YYYY-MM-DD |          |     |

## Risks / open questions

- 

- 

## Notes & useful context

- Key constraints, assumptions, discoveries, or context future-you will need.
- Add links to relevant notes rather than duplicating their contents.

## Activity log

- YYYY-MM-DD —
<%*
if (n.folder) { await tp.file.move(`${n.folder}/${n.title}`); }
else { await tp.file.rename(n.title); }
%>
