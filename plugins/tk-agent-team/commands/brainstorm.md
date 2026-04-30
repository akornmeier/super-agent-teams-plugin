---
description: Expand a chosen idea into user stories + acceptance criteria. Pass --continue to auto-chain into /plan.
argument-hint: [--continue] <slug-or-prompt>
---

# /brainstorm

Explicit entry point for the requirements-expansion phase. Thin wrapper over the `brainstorm` skill, which converts a single chosen idea into Given/When/Then acceptance criteria a planner can design against.

## Inputs

- `$ARGUMENTS` — first token may be `--continue`. Remainder is either an ideation slug (resolved against `docs/ideation/<slug>.md`) or a freeform prompt naming the chosen idea.

## Steps

1. Parse `$ARGUMENTS`. Detect `--continue` flag.
2. Dispatch to the orchestrator agent: `Agent({subagent_type: "orchestrator", description: "Route /brainstorm", prompt: "brainstorm <parsed prompt>"})`. The orchestrator classifies against `routing.yaml`, pre-loads relevant memory, writes a brief, and either invokes the matched skill (solo `team_pattern`) or calls `TeamCreate` and spawns a `team-lead` (team `team_pattern`). It returns a structured summary with `artifact_path`, `status`, and `next_skill_hint`.
3. Branch on `status`:
   - `complete` — proceed to step 4.
   - `needs_human` / `blocked` — print reason, stop, do not chain.
4. Render handoff per policy below.

## Handoff policy (manual mode, `CHAIN=false`)

Print:

```
Requirements complete: <artifact_path>
Next: /plan <slug>   (or revise the requirements doc first)
```

## Auto-chain policy (`CHAIN=true`)

After `brainstorm` returns `status: complete`:

1. Invoke `/plan <slug>` with the requirements artifact path as input. Do **not** propagate `--continue`.
2. After plan returns, print:

   ```
   Pipeline paused at /plan.
   Review docs/plans/<slug>-plan.md, then run /work <slug> (or /plan --continue) when ready.
   ```

Rationale: the plan is the last "cheap" artifact before `/work` writes real code — re-read it before committing.

## Invariants

- Never writes files directly — only the `brainstorm` skill writes to `docs/brainstorms/`.
- Auto-chain halts on any non-`complete` status from a chained skill.

## See also

- Skill: `skills/brainstorm/SKILL.md`
- Upstream: `/ideate`
- Downstream: `/plan`
