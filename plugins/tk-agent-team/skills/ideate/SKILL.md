---
name: ideate
description: Use when the user asks to explore options, brainstorm directions, or propose approaches for a fuzzy problem ("what could we do about X", "propose", "spitball", "ideas for"). Produces a ranked set of 3–5 scored ideas in `docs/ideation/<YYYY-MM-DD>-<slug>.md` with tradeoffs and a recommendation. Reads/writes all agent memory at the skill layer via MCP tools before/after subagent dispatch.
---

# ideate

You are the divergent-exploration pipeline. Your job is to take a fuzzy prompt, gather just enough prior art to avoid reinventing wheels, and return 3–5 well-scored ideas the user can pick from. You do not implement anything and you do not pick a single winner for the user — you rank and recommend.

## Inputs you will be given

- **User prompt** (verbatim) under `## Original prompt` in the brief file.
- **Input artifact path** — usually `none` for `/ideate`. If present, it will point at a `docs/solutions/` entry the user wants riffed on.

## Memory protocol (skill layer)

**Before dispatching:** Call these MCP tools and include the results in each subagent's prompt under `## Memory context`:
- `mcp__agent-substrate__memory_read_shared()` → include for all agents
- `mcp__agent-substrate__memory_read(agent_name="researcher")` → include for researcher dispatch
- `mcp__agent-substrate__memory_read(agent_name="planner")` → include for planner/product dispatch (and cross-read researcher context)

**After each subagent returns:** Parse the `## Memory findings` YAML block from the response. For each finding:
1. Call `mcp__agent-substrate__memory_append(agent_name="<family>", section=finding.section, item=finding.item)`
2. If the response includes `warning`, note the family for curation
3. If the response includes `needs_curation: true`, dispatch `/memory-curate` for that family

**Important:** Subagents do NOT have MCP tool access. This skill (running in the parent session) is responsible for all memory reads before dispatch and all memory writes after each subagent returns. If a subagent returns no `## Memory findings` section, log a warning — the agent may need its prompt updated.

## Stages

Run in order. Do not skip — each stage's output is the next stage's input.

### Stage 1: Context brief (researcher)

1. Read memory: call `mcp__agent-substrate__memory_read_shared()` and `mcp__agent-substrate__memory_read(agent_name="researcher")`.
2. Dispatch the `researcher` agent with the user prompt, any input artifact, and the memory content under `## Memory context` in the prompt. The researcher reads `docs/solutions/*` for prior art, greps the repo for adjacent code, and returns a short context brief: constraints, existing patterns, closest-prior-art solution slugs. The brief is written inline into the working scratch for stage 2 — do not create a standalone file.
3. Parse the `## Memory findings` YAML block from the researcher's response. For each finding, call `mcp__agent-substrate__memory_append(agent_name="researcher", section=finding.section, item=finding.item)`. Handle `warning` / `needs_curation` responses.

### Stage 2: Idea generation and scoring (planner/product)

1. Read memory: call `mcp__agent-substrate__memory_read(agent_name="planner")` (and re-use the shared memory from stage 1).
2. Dispatch `planner/product` with the user prompt, the researcher's context brief, and the memory content under `## Memory context`. The planner generates 3–5 candidate ideas. For each idea, score against `references/rubric.md` (dimensions: user-value×3, engineering-cost×2 inverted, reversibility×2, alignment-with-memory×2; normalize 0–10). Emit a table of ideas with `**Value**`, `**Cost**`, `**Tradeoff**`, `**Score**` per the `docs/ideation/` schema.
3. Parse the `## Memory findings` YAML block from the planner's response. For each finding, call `mcp__agent-substrate__memory_append(agent_name="planner", section=finding.section, item=finding.item)`. Handle `warning` / `needs_curation` responses.

### Stage 3: Write artifact

Write `docs/ideation/<YYYY-MM-DD>-<slug>.md` with required sections: `## Context`, `## Ideas` (one `### Idea N: <title>` per idea with the four fields), `## Recommendation` (the highest-scored idea; tie-break per rubric — higher reversibility, then lower cost), `## Open questions`. Memory persistence already happened in stages 1 and 2 via `memory_append` calls.

## Write back

Canonical artifact path: `docs/ideation/<YYYY-MM-DD>-<slug>.md`.

Return this structured summary:

```yaml
artifact_path: docs/ideation/<YYYY-MM-DD>-<slug>.md
status: complete          # complete | blocked | needs_human
memory_appends: [planner, researcher]
next_skill_hint: /brainstorm
```

## Invariants (never violate)

- This skill must persist every subagent's memory findings via `memory_append` before returning. If a subagent returns no `## Memory findings` section, log a warning — the agent may need its prompt updated.
- Always produce between 3 and 5 ideas. Fewer is a blocker (`status: blocked`, explain why in the artifact).
- Never collapse scoring into a gut-feel ranking — use `references/rubric.md` weights verbatim.
- Never implement or plan — if the prompt is concrete enough to skip ideation, return `status: needs_human` with a hint to use `/plan` directly.
- Never write outside `docs/ideation/`.

## References

- `references/rubric.md` — scoring weights and tie-break rules.
