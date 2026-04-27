---
name: work
team_pattern: solo|pair
description: Use when an approved plan doc exists and the user wants code written ("implement the plan", "build phase 2", "code this up"). Parses the plan to classify frontend/backend/full-stack. Frontend-only and backend-only paths run as a `solo` developer dispatch; full-stack paths upgrade to a `pair` team where `developer-frontend` + `developer-backend` DM each other on contract questions instead of round-tripping through this skill.
---

# work

You are the implementation pipeline. The design work happened in `/plan`; you execute against a plan doc. You do not re-argue the approach — you build what it says and surface genuine blockers (missing context, contradictions between phases) if you hit them.

## Inputs you will be given

- **User prompt** (verbatim) under `## Original prompt` in the brief file.
- **Input artifact path** — a `docs/plans/<YYYY-MM-DD>-<slug>-plan.md` file. Required. Absence = `status: blocked`.

## Mode routing

This skill has two coordination shapes selected by the input scope:

| Scope | Pattern | Why |
|-------|---------|-----|
| backend-only | `solo` | Single developer dispatch; no contract negotiation needed. |
| frontend-only | `solo` | Same. |
| full-stack | `pair` | Frontend + backend developers must align on API contract, error codes, and data shape. They DM each other directly instead of round-tripping through this skill. |

The orchestrator routes via `agents/routing.yaml`'s `/work` rule (which currently declares `team_pattern: solo`); this skill upgrades to `pair` when the plan's `## Layers affected` selects full-stack. Augmentation rules (framework / design / engineering) apply on top of either mode.

Classify by parsing the plan doc's `## Layers affected`:

- **frontend-only** — only frontend layers listed → solo, dispatch `developer-frontend`.
- **backend-only** — only backend/data/infra layers listed → solo, dispatch `developer-backend`.
- **full-stack** — both listed → pair team.

Also parse `## Implementation phases` — default to executing phase 1 unless the user prompt names a specific phase (e.g. "implement phase 3").

## Memory protocol

<!-- @ref _shared/memory-protocol.md -->
<!-- @ref _shared/team-protocol.md -->

### Memory deltas for this skill

- Both modes: each developer reads `_shared` + `developer` (their own family memory) directly via MCP at task start.
- Cross-reads stay at the teammate layer per the canonical matrix: developers read `reviewer` for ADR/pattern awareness; `developer-frontend` reads `design` when the plan touches UI/a11y; `developer-backend` reads `engineering` when the plan touches deploy/infra/data/LLM; either reads `framework` when React/Vue/Astro/motion.dev signals appear.
- Pair mode: a lightweight `team-lead` is also spawned to own the shared TaskList and serialize `_shared` writes; each developer DMs the other on contract questions but neither writes to `_shared`.
- Findings submitted via `mcp__agent-substrate__memory_findings_submit({agent: "developer", ...})` per family. Each finding MUST set `item.lens: "developer-frontend"` or `item.lens: "developer-backend"` to record the running-teammate identity (supported as of v0.4 — see `_shared/findings-schema.md`).

## Workflow

### Solo workflow (backend-only OR frontend-only)

1. Read `_shared` + `developer` family memory at the skill layer only if the dispatched developer agent has not yet been migrated to direct MCP access; otherwise skip and let the developer self-load.
2. Dispatch one developer subagent (Task tool, single-shot — same shape as v0.3) with the brief and the active phase's files/modules/tests scoped from `## Layers affected`.
3. The subagent has direct MCP access if the renamed agent (per Task 5's reviewer-update pattern) has `mcp__agent-substrate__*` in its `tools` allowlist applied to developer agents the same way. If that update has been done, the subagent reads memory and submits findings directly via `memory_findings_submit`. If not, this skill calls `memory_findings_submit` from the parent on the subagent's behalf as a v0.4 transitional broker (legacy prose `## Memory findings` block parsing remains a grandfathered fallback per `_shared/memory-protocol.md#findings-deprecated`).
4. Receive structured summary; persist findings if needed; return.

This is the only place in v0.4 where the parent-broker pattern survives — for solo dispatches that don't need a team. Documented in `_shared/team-protocol.md#pattern-solo`.

### Pair workflow (full-stack)

1. Compute `team_slug` from the plan slug: lowercase-kebab, max 32 chars (e.g. `work-user-profiles`).
2. `TeamCreate({team_name: "work-<slug>", description: "Full-stack work: <prompt-excerpt>"})`.
3. Spawn the lightweight `team-lead` first. It owns the TaskList and serializes `_shared` writes.
4. Spawn the pair concurrently (one message, parallel) and create one TaskList task per developer:
   - `Agent({subagent_type: "Frontend Developer", name: "developer-frontend", team_name: "work-<slug>", prompt: "<see step 5>", run_in_background: true})` + `TaskCreate({subject: "Frontend implementation", description: "<frontend layer items>", owner: "developer-frontend"})`
   - `Agent({subagent_type: "Backend Architect", name: "developer-backend", team_name: "work-<slug>", prompt: "<see step 5>", run_in_background: true})` + `TaskCreate({subject: "Backend implementation", description: "<backend layer items>", owner: "developer-backend"})`
5. Each developer's prompt MUST include `## Team coordination context` with their own `taskId` AND the peer's `taskId`, per `_shared/team-protocol.md#taskid-threading`. The peer-DM pattern only works if each developer can address the other.
6. Developers DM on contract questions:
   - `SendMessage({team_name: "work-<slug>", to: "developer-backend", from: "developer-frontend", body: {type: "contract_question", topic: "API shape for /users", body: "<details>"}})`
   - The other responds via `SendMessage` reply.
   - Decisions are recorded in team scratch via `mcp__agent-substrate__team_memory_append({team_name: "work-<slug>", section: "decisions", item: {...}})` so the artifact captures what was agreed.
7. Each developer submits findings to `mcp__agent-substrate__memory_findings_submit({agent: "developer", findings: [...]})` BEFORE acknowledging shutdown, per the schema in `_shared/findings-schema.md`.
8. Team-lead sends `shutdown_request` to both developers, waits for idle (60s grace per `_shared/team-protocol.md#shutdown-invariants`), then `TeamDelete({team_name: "work-<slug>"})`.

### Pair rules (load-bearing)

- Both developers run concurrently. Neither blocks on the other except via DM.
- The pair is symmetric — neither developer is the lead. Either may initiate a contract question.
- Cross-layer contracts live in the plan's `## Data-model changes` and are treated as read-only by both — DMs negotiate ambiguity, not the contract itself.
- If a contract question takes more than 3 DM round-trips to resolve, escalate to the parent skill (or to `team-lead`) — that's a sign the input scope wasn't sliced cleanly.
- Pair team-lead is *lightweight*: it owns TaskList + `_shared` write serialization, but it does NOT do code review (that's `/review`'s job after `/work` returns).

## Write back

Canonical artifact path: `docs/work/<YYYY-MM-DD>-<slug>-work.md` (short status summary; the diff itself lives in the working tree).

```yaml
artifact_path: docs/work/<YYYY-MM-DD>-<slug>-work.md
status: complete          # complete | blocked | needs_human
memory_findings: [developer]
next_skill_hint: /review
```

Pair mode adds `team_summary.contract_decisions` reading from the team scratch (`team_memory_read({team_name: "work-<slug>"})`, `decisions` section) so downstream skills see what was negotiated.

## Invariants (never violate)

- Never proceed without a plan doc. Absence is an immediate blocker.
- Never modify the plan doc mid-implementation — if the plan is wrong, return `status: needs_human` with the contradiction named.
- Solo dispatches MUST NOT call `TeamCreate`. Pair dispatches MUST.
- Pair developers run concurrently. Serial execution is only acceptable when the plan explicitly calls out a frontend-blocks-on-backend dependency in `## Implementation phases`.
- Every developer's findings persist via `memory_findings_submit` before shutdown is acknowledged (pair) or before this skill returns (solo). Silent loss contradicts the plugin's compound-knowledge thesis.
- Pair mode always `TeamDelete`s at the end. Leaked team scratch is a liability.
- Never commit — `/work` leaves changes staged-or-unstaged for the user to review.
