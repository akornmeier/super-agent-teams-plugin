---
description: Ship the change — commit, push, PR. Terminal phase of the build pipeline.
argument-hint: [--continue] <slug-or-prompt>
---

# /ship

Explicit entry point for the shipping phase. Thin wrapper over the `ship` skill, which commits the change and produces a ship record in `docs/ship/`.

## Inputs

- `$ARGUMENTS` — first token may be `--continue`. Remainder is a test slug (resolved against `docs/tests/<slug>-test-report.md`) or a freeform ship prompt.

## Steps

1. Parse `$ARGUMENTS`. Detect `--continue` flag.
2. Dispatch to the orchestrator agent: `Agent({subagent_type: "orchestrator", description: "Route /ship", prompt: "<parsed prompt>"})`. The orchestrator classifies against `routing.yaml`, pre-loads relevant memory, writes a brief, and either invokes the matched skill (solo `team_pattern`) or calls `TeamCreate` and spawns a `team-lead` (team `team_pattern`). It returns a structured summary with `artifact_path`, `status`, and `next_skill_hint`.
3. Branch on `status`:
   - `complete` — proceed to step 4.
   - `needs_human` / `blocked` — print reason, stop.
4. Render handoff per policy below.

## Handoff policy (manual mode, `CHAIN=false`)

Print:

```
Ship complete: <artifact_path>
Cycle finished. Run /compound to start a new end-to-end cycle, or pick a new /ideate topic.
```

## Auto-chain policy (`CHAIN=true`)

`/ship --continue` is a **no-op chain** — ship is the terminal phase of the build pipeline. The skill's `next_skill_hint: /compound` is not auto-invoked because `/compound` starts a *new* cradle-to-grave cycle, which should always be a deliberate user choice.

If `--continue` is passed, run ship normally and print:

```
Ship complete: <artifact_path>
--continue is a no-op at the terminal phase. Run /compound to start a fresh cycle.
```

## Invariants

- Never writes files directly — only the `ship` skill writes to `docs/ship/` (and creates commits/PRs via git/gh).
- `--continue` does NOT auto-invoke `/compound`. New cycles are always explicit.

## See also

- Skill: `skills/ship/SKILL.md`
- Upstream: `/test`
- Loop: `/compound` (deliberate cradle-to-grave restart)
