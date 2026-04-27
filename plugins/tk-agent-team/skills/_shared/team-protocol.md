<!-- Canonical team-pattern catalog and lifecycle reference for tk-agent-team v0.4. -->
<!-- SKILL.md authors reference sections here via: <!-- @ref _shared/team-protocol.md#<anchor> --> -->

# Team Protocol (canonical)

The six team patterns below are a **closed enum**. If you think you need a seventh, edit this file — do not invent one in a SKILL.md.

## Default rule (load-bearing)

Default to `staged-team` whenever a downstream stage's purpose is to *check* an upstream stage (review, test, audit) — bias avoidance wins. Choose `feature-team` only when downstream stages *build on* upstream context that cannot be fully captured in artifacts. The lint script (task 15) flags any new `feature-team` skill that does not include a `### Why feature-team` section justifying the choice.

## Pattern catalog

<!-- @ref _shared/team-protocol.md#pattern-solo -->
### `solo`
- **Use when:** sequential, short, no peer collaboration adds value (e.g., `/ideate`, `/brainstorm`, `/memory-curate`).
- **Lifecycle:** no `TeamCreate`. Skill dispatches a single agent the legacy way.
- **Coordination:** none.
- **Rotation:** N/A.
- **Members / duration:** 1 agent / minutes.
- **Anti-pattern:** wrapping `solo` work in a team for ceremony — the team-name slug overhead alone outweighs the benefit.

<!-- @ref _shared/team-protocol.md#pattern-pair -->
### `pair`
- **Use when:** two specialists must negotiate a contract (e.g., frontend ↔ backend on API shape).
- **Lifecycle:** `TeamCreate` → spawn 2 named teammates + lightweight team-lead → DM-driven contract negotiation → both submit findings → `TeamDelete`.
- **Coordination:** SendMessage DMs primary; `TaskList` for the contract-handoff checkpoint only.
- **Rotation:** persists — both members live the entire team duration.
- **Members / duration:** 2 specialists + 1 team-lead / one work session.
- **Anti-pattern:** using `pair` when one specialist could do the work alone — DMs become a status-update channel, not a contract negotiation.

<!-- @ref _shared/team-protocol.md#pattern-parallel-panel -->
### `parallel-panel`
- **Use when:** N specialists analyze the same input and findings must be deduped (e.g., `/review` with architecture/correctness/security reviewers).
- **Lifecycle:** `TeamCreate` → spawn N teammates → each gets one `TaskList` task on the same input → peer DMs surface overlap → consolidated submission → `TeamDelete`.
- **Coordination:** both — `TaskList` for work assignment, `SendMessage` for "did you already cover this?" peer DMs.
- **Rotation:** persists — all members alive concurrently.
- **Members / duration:** 3–5 specialists / minutes.
- **Anti-pattern:** parallel-panel for N=2 — that is `pair` with extra steps. Parallel-panel for N>5 — N×N DM volume regresses dedup quality.
- **Dedup-arbiter fallback:** start with peer DMs. If empirical dedup quality regresses (duplicates surviving consolidation, conflicting verdicts), designate one teammate as `arbiter` for a final pass over all findings before consolidation. This is the documented escape hatch from the task-7 lessons-learned slot.

<!-- @ref _shared/team-protocol.md#pattern-pipeline -->
### `pipeline`
- **Use when:** sequential stages where each stage strictly depends on the previous one's output (e.g., `/debug`: researcher → debugger → reviewer-correctness → developer → tester).
- **Lifecycle:** `TeamCreate` → team-lead spawns stage-1 teammate → on completion, spawns stage-2, etc. — `TaskList` `addBlockedBy` chain enforces order → `TeamDelete` on final stage.
- **Coordination:** `TaskList` primary (each stage reads prior task history); DMs only for clarification questions back to the previous stage.
- **Rotation:** members may persist or rotate per stage at the skill author's discretion (pipeline is agnostic — pick the rotation policy that matches the work).
- **Members / duration:** 4–6 across stages / one work session.
- **Anti-pattern:** pipeline when stages can run in parallel — that is `parallel-panel`.

<!-- @ref _shared/team-protocol.md#pattern-staged-team -->
### `staged-team`  (DEFAULT for multi-stage check workflows)
- **Use when:** multi-stage workflow where downstream stages *check* upstream stages (e.g., `/ship` = work → review → test). Bias avoidance is the goal: a fresh reviewer cannot be biased by having watched the code get written.
- **Lifecycle:** `TeamCreate` → team-lead persistent → spawn stage-1 members → on stage-1 complete, send shutdown_request to stage-1 members → spawn stage-2 members fresh (no prior context) → repeat → `TeamDelete`.
- **Coordination:** `TaskList` is the canonical handoff channel; durable artifacts (`docs/work/...`, `docs/reviews/...`) carry the substance. Inter-stage DMs are forbidden — that would defeat the bias-avoidance property.
- **Rotation:** **rotates per stage**. Only team-lead persists.
- **Members / duration:** 1 team-lead + 2–4 per stage / one feature cycle.
- **Anti-pattern:** keeping a stage-1 member alive into stage 2 "for context" — that is the bias leak `staged-team` exists to prevent. If you need that, you want `feature-team` and you must justify it.

<!-- @ref _shared/team-protocol.md#pattern-feature-team -->
### `feature-team`  (rare — must justify)
- **Use when:** multi-stage workflow where downstream stages *build on* upstream context that artifacts cannot fully capture (e.g., a tester who needs the developer's edge-case reasoning that did not land in the diff).
- **Lifecycle:** `TeamCreate` → spawn full member set up front → all members persist across stages → stages are `TaskList` checkpoints, not member rotations → `TeamDelete`.
- **Coordination:** both — `TaskList` for stage gating, persistent DMs for context carry.
- **Rotation:** **persists across stages**.
- **Members / duration:** 3–6 / one feature cycle.
- **Anti-pattern:** `feature-team` for review/audit/test stages — those bias-leak. If you cannot articulate a `### Why feature-team` justification in the SKILL.md, you want `staged-team` instead.

## Canonical lifecycle (worked example: `parallel-panel` review team)

Copy-paste this sequence and rename agents as needed.

```text
# 1) Create the team. Slug must match ^[a-z][a-z0-9-]{0,63}$.
TeamCreate({
  team_name: "review-2026-04-26-user-profiles",
  description: "Code review for the user-profiles diff"
})

# 2) Spawn N named teammates as full agents (each gets full tool allowlist
#    including mcp__agent-substrate__*). Names must be globally unique
#    agent file names per the v0.3-blocker rename (task 2).
Agent({ team_name: "review-2026-04-26-user-profiles", name: "reviewer-architecture" })
Agent({ team_name: "review-2026-04-26-user-profiles", name: "reviewer-correctness" })
Agent({ team_name: "review-2026-04-26-user-profiles", name: "reviewer-security" })

# 3) Team-lead seeds the shared TaskList — one task per teammate, same input.
TaskCreate({ assignee: "reviewer-architecture", description: "Review diff for architectural concerns", input_artifact: "docs/work/<slug>-work.md" })
TaskCreate({ assignee: "reviewer-correctness", description: "Review diff for correctness defects",     input_artifact: "docs/work/<slug>-work.md" })
TaskCreate({ assignee: "reviewer-security",    description: "Review diff for security defects",        input_artifact: "docs/work/<slug>-work.md" })

# 4) Teammates work concurrently. When one spots overlap with another's domain,
#    they DM directly:
SendMessage({
  team_name: "review-2026-04-26-user-profiles",
  to: "reviewer-correctness",
  from: "reviewer-security",
  body: "I'm flagging the hard-coded credential at auth.py:42 — yours?"
})

# 5) Each teammate submits findings via the validated tool (NOT prose YAML):
mcp__agent-substrate__memory_findings_submit(
  agent="reviewer-security",
  findings=[ { section: "pitfalls", item: { kind: "pitfall", summary: "Hard-coded credential in auth.py", evidence: "auth.py:42" } } ]
)

# 6) Team-lead verifies the TaskList is fully drained, then shuts members down:
SendMessage({ to: "reviewer-architecture", body: { type: "shutdown_request" } })
SendMessage({ to: "reviewer-correctness",  body: { type: "shutdown_request" } })
SendMessage({ to: "reviewer-security",     body: { type: "shutdown_request" } })

# 7) Tear down the team.
TeamDelete({ team_name: "review-2026-04-26-user-profiles" })
```

## Shutdown invariants

- Team-lead MUST verify the `TaskList` is fully drained (no `pending` or `in_progress` tasks) before sending any `shutdown_request`. Premature shutdown drops in-flight work.
- Every teammate MUST submit findings via `memory_findings_submit` BEFORE acknowledging shutdown. The legacy prose `## Memory findings` block is deprecated (see `_shared/memory-protocol.md`).
- `TeamDelete` is the last call. After it, the team-scoped scratch namespace `<base>/teams/<team-name>/` is removed.
