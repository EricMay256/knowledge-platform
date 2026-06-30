---
CreatedAt: 2026-06-27T19:43:06Z
LastUpdated: 2026-06-29T22:06:52Z
---
# Hex Board Details

Hex boards have a challenge when using x/y coordinates - essentially, they alternate, with every row being staggered half an entry from its neighbors along the Y axis. Rather than list adjacency with specific values in inconsistent coordinate scenarios, specific standard values represent relative positions consistently within a hex grid by varying the x offset dependent on whether the y value is even or odd. There are other methods to do this that may work better, but I determined this independently.

-4200000XX (69, 70, 71), used to represent x value that is dependent upon current y value.

69 = even -1 odd +1

70 = even +1 odd +2

71 = even -2 odd +1

-Non-background slots are selected using the same criteria (equivalent copies are provided as rectangle/hex tiles appropriately)
