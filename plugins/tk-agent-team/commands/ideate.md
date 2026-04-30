---
description: Kick off divergent ideation. Produces 3-5 ranked ideas in docs/ideation/. Pass --continue to auto-chain into the next phase.
argument-hint: [--continue] <topic-or-prompt>
---

# /ideate

Explicit entry point for the divergent-exploration phase of the agent-team pipeline. This is a thin wrapper over the `ideate` skill — the skill does the work; this command just declares user intent and renders the handoff.

## Inputs

- `$ARGUMENTS` — everything after `/ideate`. If the first token is `--continue`, strip it and set `CHAIN=true`. Otherwise `CHAIN=false`. The remainder is the ideation prompt.

## Steps

1. **Parse** `$ARGUMENTS`. Detect `--continue` flag. Treat the rest as the user prompt for the skill.
2. **Dispatch** to the orchestrator agent: `Agent({subagent_type: "orchestrator", description: "Route /ideate", prompt: "/ideate\n\n<parsed prompt>"})`. The orchestrator classifies against `routing.yaml`, pre-loads relevant memory, writes a brief, and either invokes the matched skill (solo `team_pattern`) or calls `TeamCreate` and spawns a `team-lead` (team `team_pattern`). It returns a structured summary with `artifact_path`, `status`, and `next_skill_hint`.
3. **Branch on `status`:**
   - `complete` — proceed to step 4.
   - `needs_human` — print the skill's reason and stop. Do not chain.
   - `blocked` — print the blocker and stop. Do not chain.
4. **Render handoff** (see policy block below).

## Handoff policy (manual mode, `CHAIN=false`)

Print exactly:

```
Ideation complete: <artifact_path>
Recommended: idea N (top score)
Next: /brainstorm <slug>   (or revise the doc first)
```

The user re-invokes `/brainstorm` themselves. No auto-execution.

## Auto-chain policy (`CHAIN=true`)

After `ideate` returns `status: complete`:

1. Read the artifact's `## Recommendation` to identify the top-scored idea.
2. Invoke `/brainstorm <slug>` with the recommended idea as inline context (`idea N from <artifact_path>`). Do **not** propagate `--continue` — the chain advances exactly one phase.
3. After brainstorm returns, print the handoff and stop:

   ```
   Pipeline paused at /brainstorm.
   Review docs/brainstorms/<slug>-requirements.md, then run /plan <slug> (or /brainstorm --continue) when ready.
   ```

Rationale: requirements deserve human review before `/plan` commits architecture. Users who want to advance further can re-enter with `/brainstorm --continue`.

## Invariants

- This command never writes files directly — only the `ideate` skill writes to `docs/ideation/`.
- Auto-chain must respect skill `status`: if any chained skill returns `blocked` or `needs_human`, halt the chain and surface the reason.
- The chain never bypasses `/plan` to reach later phases — order is fixed: ideate → brainstorm → plan → work → review → test → ship.

## See also

- Skill: `skills/ideate/SKILL.md`
- Routing fallback (signal-based, when user doesn't run this command explicitly): `agents/routing.yaml`
- Cradle-to-grave alternative: `/compound`
