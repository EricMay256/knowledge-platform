<%*
if (!tp.user || typeof tp.user.newNote !== "function") {
  throw new Error("Templater user scripts not loaded — reload Templater "
    + "(see '00 Governance/Templater Scripts/README').");
}
const n = await tp.user.newNote(tp, "Concept");
%>---
Type: Concept
Status: <% n.status %>
CreatedAt: <% n.created %>
LastUpdated: <% n.created %>
tags:
aliases:
<% n.extraProps %>---
# <% n.title %>

> One crisp sentence stating the idea.

## Explanation

## Why it matters

## Nuances / boundaries

## Connections

- [[ ]]

## Sources

-
<%*
if (n.folder) { await tp.file.move(`${n.folder}/${n.title}`); }
else { await tp.file.rename(n.title); }
%>
