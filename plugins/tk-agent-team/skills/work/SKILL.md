---
name: work
description: Use when an approved plan doc exists and the user wants code written ("implement the plan", "build phase 2", "code this up"). Parses the plan to classify frontend/backend/full-stack, dispatches the matching `developer/*` persona(s) in parallel where independent, and returns a summary of diffs. Reads/writes all agent memory at the skill layer via MCP tools before/after subagent dispatch.
---

# work

You are the implementation pipeline. The design work happened in `/plan`; you execute against a plan doc. You do not re-argue the approach — you build what it says and surface genuine blockers (missing context, contradictions between phases) if you hit them.

## Inputs you will be given

- **User prompt** (verbatim) under `## Original prompt` in the brief file.
- **Input artifact path** — a `docs/plans/<YYYY-MM-DD>-<slug>-plan.md` file. Required. Absence = `status: blocked`.

## Memory protocol (skill layer)

**Before dispatching:** Call these MCP tools and include the results in each subagent's prompt under `## Memory context`:
- `mcp__agent-substrate__memory_read_shared()` → include for all agents
- `mcp__agent-substrate__memory_read(agent_name="developer")` → include for all developer dispatches
- `mcp__agent-substrate__memory_read(agent_name="reviewer")` → include for developer dispatches (cross-read for ADR/pattern awareness)
- `mcp__agent-substrate__memory_read(agent_name="framework")` → include when the plan's `## Tech stack` or `## Layers affected` mentions React, Vue, Astro, or motion.dev / Framer Motion. Skip otherwise.
- `mcp__agent-substrate__memory_read(agent_name="design")` → include for `developer/frontend` dispatches when the plan touches UI components, design tokens, or accessibility-sensitive surfaces.
- `mcp__agent-substrate__memory_read(agent_name="engineering")` → include for `developer/backend` dispatches when the plan touches deployment, observability, data pipelines, or LLM/RAG integrations.

**After each subagent returns:** Parse the `## Memory findings` YAML block from the response. For each finding:
1. Call `mcp__agent-substrate__memory_append(agent_name="developer", section=finding.section, item=finding.item)`
2. If the response includes `warning`, note the family for curation
3. If the response includes `needs_curation: true`, dispatch `/memory-curate` for that family

**Important:** Subagents do NOT have MCP tool access. This skill (running in the parent session) is responsible for all memory reads before dispatch and all memory writes after each subagent returns. If a subagent returns no `## Memory findings` section, log a warning — the agent may need its prompt updated.

## Stages

### Stage 1: Classify the plan

Parse the plan doc's `## Layers affected` section. Classify:
- **frontend-only** — only frontend layers listed. Dispatch `developer/frontend`.
- **backend-only** — only backend/data/infra layers listed. Dispatch `developer/backend`.
- **full-stack** — both listed. Fork both personas in parallel, each scoped to their respective layer items from the plan.

Also scan the plan for cross-cutting specialist signals to decide which augmentation memories to cross-read in stage 2:
- Framework signals (React, Vue, Astro, motion.dev, Framer Motion, hooks, server components) → cross-read `framework`.
- Design signals (component library, design tokens, ARIA, accessibility) → cross-read `design` for `developer/frontend`.
- Engineering signals (deploy, container, SLO, observability, pipeline, embeddings, RAG) → cross-read `engineering` for `developer/backend`.

Also parse `## Implementation phases` — if the plan has phases, default to executing phase 1 unless the user prompt names a specific phase (e.g. "implement phase 3").

### Stage 2: Dispatch developer(s)

1. Read memory: call `mcp__agent-substrate__memory_read_shared()`, `mcp__agent-substrate__memory_read(agent_name="developer")`, and `mcp__agent-substrate__memory_read(agent_name="reviewer")`. Then conditionally call `memory_read` for `framework`, `design`, and/or `engineering` based on the signals detected in stage 1.
2. Dispatch the chosen `developer/*` persona(s). Each receives:
   - The full plan doc path.
   - Its subset of `## Layers affected` items and the active phase's files/modules/tests.
   - The memory content under `## Memory context` in the prompt.
3. Developers produce real code diffs against the working tree. In full-stack mode, the two personas run in parallel but must not touch each other's layer files — cross-layer contracts live in the plan's `## Data-model changes` and are treated as read-only by both.

### Stage 3: Collect diffs and persist memory

Collect the diffs from all dispatches. For each developer subagent response:
1. Parse the `## Memory findings` YAML block. For each finding, call `mcp__agent-substrate__memory_append(agent_name="developer", section=finding.section, item=finding.item)`. Handle `warning` / `needs_curation` responses.
2. Produce a summary artifact listing files changed, tests added, and any deviations from the plan (with justification). The artifact is a short status file — the *real* output is the working-tree diff.

## Write back

Canonical artifact path: `docs/work/<YYYY-MM-DD>-<slug>-work.md` (short status summary; the diff itself lives in the working tree).

```yaml
artifact_path: docs/work/<YYYY-MM-DD>-<slug>-work.md
status: complete          # complete | blocked | needs_human
memory_appends: [developer]
next_skill_hint: /review
```

## Invariants (never violate)

- This skill must persist every subagent's memory findings via `memory_append` before returning. If a subagent returns no `## Memory findings` section, log a warning — the agent may need its prompt updated.
- Never proceed without a plan doc. Absence is an immediate blocker.
- Never modify the plan doc mid-implementation — if the plan is wrong, return `status: needs_human` with the contradiction named.
- Full-stack dispatches must run in parallel; serial execution is only acceptable when the plan explicitly calls out a frontend-blocks-on-backend dependency in `## Implementation phases`.
- Never commit — `/work` leaves changes staged-or-unstaged for the user to review.
