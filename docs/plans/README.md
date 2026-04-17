# docs/plans/

## Purpose

Technical design artifacts that are ready to implement. Each file takes a
brainstorm's requirements and produces the architectural decisions, migration
steps, test strategy, risks, and phased implementation breakdown needed to
hand off to developers. This is where "how exactly will we build it?" gets
answered.

## Naming convention

```
docs/plans/<YYYY-MM-DD>-<slug>-plan.md
```

- `<YYYY-MM-DD>` — ISO date the plan was drafted.
- `<slug>` — kebab-case noun phrase matching the originating brainstorm's
  slug where possible.
- Suffix `-plan.md` is required.

## Required sections

Every plan artifact must contain the following top-level sections, in order:

- `## Context`
- `## Approach`
- `## Layers affected`
- `## Data-model changes`
- `## Migration steps`
- `## Test strategy`
- `## Risks`
- `## Rollback plan`
- `## Implementation phases`

## Written by

- `/plan` skill — produces the artifact after dispatching `planner/technical`
  to draft and `reviewer/architecture` to flag standing-decision conflicts.

## Read by

- `/work` skill — drives the implementation.
- `/ship` skill — drives the end-to-end build/review/test loop.
- `/test` skill — consults the test strategy section.

## Retention

Artifacts in this directory are **durable and committed to the repository**.
They are not regenerated from agent memory. A plan is the canonical record of
the approach that was approved at a given point in time — preserve it even if
implementation later diverges, so the diff between plan and outcome remains
auditable.
