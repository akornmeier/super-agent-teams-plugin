---
name: debug
team_pattern: pipeline
description: Use when a bug, stack trace, failing test, or regression is reported ("X is broken", "crash on Y", "failing since Z"). Creates a `pipeline` debug team — researcher → debugger → reviewer-correctness → developer → tester — coordinated through a `TaskList` `addBlockedBy` chain. Each stage reads prior task history at wake; teammates submit findings via `memory_findings_submit`. Output is a collaboratively-authored `docs/solutions/bug-fixes/<slug>.md`.
---

# debug

You are the root-cause pipeline. You do not guess — you reproduce, hypothesize, validate, fix, regression-test, and record. The bug-fix doc the team writes is a durable signal future orchestrator routing relies on. In v0.4 the stages are real teammates in a `pipeline` team; coordination flows through a `TaskList` `addBlockedBy` chain, not parent prose.

## Inputs you will be given

- **User prompt** (verbatim) under `## Original prompt` in the brief file — typically contains a stack trace, error message, or repro steps. May contain a hint indicating frontend vs backend layer.
- **Input artifact path** — usually `none`. May point at a previous `docs/solutions/bug-fixes/` entry if this is a re-occurrence.

## Memory protocol

<!-- @ref _shared/memory-protocol.md -->
<!-- @ref _shared/team-protocol.md -->
<!-- @ref _shared/findings-schema.md -->

This skill follows the canonical memory and team protocols. Pipeline teammates read `_shared` + their own family + per-matrix cross-family memory directly via `mcp__agent-substrate__memory_read*` and submit findings via `mcp__agent-substrate__memory_findings_submit`. The skill is a team factory; the team-lead owns the TaskList chain.

## Workflow

### Stage 0 — team creation

1. Compute `team_slug` from the prompt: lowercase-kebab-case, max 32 chars (e.g. `debug-signup-500`).
2. Call `TeamCreate({team_name: "debug-<slug>", description: "Debug: <prompt-excerpt>"})`.
3. Spawn a persistent `team-lead` for the team's lifetime. Team-lead owns the TaskList, dispatches teammates in chain order, and assembles the final artifact.

### Stage 1 — pipeline construction

Team-lead creates the full pipeline of TaskList tasks UP FRONT with an `addBlockedBy` chain. Tasks are visible at construction time so any teammate can read the chain ahead of its turn:

```python
t1 = TaskCreate({subject: "Research the bug context", owner: "researcher"})
t2 = TaskCreate({subject: "Hypothesize root cause", owner: "debugger", addBlockedBy: [t1]})
t3 = TaskCreate({subject: "Validate hypothesis", owner: "reviewer-correctness", addBlockedBy: [t2]})
t4 = TaskCreate({subject: "Implement fix", owner: "developer-backend", addBlockedBy: [t3]})
t5 = TaskCreate({subject: "Write regression test", owner: "tester-unit", addBlockedBy: [t4]})
```

For frontend bugs (UI/a11y/component signals in the prompt), swap `developer-backend` → `developer-frontend` and `tester-unit` → `tester-integration`. The dispatching prompt's signals decide; team-lead picks once at construction time.

### Stage 2 — pipeline execution

Team-lead spawns teammates in chain order. Critically, teammates spawn one at a time — each teammate's `addBlockedBy` predecessor must be `completed` first. Each teammate at wake reads:

1. Their own family memory + `_shared` directly via `mcp__agent-substrate__memory_read*`. Cross-family reads per `specs/foundation-notes.md` §5: `debugger` reads `reviewer` + `researcher`; `tester` reads `developer` + `reviewer`.
2. The TaskList — especially the descriptions and comments of completed predecessor tasks. The pipeline's coordination shape means prior context flows via TaskList history, not via parent brokering.
3. Team scratch (`mcp__agent-substrate__team_memory_read`) for any cross-cutting handoff notes the team-lead recorded under `section: "handoffs"`.

Each teammate then:

- Does their stage's work:
  - **researcher** → context brief: which files/modules the symptom touches, git blame, related prior `docs/solutions/bug-fixes/*` entries.
  - **debugger** → deterministic reproduction + root-cause hypothesis + proposed fix direction.
  - **reviewer-correctness** → confirm or refute the hypothesis with evidence.
  - **developer-backend** (or **developer-frontend**) → implement the fix.
  - **tester-unit** (or **tester-integration**) → write a regression test covering the stage-2 repro.
- Calls `mcp__agent-substrate__memory_findings_submit({agent: "<family>", findings: [...]})` with their findings (use the optional `lens` field on `FindingItem` to record the running-teammate name once the substrate `lens` rollout lands; until then, omit `lens`).
- Updates their TaskList task with status `completed` and a brief comment summarizing what they passed forward (artifact path, hypothesis statement, validation verdict, diff scope, test path).
- Optionally `SendMessage` the next teammate to wake them with context. Team-lead may do this instead.

### Stage 3 — output assembly

After tester completes:

1. Team-lead reads each task's comments from TaskList to assemble the consolidated bug-fix narrative.
2. Team-lead writes the canonical artifact `docs/solutions/bug-fixes/<YYYY-MM-DD>-<slug>.md` collaboratively, with attributed sections:
   - `## Problem` — from researcher's context brief.
   - `## Root cause` — from debugger's hypothesis (validated by reviewer-correctness).
   - `## Solution` — from developer's fix.
   - `## Regression test` — from tester.
   - `## Related patterns` and `## Applies to` — team-lead synthesizes.
   The artifact is one file with attributed sections, not five separate files.
3. Team-lead records any project-level decisions that emerged to `_shared` via `memory_append_shared({section: "decisions", item: {...}})` (team-lead is the only writer per `_shared` write serialization; the substrate slug regex disallows `agent: "_shared"`).

### Stage 4 — teardown

1. Verify the TaskList is fully drained (no `pending` or `in_progress` tasks) per `_shared/team-protocol.md` shutdown invariants.
2. Send `shutdown_request` to all teammates in reverse pipeline order — tester first, researcher last — so an in-flight clarification DM cannot strand a downstream teammate. Each teammate must have called `memory_findings_submit` before acknowledging shutdown; otherwise the 60-second escape hatch applies and unsubmitted findings are lost.
3. Call `TeamDelete({team_name: "debug-<slug>"})` to remove the team-scratch namespace.

### Pipeline rules (load-bearing)

- Tasks are created BEFORE any teammates spawn — the chain is visible at construction time. Adding tasks mid-pipeline requires explicit `addBlockedBy` updates by the team-lead.
- A teammate that fails (cannot complete its stage) does NOT block the pipeline indefinitely — team-lead receives the failure, decides whether to escalate to the user (`status: needs_human`) or spawn a parallel investigator teammate (cross-pattern dispatch per `_shared/team-protocol.md#cross-pattern-dispatch`).
- If hypothesis validation (reviewer-correctness) rejects the debugger's hypothesis, team-lead may loop back: spawn a new debugger teammate with the rejection rationale as input. Document the loop in team scratch under `section: "decisions"`. Maximum **2 hypothesis rejections** before escalating to user as `status: needs_human`.
- The artifact is collaboratively authored — each stage owns its named section, but team-lead does the integration pass.

### Memory deltas for this skill

- Pipeline teammates read prior task history at wake — they DO NOT need parent-brokered briefs.
- Each teammate submits findings to its own family memory at task end (researcher → `researcher`, debugger → `debugger`, reviewer-correctness → `reviewer`, developer-backend/frontend → `developer`, tester-unit/integration → `tester`).
- Cross-family reads stay at the teammate level per `specs/foundation-notes.md` §5: debugger reads `reviewer` + `researcher`; tester reads `developer` + `reviewer`.
- Stage handoffs land in team scratch via `mcp__agent-substrate__team_memory_append({section: "handoffs", item: {...}})` — artifact paths, hypothesis statements, validation verdicts, diff scopes, test paths.
- Hypothesis-rejection loops land in team scratch under `section: "decisions"`.
- Escalations to user land in team scratch under `section: "escalations"`.

## Write back

Canonical artifact path: `docs/solutions/bug-fixes/<YYYY-MM-DD>-<slug>.md`.

```yaml
artifact_path: docs/solutions/bug-fixes/<YYYY-MM-DD>-<slug>.md
status: complete          # complete | blocked | needs_human
memory_findings: [researcher, debugger, reviewer, developer, tester]
next_skill_hint: /compound
```

## Invariants (never violate)

- Every teammate calls `memory_findings_submit` before acknowledging shutdown. The legacy prose `## Memory findings` block is deprecated and must not appear in new code.
- Never skip the reproduction step. A fix without a deterministic repro = `status: blocked`.
- Never ship a fix without a regression test covering the stage-2 repro — the tester stage is non-optional.
- Maximum 2 hypothesis rejections (stage 3 → stage 2 loop). Third rejection = `status: needs_human`.
- Always write the solution doc, even if the fix is one line — the durability of the record is the point.
- Always `TeamDelete` at the end. Leaked team scratch is a liability.
