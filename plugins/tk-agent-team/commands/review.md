---
description: Review recent work for correctness, security, and style. Pass --continue to auto-chain into /test.
argument-hint: [--continue] <slug-or-prompt>
---

# /review

Explicit entry point for the code-review phase. Thin wrapper over the `review` skill, which produces a review report in `docs/reviews/`.

## Inputs

- `$ARGUMENTS` — first token may be `--continue`. Remainder is a work slug (resolved against `docs/work/<slug>-work.md`) or a freeform review prompt.

## Steps

1. Parse `$ARGUMENTS`. Detect `--continue` flag.
2. Dispatch to the orchestrator agent: `Agent({subagent_type: "orchestrator", description: "Route /review", prompt: "review <parsed prompt>"})`. The orchestrator classifies against `routing.yaml`, pre-loads relevant memory, writes a brief, and either invokes the matched skill (solo `team_pattern`) or calls `TeamCreate` and spawns a `team-lead` (team `team_pattern`). It returns a structured summary with `artifact_path`, `status`, and `next_skill_hint`.
3. Branch on `status`:
   - `complete` — proceed to step 4.
   - `needs_human` / `blocked` — print reason, stop, do not chain.
4. Render handoff per policy below.

## Handoff policy (manual mode, `CHAIN=false`)

Print:

```
Review complete: <artifact_path>
Next: /test <slug>   (or address review findings first)
```

## Auto-chain policy (`CHAIN=true`)

After `review` returns `status: complete`:

1. Invoke `/test <slug>` with the review artifact path as input. Do **not** propagate `--continue`.
2. After test returns, print:

   ```
   Pipeline paused at /test.
   Review docs/tests/<slug>-test-report.md, then run /ship <slug> (or /test --continue) when ready.
   ```

Rationale: test results are the last quality gate before `/ship` — confirm coverage and pass rate before releasing.

## Invariants

- Never writes files directly — only the `review` skill writes to `docs/reviews/`.
- Auto-chain halts on any non-`complete` status from a chained skill.

## See also

- Skill: `skills/review/SKILL.md`
- Upstream: `/work`
- Downstream: `/test`
