# docs/ideation/

## Purpose

Divergent exploration artifacts. Each file captures 3–5 ranked ideas for a
given topic with their tradeoffs, values, costs, and a recommendation. This is
where "what could we build?" lives before any one idea has been selected.

## Naming convention

```
docs/ideation/<YYYY-MM-DD>-<slug>.md
```

- `<YYYY-MM-DD>` — ISO date the ideation ran.
- `<slug>` — kebab-case noun phrase of the **topic**, not of a single idea.
  (e.g. `2026-04-17-user-profiles.md`, not `2026-04-17-avatar-upload.md`)

## Required sections

Every ideation artifact must contain the following top-level sections, in
order:

- `## Context`
- `## Ideas` — each idea as a subsection with:
  - `### Idea N: <title>`
  - `**Value**`
  - `**Cost**`
  - `**Tradeoff**`
  - `**Score**`
- `## Recommendation`
- `## Open questions`

## Written by

- `/ideate` skill — produces the artifact after dispatching `researcher` for a
  context brief and `planner/product` for the ranked ideas.

## Read by

- `/brainstorm` skill — consumes the selected idea and expands it into full
  requirements.

## Retention

Artifacts in this directory are **durable and committed to the repository**.
They are not regenerated from agent memory. Treat them as the canonical record
of what options were considered at a given point in time; they feed future
routing decisions and prior-art searches.
