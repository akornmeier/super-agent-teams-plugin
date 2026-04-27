---
name: review
team_pattern: parallel-panel
description: Use when code has been written and needs multi-lens critique ("review this", "audit", "check the PR", "lint this change"). Creates a `parallel-panel` review team with three named teammates (`reviewer-architecture`, `reviewer-correctness`, `reviewer-security`) that read memory directly, DM each other to dedupe overlapping findings, and submit findings via `memory_findings_submit`. Supports three modes — report-only (default), autofix, interactive.
---

# review

You are the multi-lens critique pipeline. One reviewer is a single perspective; you always run three in parallel — architecture, correctness, security — and dedupe their findings into a severity-grouped report. In v0.4 the three reviewers are real named teammates in a `parallel-panel` team, not one-shot subagents.

## Inputs you will be given

- **User prompt** (verbatim) under `## Original prompt` in the brief file. May contain a mode hint: `mode: report-only` (default), `mode: autofix`, `mode: interactive`.
- **Input artifact path** — either a `docs/work/<slug>-work.md` summary, a diff file, or `none` (in which case the team reviews the current working-tree diff via `git diff`).
- **Single file path** (e.g., `tests/fixtures/review-dedup/auth.py`) — the skill computes the diff via `git diff HEAD~1 -- <path>`. If the file is untracked (new), the entire file is treated as additions. Useful for `/review <fixture-or-test-file>` invocations.

## Memory protocol

<!-- @ref _shared/memory-protocol.md -->
<!-- @ref _shared/team-protocol.md -->

This skill follows the canonical memory and team protocols. Three reviewer teammates spawned by this skill each read `_shared` + `reviewer` directly via `mcp__agent-substrate__memory_read*` and submit findings via `mcp__agent-substrate__memory_findings_submit`. The skill no longer brokers memory — it is a team factory.

## Workflow

### Stage 1 — team creation

1. Compute `team_slug` from the prompt: lowercase-kebab-case, max 32 chars (e.g. `review-pr-auth-cleanup`).
2. Call `TeamCreate({team_name: "review-<slug>", description: "Review for: <prompt-excerpt>"})`.
3. Spawn three teammates concurrently via three `Agent` calls (one message, parallel) with these fields:
   - `Agent({subagent_type: "Code Reviewer", name: "reviewer-architecture", team_name: "review-<slug>", prompt: "<see Stage 2>", run_in_background: true})`
   - `Agent({subagent_type: "Code Reviewer", name: "reviewer-correctness", team_name: "review-<slug>", prompt: "<see Stage 2>", run_in_background: true})`
   - `Agent({subagent_type: "Security Engineer", name: "reviewer-security", team_name: "review-<slug>", prompt: "<see Stage 2>", run_in_background: true})`
4. For each teammate, also call `TaskCreate({subject: "Review <lens>", description: "<diff scope>", owner: "reviewer-<lens>"})` so the team's TaskList tracks per-lens progress.

### Stage 2 — concurrent review

Each teammate's prompt body must instruct them to:

1. Call `mcp__agent-substrate__memory_read_shared()` and `mcp__agent-substrate__memory_read(agent_name="reviewer")` directly. (Cross-reads to `developer`, `framework`, etc., per the deltas section below.)
2. Review the diff scope through their lens (architecture / correctness / security).
3. **Peer dedup loop:** Before finalizing a finding, call `TaskList()` to see what peers are working on. If a finding overlaps a peer's scope (e.g. correctness finds a hard-coded credential that security would also flag), `SendMessage({to: "reviewer-<peer>", message: {type: "potential_overlap", finding_summary: "<one-line>"}})` to negotiate. Whoever has the more specific lens keeps it; the other defers. Document this peer-DM in the team scratch via `team_memory_append({team_name, section: "dedup_decisions", item: {...}})`. The `dedup_decisions` section name is canonical per the team-memory section taxonomy in `_shared/team-protocol.md#team-memory-section-taxonomy` (the `decisions` section is reserved for durable team-coordination outcomes, not peer-DM dedup outcomes).
4. Submit findings via `mcp__agent-substrate__memory_findings_submit(agent="reviewer", findings=[...])` per the schema in `_shared/findings-schema.md`. The `agent` argument is the **family slug** `"reviewer"` (NOT your running-teammate name `reviewer-<lens>`); all three reviewers submit under the same family so the consolidated `reviewer.yaml` accumulates findings from every lens in one file. Populate `item.lens: "reviewer-<your-lens>"` (e.g., `"reviewer-architecture"`, `"reviewer-correctness"`, `"reviewer-security"`) on each finding so post-hoc audit can recover which lens flagged what. Supported as of v0.4.
5. Call `TaskUpdate({taskId: <my-task>, status: "completed"})` when done.

### Stage 3 — consolidation and shutdown

1. Wait for all three teammate tasks to be `completed` (poll TaskList; finishing-time is determined by all three Agent calls returning).
2. Read consolidated findings: each teammate already submitted via `memory_findings_submit`; the parent reads back via `mcp__agent-substrate__memory_read(agent_name="reviewer")` to assemble the final report. Also read `mcp__agent-substrate__team_memory_read({team_name: "review-<slug>"})` to surface peer-DM decisions in the report.
3. Apply mode logic per the existing skill body:
   - **`report-only`** (default): emit the consolidated report artifact and proceed to shutdown.
   - **`autofix`**: filter findings to those marked auto-fixable (typically `minor` and some `major` correctness/security items). Dispatch a `developer-backend` teammate into the same team via one additional `Agent({team_name: "review-<slug>", name: "developer-backend", ...})`. They submit via `memory_findings_submit` with `agent: "developer"`. Re-run a single delta review pass over the new diff (do not respawn all three reviewers — DM the existing teammates with the new diff scope and a fresh TaskCreate). One retry max, no second autofix loop.
   - **`interactive`**: emit the report and pause with `status: needs_human` before shutdown. Resume on user response.
4. Send `shutdown_request` to all teammates: for each, `SendMessage({to: "reviewer-<lens>", message: {type: "shutdown_request"}})` (and `developer-backend` if autofix ran). Verify TaskList is fully drained first per `_shared/team-protocol.md` shutdown invariants. Wait for them to go idle.
5. Call `TeamDelete({team_name: "review-<slug>"})` to clean up the team-scratch namespace.

### Stage 4 — write back

Canonical artifact path: `docs/reviews/<YYYY-MM-DD>-<slug>-review.md`. Output schema unchanged:

```yaml
artifact_path: docs/reviews/<YYYY-MM-DD>-<slug>-review.md
status: complete          # complete | blocked | needs_human
memory_findings: [reviewer, developer]   # developer only if autofix ran
next_skill_hint: /test
```

### Memory deltas for this skill

- Each reviewer reads `_shared` + `reviewer` always.
- `reviewer-architecture` and `reviewer-correctness` read `framework` if the diff touches React/Vue/Astro/motion.dev. (Diff-scan logic stays in the teammate prompts — they have direct MCP access to do this.)
- `reviewer-architecture` reads `design` if diff touches UI/a11y.
- `reviewer-architecture` and `reviewer-security` read `engineering` if diff touches deploy/infra/data/LLM.
- All three submit findings as `agent: "reviewer"` (the family) — finer-grained `reviewer-architecture` etc. are the running teammate identities, but findings are persisted at family level so they show up in the consolidated `reviewer.yaml`.

## Invariants (never violate)

- All three reviewers run concurrently every time. Never skip a lens to save tokens.
- Autofix never loops more than once.
- Blocker-severity findings always appear at the top of the report.
- Never edit code in `report-only` or `interactive` mode.
- Always `TeamDelete` at the end. Leaked team scratch is a liability.
