---
name: compound
description: Use at the end of a full cycle (after `/ship` or `/debug`) to harvest the run into durable signal — a solution doc in `docs/solutions/<category>/` plus curated memory files. Dispatches `docs-writer` then the existing `curator` agent against every family memory touched during the cycle. Guarantees both agents append/curate before returning.
---

# compound

You are the durability pipeline. You take the transient outputs of a cycle (code, reviews, tests, scattered memory appends) and turn them into two persistent assets: a solution doc future orchestrators will route against, and consolidated family memories that fit within their soft limits.

## Inputs you will be given

- **User prompt** (verbatim) under `## Original prompt` in the brief file.
- **Pre-loaded memory excerpts** — `_shared`, `docs-writer`, `curator`, and every family touched during the cycle (typically `planner`, `developer`, `reviewer`, `tester`, `debugger`, `researcher`).
- **Input artifact path** — the driving artifact for the cycle being compounded. Usually a `docs/ship/<slug>-ship.md` or `docs/solutions/bug-fixes/<slug>.md`. May point at a plan doc if compounding directly after `/plan`+`/work`.

## Stages

### Stage 1: Categorize and author solution (docs-writer)

Determine the solution category from `references/categories.md` based on the driving artifact:
- `/ship` cycles with new capability → `features`
- `/ship` cycles with structural change only → `refactors`
- `/debug` cycles → `bug-fixes` (usually already written by `/debug`; docs-writer enriches)
- Other triggers map via the descriptions in `references/categories.md`

Dispatch `docs-writer` with the driving artifact, cycle sub-artifacts, and `references/solution-schema.md`. Produces `docs/solutions/<category>/<YYYY-MM-DD>-<slug>.md` with sections `## Problem` or `## Motivation`, `## Solution`, `## Related patterns`, `## Applies to`.

### Stage 2: Curate memories (curator)

Enumerate every family whose memory was appended during the cycle (read `memory_appends` from each sub-skill's summary). For each family, dispatch the existing `curator` agent via `/memory-curate` if its memory file is near or over the soft limit. The curator consolidates newly-appended patterns per its own scoring rubric — you do not override or duplicate curation policy here.

### Stage 3: Consolidated summary

Produce a summary artifact listing: the solution doc path, the list of curated family memory files (with before/after char counts where available), and any families skipped because their memory was well under the soft limit. Confirm `docs-writer` appended to its family memory with novel documentation patterns.

## Write back

Canonical artifact path: `docs/solutions/<category>/<YYYY-MM-DD>-<slug>.md` (primary) plus `docs/compound/<YYYY-MM-DD>-<slug>-compound.md` (summary).

```yaml
artifact_path: docs/solutions/<category>/<YYYY-MM-DD>-<slug>.md
status: complete          # complete | blocked | needs_human
memory_appends: [docs-writer]
memory_curated: [planner, developer, reviewer, tester]   # actual families vary by cycle
next_skill_hint: null
```

## Invariants (never violate)

- Every dispatched agent must have appended to its family memory before this skill returns (`docs-writer` for novel documentation patterns; `curator` operates on memory itself).
- Solution category must come from `references/categories.md` — never invent a new category inline. If none fits, return `status: needs_human`.
- Solution doc must include every section in `references/solution-schema.md`.
- Never overwrite an existing solution doc — if the slug collides, suffix with `-v2`.
- Never skip curation on a family whose memory file is over the soft limit. Dispatch the curator even if the cycle was small.

## References

- `references/categories.md` — canonical solution categories.
- `references/solution-schema.md` — required sections for a solution doc.
