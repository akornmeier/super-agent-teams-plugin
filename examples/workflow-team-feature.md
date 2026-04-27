# Workflow: shipping a feature end-to-end as a staged-team

> Skill: `/ship`. Pattern: `staged-team`. Members rotate per stage — bias avoidance wins.

This walkthrough follows a single prompt — `/ship "Add user profiles with avatar upload"` — through the v0.4 team pipeline. It shows how `TeamCreate` spawns a real, named team, how `team-lead` rotates members across stages, and how the live `TaskList` gates each handoff. Every agent name, skill name, and MCP tool name below is a real primitive in this plugin.

## The prompt

> "Add user profiles with avatar upload."

## Step 1 — orchestrator classifies

**Activate:** `orchestrator`

The prompt contains the signals `add` and `upload`. The orchestrator loads `agents/routing.yaml`, walks rules top-to-bottom, and matches the **feature** row:

```yaml
- signals: [add, implement, build, new feature, ...]
  task_type: feature
  skill: /ship
  team_pattern: staged-team
  families: [_shared, planner, developer, reviewer, tester]
```

No augmentation triggers fire (no `framework`, `design`, `engineering`, or `marketing` signals). Pre-load is `_shared` + `planner` + `developer` + `reviewer` + `tester` — five families, not all twelve.

The orchestrator writes a brief at `docs/briefs/2026-04-26-add-user-profiles.md` containing the prompt, classification, and pre-loaded memory excerpts (e.g., reviewer pitfall: "user-supplied URLs rendered as `<img src>` require CSP review"). Then:

```text
TeamCreate({
  team_name: "ship-add-user-profiles-with-avatar-upload",
  description: "feature: Add user profiles with avatar upload"
})
```

## Step 2 — team-lead is born

The orchestrator spawns the persistent coordinator and stops:

```text
Agent({ subagent_type: "general-purpose", name: "team-lead",
        team_name: "ship-add-user-profiles-with-avatar-upload",
        prompt: "<routing summary + brief path>", run_in_background: true })
```

`team-lead` reads `_shared` and `team_memory_read({team_name})` (empty on creation), reads the brief, and records its first scratch entry under `section: "handoffs"`. The team is alive. Only `team-lead` is in it. Stage 1 starts.

## Stage 1 — work

**Mode signal:** the prompt mentions both "profiles" (backend data) and "avatar upload" (frontend file picker + backend storage). `team-lead` reads this as **full-stack** and spawns both developers concurrently:

```text
TaskCreate({ subject: "Backend: profile entity + PATCH /users/:id + S3 signing", owner: "developer-backend" })  → task_101
TaskCreate({ subject: "Frontend: ProfileEditForm + avatar picker", owner: "developer-frontend" })              → task_102

Agent({ team_name: "ship-add-user-profiles-with-avatar-upload", name: "developer-backend",  prompt: <see below>, run_in_background: true })
Agent({ team_name: "ship-add-user-profiles-with-avatar-upload", name: "developer-frontend", prompt: <see below>, run_in_background: true })
```

Each developer's prompt carries the canonical `## Team coordination context` block (`_shared/team-protocol.md#taskid-threading-load-bearing-for-spawning-skills`):

```markdown
## Team coordination context
- Your taskId: task_101
- Your role: developer-backend
- Peer taskIds: { developer-frontend: task_102 }
- Team scratch namespace: ship-add-user-profiles-with-avatar-upload
```

**Live TaskList state:**

| id | subject | owner | status |
|----|---------|-------|--------|
| task_101 | Backend: profile entity + PATCH /users/:id + S3 signing | developer-backend  | in_progress |
| task_102 | Frontend: ProfileEditForm + avatar picker               | developer-frontend | in_progress |

Mid-stage, `developer-frontend` DMs `developer-backend`:

```text
SendMessage({
  team_name: "ship-add-user-profiles-with-avatar-upload",
  to: "developer-backend",
  from: "developer-frontend",
  body: { type: "contract_question", topic: "S3 signed URL shape", body: "Are you returning a presigned PUT URL or a multipart token?" }
})
```

`developer-backend` replies via `SendMessage` and the agreement lands in team scratch:

```text
team_memory_append({
  team_name: "ship-add-user-profiles-with-avatar-upload",
  section: "decisions",
  item: { kind: "decision", summary: "Avatar upload uses presigned PUT URL; backend returns { uploadUrl, expiresAt }" }
})
```

When each developer finishes, they submit findings BEFORE acknowledging shutdown (the 60-second timeout per `_shared/team-protocol.md#shutdown-invariants` discards unsubmitted findings):

```text
mcp__agent-substrate__memory_findings_submit(
  agent="developer",
  findings=[{
    section: "patterns",
    item: { kind: "pattern",
            summary: "Avatar upload via presigned PUT URL — backend signs, frontend PUTs directly to S3",
            evidence: "src/services/avatarService.ts:34" }
  }]
)
TaskUpdate({ taskId: task_101, status: "completed" })
```

`team-lead` verifies both tasks are `completed`, sends `SendMessage({to: "developer-<role>", body: {type: "shutdown_request"}})` to each, waits for idle, and records the stage transition under `section: "handoffs"`. Both developers are now gone. Their context is gone. The diff and the work artifact are the only things that survive.

## Stage 2 — review (fresh members, no exposure to dev reasoning)

`team-lead` spawns the parallel-panel reviewers. The prompt mentions auth-adjacent surfaces (user identity, presigned URLs), so `reviewer-security` is included:

```text
TaskCreate({ subject: "Architecture review of work diff", owner: "reviewer-architecture" }) → task_201
TaskCreate({ subject: "Correctness review of work diff",  owner: "reviewer-correctness"  }) → task_202
TaskCreate({ subject: "Security review of work diff",     owner: "reviewer-security"     }) → task_203

Agent({ team_name: "ship-add-user-profiles-with-avatar-upload", name: "reviewer-architecture", run_in_background: true })
Agent({ team_name: "ship-add-user-profiles-with-avatar-upload", name: "reviewer-correctness",  run_in_background: true })
Agent({ team_name: "ship-add-user-profiles-with-avatar-upload", name: "reviewer-security",     run_in_background: true })
```

**Live TaskList state:**

| id | subject | owner | status |
|----|---------|-------|--------|
| task_101 | Backend: profile entity + PATCH /users/:id + S3 signing | developer-backend  | completed |
| task_102 | Frontend: ProfileEditForm + avatar picker               | developer-frontend | completed |
| task_201 | Architecture review of work diff                        | reviewer-architecture | in_progress |
| task_202 | Correctness review of work diff                         | reviewer-correctness  | in_progress |
| task_203 | Security review of work diff                            | reviewer-security     | in_progress |

Each reviewer reads `_shared` + `reviewer` directly, then walks the diff through their lens.

### Peer-DM dedup negotiation (severity ≤ minor)

Both `reviewer-correctness` and `reviewer-security` notice the same line: the presigned URL's `expiresAt` is set to 24 hours. Correctness sees a UX issue (stale URLs in long sessions); security sees a credential-lifetime issue. They DM directly:

```text
SendMessage({
  team_name: "ship-add-user-profiles-with-avatar-upload",
  to: "reviewer-security", from: "reviewer-correctness",
  body: { type: "potential_overlap", finding_summary: "expiresAt=24h on avatar upload URL — yours?" }
})
```

`reviewer-security` replies that the security lens is more specific; `reviewer-correctness` defers. The decision lands in team scratch under the canonical `dedup_decisions` section (`_shared/team-protocol.md#team-memory-section-taxonomy`).

### Team-lead arbitrates a severity-major finding

`reviewer-architecture` flags an architectural concern at severity `major`: the avatar-upload flow couples the user service to S3 directly, bypassing the storage abstraction. `reviewer-correctness` separately flags the same line at severity `major` (the abstraction's error contract isn't honored). Per `_shared/team-protocol.md#pattern-parallel-panel`, severity ≥ major triggers the dedup-arbiter — that's `team-lead`. It applies the canonical severity lattice, assigns the finding to the architectural lens (more specific to the layering concern), and records the resolution under `section: "dedup_decisions"`.

Each reviewer submits findings before shutdown. Findings persist at the family level (`agent: "reviewer"`); the running-teammate identity survives in `item.lens`:

```text
# reviewer-architecture
mcp__agent-substrate__memory_findings_submit(
  agent="reviewer",
  findings=[{
    section: "pitfalls",
    item: { kind: "pitfall",
            summary: "Direct S3 client in user service bypasses storage abstraction",
            evidence: "src/services/avatarService.ts:34",
            lens: "reviewer-architecture",
            why: "Violates layered-storage standing decision" }
  }]
)

# reviewer-security
mcp__agent-substrate__memory_findings_submit(
  agent="reviewer",
  findings=[{
    section: "pitfalls",
    item: { kind: "pitfall",
            summary: "Presigned URL TTL of 24h exceeds avatar-upload UX window",
            evidence: "src/services/avatarService.ts:51",
            lens: "reviewer-security",
            why: "Credential-lifetime principle: TTL should bound the session" }
  }]
)
```

`team-lead` consolidates the report at `docs/reviews/2026-04-26-add-user-profiles-review.md`, sends `shutdown_request` to all three reviewers, and records the Stage 2 → Stage 3 transition under `section: "handoffs"`.

> **Why no DM between developer-backend and reviewer-architecture?**
>
> They're never alive at the same time — that's the point of `staged-team`. The reviewer reviews the diff cold. A reviewer who watched the developer reason their way through edge cases would be biased toward approving the developer's edge-case dismissals. Bias avoidance is the staged-team default; if a future skill genuinely needs dev↔reviewer carry-over, that's a `feature-team` and must be justified per `_shared/team-protocol.md#default-rule-load-bearing`.

## Stage 3 — test (fresh members, no inheritance)

The review surfaced no `blocker`-severity findings (only `major` and `minor`), so Stage 3 proceeds without an autofix loop. `team-lead` spawns `tester-unit`:

```text
TaskCreate({ subject: "Unit + integration tests for profile + avatar flow", owner: "tester-unit" }) → task_301

Agent({ team_name: "ship-add-user-profiles-with-avatar-upload", name: "tester-unit", run_in_background: true })
```

**Live TaskList state:**

| id | subject | owner | status |
|----|---------|-------|--------|
| task_101 | Backend: profile entity + PATCH /users/:id + S3 signing | developer-backend  | completed |
| task_102 | Frontend: ProfileEditForm + avatar picker               | developer-frontend | completed |
| task_201 | Architecture review of work diff                        | reviewer-architecture | completed |
| task_202 | Correctness review of work diff                         | reviewer-correctness  | completed |
| task_203 | Security review of work diff                            | reviewer-security     | completed |
| task_301 | Unit + integration tests for profile + avatar flow      | tester-unit | in_progress |

`tester-unit` reads `_shared` + `tester` + cross-family `developer` + `reviewer` (per the matrix in `specs/foundation-notes.md` §5), reads the work artifact and the consolidated review report from TaskList history, and writes tests. It has no carry-over from the developers' design intent — only what's in the diff and the artifacts. That's the staged-team contract.

It submits findings:

```text
mcp__agent-substrate__memory_findings_submit(
  agent="tester",
  findings=[{
    section: "patterns",
    item: { kind: "pattern",
            summary: "Avatar upload integration tests mock S3 at module level, not call site",
            evidence: "tests/integration/test_avatar_upload.py:12",
            why: "Per-call mocking misses the presigned-URL signing path" }
  }]
)
TaskUpdate({ taskId: task_301, status: "completed" })
```

`team-lead` sends `shutdown_request` to `tester-unit`.

## Stage 4 — teardown

`team-lead` does the final consolidation pass:

1. Reads `team_memory_read({team_name: "ship-add-user-profiles-with-avatar-upload"})` for handoffs and dedup decisions.
2. Mirrors any project-level decisions to `_shared` (only team-lead may write `_shared` — per `_shared/memory-protocol.md#_shared-write-serialization`):

   ```text
   memory_append_shared({
     section: "decisions",
     item: { kind: "decision", summary: "Avatar upload pattern: presigned PUT URL via storage abstraction; TTL bounded to session" }
   })
   ```

3. Writes the canonical ship artifact at `docs/ship/2026-04-26-add-user-profiles-ship.md`.
4. Tears the team down:

   ```text
   TeamDelete({ team_name: "ship-add-user-profiles-with-avatar-upload" })
   ```

The team-scratch namespace at `<base>/teams/ship-add-user-profiles-with-avatar-upload/` is removed. The persistent family memories (`developer.yaml`, `reviewer.yaml`, `tester.yaml`, `_shared.yaml`) survive — they're the durable knowledge.

The orchestrator receives the structured summary:

```yaml
artifact_path: docs/ship/2026-04-26-add-user-profiles-ship.md
status: complete
memory_findings: [developer, reviewer, tester]
sub_artifacts:
  work: docs/work/2026-04-26-add-user-profiles-work.md
  review: docs/reviews/2026-04-26-add-user-profiles-review.md
  test: docs/tests/2026-04-26-add-user-profiles-test-report.md
team_summary:
  team_name: ship-add-user-profiles-with-avatar-upload
  handoffs: 3
  dedup_decisions: 2
next_skill_hint: /compound
```

## What got persisted to memory

The team is gone. What survived:

- **`developer.yaml`** gained a pattern: "Avatar upload via presigned PUT URL — backend signs, frontend PUTs directly to S3" (with evidence).
- **`reviewer.yaml`** gained two pitfalls: the storage-abstraction bypass (lens: architecture) and the 24h TTL concern (lens: security). Both carry the `lens` field so post-hoc audit can recover which reviewer flagged what.
- **`tester.yaml`** gained a pattern: "Mock S3 at module level for avatar upload integration tests."
- **`_shared.yaml`** gained the cross-cutting decision about presigned-URL upload pattern + session-bounded TTL.

The next prompt that mentions avatar uploads or presigned URLs will arrive into a smarter team. The reviewer family will pre-flag the TTL pattern. The developer family will pre-apply the storage-abstraction layering. The tester family will pre-write the module-level S3 mock. That is the compounding — stored at the family level, surviving every team's lifecycle.

## Key takeaways

1. **Members rotate per stage by design.** Stage 1 developers shut down before Stage 2 reviewers spawn. Stage 2 reviewers shut down before Stage 3 testers spawn. The reviewer reviews the diff cold; the tester writes tests against the artifact + diff, not against developer intent.
2. **TaskList is the canonical handoff channel.** Every stage transition is a TaskList state transition. Inter-stage DMs are forbidden in `staged-team` — that would defeat the bias-avoidance property.
3. **Findings persist at the family level, lens lives in `item.lens`.** A teammate spawned as `reviewer-security` submits findings with `agent: "reviewer"`. The running-teammate identity survives only in `item.lens` for post-hoc audit.
4. **Team scratch is ephemeral; family memory is durable.** Handoffs, dedup decisions, and escalations live in `<base>/teams/<team-name>/` and die with `TeamDelete`. Patterns, pitfalls, decisions, and open questions persist to `<base>/<family>.yaml` and compound across cycles.
