---
name: compound
description: Use at the end of a full cycle (after `/ship` or `/debug`) to harvest the run into durable signal — a solution doc in `docs/solutions/<category>/` plus curated memory files. Dispatches `docs-writer` then `/memory-curate` for families near the soft limit. Reads/writes all agent memory at the skill layer via MCP tools before/after subagent dispatch.
---

# compound

You are the durability pipeline. You take the transient outputs of a cycle (code, reviews, tests, scattered memory appends) and turn them into two persistent assets: a solution doc future orchestrators will route against, and consolidated family memories that fit within their soft limits.

## Inputs you will be given

- **User prompt** (verbatim) under `## Original prompt` in the brief file.
- **Input artifact path** — the driving artifact for the cycle being compounded. Usually a `docs/ship/<slug>-ship.md` or `docs/solutions/bug-fixes/<slug>.md`. May point at a plan doc if compounding directly after `/plan`+`/work`.

## Memory protocol (skill layer)

**Before dispatching docs-writer:** Call these MCP tools and include the results in the subagent's prompt under `## Memory context`:
- `mcp__agent-substrate__memory_read_shared()` → include for all agents
- `mcp__agent-substrate__memory_read(agent_name="docs-writer")` → include for docs-writer dispatch
- Read all family memories touched during the cycle (typically `planner`, `developer`, `reviewer`, `tester`, `debugger`, `researcher`; also `design`, `framework`, `engineering`, `marketing` whenever those families were dispatched or cross-read during the cycle) via `mcp__agent-substrate__memory_read(agent_name="<family>")` for each — include all as cross-read context for docs-writer

**After docs-writer returns:** Parse the `## Memory findings` YAML block from the response. For each finding:
1. Call `mcp__agent-substrate__memory_append(agent_name="docs-writer", section=finding.section, item=finding.item)`
2. If the response includes `warning`, note the family for curation
3. If the response includes `needs_curation: true`, dispatch `/memory-curate` for that family

**For curation (stage 2):** This skill dispatches `/memory-curate` which handles its own memory read/write cycle. See the `/memory-curate` skill's memory protocol for details.

**Important:** Subagents do NOT have MCP tool access. This skill (running in the parent session) is responsible for all memory reads before dispatch and all memory writes after each subagent returns. If a subagent returns no `## Memory findings` section, log a warning — the agent may need its prompt updated.

## Stages

### Stage 1: Categorize and author solution (docs-writer)

Determine the solution category from `references/categories.md` based on the driving artifact:
- `/ship` cycles with new capability → `features`
- `/ship` cycles with structural change only → `refactors`
- `/debug` cycles → `bug-fixes` (usually already written by `/debug`; docs-writer enriches)
- Other triggers map via the descriptions in `references/categories.md`

1. Read memory: call `mcp__agent-substrate__memory_read_shared()`, `mcp__agent-substrate__memory_read(agent_name="docs-writer")`, and read all family memories touched during the cycle via `mcp__agent-substrate__memory_read(agent_name="<family>")` for each — including any of `design`, `framework`, `engineering`, `marketing` that were dispatched.
2. Dispatch `docs-writer` with the driving artifact, cycle sub-artifacts, `references/solution-schema.md`, and all memory content under `## Memory context`. Produces `docs/solutions/<category>/<YYYY-MM-DD>-<slug>.md` with sections `## Problem` + `## Root cause` (bug-fixes) **or** `## Motivation` (all other categories), `## Solution`, `## Related patterns`, `## Applies to`.
3. Parse the `## Memory findings` YAML block from the docs-writer's response. For each finding, call `mcp__agent-substrate__memory_append(agent_name="docs-writer", section=finding.section, item=finding.item)`. Handle `warning` / `needs_curation` responses.

### Stage 2: Curate memories

Enumerate every family whose memory was appended during the cycle (read `memory_findings` from each sub-skill's summary). For each family, dispatch `/memory-curate` if its memory file is near or over the soft limit. The `/memory-curate` skill handles its own memory read/write cycle (reading the current YAML, passing it to the curator subagent, then writing the curated result back) — you do not override or duplicate curation policy here.

### Stage 3: Consolidated summary

Produce a summary artifact listing: the solution doc path, the list of curated family memory files (with before/after char counts where available), and any families skipped because their memory was well under the soft limit. Confirm docs-writer's memory findings were persisted in stage 1.

## Write back

Canonical artifact path: `docs/solutions/<category>/<YYYY-MM-DD>-<slug>.md` (primary) plus `docs/compound/<YYYY-MM-DD>-<slug>-compound.md` (summary).

```yaml
artifact_path: docs/solutions/<category>/<YYYY-MM-DD>-<slug>.md
status: complete          # complete | blocked | needs_human
memory_findings: [docs-writer]
memory_curated: [planner, developer, reviewer, tester]   # actual families vary by cycle
next_skill_hint: null
```

## Invariants (never violate)

- This skill must persist every subagent's memory findings via `memory_append` before returning (`docs-writer` findings in stage 1; curation handled by `/memory-curate` in stage 2). If a subagent returns no `## Memory findings` section, log a warning — the agent may need its prompt updated.
- Solution category must come from `references/categories.md` — never invent a new category inline. If none fits, return `status: needs_human`.
- Solution doc must include every section in `references/solution-schema.md`.
- Never overwrite an existing solution doc — if the slug collides, suffix with `-v2`.
- Never skip curation on a family whose memory file is over the soft limit. Dispatch the curator even if the cycle was small.

## References

- `references/categories.md` — canonical solution categories.
- `references/solution-schema.md` — required sections for a solution doc.
