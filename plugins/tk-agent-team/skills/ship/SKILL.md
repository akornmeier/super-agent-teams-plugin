---
name: ship
description: Use when the user wants a plan taken to implemented+reviewed+tested in one shot ("ship it", "full cycle", "end-to-end", "take the plan to green"). Composite skill that runs `/work` → `/review` → `/test` sequentially with halt-on-blocker behavior and a single autofix retry. Sub-skills handle their own memory reads/writes at the skill layer via MCP tools.
---

# ship

You are the composite cycle. You do not dispatch agents directly — you dispatch *skills*, collect their artifacts, and return a combined summary. Your job is flow control: halt on blockers, run one autofix retry, otherwise push through to `/test`.

## Inputs you will be given

- **User prompt** (verbatim) under `## Original prompt` in the brief file.
- **Input artifact path** — a `docs/plans/<YYYY-MM-DD>-<slug>-plan.md` file. Required. Absence = `status: blocked`.

## Memory protocol (skill layer)

This is a composite skill that dispatches other skills (`/work`, `/review`, `/test`). Each sub-skill handles its own memory reads and writes per its own `## Memory protocol (skill layer)` section. This skill does NOT read or write memory directly — it delegates that responsibility to the sub-skills it invokes.

The only memory-related responsibility of `/ship` is to confirm that each sub-skill's `memory_findings` list is non-empty in its returned summary. If a sub-skill returns an empty `memory_findings`, log a warning.

## Stages

### Stage 1: Implement (`/work`)

Invoke `/work` with the plan doc. Receive back the `artifact_path` (a `docs/work/` summary) and a working-tree diff.

- On `status: complete`: proceed to stage 2.
- On `status: blocked` or `needs_human`: halt. Return combined summary with `/work`'s artifact and reason; do not run `/review` or `/test`.

### Stage 2: Review (`/review`, two-pass with autofix retry)

Invoke `/review` in `report-only` mode against the diff from stage 1. Inspect the findings:

- **No blockers**: proceed to stage 3.
- **Blockers present, first pass**: invoke `/review` in `autofix` mode (which internally runs developer on auto-fixable findings and re-reviews once). Then inspect the updated report:
  - No remaining blockers → proceed to stage 3.
  - Blockers still present → halt. Return combined summary with `status: blocked`. Do not run `/test` on known-broken code. **This is the one and only autofix retry — never loop a second time.**
- **`status: needs_human`** from review → halt.

### Stage 3: Test (`/test`)

Invoke `/test` with the plan doc (so the tester reads `## Test strategy`) and the diff. Collect the coverage-gap report.

### Stage 4: Combined summary

Produce a summary artifact at `docs/ship/<YYYY-MM-DD>-<slug>-ship.md` listing all three sub-skill artifact paths, overall status (worst of the three), and a one-line per-stage result.

## Write back

Canonical artifact path: `docs/ship/<YYYY-MM-DD>-<slug>-ship.md`.

```yaml
artifact_path: docs/ship/<YYYY-MM-DD>-<slug>-ship.md
status: complete          # complete | blocked | needs_human
memory_findings: [developer, reviewer, tester]
sub_artifacts:
  work: docs/work/<slug>-work.md
  review: docs/reviews/<slug>-review.md
  test: docs/tests/<slug>-test-report.md
next_skill_hint: /compound
```

## Invariants (never violate)

- Each sub-skill (`/work`, `/review`, `/test`) must persist its subagents' memory findings via `memory_append` before returning. `/ship` confirms this by checking each sub-skill's `memory_findings` list is non-empty. If a sub-skill returns an empty list, log a warning.
- Halt-on-blocker is strict: never run `/test` against a diff with unresolved review blockers.
- Autofix retry is limited to **one pass** in stage 2. A second oscillation is always `status: blocked`.
- Never invoke sub-skills in parallel — the pipeline order `/work → /review → /test` is load-bearing.
- Never edit code directly — all code changes flow through sub-skills.
