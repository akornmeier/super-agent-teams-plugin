---
name: brainstorm
description: Use when the user has selected an idea from an ideation doc (or names a concrete feature directly) and needs it expanded into user stories and acceptance criteria. Produces `docs/brainstorms/<YYYY-MM-DD>-<slug>-requirements.md` with Given/When/Then criteria, out-of-scope, and open questions. Reads/writes all agent memory at the skill layer via MCP tools before/after subagent dispatch.
---

# brainstorm

You convert a single chosen idea into a requirements doc a planner can design against. No tradeoff scoring here — that already happened in `/ideate`. You are turning prose into testable acceptance criteria.

## Inputs you will be given

- **User prompt** (verbatim) under `## Original prompt` in the brief file.
- **Input artifact path** — a `docs/ideation/<YYYY-MM-DD>-<slug>.md` file the user picked an idea from. If none, you must extract the "selected idea" from the user prompt itself.

## Memory protocol (skill layer)

**Before dispatching:** Call these MCP tools and include the results in each subagent's prompt under `## Memory context`:
- `mcp__agent-substrate__memory_read_shared()` → include for all agents
- `mcp__agent-substrate__memory_read(agent_name="planner")` → include for planner/product dispatch

**After each subagent returns:** Parse the `## Memory findings` YAML block from the response. For each finding:
1. Call `mcp__agent-substrate__memory_append(agent_name="planner", section=finding.section, item=finding.item)`
2. If the response includes `warning`, note the family for curation
3. If the response includes `needs_curation: true`, dispatch `/memory-curate` for that family

**Important:** Subagents do NOT have MCP tool access. This skill (running in the parent session) is responsible for all memory reads before dispatch and all memory writes after each subagent returns. If a subagent returns no `## Memory findings` section, log a warning — the agent may need its prompt updated.

## Stages

### Stage 1: Load selected idea

Read the input ideation doc (if present) and pull out the idea the user named. If the prompt names an idea number (e.g. "go with idea 2") resolve against the doc's `### Idea N:` headings. If no ideation doc exists, treat the user prompt as the selected idea and note the absence of prior ideation in the artifact's `## Selected idea` section.

### Stage 2: Expand into requirements (planner/product)

1. Read memory: call `mcp__agent-substrate__memory_read_shared()` and `mcp__agent-substrate__memory_read(agent_name="planner")`.
2. Dispatch `planner/product` with the selected idea and the memory content under `## Memory context`. The planner produces:
   - **User stories** in `As a <role>, I want <capability>, so that <outcome>` form — aim for 3–7.
   - **Acceptance criteria** in `Given <state>, When <action>, Then <observable>` form — at least one per story, multiple where behavior branches.
   - **Out of scope** — explicit list of adjacent work this does NOT cover.
   - **Open questions** — items that must be answered before `/plan` can safely run.
3. Parse the `## Memory findings` YAML block from the planner's response. For each finding, call `mcp__agent-substrate__memory_append(agent_name="planner", section=finding.section, item=finding.item)`. Handle `warning` / `needs_curation` responses.

### Stage 3: Write artifact

Write `docs/brainstorms/<YYYY-MM-DD>-<slug>-requirements.md` with required sections: `## Selected idea`, `## User stories`, `## Acceptance criteria`, `## Out of scope`, `## Open questions`. Memory persistence already happened in stage 2 via `memory_append` calls.

## Write back

Canonical artifact path: `docs/brainstorms/<YYYY-MM-DD>-<slug>-requirements.md`.

```yaml
artifact_path: docs/brainstorms/<YYYY-MM-DD>-<slug>-requirements.md
status: complete          # complete | blocked | needs_human
memory_appends: [planner]
next_skill_hint: /plan
```

## Invariants (never violate)

- This skill must persist every subagent's memory findings via `memory_append` before returning. If a subagent returns no `## Memory findings` section, log a warning — the agent may need its prompt updated.
- Every user story must have at least one Given/When/Then acceptance criterion. Zero criteria = `status: blocked`.
- If `## Open questions` contains blockers that make the requirements ambiguous, return `status: needs_human` rather than proceeding.
- Never write design or implementation detail — that is `/plan`'s job. Keep the doc about *what*, not *how*.
- Never write outside `docs/brainstorms/`.
