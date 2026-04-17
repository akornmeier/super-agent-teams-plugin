# Plan document schema

Every plan doc written by `/plan` MUST contain these sections in this order.
`planner/technical` drafts against this schema; `reviewer/architecture`
validates completeness before sign-off. Missing sections are a blocker.

Copied from `specs/foundation-notes.md §3 docs/plans/`. Changing this file
changes the contract for every downstream skill (`/work`, `/ship`, `/test`).

## Required sections

### `## Context`
One paragraph on why this work exists. Links to the `docs/brainstorms/` doc (if any) and the originating user request. Mention any prior-art `docs/solutions/` entries.

### `## Approach`
Prose description of the chosen technical approach in 2–5 paragraphs. Names the architectural pattern (e.g. repository, CQRS, event-sourced) explicitly. Calls out alternatives considered and why they were rejected.

### `## Layers affected`
Bullet list of layers touched: frontend (routes, components), backend (controllers, services, repositories), data (schema, indexes), infra (queues, caches, third-party). Used by `/work` to classify frontend/backend/full-stack dispatch.

### `## Data-model changes`
Every new/modified entity, field, relation. Include column types, nullability, defaults, and index choices. If none, write `None` — do not omit the section.

### `## Migration steps`
Ordered, numbered steps to roll the schema/data forward. Each step names the tool (e.g. `knex migrate`, `alembic`, `sql script`). If none, write `None`.

### `## Test strategy`
Which layers get unit vs. integration vs. e2e coverage. Lists the specific acceptance criteria (from the brainstorm doc) each new test must cover. Used by `/test` to scope tester dispatch.

### `## Risks`
Bullet list of risks with severity (`high` / `med` / `low`) and mitigation. Any standing-decision overrides from `/plan` stage 2 are recorded here with explicit justification.

### `## Rollback plan`
Ordered steps to back out the change if it lands and misbehaves. Must cover both code revert and data rollback (migration-down, feature-flag off, etc.). "Re-deploy previous" is acceptable only for pure-additive changes.

### `## Implementation phases`
Ordered, numbered phases (≤5). Each phase is independently shippable and testable. Each phase names: files/modules touched, tests added, acceptance criteria satisfied. `/work` executes phases in order.
