# Scoring rubric for Stage 2 of memory-curate

This file defines how the curator ranks unprotected memory items when it must
drop the weakest. Items are scored **0–10**, highest survives.

Scoring a memory item means answering: *if this item were lost, how much
would the agent regret not having it next time?* Low regret = low score =
drop first.

## Scoring dimensions

Each dimension contributes to the final score. Weights are intentionally
**fixed here** rather than in the SKILL so curation runs are reproducible —
if you want to change the policy, change this file, not a prompt.

<!--
  TODO (USER CONTRIBUTION):

  Below is the weighted rubric. I've drafted a starting point based on
  general curation instincts, but YOU know your domain — what actually
  matters for your agents depends on what they're doing day-to-day
  (research? code review? UI work?).

  Please edit the weights, thresholds, and the "drop threshold" line
  so they reflect what you want preserved vs. discarded. Aim for 5-10
  meaningful edits — this is the policy that will shape every curation
  run for the life of the plugin.

  Dimensions you might want to tune:
    - recency           (how much does "updated recently" matter?)
    - evidence density  (is a pattern w/ concrete evidence worth more?)
    - specificity       (generic wisdom vs. domain-specific detail?)
    - reversibility     (is it costly to rediscover if dropped?)
    - supersession      (decisions that supersede others = anchor points)

  Consider adding your own dimensions. Consider also whether the drop
  threshold should be a fixed number (e.g. "drop anything scoring < 4")
  or adaptive (e.g. "drop the bottom quartile").
-->

### 1. Recency (weight: 2)
- 10: updated in the last 7 days
- 7: updated in the last 30 days
- 4: updated in the last 90 days
- 1: older than 90 days

### 2. Evidence density (weight: 3)
- 10: item has concrete evidence/rationale with specifics (numbers, file paths, project names)
- 6: item has evidence but it's vague
- 2: evidence field is empty or filler

### 3. Specificity (weight: 2)
- 10: domain-specific, non-obvious ("use react-virtual when >500 rows")
- 5: somewhat generic but actionable
- 1: generic wisdom the agent would rediscover anyway ("write tests")

### 4. Reversibility cost (weight: 3)
- 10: hard to rediscover — came from an incident, a user correction, or long investigation
- 5: moderate — derivable with some effort
- 1: trivially re-derivable by reading the code

## Final score

```
score = 2*recency + 3*evidence + 2*specificity + 3*reversibility
# max: 2*10 + 3*10 + 2*10 + 3*10 = 100
# normalize to 0-10 by dividing by 10
```

## Drop threshold

Drop any item scoring **below 4.0** (on the normalized 0–10 scale).
If the file is still over the soft limit after that, proceed to Stage 3.
