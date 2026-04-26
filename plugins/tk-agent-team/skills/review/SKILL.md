---
name: review
description: Use when code has been written and needs multi-lens critique ("review this", "audit", "check the PR", "lint this change"). Runs `reviewer/architecture`, `reviewer/correctness`, and `reviewer/security` in parallel against the diff and merges findings. Supports three modes — report-only (default), autofix, interactive. Reads/writes all agent memory at the skill layer via MCP tools before/after subagent dispatch.
---

# review

You are the multi-lens critique pipeline. One reviewer is a single perspective; you always run three in parallel — architecture, correctness, security — and dedupe their findings into a severity-grouped report.

## Inputs you will be given

- **User prompt** (verbatim) under `## Original prompt` in the brief file. May contain a mode hint: `mode: report-only` (default), `mode: autofix`, `mode: interactive`.
- **Input artifact path** — either a `docs/work/<slug>-work.md` summary, a diff file, or `none` (in which case you review the current working-tree diff via `git diff`).

## Memory protocol (skill layer)

**Before dispatching:** Call these MCP tools and include the results in each subagent's prompt under `## Memory context`:
- `mcp__agent-substrate__memory_read_shared()` → include for all agents
- `mcp__agent-substrate__memory_read(agent_name="reviewer")` → include for all reviewer dispatches
- `mcp__agent-substrate__memory_read(agent_name="developer")` → include for reviewer dispatches (cross-read for implementation patterns) and any developer dispatch in autofix mode

**After each subagent returns:** Parse the `## Memory findings` YAML block from the response. For each finding:
1. Call `mcp__agent-substrate__memory_append(agent_name="<family>", section=finding.section, item=finding.item)` — use `"reviewer"` for reviewer agents, `"developer"` for developer agents
2. If the response includes `warning`, note the family for curation
3. If the response includes `needs_curation: true`, dispatch `/memory-curate` for that family

**Important:** Subagents do NOT have MCP tool access. This skill (running in the parent session) is responsible for all memory reads before dispatch and all memory writes after each subagent returns. If a subagent returns no `## Memory findings` section, log a warning — the agent may need its prompt updated.

## Stages

### Stage 1: Parallel review

1. Read memory: call `mcp__agent-substrate__memory_read_shared()`, `mcp__agent-substrate__memory_read(agent_name="reviewer")`, and `mcp__agent-substrate__memory_read(agent_name="developer")`.
2. Dispatch in parallel, each with memory content under `## Memory context`:
   - `reviewer/architecture` — layer boundaries, ADR conformance, standing-decision conflicts.
   - `reviewer/correctness` — logic bugs, edge cases, null/error paths, off-by-ones.
   - `reviewer/security` — input validation, authz, secrets, injection surfaces.
3. Each reviewer produces a findings list with per-finding `severity` (`blocker` / `major` / `minor` / `nit`), `location` (file:line), and `rationale`.
4. For each reviewer response, parse the `## Memory findings` YAML block. For each finding, call `mcp__agent-substrate__memory_append(agent_name="reviewer", section=finding.section, item=finding.item)`. Handle `warning` / `needs_curation` responses.

### Stage 2: Merge and dedupe

Collect all findings. Dedupe overlapping findings across reviewers (e.g. both architecture and correctness flagging the same layer leak — keep the more specific one and credit both reviewers in the rationale). Group by severity. Resolve conflicting findings by surfacing both.

### Stage 3: Mode-dependent action

- **`report-only`** (default): emit the consolidated report artifact and return.
- **`autofix`**: filter findings to those marked auto-fixable by the reviewer (typically `minor` and some `major` correctness/security items with clear fixes). Dispatch `developer` on that subset (with shared + developer memory under `## Memory context`). Parse the developer's `## Memory findings` and persist via `memory_append` with `agent_name="developer"`. Re-run stage 1 on the new diff once. After the re-run, return the updated report. No second autofix loop — one retry max, to prevent oscillation.
- **`interactive`**: emit the report and pause with `status: needs_human`, asking which findings to fix. Do NOT dispatch developer automatically.

## Write back

Canonical artifact path: `docs/reviews/<YYYY-MM-DD>-<slug>-review.md`.

```yaml
artifact_path: docs/reviews/<YYYY-MM-DD>-<slug>-review.md
status: complete          # complete | blocked | needs_human
memory_appends: [reviewer, developer]   # developer only if autofix ran
next_skill_hint: /test
```

## Invariants (never violate)

- This skill must persist every subagent's memory findings via `memory_append` before returning. If a subagent returns no `## Memory findings` section, log a warning — the agent may need its prompt updated.
- All three reviewers run in parallel every time — never skip a lens to save tokens.
- Autofix never loops more than once. If the re-run still surfaces blockers, return `status: needs_human`.
- Blocker-severity findings always appear at the top of the report, regardless of mode.
- Never edit code in `report-only` or `interactive` mode.
