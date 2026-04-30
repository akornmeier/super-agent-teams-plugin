---
description: Run tests and produce a test report. Pass --continue to auto-chain into /ship.
argument-hint: [--continue] <slug-or-prompt>
---

# /test

Explicit entry point for the verification phase. Thin wrapper over the `test` skill, which produces a test report in `docs/tests/`.

## Inputs

- `$ARGUMENTS` — first token may be `--continue`. Remainder is a review slug (resolved against `docs/reviews/<slug>-review.md`) or a freeform test prompt.

## Steps

1. Parse `$ARGUMENTS`. Detect `--continue` flag.
2. Dispatch to the orchestrator agent: `Agent({subagent_type: "orchestrator", description: "Route /test", prompt: "test <parsed prompt>"})`. The orchestrator classifies against `routing.yaml`, pre-loads relevant memory, writes a brief, and either invokes the matched skill (solo `team_pattern`) or calls `TeamCreate` and spawns a `team-lead` (team `team_pattern`). It returns a structured summary with `artifact_path`, `status`, and `next_skill_hint`.
3. Branch on `status`:
   - `complete` — proceed to step 4.
   - `needs_human` / `blocked` — print reason, stop, do not chain.
4. Render handoff per policy below.

## Handoff policy (manual mode, `CHAIN=false`)

Print:

```
Test report complete: <artifact_path>
Next: /ship <slug>   (or fix failing tests first)
```

## Auto-chain policy (`CHAIN=true`)

After `test` returns `status: complete`:

1. Invoke `/ship <slug>` with the test report artifact path as input. Do **not** propagate `--continue`.
2. After ship returns, print:

   ```
   Pipeline paused at /ship.
   Review docs/ship/<slug>-ship.md and verify deployment health.
   ```

Rationale: shipping is the terminal phase of the build pipeline. After ship, the cycle either ends or loops back via `/compound`.

## Invariants

- Never writes files directly — only the `test` skill writes to `docs/tests/`.
- Auto-chain halts on any non-`complete` status from a chained skill.

## See also

- Skill: `skills/test/SKILL.md`
- Upstream: `/review`
- Downstream: `/ship`
