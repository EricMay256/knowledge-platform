<%*
if (!tp.user || typeof tp.user.newNote !== "function") {
  throw new Error("Templater user scripts not loaded — reload Templater "
    + "(see '00 Governance/Templater Scripts/README').");
}
const n = await tp.user.newNote(tp, "Decision");
%>---
Type: Decision
Status: <% n.status %>
CreatedAt: <% n.created %>
LastUpdated: <% n.created %>
tags:
aliases:
<% n.extraProps %>---
# Decision: <% n.title %>

## Context

What prompted this decision?

## Decision

What was chosen?

## Rationale

Why this option?

## Consequences

What does this enable, constrain, or require next?
<%*
if (n.folder) { await tp.file.move(`${n.folder}/${n.title}`); }
else { await tp.file.rename(n.title); }
%>
