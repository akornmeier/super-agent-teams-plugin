# Scoring rubric for /ideate

This file defines how `planner/product` scores candidate ideas in Stage 2 of
`/ideate`. Weights live here — not in the SKILL prompt — so ranking runs are
reproducible. Changing a weight is a deliberate policy edit.

## Scoring dimensions

Each idea is scored 0–10 on each dimension, then combined via the weighted
formula below and normalized to a final 0–10 score.

### 1. User-value (weight: 3)
- 10: directly unblocks a stated user goal with measurable impact
- 6: meaningful quality-of-life improvement, not a blocker
- 2: speculative value, "nice to have"

### 2. Engineering-cost (weight: 2, **inverted**)
Score the cost first (10 = very expensive, 0 = trivial), then invert
(`inverted = 10 - raw`) before applying the weight. Lower cost → higher
contribution to the final score.
- raw 10 (→ inverted 0): multi-sprint, cross-repo, new infra
- raw 5 (→ inverted 5): a few days of focused work, no new infra
- raw 1 (→ inverted 9): hours of work, localized change

### 3. Reversibility (weight: 2)
How easy is it to back this out if we're wrong? Easier to reverse → higher
score.
- 10: pure additive, feature-flagged, can delete in one commit
- 5: touches shared code paths, reversible with care
- 1: schema migration, public API surface, or third-party integration

### 4. Alignment-with-memory (weight: 2)
Does this respect the agents' standing decisions (protected memory items,
ADRs referenced in `_shared` or `reviewer`)?
- 10: directly reinforces an existing standing decision
- 5: orthogonal to existing decisions
- 1: contradicts a standing decision (must be called out in `## Tradeoff`)

## Final score

```
score = 3*user_value + 2*(10 - engineering_cost) + 2*reversibility + 2*alignment
# max: 3*10 + 2*10 + 2*10 + 2*10 = 90
# normalize to 0-10 by dividing by 9
```

## Tie-breaking

When two ideas share a normalized score within 0.3 of each other:

1. Prefer the idea with higher **reversibility**.
2. If still tied, prefer the idea with lower **engineering-cost** (higher inverted value).
3. If still tied, list them both in `## Recommendation` and mark the decision as `needs_human`.
