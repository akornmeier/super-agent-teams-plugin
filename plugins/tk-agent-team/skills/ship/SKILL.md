---
name: ship
team_pattern: staged-team
description: Use when the user wants a plan taken to implemented+reviewed+tested in one shot ("ship it", "full cycle", "end-to-end", "take the plan to green"). Creates a `staged-team` whose members rotate per stage — work → review → test — so each downstream stage checks the upstream stage with no carry-over bias. Halt-on-blocker, single review-rework cycle, hard cap at two cycles before escalation.
---

# ship

You are the staged-team coordinator for full-cycle delivery. The team persists across stages; its **membership rotates** per stage. A `team-lead` teammate is the only persistent member. Stage 1 (work) developers shut down before Stage 2 (review) reviewers spawn; Stage 2 reviewers shut down before Stage 3 (test) testers spawn. This is the bias-avoidance default of `staged-team` — a reviewer who watched the code get written would be biased toward approving it.

## Inputs and ground rules

- **User prompt** (verbatim) under `## Original prompt` in the brief file.
- **Input artifact path** — a `docs/plans/<YYYY-MM-DD>-<slug>-plan.md` file. Required. Absence = `status: blocked`.
- **Mode hints** in the prompt: backend-only / frontend-only / full-stack signal which Stage 1 developers spawn.

Default rule: this skill uses `team_pattern: staged-team` because each downstream stage *checks* the upstream stage. See `_shared/team-protocol.md#default-rule-load-bearing`.

## Memory protocol

<!-- @ref _shared/memory-protocol.md -->
<!-- @ref _shared/team-protocol.md -->

This skill follows the canonical memory and team protocols. Teammates spawned by each stage have direct MCP access — they read family memory and submit findings via `memory_findings_submit` themselves. The skill is a team factory and stage-transition coordinator, not a memory broker.

### Memory deltas for this skill

- `_shared` writes flow through the persistent `team-lead` teammate (only it can serialize to `_shared.yaml`).
- Stage handoffs are recorded in team scratch via `team_memory_append({section: "handoffs", ...})` per the team-memory section taxonomy in `_shared/team-protocol.md`.
- Each teammate calls `memory_findings_submit` BEFORE acknowledging shutdown — the team-lead's 60-second shutdown timeout discards unsubmitted findings.

## Workflow

### Stage 0 — team creation

1. Compute `team_slug` from the prompt: lowercase-kebab, max 32 chars (e.g. `ship-user-profiles`).
2. `TeamCreate({team_name: "ship-<slug>", description: "Ship: <prompt-excerpt>"})`.
3. Spawn the persistent `team-lead`: `Agent({subagent_type: "general-purpose", name: "team-lead", team_name: "ship-<slug>", prompt: "<lifecycle brief>", run_in_background: true})`. Team-lead lives the entire team's lifetime.
4. Team-lead reads `_shared` and writes the initial team scratch entries (`section: "handoffs"`) so subsequent teammates know what stage we are in.

### Stage 1 — work (members rotate per stage)

1. Team-lead spawns work teammates per the prompt's frontend/backend signal:
   - Backend signal → `Agent({name: "developer-backend", team_name: "ship-<slug>", ...})` + `TaskCreate({subject: "Implement <component>", owner: "developer-backend"})`.
   - Frontend signal → `Agent({name: "developer-frontend", ...})` + matching `TaskCreate`.
   - Both → both spawn (they DM each other for contract negotiation, mirroring the `/work` pair pattern).
2. Each developer teammate's prompt MUST include a `## Team coordination context` heading carrying their own `taskId` and any peer `taskId`s, per `_shared/team-protocol.md#taskid-threading-load-bearing-for-spawning-skills`.
3. Developers do their work directly: read family memory, edit code, run tests, submit findings via `memory_findings_submit({agent: "developer", ...})` (family-level slug; running-teammate-name `developer-backend`/`developer-frontend` may be captured optionally in `item.lens` once substrate task 20 lands — see `_shared/findings-schema.md`).
4. When the work task is `completed`, each developer MUST call `memory_findings_submit` BEFORE acknowledging shutdown.
5. Team-lead sends `SendMessage({to: "developer-<lens>", message: {type: "shutdown_request"}})` to each developer, waits for idle (≤60s grace per `_shared/team-protocol.md#shutdown-invariants`), then records `team_memory_append({team_name: "ship-<slug>", section: "handoffs", item: {...}})` documenting "stage 1 → stage 2 transition; work artifact at `docs/work/<slug>-work.md`".

**Critical:** developers shut down at stage end. The next stage's reviewers spawn FRESH with NO exposure to developer reasoning beyond what is in the artifact and diff.

### Stage 2 — review (fresh members, parallel-panel sub-shape)

1. Team-lead spawns three reviewer teammates per `/review`'s migrated `parallel-panel` pattern:
   - `reviewer-architecture`, `reviewer-correctness`, `reviewer-security`
   - `Agent({subagent_type: "Code Reviewer", name: "reviewer-<lens>", team_name: "ship-<slug>", ...})` + `TaskCreate` per teammate.
   - Augmentation rule: if the prompt or diff carries security signals (`auth`, `credential`, `crypto`, `token`), `reviewer-security` is mandatory; otherwise default-include.
2. Reviewers run concurrently per `parallel-panel` discipline. Severity dedup follows `_shared/team-protocol.md#severity-vocabulary-canonical-lattice`: peer-DM dedup for severity ≤ `minor`; dedup-arbiter (team-lead) for severity ≥ `major`. Peer-DM outcomes are logged via `team_memory_append({section: "dedup_decisions", ...})`.
3. Reviewers submit findings as `agent: "reviewer"` (family) and may set `item.lens: "reviewer-<lens>"` once substrate task 20 lands.
4. When the review task completes, team-lead consolidates the report at `docs/reviews/<YYYY-MM-DD>-<slug>-review.md`, records `team_memory_append({section: "handoffs", ...})` for the stage 2→3 transition, and sends `shutdown_request` to all reviewers.
5. **Blocker handling:** if the consolidated report contains any `blocker`-severity findings, team-lead spawns ONE follow-up `developer-backend` (or `developer-frontend`) teammate in a NEW work cycle to autofix. This counts as cycle 2; max 2 review-rework cycles total before escalating to the user with `status: blocked`.

### Stage 3 — test (fresh members, no inheritance)

1. Team-lead spawns test teammates:
   - Default: `tester-unit`. Spawn `tester-integration` if review-stage flagged "needs integration coverage" (look in team scratch under `section: "dedup_decisions"` or `section: "handoffs"`).
   - `Agent({subagent_type: "general-purpose", name: "tester-<lens>", team_name: "ship-<slug>", ...})` + `TaskCreate` per teammate.
2. Testers read the work artifact and the consolidated review report from `TaskList` history plus `team_memory_read({team_name: "ship-<slug>"})`. They do NOT see developer reasoning except through the artifact — this is the staged-team bias-avoidance contract.
3. Testers write tests, run them, submit findings via `memory_findings_submit({agent: "tester", ...})` BEFORE shutdown.
4. Team-lead sends `shutdown_request` to testers, waits for idle.

### Stage 4 — teardown

1. Team-lead writes the final `## Memory deltas` summary into `_shared` if the cycle produced any project-level decisions (via `memory_findings_submit({agent: "_shared", ...})` — only team-lead may do this).
2. Parent skill sends `SendMessage({to: "team-lead", message: {type: "shutdown_request"}})` (or team-lead self-shutdowns once final summary is committed).
3. `TeamDelete({team_name: "ship-<slug>"})`.

### Stage transition rules (load-bearing)

- Stage transitions are `TaskList` checkpoints owned by `team-lead`. The next stage does NOT spawn until the previous stage's tasks are all `completed`.
- Each stage's teammates shut down BEFORE the next stage's teammates spawn — this is what makes it `staged-team`, not `feature-team`.
- If a stage produces blockers (review finds a `blocker`; test catches a regression), team-lead may spawn a follow-up developer teammate in a NEW work stage (recursive descent). Hard cap: **2 review-rework cycles** before escalating to the user with `status: blocked`.

## Output schema

Canonical artifact path: `docs/ship/<YYYY-MM-DD>-<slug>-ship.md`.

```yaml
artifact_path: docs/ship/<YYYY-MM-DD>-<slug>-ship.md
status: complete          # complete | blocked | needs_human
memory_findings: [developer, reviewer, tester]
sub_artifacts:
  work: docs/work/<slug>-work.md
  review: docs/reviews/<YYYY-MM-DD>-<slug>-review.md
  test: docs/tests/<slug>-test-report.md
team_summary:
  team_name: ship-<slug>
  handoffs: <team_memory_read section: handoffs>
  dedup_decisions: <team_memory_read section: dedup_decisions>
next_skill_hint: /compound
```

## Invariants (never violate)

- Stage members rotate per stage. Never carry a Stage 1 developer into Stage 2.
- Halt-on-blocker is strict: never run Stage 3 against a diff with unresolved Stage 2 blockers.
- Review-rework cycles capped at 2. A second oscillation always escalates to `status: blocked`.
- Every teammate calls `memory_findings_submit` before acknowledging shutdown.
- Always `TeamDelete` at the end. Leaked team scratch is a liability.
