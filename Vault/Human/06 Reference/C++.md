---
Type:
Status:
CreatedAt: 2026-06-24T16:16:54Z
LastUpdated: 2026-06-29T22:06:52Z
Tags:
  - language
Aliases:
Related:
  - "[[Unreal]]"
  - "[[Python]]"
  - "[[Unity]]"
  - "[[C-Sharp]]"
Category:
---
# C++

## Dependencies

- Varied

## Used In

- [[Unreal]]
- [[Python]]
- [[Unity]] [[C-Sharp]] (Intermediate compilation)

## Quick Reference

## Notes

Virtual Destructors are required to delete Base b = Derived(), but that should only be done on classes expecting to be used in polymorphic ways because it invokes [[Rule of 3, 5, zero; RAII]] and disallows simple copying, while also adding a vptr
