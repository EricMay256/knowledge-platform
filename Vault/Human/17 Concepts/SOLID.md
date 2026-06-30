---
CreatedAt: 2026-06-27T15:42:11Z
LastUpdated: 2026-06-29T22:06:50Z
Type: Reference
Status:
Tags:
Aliases:
Related:
Category: Coding Concept
---
# SOLID

S - Single-responsibility Principle (separation of concerns)

- "Each function is responsible for one thing"
- Barrier between entities needs to be properly identified logically - use words to determine what the objects are. "a `game` is played, producing a verifiable `run` with a corresponding `score` that is then submitted to the high score table."

O - Open-closed Principle (open for extension, closed for changing)

- The operation can be modified substantially without needing to change source code
- Strongly discourage changes to source code you don't own - better to override a class, or provide a static helper method, etc etc
- Example of failing criteria: Switch statement for types - new type couldn't be added without changing source code (not just extending the code)

L - Liskov Substitution Principle (Should be usable in stead of base)

- If you have FlyingMonster inheriting from Monster, you should be able to use a FlyingMonster as a Monster. Pairs well with overrides.

I - Interface Segregation Principle (Objects shouldn’t have irrelevant interfaces/methods/etc)

- Ties heavily back to 'S', ensure you provide a focused set of operations clearly with no noise to confuse users
- When followed, keeps project organization clear (no need to remember obscure connections, like the game manager having a public stateless math function)

D - Dependency Inversion Principle (Depend upon interfaces, not specific implementations)

- Use generic interfaces so that providers may be swapped out
- Interface can be a thin wrapper
- Interfaces provide specs for substitutes - they are the contract and the connection

## Quick Reference

## Common Commands
