---
description: Turn requirements into an implementation plan. Pass --continue to auto-chain into /work.
argument-hint: [--continue] <slug-or-prompt>
---

# /plan

Explicit entry point for the architecture-and-design phase. Thin wrapper over the `plan` skill, which produces an implementation plan in `docs/plans/`.

## Inputs

- `$ARGUMENTS` — first token may be `--continue`. Remainder is a brainstorm slug (resolved against `docs/brainstorms/<slug>-requirements.md`) or a freeform planning prompt.

## Steps

1. Parse `$ARGUMENTS`. Detect `--continue` flag.
2. Dispatch to the orchestrator agent: `Agent({subagent_type: "orchestrator", description: "Route /plan", prompt: "<parsed prompt>"})`. The orchestrator classifies against `routing.yaml`, pre-loads relevant memory, writes a brief, and either invokes the matched skill (solo `team_pattern`) or calls `TeamCreate` and spawns a `team-lead` (team `team_pattern`). It returns a structured summary with `artifact_path`, `status`, and `next_skill_hint`.
3. Branch on `status`:
   - `complete` — proceed to step 4.
   - `needs_human` / `blocked` — print reason, stop, do not chain.
4. Render handoff per policy below.

## Handoff policy (manual mode, `CHAIN=false`)

Print:

```
Plan complete: <artifact_path>
Next: /work <slug>   (or revise the plan first)
```

## Auto-chain policy (`CHAIN=true`)

After `plan` returns `status: complete`:

1. Invoke `/work <slug>` with the plan artifact path as input. Do **not** propagate `--continue`.
2. After work returns, print:

   ```
   Pipeline paused at /work.
   Review docs/work/<slug>-work.md and the diff, then run /review <slug> (or /work --continue) when ready.
   ```

Rationale: `/work` is the first phase that writes real code — review the diff before continuing into `/review`.

## Invariants

- Never writes files directly — only the `plan` skill writes to `docs/plans/`.
- Auto-chain halts on any non-`complete` status from a chained skill.

## See also

- Skill: `skills/plan/SKILL.md`
- Upstream: `/brainstorm`
- Downstream: `/work`
