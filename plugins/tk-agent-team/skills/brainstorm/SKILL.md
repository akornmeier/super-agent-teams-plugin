---
name: brainstorm
description: Use when the user has selected an idea from an ideation doc (or names a concrete feature directly) and needs it expanded into user stories and acceptance criteria. Produces `docs/brainstorms/<YYYY-MM-DD>-<slug>-requirements.md` with Given/When/Then criteria, out-of-scope, and open questions. Guarantees `planner/product` appends novel story patterns to its family memory before returning.
---

# brainstorm

You convert a single chosen idea into a requirements doc a planner can design against. No tradeoff scoring here — that already happened in `/ideate`. You are turning prose into testable acceptance criteria.

## Inputs you will be given

- **User prompt** (verbatim) under `## Original prompt` in the brief file.
- **Pre-loaded memory excerpts** — `_shared` and `planner` family snippets under `## Relevant memory`.
- **Input artifact path** — a `docs/ideation/<YYYY-MM-DD>-<slug>.md` file the user picked an idea from. If none, you must extract the "selected idea" from the user prompt itself.

## Stages

### Stage 1: Load selected idea

Read the input ideation doc (if present) and pull out the idea the user named. If the prompt names an idea number (e.g. "go with idea 2") resolve against the doc's `### Idea N:` headings. If no ideation doc exists, treat the user prompt as the selected idea and note the absence of prior ideation in the artifact's `## Selected idea` section.

### Stage 2: Expand into requirements (planner/product)

Dispatch `planner/product` with the selected idea plus the pre-loaded memory excerpts. The planner produces:
- **User stories** in `As a <role>, I want <capability>, so that <outcome>` form — aim for 3–7.
- **Acceptance criteria** in `Given <state>, When <action>, Then <observable>` form — at least one per story, multiple where behavior branches.
- **Out of scope** — explicit list of adjacent work this does NOT cover.
- **Open questions** — items that must be answered before `/plan` can safely run.

### Stage 3: Write artifact and memory-append

Write `docs/brainstorms/<YYYY-MM-DD>-<slug>-requirements.md` with required sections: `## Selected idea`, `## User stories`, `## Acceptance criteria`, `## Out of scope`, `## Open questions`. Ensure `planner/product` called `memory_append` for any novel story/criteria pattern (e.g. a role previously un-modeled, a cross-cutting acceptance pattern).

## Write back

Canonical artifact path: `docs/brainstorms/<YYYY-MM-DD>-<slug>-requirements.md`.

```yaml
artifact_path: docs/brainstorms/<YYYY-MM-DD>-<slug>-requirements.md
status: complete          # complete | blocked | needs_human
memory_appends: [planner]
next_skill_hint: /plan
```

## Invariants (never violate)

- Every dispatched agent must have appended to its family memory before this skill returns (or explicitly noted "no novel patterns").
- Every user story must have at least one Given/When/Then acceptance criterion. Zero criteria = `status: blocked`.
- If `## Open questions` contains blockers that make the requirements ambiguous, return `status: needs_human` rather than proceeding.
- Never write design or implementation detail — that is `/plan`'s job. Keep the doc about *what*, not *how*.
- Never write outside `docs/brainstorms/`.
