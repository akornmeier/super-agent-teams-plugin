# docs/brainstorms/

## Purpose

Expanded-requirements artifacts. Each file takes **one** idea — usually the
recommended idea from a `docs/ideation/` doc — and blows it out into user
stories, acceptance criteria, out-of-scope boundaries, and open questions.
This is where "what exactly are we building?" gets pinned down before a
technical plan is drafted.

## Naming convention

```
docs/brainstorms/<YYYY-MM-DD>-<slug>-requirements.md
```

- `<YYYY-MM-DD>` — ISO date the brainstorm ran.
- `<slug>` — kebab-case noun phrase of the selected idea.
- Suffix `-requirements.md` is required — it disambiguates these artifacts
  from other stages at a glance.

## Required sections

Every brainstorm artifact must contain the following top-level sections, in
order:

- `## Selected idea`
- `## User stories` — each written in `As a ... / I want ... / So that ...`
  form.
- `## Acceptance criteria` — each written in `Given ... / When ... / Then ...`
  form.
- `## Out of scope`
- `## Open questions`

## Written by

- `/brainstorm` skill — produces the artifact after dispatching
  `planner/product` to expand the selected idea.

## Read by

- `/plan` skill — consumes the requirements and produces the technical plan.

## Retention

Artifacts in this directory are **durable and committed to the repository**.
They are not regenerated from agent memory. They are the traceability bridge
between an ideation doc and a plan doc; keep them intact even after the
feature ships.
