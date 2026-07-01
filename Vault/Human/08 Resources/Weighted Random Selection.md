---
Type: Resource
Status:
CreatedAt: 2026-06-27T16:00:53Z
LastUpdated: 2026-07-01T01:16:22Z
tags:
aliases:
SeeAlso:
URL: https://github.com/cdanek/KaimiraWeightedList/tree/main
---
# Weighted Random Selection

## Description

- Generic with pairs of  ```(float, <T>)```
- Methods to select a random T, which will select one randomly according to the provided weights

## Use Cases

## Strengths

## Weaknesses

## Notes

"Rolling":

1. Generate random number in range [0, sum(weights)]
2. Loop through pairs, checking to see if the current value plus the previously iterated sum is greater than the random number
	1. If so, value is returned as chosen
	2. If not, loop continues
	3. Guaranteed to map to a value in the set

## Related

- [[ ]]
