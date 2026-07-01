---
Type: Concept
Status:
CreatedAt: 2026-06-28T01:41:31Z
LastUpdated: 2026-07-01T01:12:32Z
tags:
aliases:
SeeAlso:
Subtype:
---
# Rule of 3, 5, zero; RAII

## Quick Reference

### Rule of 3

If you have any manually managed memory in your class (ie new, delete) then you must define the copy constructor, assignment operator, and destructor in order to get proper behavior.

### Rule of 5

If you touch the default destructor, the compiler default move constructor and move assignment operations stop working, so they are often included in the rule.

### Rule of 0

If you only use RAII resources in your class, you don't need to touch the compiler default versions of the above.

## Common Commands

```text
