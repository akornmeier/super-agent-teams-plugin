---
name: plan
description: Use when requirements exist (from `/brainstorm`) or the user asks for a technical design, ADR, or implementation plan. Produces `docs/plans/<YYYY-MM-DD>-<slug>-plan.md` conforming to `references/plan-schema.md`, reviewed once by `reviewer/architecture` for standing-decision conflicts. Reads/writes all agent memory at the skill layer via MCP tools before/after subagent dispatch.
---

# plan

You turn requirements into an implementable technical plan. You are not writing code and not picking ideas — those happened upstream. You *are* naming layers, data model changes, migrations, and risks concretely enough that `/work` can execute without asking follow-up questions.

## Inputs you will be given

- **User prompt** (verbatim) under `## Original prompt` in the brief file.
- **Input artifact path** — a `docs/brainstorms/<YYYY-MM-DD>-<slug>-requirements.md` file. If none, you must synthesize implicit requirements from the prompt and call that out in `## Context`.

## Memory protocol (skill layer)

**Before dispatching:** Call these MCP tools and include the results in each subagent's prompt under `## Memory context`:
- `mcp__agent-substrate__memory_read_shared()` → include for all agents
- `mcp__agent-substrate__memory_read(agent_name="planner")` → include for planner/technical dispatches
- `mcp__agent-substrate__memory_read(agent_name="reviewer")` → include for reviewer/architecture dispatch (and cross-read for planner so it knows standing decisions/ADRs)
- `mcp__agent-substrate__memory_read(agent_name="framework")` → include when the requirements / prompt mentions React, Vue, Astro, or motion.dev. Skip otherwise.
- `mcp__agent-substrate__memory_read(agent_name="design")` → include when the requirements involve UI surfaces, design systems, or accessibility commitments.
- `mcp__agent-substrate__memory_read(agent_name="engineering")` → include when the requirements involve deployment, observability, data pipelines, or LLM/RAG work.

**After each subagent returns:** Parse the `## Memory findings` YAML block from the response. For each finding:
1. Call `mcp__agent-substrate__memory_append(agent_name="<family>", section=finding.section, item=finding.item)`
2. If the response includes `warning`, note the family for curation
3. If the response includes `needs_curation: true`, dispatch `/memory-curate` for that family

**Important:** Subagents do NOT have MCP tool access. This skill (running in the parent session) is responsible for all memory reads before dispatch and all memory writes after each subagent returns. If a subagent returns no `## Memory findings` section, log a warning — the agent may need its prompt updated.

## Stages

### Stage 1: Draft (planner/technical)

1. Read memory: call `mcp__agent-substrate__memory_read_shared()`, `mcp__agent-substrate__memory_read(agent_name="planner")`, and `mcp__agent-substrate__memory_read(agent_name="reviewer")`. Then conditionally call `memory_read` for `framework`, `design`, and/or `engineering` based on the signals in the requirements doc / prompt.
2. Dispatch `planner/technical` with the requirements doc and memory content under `## Memory context` (include shared, planner, and reviewer memories so the planner knows standing decisions). The planner drafts against `references/plan-schema.md` — every required section must be populated or explicitly marked `N/A (reason)`. The draft is written to the artifact path in full before stage 2 begins.
3. Parse the `## Memory findings` YAML block from the planner's response. For each finding, call `mcp__agent-substrate__memory_append(agent_name="planner", section=finding.section, item=finding.item)`. Handle `warning` / `needs_curation` responses.

### Stage 2: Architecture review (reviewer/architecture)

1. Dispatch `reviewer/architecture` with the draft plan and memory content under `## Memory context` (include shared and reviewer memories). The reviewer flags:
   - Conflicts with standing decisions / protected memory items (ADRs).
   - Missing migration or rollback detail.
   - Layer-boundary violations implied by the plan.
2. Parse the `## Memory findings` YAML block from the reviewer's response. For each finding, call `mcp__agent-substrate__memory_append(agent_name="reviewer", section=finding.section, item=finding.item)`. Handle `warning` / `needs_curation` responses.

Output is a findings list — blockers vs. advisories — handed to stage 3.

### Stage 3: Revise and finalize (planner/technical)

1. Dispatch `planner/technical` again with the findings list and memory content under `## Memory context`. All blockers must be resolved (by changing the plan OR by explicitly overriding a standing decision with justification in `## Risks`). Advisories may be addressed or acknowledged. Write final plan to `docs/plans/<YYYY-MM-DD>-<slug>-plan.md`.
2. Parse the `## Memory findings` YAML block from the planner's response. For each finding, call `mcp__agent-substrate__memory_append(agent_name="planner", section=finding.section, item=finding.item)`. Handle `warning` / `needs_curation` responses.

## Write back

Canonical artifact path: `docs/plans/<YYYY-MM-DD>-<slug>-plan.md`.

```yaml
artifact_path: docs/plans/<YYYY-MM-DD>-<slug>-plan.md
status: complete          # complete | blocked | needs_human
memory_findings: [planner, reviewer]
next_skill_hint: /work
```

## Invariants (never violate)

- This skill must persist every subagent's memory findings via `memory_append` before returning. If a subagent returns no `## Memory findings` section, log a warning — the agent may need its prompt updated.
- Every section in `references/plan-schema.md` must be present. Missing = `status: blocked`.
- Blocker-severity findings from stage 2 must be resolved or explicitly overridden with justification — never silently ignored.
- Never include code diffs — the plan names files/functions, not implementations.
- Never write outside `docs/plans/`.

## References

- `references/plan-schema.md` — required sections a valid plan doc must contain.
