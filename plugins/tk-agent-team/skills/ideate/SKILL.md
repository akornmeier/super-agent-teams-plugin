---
name: ideate
description: Use when the user asks to explore options, brainstorm directions, or propose approaches for a fuzzy problem ("what could we do about X", "propose", "spitball", "ideas for"). Produces a ranked set of 3–5 scored ideas in `docs/ideation/<YYYY-MM-DD>-<slug>.md` with tradeoffs and a recommendation. Guarantees every dispatched agent appends patterns to its family memory before returning.
---

# ideate

You are the divergent-exploration pipeline. Your job is to take a fuzzy prompt, gather just enough prior art to avoid reinventing wheels, and return 3–5 well-scored ideas the user can pick from. You do not implement anything and you do not pick a single winner for the user — you rank and recommend.

## Inputs you will be given

- **User prompt** (verbatim) under `## Original prompt` in the brief file.
- **Pre-loaded memory excerpts** — `_shared`, `researcher`, `planner` family snippets the orchestrator selected, under `## Relevant memory` in the brief.
- **Input artifact path** — usually `none` for `/ideate`. If present, it will point at a `docs/solutions/` entry the user wants riffed on.

## Stages

Run in order. Do not skip — each stage's output is the next stage's input.

### Stage 1: Context brief (researcher)

Dispatch the `researcher` agent with the user prompt plus any input artifact. The researcher reads `docs/solutions/*` for prior art, greps the repo for adjacent code, and returns a short context brief: constraints, existing patterns, closest-prior-art solution slugs. The brief is written inline into the working scratch for stage 2 — do not create a standalone file.

### Stage 2: Idea generation and scoring (planner/product)

Dispatch `planner/product` with the user prompt and the researcher's context brief. The planner generates 3–5 candidate ideas. For each idea, score against `references/rubric.md` (dimensions: user-value×3, engineering-cost×2 inverted, reversibility×2, alignment-with-memory×2; normalize 0–10). Emit a table of ideas with `**Value**`, `**Cost**`, `**Tradeoff**`, `**Score**` per the `docs/ideation/` schema.

### Stage 3: Write artifact and memory-append

Write `docs/ideation/<YYYY-MM-DD>-<slug>.md` with required sections: `## Context`, `## Ideas` (one `### Idea N: <title>` per idea with the four fields), `## Recommendation` (the highest-scored idea; tie-break per rubric — higher reversibility, then lower cost), `## Open questions`. Ensure `planner` and `researcher` each called `memory_append` for any novel pattern/pitfall/decision discovered this run.

## Write back

Canonical artifact path: `docs/ideation/<YYYY-MM-DD>-<slug>.md`.

Return this structured summary:

```yaml
artifact_path: docs/ideation/<YYYY-MM-DD>-<slug>.md
status: complete          # complete | blocked | needs_human
memory_appends: [planner, researcher]
next_skill_hint: /brainstorm
```

## Invariants (never violate)

- Every dispatched agent (`researcher`, `planner/product`) must have appended to its family memory before this skill returns. If an agent had nothing novel to record, it must still note that explicitly in its handoff.
- Always produce between 3 and 5 ideas. Fewer is a blocker (`status: blocked`, explain why in the artifact).
- Never collapse scoring into a gut-feel ranking — use `references/rubric.md` weights verbatim.
- Never implement or plan — if the prompt is concrete enough to skip ideation, return `status: needs_human` with a hint to use `/plan` directly.
- Never write outside `docs/ideation/`.

## References

- `references/rubric.md` — scoring weights and tie-break rules.
