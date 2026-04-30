---
description: Execute an implementation plan — writes real code. Pass --continue to auto-chain into /review.
argument-hint: [--continue] <slug-or-prompt>
---

# /work

Explicit entry point for the implementation phase. Thin wrapper over the `work` skill, which executes a plan and produces a work record in `docs/work/`.

## Inputs

- `$ARGUMENTS` — first token may be `--continue`. Remainder is a plan slug (resolved against `docs/plans/<slug>-plan.md`) or a freeform implementation prompt.

## Steps

1. Parse `$ARGUMENTS`. Detect `--continue` flag.
2. Dispatch to the orchestrator agent: `Agent({subagent_type: "orchestrator", description: "Route /work", prompt: "<parsed prompt>"})`. The orchestrator classifies against `routing.yaml`, pre-loads relevant memory, writes a brief, and either invokes the matched skill (solo `team_pattern`) or calls `TeamCreate` and spawns a `team-lead` (team `team_pattern`). It returns a structured summary with `artifact_path`, `status`, and `next_skill_hint`.
3. Branch on `status`:
   - `complete` — proceed to step 4.
   - `needs_human` / `blocked` — print reason, stop, do not chain.
4. Render handoff per policy below.

## Handoff policy (manual mode, `CHAIN=false`)

Print:

```
Work complete: <artifact_path>
Next: /review <slug>   (or inspect the diff first)
```

## Auto-chain policy (`CHAIN=true`)

After `work` returns `status: complete`:

1. Invoke `/review <slug>` with the work artifact path as input. Do **not** propagate `--continue`.
2. After review returns, print:

   ```
   Pipeline paused at /review.
   Review docs/reviews/<slug>-review.md, then run /test <slug> (or /review --continue) when ready.
   ```

Rationale: code review is a quality gate that benefits from human attention even when automated checks pass.

## Invariants

- Never writes files directly — only the `work` skill writes to `docs/work/` (and source files via subagents).
- Auto-chain halts on any non-`complete` status from a chained skill.

## See also

- Skill: `skills/work/SKILL.md`
- Upstream: `/plan`
- Downstream: `/review`
