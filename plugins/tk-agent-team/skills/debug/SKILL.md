---
name: debug
description: Use when a bug, stack trace, failing test, or regression is reported ("X is broken", "crash on Y", "failing since Z"). Runs researcher → debugger → reviewer/correctness → developer, then writes the fix as a durable `docs/solutions/bug-fixes/<YYYY-MM-DD>-<slug>.md` entry that feeds `/compound`. Guarantees every dispatched agent appends to its family memory before returning.
---

# debug

You are the root-cause pipeline. You do not guess — you reproduce, hypothesize, validate, fix, and record. The bug-fix doc you write is a durable signal future orchestrator routing relies on.

## Inputs you will be given

- **User prompt** (verbatim) under `## Original prompt` in the brief file — typically contains a stack trace, error message, or repro steps.
- **Pre-loaded memory excerpts** — `_shared`, `researcher`, `debugger`, `reviewer`, and `developer` family snippets under `## Relevant memory`.
- **Input artifact path** — usually `none`. May point at a previous `docs/solutions/bug-fixes/` entry if this is a re-occurrence.

## Stages

### Stage 1: Context brief (researcher)

Dispatch `researcher` with the prompt + stack trace. Returns: which files/modules the symptom touches, git blame on relevant lines, related prior `docs/solutions/bug-fixes/*` entries (for near-duplicates).

### Stage 2: Reproduction + hypothesis (debugger)

Dispatch `debugger` with the researcher's brief. Produces:
- A deterministic reproduction (minimal repro script, failing-test stub, or exact command).
- A root-cause hypothesis with evidence (file:line, variable state, sequence of events).
- A proposed fix direction (not the fix itself).

### Stage 3: Hypothesis validation (reviewer/correctness)

Dispatch `reviewer/correctness` with the hypothesis and the code under suspicion. Confirms or refutes. If refuted, loop back to stage 2 once with the refutation evidence. Second refutation = `status: needs_human`.

### Stage 4: Fix (developer)

Dispatch `developer` (frontend or backend per the affected layer) with the validated hypothesis and proposed direction. Developer writes the fix and a regression test covering the repro from stage 2.

### Stage 5: Record solution and memory-append

Write `docs/solutions/bug-fixes/<YYYY-MM-DD>-<slug>.md` with the canonical solution schema: `## Problem`, `## Root cause`, `## Solution`, `## Related patterns`, `## Applies to`. Ensure every dispatched agent (`researcher`, `debugger`, `reviewer/correctness`, `developer`) called `memory_append` — especially `debugger` with the pitfall pattern.

## Write back

Canonical artifact path: `docs/solutions/bug-fixes/<YYYY-MM-DD>-<slug>.md`.

```yaml
artifact_path: docs/solutions/bug-fixes/<YYYY-MM-DD>-<slug>.md
status: complete          # complete | blocked | needs_human
memory_appends: [researcher, debugger, reviewer, developer]
next_skill_hint: /compound
```

## Invariants (never violate)

- Every dispatched agent must have appended to its family memory before this skill returns — `debugger` in particular must record the pitfall.
- Never skip the reproduction step. A fix without a repro = `status: blocked`.
- Never ship a fix without a regression test covering the stage-2 repro.
- Loop back from stage 3 to stage 2 at most once. Second hypothesis refutation = `needs_human`.
- Always write the solution doc, even if the fix is one line — the durability of the record is the point.
