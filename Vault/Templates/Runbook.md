<%*
if (!tp.user || typeof tp.user.newNote !== "function") {
  throw new Error("Templater user scripts not loaded — reload Templater "
    + "(see '00 Governance/Templater Scripts/README').");
}
// Runbook = a Reference with Subtype Runbook, filed under Reference/Runbooks.
const n = await tp.user.newNote(tp, "Reference",
  { titlePrompt: "Runbook title", folder: "Human/06 Reference/Runbooks", recommended: [] });
%>---
Type: Reference
Status: <% n.status %>
CreatedAt: <% n.created %>
LastUpdated: <% n.created %>
tags:
aliases:
Subtype: Runbook
<% n.extraProps %>---
# <% n.title %>

## Purpose

## Prerequisites

-

## Steps

1.

## Verification

## Rollback
<%*
if (n.folder) { await tp.file.move(`${n.folder}/${n.title}`); }
else { await tp.file.rename(n.title); }
%>
