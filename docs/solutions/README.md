# docs/solutions/

## Purpose

Durable records of solved problems. Each file captures a completed piece of
work — the problem, its root cause (or motivation, for non-bug work), the
solution that was applied, related patterns, and where else the solution
applies. These entries feed future orchestrator routing decisions and are
consulted by `/ideate` for prior art.

## Categories

Solutions live under a category subdirectory. The six canonical categories:

- `bug-fixes/` — defects resolved; written as a side-effect of `/debug`.
- `features/` — net-new user-facing capability shipped end-to-end.
- `refactors/` — structural changes with no external behavior change.
- `integrations/` — new third-party or cross-service wiring.
- `performance/` — measurable latency, throughput, or resource wins.
- `security/` — hardening, vulnerability fixes, policy enforcement.

## Naming convention

```
docs/solutions/<category>/<YYYY-MM-DD>-<slug>.md
```

- `<category>` — one of the six above.
- `<YYYY-MM-DD>` — ISO date the solution landed.
- `<slug>` — kebab-case noun phrase of the problem or feature.

## Required sections

Every solution artifact must contain the following top-level sections, in
order:

- `## Problem`
- `## Root cause` — **or** `## Motivation` for non-bug categories
  (features, refactors, integrations, performance, security).
- `## Solution`
- `## Related patterns`
- `## Applies to`

## Written by

- `/compound` skill — authors solution entries across every category via the
  `docs-writer` agent.
- `/debug` skill — writes `bug-fixes/` entries as a side-effect of closing a
  defect.

## Read by

- Future orchestrator routing — consults prior solutions when classifying new
  prompts.
- `/ideate` skill — consults related categories for prior art before
  diverging.
- `curator` agent — consults when consolidating family memories.

## Retention

Artifacts in this directory are **durable and committed to the repository**.
They are not regenerated from agent memory. Solutions are the long-term
institutional memory of the agent team; never delete an entry just because
the code it describes has moved — update the `## Applies to` section
instead.
