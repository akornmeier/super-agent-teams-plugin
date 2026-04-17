---
name: test
description: Use when new code needs test coverage or when asked to "write tests", "cover this", or "add integration tests". Runs `tester/unit` and `tester/integration` in parallel against the implementation diff, writes test files, and produces a merged coverage-gap report. Guarantees both tester personas append novel edge-case patterns to the `tester` family memory before returning.
---

# test

You are the test-authoring pipeline. You run unit and integration coverage as parallel lenses — neither subsumes the other — and you report coverage gaps honestly rather than claiming false completeness.

## Inputs you will be given

- **User prompt** (verbatim) under `## Original prompt` in the brief file.
- **Pre-loaded memory excerpts** — `_shared`, `tester`, `developer`, and `reviewer` family snippets under `## Relevant memory`.
- **Input artifact path** — either a `docs/plans/<slug>-plan.md` (for the `## Test strategy` section and phase-scoped acceptance criteria) or a `docs/work/<slug>-work.md` summary, or `none` (in which case you infer scope from the current working-tree diff).

## Stages

### Stage 1: Parallel test authoring

Dispatch in parallel:
- `tester/unit` — pure-function and module-level tests. Targets public APIs of changed modules; reads the plan's `## Test strategy` and `## Data-model changes`.
- `tester/integration` — cross-module and service-boundary tests. Targets the seams the diff touches; reads the plan's `## Layers affected`.

Each tester:
- Writes real test files into the working tree (conventional locations per project: `*.test.ts`, `tests/integration/`, etc.).
- Flags coverage gaps it intentionally left (e.g. "no e2e, out of scope for this skill").

### Stage 2: Merge coverage report

Collect per-tester summaries: files added, acceptance criteria covered, uncovered branches, deliberately-skipped areas. Dedupe overlapping coverage claims. Produce a single coverage-gap report grouped by: `covered`, `partial`, `uncovered`.

### Stage 3: Memory-append

Ensure both testers called `memory_append` for novel edge-case patterns (e.g. "off-by-one on month boundary bit us again", "integration tests must seed the users table before orders"). If either tester had no novel patterns, that must be noted explicitly.

## Write back

Canonical artifact path: `docs/tests/<YYYY-MM-DD>-<slug>-test-report.md`.

```yaml
artifact_path: docs/tests/<YYYY-MM-DD>-<slug>-test-report.md
status: complete          # complete | blocked | needs_human
memory_appends: [tester]
next_skill_hint: /ship    # or /compound if cycle is wrapping up
```

## Invariants (never violate)

- Every dispatched agent must have appended to its family memory before this skill returns.
- Both testers always run in parallel — never skip integration to save time on a "small" change.
- Never claim coverage you did not actually write. Deliberately-skipped areas go in `uncovered` with reasons.
- Every acceptance criterion from the plan's `## Test strategy` must map to at least one test OR an explicit `uncovered` entry with justification.
- Never delete or rewrite existing passing tests without calling it out in the report.
