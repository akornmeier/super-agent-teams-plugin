---
name: plan
description: Use when requirements exist (from `/brainstorm`) or the user asks for a technical design, ADR, or implementation plan. Produces `docs/plans/<YYYY-MM-DD>-<slug>-plan.md` conforming to `references/plan-schema.md`, reviewed once by `reviewer/architecture` for standing-decision conflicts. Guarantees `planner/technical` and `reviewer/architecture` both append to their family memory before returning.
---

# plan

You turn requirements into an implementable technical plan. You are not writing code and not picking ideas — those happened upstream. You *are* naming layers, data model changes, migrations, and risks concretely enough that `/work` can execute without asking follow-up questions.

## Inputs you will be given

- **User prompt** (verbatim) under `## Original prompt` in the brief file.
- **Pre-loaded memory excerpts** — `_shared`, `planner`, and `reviewer` snippets under `## Relevant memory`. The reviewer snippets must include any protected standing decisions (ADRs).
- **Input artifact path** — a `docs/brainstorms/<YYYY-MM-DD>-<slug>-requirements.md` file. If none, you must synthesize implicit requirements from the prompt and call that out in `## Context`.

## Stages

### Stage 1: Draft (planner/technical)

Dispatch `planner/technical` with the requirements doc and pre-loaded memory. The planner drafts against `references/plan-schema.md` — every required section must be populated or explicitly marked `N/A (reason)`. The draft is written to the artifact path in full before stage 2 begins.

### Stage 2: Architecture review (reviewer/architecture)

Dispatch `reviewer/architecture` with the draft plan and the `reviewer` family memory. The reviewer flags:
- Conflicts with standing decisions / protected memory items (ADRs).
- Missing migration or rollback detail.
- Layer-boundary violations implied by the plan.

Output is a findings list — blockers vs. advisories — handed to stage 3.

### Stage 3: Revise and finalize (planner/technical)

Dispatch `planner/technical` again with the findings list. All blockers must be resolved (by changing the plan OR by explicitly overriding a standing decision with justification in `## Risks`). Advisories may be addressed or acknowledged. Write final plan to `docs/plans/<YYYY-MM-DD>-<slug>-plan.md`. Ensure both `planner` and `reviewer` called `memory_append` for novel architectural patterns, conflicts resolved, or new standing decisions.

## Write back

Canonical artifact path: `docs/plans/<YYYY-MM-DD>-<slug>-plan.md`.

```yaml
artifact_path: docs/plans/<YYYY-MM-DD>-<slug>-plan.md
status: complete          # complete | blocked | needs_human
memory_appends: [planner, reviewer]
next_skill_hint: /work
```

## Invariants (never violate)

- Every dispatched agent must have appended to its family memory before this skill returns.
- Every section in `references/plan-schema.md` must be present. Missing = `status: blocked`.
- Blocker-severity findings from stage 2 must be resolved or explicitly overridden with justification — never silently ignored.
- Never include code diffs — the plan names files/functions, not implementations.
- Never write outside `docs/plans/`.

## References

- `references/plan-schema.md` — required sections a valid plan doc must contain.
