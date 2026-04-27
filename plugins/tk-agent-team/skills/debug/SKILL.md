---
name: debug
description: Use when a bug, stack trace, failing test, or regression is reported ("X is broken", "crash on Y", "failing since Z"). Runs researcher → debugger → reviewer/correctness → developer, then writes the fix as a durable `docs/solutions/bug-fixes/<YYYY-MM-DD>-<slug>.md` entry that feeds `/compound`. Reads/writes all agent memory at the skill layer via MCP tools before/after subagent dispatch.
---

# debug

You are the root-cause pipeline. You do not guess — you reproduce, hypothesize, validate, fix, and record. The bug-fix doc you write is a durable signal future orchestrator routing relies on.

## Inputs you will be given

- **User prompt** (verbatim) under `## Original prompt` in the brief file — typically contains a stack trace, error message, or repro steps.
- **Input artifact path** — usually `none`. May point at a previous `docs/solutions/bug-fixes/` entry if this is a re-occurrence.

## Memory protocol (skill layer)

**Before dispatching:** Call these MCP tools and include the results in each subagent's prompt under `## Memory context`:
- `mcp__agent-substrate__memory_read_shared()` → include for all agents
- `mcp__agent-substrate__memory_read(agent_name="researcher")` → include for researcher dispatch
- `mcp__agent-substrate__memory_read(agent_name="debugger")` → include for debugger dispatch
- `mcp__agent-substrate__memory_read(agent_name="reviewer")` → include for reviewer/correctness dispatch
- `mcp__agent-substrate__memory_read(agent_name="developer")` → include for developer dispatch

**After each subagent returns:** Parse the `## Memory findings` YAML block from the response. For each finding:
1. Call `mcp__agent-substrate__memory_append(agent_name="<family>", section=finding.section, item=finding.item)` — use the appropriate family for each agent
2. If the response includes `warning`, note the family for curation
3. If the response includes `needs_curation: true`, dispatch `/memory-curate` for that family

**Important:** Subagents do NOT have MCP tool access. This skill (running in the parent session) is responsible for all memory reads before dispatch and all memory writes after each subagent returns. If a subagent returns no `## Memory findings` section, log a warning — the agent may need its prompt updated.

## Stages

### Stage 1: Context brief (researcher)

1. Read memory: call `mcp__agent-substrate__memory_read_shared()` and `mcp__agent-substrate__memory_read(agent_name="researcher")`.
2. Dispatch `researcher` with the prompt + stack trace and memory content under `## Memory context`. Returns: which files/modules the symptom touches, git blame on relevant lines, related prior `docs/solutions/bug-fixes/*` entries (for near-duplicates).
3. Parse the `## Memory findings` YAML block from the researcher's response. For each finding, call `mcp__agent-substrate__memory_append(agent_name="researcher", section=finding.section, item=finding.item)`. Handle `warning` / `needs_curation` responses.

### Stage 2: Reproduction + hypothesis (debugger)

1. Read memory: call `mcp__agent-substrate__memory_read(agent_name="debugger")`.
2. Dispatch `debugger` with the researcher's brief and memory content under `## Memory context`. Produces:
   - A deterministic reproduction (minimal repro script, failing-test stub, or exact command).
   - A root-cause hypothesis with evidence (file:line, variable state, sequence of events).
   - A proposed fix direction (not the fix itself).
3. Parse the `## Memory findings` YAML block from the debugger's response. For each finding, call `mcp__agent-substrate__memory_append(agent_name="debugger", section=finding.section, item=finding.item)`. Handle `warning` / `needs_curation` responses.

### Stage 3: Hypothesis validation (reviewer/correctness)

1. Read memory: call `mcp__agent-substrate__memory_read(agent_name="reviewer")`.
2. Dispatch `reviewer/correctness` with the hypothesis, the code under suspicion, and memory content under `## Memory context`. Confirms or refutes. If refuted, loop back to stage 2 once with the refutation evidence. Second refutation = `status: needs_human`.
3. Parse the `## Memory findings` YAML block from the reviewer's response. For each finding, call `mcp__agent-substrate__memory_append(agent_name="reviewer", section=finding.section, item=finding.item)`. Handle `warning` / `needs_curation` responses.

### Stage 4: Fix (developer)

1. Read memory: call `mcp__agent-substrate__memory_read(agent_name="developer")`.
2. Dispatch `developer` (frontend or backend per the affected layer) with the validated hypothesis, proposed direction, and memory content under `## Memory context`. Developer writes the fix and a regression test covering the repro from stage 2.
3. Parse the `## Memory findings` YAML block from the developer's response. For each finding, call `mcp__agent-substrate__memory_append(agent_name="developer", section=finding.section, item=finding.item)`. Handle `warning` / `needs_curation` responses.

### Stage 5: Record solution

Write `docs/solutions/bug-fixes/<YYYY-MM-DD>-<slug>.md` with the canonical solution schema: `## Problem`, `## Root cause`, `## Solution`, `## Related patterns`, `## Applies to`. Memory persistence already happened in stages 1-4 via `memory_append` calls.

## Write back

Canonical artifact path: `docs/solutions/bug-fixes/<YYYY-MM-DD>-<slug>.md`.

```yaml
artifact_path: docs/solutions/bug-fixes/<YYYY-MM-DD>-<slug>.md
status: complete          # complete | blocked | needs_human
memory_findings: [researcher, debugger, reviewer, developer]
next_skill_hint: /compound
```

## Invariants (never violate)

- This skill must persist every subagent's memory findings via `memory_append` before returning — `debugger` pitfall patterns are especially important. If a subagent returns no `## Memory findings` section, log a warning — the agent may need its prompt updated.
- Never skip the reproduction step. A fix without a repro = `status: blocked`.
- Never ship a fix without a regression test covering the stage-2 repro.
- Loop back from stage 3 to stage 2 at most once. Second hypothesis refutation = `needs_human`.
- Always write the solution doc, even if the fix is one line — the durability of the record is the point.
