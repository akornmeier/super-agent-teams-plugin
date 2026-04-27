---
name: test
description: Use when new code needs test coverage or when asked to "write tests", "cover this", or "add integration tests". Runs `tester/unit` and `tester/integration` in parallel against the implementation diff, writes test files, and produces a merged coverage-gap report. Reads/writes all agent memory at the skill layer via MCP tools before/after subagent dispatch.
team_pattern: solo
---

# test

You are the test-authoring pipeline. You run unit and integration coverage as parallel lenses — neither subsumes the other — and you report coverage gaps honestly rather than claiming false completeness.

## Inputs you will be given

- **User prompt** (verbatim) under `## Original prompt` in the brief file.
- **Input artifact path** — either a `docs/plans/<slug>-plan.md` (for the `## Test strategy` section and phase-scoped acceptance criteria) or a `docs/work/<slug>-work.md` summary, or `none` (in which case you infer scope from the current working-tree diff).

## Memory protocol (skill layer)

<!-- @ref _shared/memory-protocol.md -->

This skill follows the canonical memory protocol in `skills/_shared/memory-protocol.md`. See that file for the read-before / persist-after contract, the `_shared` write serialization rule, and the deprecated `## Memory findings` legacy path.

### Memory deltas for this skill

- Pre-dispatch reads at the skill layer: `_shared`, `tester` (for both tester dispatches), `developer` (cross-read for implementation context), `reviewer` (cross-read for known issues).
- All findings from both testers append under `agent_name="tester"` regardless of which dispatch produced them.
- Subagents now call `memory_findings_submit` directly per `_shared/findings-schema.md`. The legacy `## Memory findings` YAML block is DEPRECATED but still parsed by the substrate in v0.4.

## Stages

### Stage 1: Parallel test authoring

1. Read memory: call `mcp__agent-substrate__memory_read_shared()`, `mcp__agent-substrate__memory_read(agent_name="tester")`, `mcp__agent-substrate__memory_read(agent_name="developer")`, and `mcp__agent-substrate__memory_read(agent_name="reviewer")`.
2. Dispatch in parallel, each with memory content under `## Memory context`:
   - `tester/unit` — pure-function and module-level tests. Targets public APIs of changed modules; reads the plan's `## Test strategy` and `## Data-model changes`.
   - `tester/integration` — cross-module and service-boundary tests. Targets the seams the diff touches; reads the plan's `## Layers affected`.
3. Each tester:
   - Writes real test files into the working tree (conventional locations per project: `*.test.ts`, `tests/integration/`, etc.).
   - Flags coverage gaps it intentionally left (e.g. "no e2e, out of scope for this skill").
4. For each tester response, parse the `## Memory findings` YAML block. For each finding, call `mcp__agent-substrate__memory_append(agent_name="tester", section=finding.section, item=finding.item)`. Handle `warning` / `needs_curation` responses.

### Stage 2: Merge coverage report

Collect per-tester summaries: files added, acceptance criteria covered, uncovered branches, deliberately-skipped areas. Dedupe overlapping coverage claims. Produce a single coverage-gap report grouped by: `covered`, `partial`, `uncovered`.

### Stage 3: Verify memory persistence

Confirm that all memory findings from both testers were persisted via `memory_append` in stage 1 step 4. If either tester returned no `## Memory findings` section, log a warning — the agent may need its prompt updated.

## Write back

Canonical artifact path: `docs/tests/<YYYY-MM-DD>-<slug>-test-report.md`.

```yaml
artifact_path: docs/tests/<YYYY-MM-DD>-<slug>-test-report.md
status: complete          # complete | blocked | needs_human
memory_findings: [tester]
next_skill_hint: /ship    # or /compound if cycle is wrapping up
```

## Invariants (never violate)

- This skill must persist every subagent's memory findings via `memory_append` before returning. If a subagent returns no `## Memory findings` section, log a warning — the agent may need its prompt updated.
- Both testers always run in parallel — never skip integration to save time on a "small" change.
- Never claim coverage you did not actually write. Deliberately-skipped areas go in `uncovered` with reasons.
- Every acceptance criterion from the plan's `## Test strategy` must map to at least one test OR an explicit `uncovered` entry with justification.
- Never delete or rewrite existing passing tests without calling it out in the report.
