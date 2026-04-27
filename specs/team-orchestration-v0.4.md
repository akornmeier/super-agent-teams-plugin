# Plan: Team-Native Orchestration (v0.4) — Super-Charging With TeamCreate

## Task Description

The `tk-agent-team` plugin currently coordinates work through a **skill-as-broker** pattern: a parent skill runs in the user's session, reads memory via MCP, dispatches one-shot subagents (which lack MCP access), parses a `## Memory findings` YAML block from each return, and writes findings back to the substrate. This pattern was a correct workaround for the platform constraint that historically forbade subagents from talking to each other or to MCP servers.

Two things have changed:

1. **`TeamCreate` is now available.** It creates a named team with a 1:1 task list, lets agents be spawned as persistent teammates with `team_name` + `name`, and gives them peer-to-peer `SendMessage` plus shared `TaskList` access. Teammates go idle between turns rather than dying, and any teammate can re-wake any other.
2. **The current architecture shows the strain of growth.** The October 2025 architecture review surfaced six concrete drag points — central routing table with no test fixtures, prose-parsed `## Memory findings` (silent loss on malformed YAML), copy-pasted memory protocol across 10 SKILL.md files, ~120 KB cross-read tax on every prompt, and orchestrator/skill broker ambiguity.

This plan integrates `TeamCreate` as a first-class primitive and uses the migration to fix the underlying architectural debt. The end state is a plugin where:

- **Composite skills become persistent teams.** `/ship`, `/debug`, full-stack `/work`, and `/review` create real teams whose teammates live across stages, share a `TaskList`, and DM each other instead of round-tripping through the parent.
- **Memory protocol is one referenced contract**, not 10 copies.
- **`## Memory findings` is replaced by a schema-validated MCP tool** that any teammate can call directly — no more silent learning loss.
- **The orchestrator becomes a team factory + classifier**, not a memory broker.
- **A new `team-substrate` namespace** lets teams keep ephemeral scratch memory separate from durable per-family memory.
- **Cross-read scope shrinks** — orchestrator no longer reads all 12 family memories every prompt.

This is a v0.3 → v0.4 architectural step. It is intentionally scoped: the substrate Python and a small number of high-leverage skills change; most agent persona files do not.

## Objective

When this plan is complete:

- `mcp-servers/agent-substrate/` exposes new tools: `team_memory_read`, `team_memory_append`, `team_memory_summary`, and `memory_findings_submit` (the validated replacement for prose-parsed findings).
- `plugins/tk-agent-team/skills/_shared/{memory-protocol.md, team-protocol.md, findings-schema.md}` exist as the canonical referenced contracts; every SKILL.md replaces its inline protocol prose with a one-line reference plus skill-specific deltas.
- `/review`, `/ship`, `/debug`, and full-stack `/work` are converted to **team-based** skills that call `TeamCreate`, spawn named teammates, coordinate via `SendMessage` + `TaskList`, and shut the team down at completion.
- `agents/orchestrator.md` is rewritten as a **team factory**: it classifies, decides whether the dispatched skill needs a team or runs solo, creates the team, and hands off to a team-lead teammate.
- A new `agents/team-lead.md` archetype exists — an in-team coordinator that owns the team's `TaskList`, dispatches peers, and reports the structured summary back to the user-facing orchestrator at completion.
- A `routing.yaml` data file replaces the markdown classification table in `orchestrator.md`. A new `tests/test_routing.py` file holds 20+ prompt fixtures asserting expected `(skill, team_pattern, families)` tuples.
- `examples/workflow-team-feature.md` walks an end-to-end team-based feature flow showing live TaskList state and peer DMs.
- All existing tests still pass. New tests cover: team-scoped substrate storage, findings schema validation, routing fixtures, and one end-to-end smoke test of `/review` as a team.
- `plugin.json` version is bumped to `0.4.0`.

## Problem Statement

### What's broken or limited today

1. **Sequential skill stages waste wall-clock time.** `/plan` Stage 2 (architecture review) sees the planner's draft, returns to the parent, the parent re-dispatches the planner with findings. Three round-trips, three cold-start agents, three memory pre-loads. With teams, the planner and reviewer would DM each other directly, in-place, no parent involvement.

2. **Parallel reviewers can't see each other.** `/review` dispatches three reviewer personas in parallel — but they're isolated. Architecture and correctness frequently double-flag the same issue. Today's dedup happens *after* via prose parsing in the parent, which costs context and frequently misses near-duplicates.

3. **Composite skills lose carry-over context.** `/ship` is `/work` → `/review` → `/test`, each a fresh dispatch. The tester knows nothing about the developer's reasoning that wasn't in the diff. A persistent feature team would carry the developer's design intent into the test author's context for free.

4. **Memory-finding parsing is prose, not validated.** `plan/SKILL.md:30` documents that a missing `## Memory findings` section just logs a warning — and the learning is permanently lost. The whole product premise is "compound knowledge across cycles," and the wire format is hand-parsed YAML that fails open. This contradicts the thesis.

5. **The memory protocol is copy-pasted across 10 files.** Adding `memory_append_batch` requires editing 10 SKILL.md files. They will drift. They already exhibit subtle differences (some include `framework`/`design`/`engineering` conditional reads; others don't).

6. **Orchestrator reads 12 family memories on every prompt.** Up to ~120 KB before any skill runs. As families grow, this dominates context and *degrades* the classification quality the cross-reads were meant to improve.

7. **Routing has no test fixtures.** `orchestrator.md` lines 53–75 are a 10-row markdown table plus four cross-cutting augmentation rules plus three overrides. Adding a family is a markdown edit with zero verification that historical signals still route correctly. At 13 families it's manageable; at 25 it becomes regex soup with silent precedence bugs.

### What's missing that TeamCreate enables

8. **No persistent team identity across stages.** Every dispatch is cold-start. There is no abstraction for "the feature team working on user-profiles is this set of 4 named teammates."
9. **No peer-to-peer agent messaging.** Two reviewers cannot ask each other "did you already cover this?" without going through the parent.
10. **No shared coordination substrate.** The `TaskList` primitive — every teammate sees pending work, can claim a task, can mark it done — has no analog today.
11. **No team-scoped scratch memory.** All memory is per-family or `_shared`. There is no place for a team to negotiate ("we tried approach A, hit blocker B, pivoting to C") without polluting durable substrate.

## Solution Approach

### Three architectural shifts

**Shift 1: Skills choose between solo dispatch and team dispatch.**

Not every skill needs a team. `/ideate` is sequential and short — solo dispatch is correct. But `/ship` (composite, multi-stage), `/review` (3 parallel reviewers needing dedup), `/debug` (researcher→debugger→reviewer→developer chain), and full-stack `/work` (frontend+backend pair) all benefit from teams. We define a **team-pattern catalog** of six named patterns — `solo`, `pair`, `parallel-panel`, `pipeline`, `staged-team`, `feature-team` — and each skill declares which pattern it uses in frontmatter.

The two multi-stage patterns differ on a critical axis: **context carry vs. bias avoidance**. `staged-team` rotates members per stage — fresh reviewer, fresh tester — handing off via the shared `TaskList` and durable artifacts. `feature-team` keeps the same members across stages so the tester sees the developer's design intent that wasn't in the diff. Carry-over is sometimes a feature (testing intent) and sometimes a bug (a reviewer who watched the code get written is biased toward approving it). Skills declare which tradeoff they want.

**Shift 2: Teammates have direct MCP access.**

The "skill is the broker" rule existed because subagents lacked MCP tool access. With `TeamCreate`, teammates spawned via `Agent` are full agents with full tool allowlists — they can read and write memory directly. We retain a single broker exception: `_shared` writes still flow through the team-lead to prevent racing. But every other read and append is direct.

**Shift 3: Findings become a tool call, not a YAML block.**

Add `mcp__agent-substrate__memory_findings_submit(agent, findings: list[Finding])` with Pydantic validation. Teammates call it directly. Schema enforced at the substrate boundary. No more "agent forgot the YAML header, learning lost forever."

### Why these shifts compose

The three shifts reinforce each other:

- Direct MCP access (Shift 2) is what makes the validated tool (Shift 3) usable from inside teams without parent broker ceremony.
- The team patterns (Shift 1) give skills a vocabulary for *when* parallel collaboration matters, so we don't team-ify trivially-sequential work.
- Removing the broker bottleneck (Shifts 2+3) reduces parent context bloat, which is the actual constraint that made the orchestrator's 12-family pre-read look reasonable. Once teams self-coordinate, the orchestrator can shrink to "pre-load only the routed family + `_shared`."

### What this is NOT

- **Not** a rewrite of the persona library. The 30 agent files mostly survive untouched (the only changes are removing the inline memory protocol prose in favor of a one-line reference).
- **Not** a substrate refactor. The existing memory storage, lock files, atomic writes, curation pipeline — all preserved. Team memory is a *new* namespace alongside, not a replacement.
- **Not** a marketing-skill churn. We are not adding new skills. We are upgrading four existing skills to team-based and leaving the other six solo.

## Persistent Memory and Learning Guarantees (load-bearing)

**This is the contract every other section of this plan must honor.** The plugin's identity is "agents that learn and compound knowledge across sessions." Nothing in v0.4 may weaken that. Concretely:

### What is preserved unchanged

- **Per-family durable memory** at `<base>/<family>.yaml`. Same 8 KB soft / 10 KB hard caps, same atomic write + lock-file semantics, same curator overflow pipeline, same Pydantic validation, same path-traversal defenses. Existing `MemoryStorage` class is **not modified** — the substrate change in task 3 is strictly additive.
- **Specialist cross-family reads.** Every cross-read documented in `specs/foundation-notes.md` section 5 ("Per-agent memory-read matrix") survives: tester reads `developer` + `reviewer`, debugger reads `reviewer` + `researcher`, planner/technical reads `reviewer`, docs-writer reads every family. These read patterns move into specialist agent prompts where they belong (specialists keep them), not the orchestrator (which sheds them).
- **`_shared.yaml` project conventions.** Untouched. Orchestrator still owns serialized writes to `_shared` to prevent races. Every teammate still reads `_shared` at task start.
- **Compound knowledge cycle.** `/compound` stays solo, still authors `docs/solutions/<category>/<slug>.md`, still triggers `curator` to consolidate touched family memories. The whole "knowledge compounds across sessions" loop works identically — just faster, because findings stop getting silently dropped.

### What is strengthened

- **Findings persistence reliability.** Today, if a subagent emits malformed `## Memory findings` YAML or omits the header, `plan/SKILL.md:30` documents that the parent "log a warning" and the learning is permanently lost. The new `memory_findings_submit(agent, findings: list[Finding])` MCP tool replaces prose parsing with a Pydantic-validated boundary. Invalid findings are rejected loudly with actionable error; valid findings are guaranteed persisted via the existing `memory_append` machinery. Net effect: **more learning preserved per cycle, less silent loss**. This is a feature improvement, not a regression.
- **Direct teammate access.** Today subagents have no MCP access; the parent skill must broker every read and write, and the brokering itself is a source of bugs. Teammates spawned via TeamCreate have full tool allowlists including `mcp__agent-substrate__*`. They read their own family memory directly at task start and submit findings directly at task end — fewer hops, fewer parsing failures, identical durability.
- **Cross-family reads scoped per agent, not amassed at orchestrator.** Today the orchestrator reads all 12 family memories on every prompt (~120 KB context tax that degrades classification per the architecture review). Specialist cross-reads were already in the specialists. v0.4 keeps specialist reads exactly as they are and shrinks only the orchestrator's pre-load to `_shared` + the routed family + signal-driven augmentations. No specialist loses access to any memory it had before.

### What is added

- **Per-team scratch memory** at `<base>/teams/<team-name>/`. A *new namespace alongside* family memory, not a replacement. Lifecycle: created when `TeamCreate` runs, deleted when `TeamDelete` runs. Purpose: ephemeral team coordination ("we tried A, hit B, pivoting to C") that today has nowhere to live except the parent's transient context. The team-lead can promote durable patterns to family memory at shutdown via `memory_findings_submit` — explicit promotion, not automatic leakage.
- **Validated `Finding` schema** with `kind ∈ {pattern, pitfall, decision, open_question}` and `extra="forbid"`. Same vocabulary the curator already uses, now enforced at the wire boundary.

### Migration safety net

- The legacy prose-parsed `## Memory findings` path remains parseable in v0.4. `_shared/memory-protocol.md` marks it DEPRECATED but the substrate continues to accept it for one version. Removal lands in v0.5 only after we verify zero in-the-wild reliance.
- Task 18 (final validation) explicitly greps for any silent regression: every existing memory read/append call site must still resolve, no agent loses access to a family it could read in v0.3, and the curator pipeline runs unchanged.

## Relevant Files

Use these files to complete the task:

- `plugins/tk-agent-team/agents/orchestrator.md` — the file that becomes a team factory; current routing table moves to `routing.yaml`
- `plugins/tk-agent-team/agents/_TEMPLATE.md` — must be moved to `templates/_TEMPLATE.md.example` so it doesn't load as a placeholder agent (also fixes a v0.3 plugin-validation issue surfaced in the recent review)
- `plugins/tk-agent-team/skills/review/SKILL.md` — first migration target; converts a `parallel-panel` of 3 reviewers into a persistent team
- `plugins/tk-agent-team/skills/ship/SKILL.md` — second migration target; becomes a `staged-team` handing off through work → review → test stages with fresh members per stage (deliberate bias-avoidance choice)
- `plugins/tk-agent-team/skills/debug/SKILL.md` — third migration target; becomes a `pipeline` team
- `plugins/tk-agent-team/skills/work/SKILL.md` — fourth migration target; full-stack mode becomes a `pair` team (frontend + backend)
- `plugins/tk-agent-team/skills/plan/SKILL.md` — reference example of the current memory protocol prose that will be replaced with a one-line `_shared/memory-protocol.md` reference
- `plugins/tk-agent-team/skills/ideate/SKILL.md` — sample of a skill that stays `solo`; gets the same one-line reference replacement but no team conversion
- `plugins/tk-agent-team/skills/brainstorm/SKILL.md` — same as ideate; stays solo
- `plugins/tk-agent-team/skills/test/SKILL.md` — stays solo for now; flagged for future team conversion if patterns emerge
- `plugins/tk-agent-team/skills/compound/SKILL.md` — stays solo; long-running but sequential
- `plugins/tk-agent-team/skills/memory-curate/SKILL.md` — stays solo; reference skill format
- `plugins/tk-agent-team/mcp-servers/agent-substrate/src/agent_substrate/server.py` — gets four new tools: `team_memory_read`, `team_memory_append`, `team_memory_summary`, `memory_findings_submit`
- `plugins/tk-agent-team/mcp-servers/agent-substrate/src/agent_substrate/storage.py` — gains a `TeamMemoryStorage` class parallel to `MemoryStorage` rooted at `<base>/teams/<team-name>/`
- `plugins/tk-agent-team/mcp-servers/agent-substrate/src/agent_substrate/schema.py` — gains `Finding` model and team-name slug validator
- `plugins/tk-agent-team/mcp-servers/agent-substrate/tests/` — gains `test_team_storage.py`, `test_findings_schema.py`
- `plugins/tk-agent-team/.claude-plugin/plugin.json` — version bump to 0.4.0
- `.claude-plugin/marketplace.json` — version + description sync
- `scripts/lint-agents.sh` — extended to validate `team_pattern` frontmatter on SKILL.md and the new shared-protocol references resolve
- `README.md` — documents the team mental model and team-pattern catalog
- `CONTRIBUTING.md` — adds "Choosing a team pattern" section and "Migrating a solo skill to team-based"
- `specs/super-agent-team-orchestration.md` — superseded as the architectural source of truth; this v0.4 plan amends sections 1, 2, and 5 of `specs/foundation-notes.md`

### New Files

**Shared skill protocols (single source of truth, killing copy-paste drift):**
- `plugins/tk-agent-team/skills/_shared/memory-protocol.md` — canonical "before-dispatch read / after-dispatch persist" contract; all SKILL.md files reference it
- `plugins/tk-agent-team/skills/_shared/team-protocol.md` — canonical team lifecycle (create → spawn → coordinate → shutdown → delete) and team-pattern catalog
- `plugins/tk-agent-team/skills/_shared/findings-schema.md` — schema description for `memory_findings_submit` tool calls

**New agents:**
- `plugins/tk-agent-team/agents/team-lead.md` — the in-team coordinator archetype; owns `TaskList`, dispatches peers, escalates blockers, returns structured summary

**Routing as data:**
- `plugins/tk-agent-team/agents/routing.yaml` — replaces the markdown classification table in `orchestrator.md`; columns: `signals`, `task_type`, `skill`, `team_pattern`, `families`, `augmentations`
- `plugins/tk-agent-team/tests/test_routing.py` — pytest fixtures that load `routing.yaml` and assert `(skill, team_pattern, families)` for ~20 historical prompts

**Substrate extensions:**
- `plugins/tk-agent-team/mcp-servers/agent-substrate/src/agent_substrate/team_storage.py` — `TeamMemoryStorage` class
- `plugins/tk-agent-team/mcp-servers/agent-substrate/tests/test_team_storage.py` — unit tests for team-scoped read/append/summary, lock contention, atomic write
- `plugins/tk-agent-team/mcp-servers/agent-substrate/tests/test_findings_schema.py` — Pydantic validation tests for the new findings tool

**Documentation:**
- `examples/workflow-team-feature.md` — walks `/ship "Add user profiles with avatar upload"` end-to-end as a team: shows TeamCreate, the live TaskList, peer DMs between developer/backend and reviewer/architecture, and final shutdown
- `specs/team-orchestration-v0.4.md` — this plan (already written)

## Implementation Phases

### Phase 1: Foundation — substrate + shared protocols

Lay the primitives every later phase depends on. No team migrations yet.

- Extend the agent-substrate MCP server with team-scoped storage (`TeamMemoryStorage`) and its four new tools (`team_memory_read`, `team_memory_append`, `team_memory_summary`, `memory_findings_submit`).
- Add a `Finding` Pydantic model with strict validation (agent name, section, item; reject extras).
- Write the three `_shared/*.md` protocol references — these are the single source of truth that all SKILL.md files will collapse onto.
- Move `agents/_TEMPLATE.md` out of the auto-discovered directory (it currently loads as a placeholder agent named `teammate-name-here`, surfaced in the recent plugin-validator review).
- Pre-emptively address the v0.3 plugin-validator findings that block this work: rename colliding agent `name:` fields to `<family>-<persona>` so team spawning resolves the right teammate.

### Phase 2: Prototype — convert `/review` to a team

Pick the highest-value, lowest-risk skill as the prototype. `/review` has three parallel reviewers today that already need dedup — converting it to a `parallel-panel` team should produce visibly better dedup with no behavior regression.

- Rewrite `skills/review/SKILL.md` to: create team `review-<slug>`, spawn 3 named teammates (`reviewer-architecture`, `reviewer-correctness`, `reviewer-security`), assign each one a TaskList task, let them DM peers when they spot overlap, collect findings via the new `memory_findings_submit` tool, shutdown.
- Build the smoke test: a fixture diff containing a known overlap pattern (e.g., a hard-coded credential that *both* security and correctness should flag). Verify exactly one finding survives dedup.
- Capture lessons learned in `_shared/team-protocol.md` before migrating other skills.

### Phase 3: Core team migrations

With the pattern proven on `/review`, migrate the other three high-value skills in parallel.

- `/ship` becomes a `staged-team`: each stage gets fresh members handing off through the shared `TaskList` and the canonical `docs/<type>/<slug>.md` artifacts. The work stage's `developer-backend` shuts down before the review stage spawns its `reviewer-architecture` and `reviewer-correctness` — the reviewer reviews the diff cold, with no exposure to the developer's reasoning that didn't make it into the code. Same for the test stage. This trades context carry-over for review rigor; that's the deliberate v0.4 choice.
- `/debug` becomes a `pipeline` team: researcher posts context brief → debugger claims, posts hypothesis → reviewer-correctness validates → developer-backend implements fix → tester-unit writes regression test. All in one TaskList, all DM-coordinated.
- `/work` (full-stack mode only) becomes a `pair` team of `developer-frontend` + `developer-backend` who DM each other on contract questions instead of going through the parent.

Skills that stay solo (`/ideate`, `/brainstorm`, `/plan`, `/test`, `/compound`, `/memory-curate`) get only the protocol-reference collapse — no team conversion.

### Phase 4: Orchestrator rebalance

Now that skills know their team patterns, the orchestrator can shed weight.

- Convert routing table from markdown prose in `orchestrator.md` to `agents/routing.yaml` (data file).
- Add `tests/test_routing.py` with 20+ prompt fixtures asserting `(skill, team_pattern, families)`.
- Resolve the orchestrator-vs-skill broker ambiguity: orchestrator pre-loads ONLY `_shared` + the routed family (not all 12). Skills load any additional families they need.
- Author `agents/team-lead.md` archetype — the in-team coordinator that the orchestrator hands off to. Defines the `TaskList`-watching loop and the shutdown sequence.

### Phase 5: Polish, docs, validation

- Update README to document the team mental model + team-pattern catalog with a one-paragraph "when to use which pattern" guide.
- Update CONTRIBUTING with "Choosing a team pattern" and "Migrating a solo skill to team-based" sections.
- Write `examples/workflow-team-feature.md` with a real walkthrough.
- Extend `scripts/lint-agents.sh` to validate `team_pattern` frontmatter and that every `_shared/` reference resolves.
- Bump `plugin.json` to v0.4.0; mirror to `marketplace.json`.
- Final validation: lint passes, all pytests pass, manifest JSON parses, every `_shared/` reference in any SKILL.md resolves to a real file, every teammate name in any SKILL.md resolves to a real agent file (with the renamed `<family>-<persona>` names from Phase 1).

## Team Orchestration

- You operate as the team lead and orchestrate the team to execute the plan.
- You're responsible for deploying the right team members with the right context to execute the plan.
- IMPORTANT: You NEVER operate directly on the codebase. You use `Task` and `Task*` tools to deploy team members to to the building, validating, testing, deploying, and other tasks.
  - This is critical. You're job is to act as a high level director of the team, not a builder.
  - You're role is to validate all work is going well and make sure the team is on track to complete the plan.
  - You'll orchestrate this by using the Task\* Tools to manage coordination between the team members.
  - Communication is paramount. You'll use the Task\* Tools to communicate with the team members and ensure they're on track to complete the plan.
- Take note of the session id of each team member. This is how you'll reference them.

### Team Members

- Builder
  - Name: architect
  - Role: Owns Phase 1 design output and Phase 4 routing-as-data design. Writes `_shared/team-protocol.md`, `_shared/memory-protocol.md`, `_shared/findings-schema.md`, the team-pattern catalog, and the `routing.yaml` schema. Reviews migration patterns from Phase 2 and updates protocol docs with lessons learned. Never edits substrate code or skill bodies directly — produces the contracts that other builders implement against.
  - Agent Type: Software Architect
  - Resume: true
- Builder
  - Name: substrate-engineer
  - Role: Phase 1 substrate work. Implements `TeamMemoryStorage`, the four new MCP tools (`team_memory_read`, `team_memory_append`, `team_memory_summary`, `memory_findings_submit`), the `Finding` Pydantic model, and the matching pytest suites. Owns the slug regex extension for team names. Does not modify existing `MemoryStorage` behavior — additive only.
  - Agent Type: Backend Architect
  - Resume: true
- Builder
  - Name: prototype-builder
  - Role: Phase 2 only. Migrates `/review` from solo-parallel to a `parallel-panel` team. Builds the dedup smoke test. Reports back lessons-learned to the architect for the team-protocol doc. After Phase 2 ships, this teammate is shut down.
  - Agent Type: general-purpose
  - Resume: true
- Builder
  - Name: migration-builder-ship
  - Role: Phase 3 — migrates `/ship` to a `feature-team` pattern. Coordinates with `migration-builder-debug` and `migration-builder-work` to keep team-protocol consistent across all three migrations.
  - Agent Type: general-purpose
  - Resume: true
- Builder
  - Name: migration-builder-debug
  - Role: Phase 3 — migrates `/debug` to a `pipeline` team. Runs in parallel with the other migration builders.
  - Agent Type: general-purpose
  - Resume: true
- Builder
  - Name: migration-builder-work
  - Role: Phase 3 — migrates `/work` full-stack mode to a `pair` team. Runs in parallel with the other migration builders.
  - Agent Type: general-purpose
  - Resume: true
- Builder
  - Name: orchestrator-author
  - Role: Phase 4. Converts the markdown routing table to `routing.yaml`, authors `tests/test_routing.py` fixtures, rewrites `agents/orchestrator.md` as a team factory, authors the new `agents/team-lead.md` archetype, and shrinks the orchestrator's pre-load scope from 12 families to `_shared` + routed family.
  - Agent Type: general-purpose
  - Resume: true
- Builder
  - Name: protocol-collapser
  - Role: Phase 1 + Phase 5. Authors the three `_shared/*.md` files (Phase 1) and then sweeps every existing SKILL.md to collapse the inline memory protocol prose into a single `<!-- @ref _shared/memory-protocol.md -->` reference (Phase 5). Mechanical sweep, but must preserve any skill-specific deltas (e.g., `/plan`'s conditional `framework`/`design`/`engineering` reads).
  - Agent Type: Technical Writer
  - Resume: true
- Builder
  - Name: docs-author
  - Role: Phase 5. Writes `examples/workflow-team-feature.md`, updates `README.md` with the team mental model, adds CONTRIBUTING sections.
  - Agent Type: Technical Writer
  - Resume: true
- Builder
  - Name: validator
  - Role: Final validation across all phases. Runs lint, pytest, JSON manifest checks, dangling-reference greps, and the dedup smoke test from Phase 2 end-to-end. Starts fresh on each validation pass to avoid context contamination.
  - Agent Type: Code Reviewer
  - Resume: false

## Step by Step Tasks

- IMPORTANT: Execute every step in order, top to bottom. Each task maps directly to a `TaskCreate` call.
- Before you start, run `TaskCreate` to create the initial task list that all team members can see and execute.

### 1. Design the Team-Pattern Catalog and Foundation Contracts

- **Task ID**: design-foundation
- **Depends On**: none
- **Assigned To**: architect
- **Agent Type**: Software Architect
- **Parallel**: false
- Define the team-pattern catalog with six named patterns: `solo`, `pair`, `parallel-panel`, `pipeline`, `staged-team`, `feature-team`. For each, specify: when to use, lifecycle (create → spawn → coordinate → shutdown), how members coordinate (DM vs TaskList vs both), member rotation policy (rotate-per-stage vs persist-across-stages), expected member count, expected duration.
- Document the `staged-team` vs `feature-team` decision rule explicitly in `_shared/team-protocol.md`: default to `staged-team` whenever a downstream stage's purpose is to *check* an upstream stage (review, test, audit) — bias avoidance wins. Choose `feature-team` only when downstream stages *build on* upstream context that isn't fully captured in artifacts (rare; reserved for future skills that explicitly justify the choice).
- Write `plugins/tk-agent-team/skills/_shared/team-protocol.md` documenting the catalog plus the canonical `TeamCreate` → `Agent(team_name=..., name=...)` → `SendMessage` → `TaskUpdate` → `SendMessage(message: {type: "shutdown_request"})` → `TeamDelete` lifecycle.
- Write `plugins/tk-agent-team/skills/_shared/memory-protocol.md` documenting: which memory reads happen at the orchestrator layer, which at the skill layer, which at the teammate layer; how `_shared` writes are serialized (team-lead only); how findings are submitted via `memory_findings_submit` (deprecating the prose-parsed `## Memory findings` block).
- Write `plugins/tk-agent-team/skills/_shared/findings-schema.md` documenting the `Finding` Pydantic model: required fields (`agent`, `section`, `item.kind`, `item.summary`), optional fields (`item.protected`, `item.related`), kind enum (`pattern`, `pitfall`, `decision`, `open_question`).
- Define the `routing.yaml` schema (will be populated by orchestrator-author in Phase 4): top-level `rules:` array with `signals`, `task_type`, `skill`, `team_pattern`, `families`, `augmentations` keys plus an `overrides:` array.

### 2. Resolve Pre-Existing v0.3 Plugin-Validator Blockers

- **Task ID**: resolve-v03-blockers
- **Depends On**: none
- **Assigned To**: substrate-engineer
- **Agent Type**: Backend Architect
- **Parallel**: true (with task 1)
- Rename frontmatter `name:` in colliding agent files to `<family>-<persona>` (e.g., `agents/design/ui-designer.md` → `name: design-ui-designer`). Apply across `agents/{design,reviewer,developer,engineering,framework,marketing,planner,tester}/*.md` (8 families × multiple personas).
- Move `agents/_TEMPLATE.md` to `templates/_TEMPLATE.md.example` so the auto-loader stops creating a placeholder agent named `teammate-name-here`.
- Move stray runtime artifacts: delete or `.gitignore` `agents/logs/`, `skills/logs/`, `mcp-servers/agent-substrate/logs/`. Audit the JSON files inside for any leaked tokens or PII before removal.
- Tighten `.mcp.json` env-var fallback: edit `plugins/tk-agent-team/mcp-servers/agent-substrate/src/agent_substrate/server.py` to validate `AGENT_SUBSTRATE_BASE_DIR` is set and absolute at startup; fail loudly otherwise.
- This task is required for team spawning to work — `Agent(name="reviewer-architecture", ...)` must resolve to a unique agent file.

### 3. Implement Team-Scoped Substrate Storage

- **Task ID**: implement-team-storage
- **Depends On**: design-foundation, resolve-v03-blockers
- **Assigned To**: substrate-engineer
- **Agent Type**: Backend Architect
- **Parallel**: false
- Add `team_storage.py` with `TeamMemoryStorage` class rooted at `<base>/teams/<team-name>/`. Mirror `MemoryStorage`'s atomic-write + lock-file patterns. Slug regex must accept team names.
- Extend `schema.py` with `Finding` model: required `agent: str`, `section: str`, `item: FindingItem` where `FindingItem` has `kind: Literal["pattern", "pitfall", "decision", "open_question"]`, `summary: str`, optional `protected: bool`, optional `related: list[str]`. `model_config = {"extra": "forbid"}`.
- Add four new tools to `server.py`: `team_memory_read(team_name)`, `team_memory_append(team_name, section, item)`, `team_memory_summary(team_name)`, `memory_findings_submit(agent, findings: list[Finding])`. The findings tool calls `MemoryStorage.append` per finding, returning a structured response with per-finding success/warning state.
- Add `tests/test_team_storage.py` covering: read empty namespace, append + read round-trip, soft-limit warning, hard-limit error, slug rejection (`../etc/passwd`), concurrent append serialization.
- Add `tests/test_findings_schema.py` covering: valid finding accepted, missing `kind` rejected, unknown `kind` rejected, extra field rejected, invalid agent slug rejected.
- All existing tests in `mcp-servers/agent-substrate/tests/` must still pass unchanged.

### 4. Author Shared Protocol References

- **Task ID**: author-shared-protocols
- **Depends On**: design-foundation
- **Assigned To**: protocol-collapser
- **Agent Type**: Technical Writer
- **Parallel**: true (with task 2 and 3)
- Materialize the three `_shared/*.md` files designed in task 1 into final form with concrete examples that authors can copy-paste.
- `_shared/team-protocol.md` includes a worked example: a `parallel-panel` review team showing the exact `TeamCreate({...})` → 3× `Agent({team_name, name, ...})` → `TaskCreate` per teammate → ... → shutdown sequence.
- `_shared/memory-protocol.md` includes a worked example of a teammate calling `memory_findings_submit` directly versus the legacy parent-broker pattern (mark legacy as DEPRECATED but document for grandfathering).
- `_shared/findings-schema.md` includes a copy-pasteable JSON schema and a Python-call example.

### 5. Migrate `/review` to Parallel-Panel Team (Prototype)

- **Task ID**: migrate-review-skill
- **Depends On**: implement-team-storage, author-shared-protocols, resolve-v03-blockers
- **Assigned To**: prototype-builder
- **Agent Type**: general-purpose
- **Parallel**: false
- Rewrite `plugins/tk-agent-team/skills/review/SKILL.md` to use the `parallel-panel` team pattern. Frontmatter gains `team_pattern: parallel-panel`.
- Skill body replaces inline memory-protocol prose with `<!-- @ref _shared/memory-protocol.md -->` and `<!-- @ref _shared/team-protocol.md -->`.
- Skill workflow: `TeamCreate({team_name: "review-<slug>", description: "Review for <prompt>"})` → spawn 3 teammates (`reviewer-architecture`, `reviewer-correctness`, `reviewer-security`) → for each, `TaskCreate` with the diff scope → teammates work concurrently, post findings, DM peers when they spot overlap → team-lead consolidates → `memory_findings_submit` per teammate → `SendMessage(shutdown_request)` to all → `TeamDelete`.
- Update `agents/reviewer/{architecture,correctness,security}.md` (remember they were renamed in task 2 to `reviewer-architecture`, etc.) to call `memory_findings_submit` directly instead of emitting `## Memory findings` YAML in their response.

### 6. Build Dedup Smoke Test for `/review` Team

- **Task ID**: build-review-smoke-test
- **Depends On**: migrate-review-skill
- **Assigned To**: validator
- **Agent Type**: Code Reviewer
- **Parallel**: false
- Construct a fixture diff under `tests/fixtures/review-dedup/` containing a hard-coded credential that *both* `reviewer-correctness` and `reviewer-security` should historically flag.
- Run `/review` against the fixture. Assert: the consolidated report contains the credential finding exactly once. Assert: at least one peer DM was logged showing one reviewer noting the other had already flagged it.
- Document the test result in `tests/fixtures/review-dedup/README.md` so future migrations can use the same harness.

### 7. Capture Phase 2 Lessons Learned in Team Protocol

- **Task ID**: refine-team-protocol
- **Depends On**: build-review-smoke-test
- **Assigned To**: architect
- **Agent Type**: Software Architect
- **Parallel**: false
- Read prototype-builder's PR + the smoke-test outcome. Identify any rough edges (DM volume, TaskList contention, shutdown ordering, memory-write races).
- Update `_shared/team-protocol.md` with concrete guidance derived from the prototype: e.g., "for `parallel-panel`, designate one teammate as the dedup-arbiter to avoid N×N peer DMs"; "for shutdown, team-lead must verify TaskList is fully drained before sending shutdown_request."
- This task gates Phase 3 — migration builders must have refined protocol before they start.

### 8. Migrate `/ship` to Staged-Team Pattern

- **Task ID**: migrate-ship-skill
- **Depends On**: refine-team-protocol
- **Assigned To**: migration-builder-ship
- **Agent Type**: general-purpose
- **Parallel**: true (with tasks 9, 10)
- Rewrite `plugins/tk-agent-team/skills/ship/SKILL.md` for `team_pattern: staged-team`. The team persists across `/work` → `/review` → `/test` stages, but its **membership rotates per stage** — bias avoidance over context carry-over.
- Persistent members for the lifetime of the team: `team-lead` (always alive, owns the `TaskList`).
- Stage 1 (work) members: `developer-backend` and/or `developer-frontend`. Spawn at stage start, shut down at stage end (via `SendMessage({type: "shutdown_request"})`) once the work artifact is committed and the implementation task is marked complete.
- Stage 2 (review) members: `reviewer-architecture` + `reviewer-correctness` (+ `reviewer-security` when augmentations indicate). Spawn at stage start with no prior exposure to the developer's reasoning beyond what's in the artifact and diff. Shut down at stage end.
- Stage 3 (test) members: `tester-unit` and/or `tester-integration`. Spawn at stage start. Read the work artifact + the review report from `TaskList` history; do not inherit any developer-stage context.
- Stage transitions are explicit `TaskList` checkpoints owned by `team-lead`: when the implementation task transitions to `completed`, team-lead spawns the review-stage members; when the review task completes, team-lead spawns the test-stage members. This is the staged-team handoff pattern from `_shared/team-protocol.md`.
- Replace inline memory protocol with `_shared/` references. Memory findings from each stage flow through `memory_findings_submit` per teammate before that teammate shuts down.

### 9. Migrate `/debug` to Pipeline Team Pattern

- **Task ID**: migrate-debug-skill
- **Depends On**: refine-team-protocol
- **Assigned To**: migration-builder-debug
- **Agent Type**: general-purpose
- **Parallel**: true (with tasks 8, 10)
- Rewrite `plugins/tk-agent-team/skills/debug/SKILL.md` for `team_pattern: pipeline`. Stages flow as TaskList tasks with explicit `addBlockedBy` dependencies: researcher (no blockers) → debugger (blocked by researcher) → reviewer-correctness (blocked by debugger) → developer-backend (blocked by reviewer-correctness) → tester-unit (blocked by developer).
- Crucially, every teammate sees the full prior task history when they wake — debugger reads researcher's findings from the TaskList, not from a parent-passed brief.
- Replace inline memory protocol with `_shared/` references. Output artifact `docs/solutions/bug-fixes/<slug>.md` is now written collaboratively (developer + tester contribute sections).

### 10. Migrate `/work` Full-Stack to Pair Team Pattern

- **Task ID**: migrate-work-skill
- **Depends On**: refine-team-protocol
- **Assigned To**: migration-builder-work
- **Agent Type**: general-purpose
- **Parallel**: true (with tasks 8, 9)
- Rewrite `plugins/tk-agent-team/skills/work/SKILL.md` so the full-stack code path uses `team_pattern: pair` (frontend-only and backend-only paths stay solo).
- Pair team: `developer-frontend` + `developer-backend` + a lightweight team-lead. They DM each other on contract questions ("what's the API shape?", "what error codes do I throw?") instead of round-tripping through the parent skill.
- Solo paths in the same SKILL.md retain their current pattern; the team_pattern frontmatter becomes `solo|pair` with a routing rule embedded in the skill body.

### 11. Author the Team-Lead Archetype Agent

- **Task ID**: author-team-lead
- **Depends On**: refine-team-protocol
- **Assigned To**: orchestrator-author
- **Agent Type**: general-purpose
- **Parallel**: true (with tasks 8, 9, 10)
- Create `plugins/tk-agent-team/agents/team-lead.md`. Identity: in-team coordinator. Owns the team's TaskList, dispatches peers via `SendMessage`, escalates blockers, performs the shutdown sequence at completion.
- Tool allowlist: `Read, Grep, Glob, mcp__agent-substrate__*, TaskCreate, TaskUpdate, TaskList, TaskGet, SendMessage, TeamDelete`. Notably no `Edit/Write/Bash` — team-leads coordinate, they don't implement.
- Frontmatter: `name: team-lead`, distinct color/emoji/vibe.
- Memory protocol: reads `_shared` only at task start; the family memories live with the specialist teammates.

### 12. Convert Routing Table to YAML and Add Test Fixtures

- **Task ID**: routing-as-data
- **Depends On**: design-foundation
- **Assigned To**: orchestrator-author
- **Agent Type**: general-purpose
- **Parallel**: true (with tasks 8, 9, 10, 11)
- Create `plugins/tk-agent-team/agents/routing.yaml` with the existing 10-row classification table plus the new `team_pattern` column populated for each row (matching the migrations decided in Phase 3).
- Create `plugins/tk-agent-team/tests/test_routing.py` with a pytest fixture loader for `routing.yaml` and 20+ historical-prompt assertions: `("fix the broken signup flow", "bugfix", "/debug", "pipeline", ["_shared", "researcher", "debugger", "reviewer", "developer"])`, etc. Cover happy paths, override paths (stack-trace force), and augmentation stacking ("ship the React landing page with growth tracking" → adds `framework + marketing + engineering`).
- Test must pass before task 13 starts.

### 13. Rewrite Orchestrator as Team Factory

- **Task ID**: rewrite-orchestrator
- **Depends On**: routing-as-data, author-team-lead, migrate-ship-skill, migrate-debug-skill, migrate-work-skill
- **Assigned To**: orchestrator-author
- **Agent Type**: general-purpose
- **Parallel**: false
- Rewrite `plugins/tk-agent-team/agents/orchestrator.md`. Body shrinks dramatically: no inline routing table (now `routing.yaml`), no inline memory protocol (now `_shared/memory-protocol.md`).
- New responsibility flow: classify via routing.yaml lookup → if `team_pattern == solo`, dispatch the skill as today → else `TeamCreate` and hand off to a `team-lead` teammate spawned with the brief.
- Pre-load scope shrinks from "all 12 families" to "`_shared` + the routed family from routing.yaml." Cross-augmentations add specific families on top.
- Update `## Workflow process` to describe the new flow and explicitly mark the orchestrator as no longer being the memory broker for subagents — teammates have direct MCP access now.

### 14. Sweep Remaining SKILL.md Files for Protocol-Reference Collapse

- **Task ID**: collapse-protocol-prose
- **Depends On**: author-shared-protocols
- **Assigned To**: protocol-collapser
- **Agent Type**: Technical Writer
- **Parallel**: true (with Phase 3 migrations)
- For each `plugins/tk-agent-team/skills/*/SKILL.md` not yet rewritten by Phase 3 (`ideate`, `brainstorm`, `plan`, `test`, `compound`, `memory-curate`): replace the inline "Memory protocol (skill layer)" section with `<!-- @ref _shared/memory-protocol.md -->`.
- Preserve any skill-specific deltas (e.g., `/plan`'s conditional `framework`/`design`/`engineering` reads) as a small `### Memory deltas for this skill` section after the reference.
- Add `team_pattern: solo` to each of these skills' frontmatter for consistency with the migrated skills' `team_pattern: <pattern>`.
- Verify with grep: `grep -rln "memory_read_shared" plugins/tk-agent-team/skills/` should now show only the `_shared/memory-protocol.md` file plus any per-skill deltas, not 10 duplicates.

### 15. Extend Lint Script for Team Frontmatter

- **Task ID**: extend-lint-script
- **Depends On**: collapse-protocol-prose, rewrite-orchestrator
- **Assigned To**: validator
- **Agent Type**: Code Reviewer
- **Parallel**: true (with task 16)
- Extend `scripts/lint-agents.sh` to validate every SKILL.md has `team_pattern` in frontmatter and the value is one of the six catalog patterns (`solo`, `pair`, `parallel-panel`, `pipeline`, `staged-team`, `feature-team`). A skill declaring `team_pattern: feature-team` must additionally include a `### Why feature-team` section in the body justifying the bias-vs-context-carry tradeoff (lint warns if missing).
- Add a check that every `<!-- @ref _shared/*.md -->` reference in any SKILL.md resolves to a real file under `skills/_shared/`.
- Add a check that every teammate name referenced in a SKILL.md (e.g., `Agent({name: "reviewer-architecture", ...})`) corresponds to a real agent frontmatter `name:`.
- Existing checks must continue to pass on the rewritten files.

### 16. Update README, CONTRIBUTING, and Write End-to-End Example

- **Task ID**: update-docs
- **Depends On**: rewrite-orchestrator, collapse-protocol-prose
- **Assigned To**: docs-author
- **Agent Type**: Technical Writer
- **Parallel**: true (with task 15)
- Update `README.md` to document the team mental model: "v0.4 introduces real teams. Composite skills create persistent named teammates that share a TaskList, DM each other, and shut down when the work is done. Solo skills still run as before. The orchestrator picks." Include a one-paragraph team-pattern catalog.
- Update `CONTRIBUTING.md` with two new sections: "Choosing a team pattern when writing a new skill" (decision tree from `solo` to `feature-team`) and "Migrating a solo skill to a team-based skill" (step-by-step using `/review` as the worked example).
- Write `examples/workflow-team-feature.md`: walk `/ship "Add user profiles with avatar upload"` end-to-end as a `staged-team`. Show: (1) `TeamCreate` + `team-lead` spawn, (2) Stage 1 — dev-backend spawn → work → `memory_findings_submit` → shutdown, (3) Stage 2 — reviewer-architecture + reviewer-correctness spawn fresh (no exposure to dev's reasoning), peer DM example between the two reviewers when they spot overlap, both shut down after submitting findings, (4) Stage 3 — tester-unit spawns reading only the work artifact + review report from TaskList history, (5) `TeamDelete`. Include a sidebar callout: "Why no DM between dev-backend and reviewer-architecture? They're never alive at the same time — that's the point of `staged-team`." Show the live TaskList state at each stage transition.

### 17. Bump Plugin Version and Mirror to Marketplace

- **Task ID**: bump-version
- **Depends On**: update-docs, extend-lint-script
- **Assigned To**: substrate-engineer
- **Agent Type**: Backend Architect
- **Parallel**: false
- Bump `plugins/tk-agent-team/.claude-plugin/plugin.json` `version` to `0.4.0`. Update description to mention TeamCreate.
- Mirror version bump and description sync to `.claude-plugin/marketplace.json`.
- Validate JSON: `python -c "import json; json.load(open('plugins/tk-agent-team/.claude-plugin/plugin.json'))"` and same for marketplace.

### 18. Final Integrated Validation

- **Task ID**: validate-all
- **Depends On**: bump-version, build-review-smoke-test, migrate-ship-skill, migrate-debug-skill, migrate-work-skill, rewrite-orchestrator, extend-lint-script, update-docs
- **Assigned To**: validator
- **Agent Type**: Code Reviewer
- **Parallel**: false
- Run `bash scripts/lint-agents.sh` — exit 0 across all agent files (now uniquely named) and all SKILL.md files (now with `team_pattern` frontmatter and `_shared/` references that resolve).
- Run `cd plugins/tk-agent-team/mcp-servers/agent-substrate && pytest` — all existing tests pass plus all new team-storage and findings-schema tests pass.
- Run `pytest plugins/tk-agent-team/tests/test_routing.py` — all 20+ routing fixtures pass.
- Re-run the `/review` dedup smoke test from task 6 — still produces a single deduplicated finding.
- JSON validation: `python -c "import json; json.load(open('plugins/tk-agent-team/.claude-plugin/plugin.json'))"` and marketplace.json.
- Grep for dangling refs: `grep -rln "@ref _shared/" plugins/tk-agent-team/skills/` — every reference target exists.
- Grep for old prose protocol leakage: `grep -rln "Subagents do NOT have MCP tool access" plugins/tk-agent-team/skills/` — should return zero results (this prose moved into `_shared/memory-protocol.md` only).
- Grep for orphan agent names: every `name:` field across `agents/**/*.md` is unique. Run `awk '/^name: /{print $2}' plugins/tk-agent-team/agents/**/*.md | sort | uniq -d` and assert zero output.
- Manual smoke: spawn `/ship "test feature"` against a throwaway repo, observe TeamCreate, observe TaskList progression, observe shutdown_request flow, observe TeamDelete cleanup. Document the run in the task comment.
- Report: PASS / FAIL per check with file:line references for any failures. No PASS-with-warnings — anything not green requires the responsible builder to remediate.

## Acceptance Criteria

- `bash scripts/lint-agents.sh` returns PASS with 0 errors and validates `team_pattern` frontmatter on every SKILL.md
- `pytest` in `mcp-servers/agent-substrate/` passes with all new tests (`test_team_storage.py`, `test_findings_schema.py`) plus all existing tests unchanged
- `pytest plugins/tk-agent-team/tests/test_routing.py` passes with at least 20 fixture assertions covering happy paths, overrides, and augmentation stacking
- `python -c "import json; json.load(open('plugins/tk-agent-team/.claude-plugin/plugin.json'))"` succeeds and reports version `0.4.0`
- `python -c "import json; json.load(open('.claude-plugin/marketplace.json'))"` succeeds
- Every agent frontmatter `name:` value is unique across `plugins/tk-agent-team/agents/**/*.md` (no duplicates from the v0.3 collision issue)
- `plugins/tk-agent-team/agents/_TEMPLATE.md` no longer exists at its old path; `templates/_TEMPLATE.md.example` exists
- `plugins/tk-agent-team/agents/team-lead.md` exists and follows the 8-section template
- `plugins/tk-agent-team/agents/routing.yaml` exists with all rows from the previous markdown table plus a `team_pattern` column
- `plugins/tk-agent-team/skills/_shared/{memory-protocol.md,team-protocol.md,findings-schema.md}` exist
- `plugins/tk-agent-team/skills/{review,ship,debug,work}/SKILL.md` declare `team_pattern` other than `solo` in frontmatter and call `TeamCreate` in their body workflows
- `plugins/tk-agent-team/skills/{ideate,brainstorm,plan,test,compound,memory-curate}/SKILL.md` declare `team_pattern: solo` and reference `_shared/memory-protocol.md` instead of inline prose
- `mcp-servers/agent-substrate/src/agent_substrate/server.py` exposes new tools: `team_memory_read`, `team_memory_append`, `team_memory_summary`, `memory_findings_submit`
- `mcp-servers/agent-substrate/src/agent_substrate/schema.py` exports a `Finding` Pydantic model with `extra="forbid"`
- The `/review` dedup smoke test from task 6 is committed under `tests/fixtures/review-dedup/` and runs green
- `examples/workflow-team-feature.md` exists and references only real agent names, real skill names, and a plausible TaskList progression
- `README.md` documents the team-pattern catalog in a section titled `## Teams (v0.4)` or equivalent
- `CONTRIBUTING.md` has new "Choosing a team pattern" and "Migrating a solo skill" sections
- No SKILL.md contains the line `Subagents do NOT have MCP tool access` (it moved into `_shared/memory-protocol.md` exactly once, marked as legacy context)
- The orchestrator's pre-load scope is reduced from 12 families to `_shared` + routed family + augmentations (verifiable by reading the rewritten `agents/orchestrator.md`)
- No existing functionality regresses: `/ideate`, `/brainstorm`, `/plan`, `/test`, `/compound`, `/memory-curate` continue to work as solo skills
- **Memory preservation invariant**: every cross-family read documented in `specs/foundation-notes.md` section 5 still appears in the corresponding specialist agent's `## Memory protocol` section (or its skill-level deltas after the protocol-collapse sweep). No specialist loses access to any family memory it had read access to in v0.3.
- **Findings durability invariant**: the `memory_findings_submit` tool persists every valid `Finding` via the existing `memory_append` codepath. A property test in `test_findings_schema.py` asserts that for any valid `Finding`, calling `memory_findings_submit` then `memory_read(agent_name=finding.agent)` returns the appended item.
- **Curator continuity**: the `memory-curate` skill and the curator agent are unmodified by this plan. Curation triggered by overflow on any family memory still runs identically.

## Validation Commands

Execute these commands to validate the task is complete:

- `bash scripts/lint-agents.sh` — lint passes for all agent files and SKILL.md files including new `team_pattern` and `_shared/` reference checks
- `cd plugins/tk-agent-team/mcp-servers/agent-substrate && pytest -v` — substrate tests pass including new team-storage and findings-schema suites
- `cd plugins/tk-agent-team && pytest tests/test_routing.py -v` — routing fixtures all pass
- `python -c "import json; json.load(open('plugins/tk-agent-team/.claude-plugin/plugin.json'))" && echo OK` — manifest parses
- `python -c "import json; v=json.load(open('plugins/tk-agent-team/.claude-plugin/plugin.json'))['version']; assert v=='0.4.0', v"` — version bumped
- `python -c "import json; json.load(open('.claude-plugin/marketplace.json'))" && echo OK` — marketplace manifest parses
- `awk '/^name: /{print $2}' plugins/tk-agent-team/agents/**/*.md 2>/dev/null | sort | uniq -d | wc -l` — expected output: `0` (no duplicate agent names)
- `test -f plugins/tk-agent-team/skills/_shared/memory-protocol.md && test -f plugins/tk-agent-team/skills/_shared/team-protocol.md && test -f plugins/tk-agent-team/skills/_shared/findings-schema.md && echo OK` — all three shared protocols exist
- `test -f plugins/tk-agent-team/agents/team-lead.md && echo OK` — team-lead archetype exists
- `test -f plugins/tk-agent-team/agents/routing.yaml && echo OK` — routing data file exists
- `! test -f plugins/tk-agent-team/agents/_TEMPLATE.md && echo OK` — old template path removed
- `grep -lE '^team_pattern:' plugins/tk-agent-team/skills/*/SKILL.md | wc -l` — expected output equals total SKILL.md count (every skill declares its pattern)
- `grep -rln "Subagents do NOT have MCP tool access" plugins/tk-agent-team/skills/ | grep -v "_shared/" | wc -l` — expected output: `0` (legacy prose only survives in the shared protocol doc)
- `grep -rl "TeamCreate" plugins/tk-agent-team/skills/{review,ship,debug,work}/SKILL.md | wc -l` — expected output: `4` (each migrated skill calls TeamCreate)
- `find plugins/tk-agent-team/skills/_shared -name '*.md' | wc -l` — expected output: `3`
- Manual: run `/ship "test feature"` in a throwaway repo, observe `TeamCreate` is called, observe a `TaskList` populates with stage tasks, observe peer DMs in the team transcript, observe `TeamDelete` at completion.
- **Memory-preservation grep**: for each specialist family (`tester`, `debugger`, `planner`, `developer`, `reviewer`, `docs-writer`, `researcher`), confirm the cross-family reads from `specs/foundation-notes.md` section 5 still appear in either the agent file or its skill's `### Memory deltas` block. Run: `for fam in tester debugger planner; do grep -rln "memory_read(agent_name=\"$fam\")" plugins/tk-agent-team/{agents,skills} || echo "MISSING: $fam"; done` — expected: zero MISSING lines.
- **Findings round-trip property**: in `test_findings_schema.py`, a parameterized test submits 10 valid synthetic findings spanning all four `kind` values, then reads each back via `memory_read` and asserts byte-for-byte equality of `summary` and `kind`. Must pass.

## Notes

- **Why this is the right next step.** The recent four-agent review identified architectural debt (orchestrator routing-table-as-prose, memory-protocol drift across SKILL.md, prose-parsed findings with silent loss, 120 KB cross-read tax). TeamCreate isn't just a new toy — it's the primitive that lets us *fix* that debt by removing the broker bottleneck. Trying to integrate TeamCreate without the protocol cleanup would create a worse mess than v0.3; trying to clean up without TeamCreate would leave the system stuck in cold-dispatch mode.
- **Scope discipline.** This plan does not introduce new skills, new families, or new persona files (other than `team-lead.md`). The persona library is left alone — only the SKILL.md prose collapses onto shared references.
- **Backwards compatibility for grandfathered consumers.** The legacy prose-parsed `## Memory findings` path stays parseable in the substrate for one version (v0.4) and is removed in v0.5. The `_shared/memory-protocol.md` doc marks it as DEPRECATED. New skills must use `memory_findings_submit`.
- **Why team patterns are a closed enum.** Six named patterns (`solo`, `pair`, `parallel-panel`, `pipeline`, `staged-team`, `feature-team`) cover every team shape we've identified, with `staged-team` and `feature-team` distinguished on the carry-vs-bias axis. Closing the enum prevents skill-authors from inventing one-off patterns that nobody else can reason about. If a seventh pattern emerges, it's a deliberate `_shared/team-protocol.md` change — not a per-skill decision.
- **Default to `staged-team` over `feature-team`.** Across software lifecycle stages (work → review → test, plan → implement, etc.), the downstream stage's job is almost always to *check* the upstream stage, not to extend it. A reviewer who watched the developer write the code is biased; a tester who watched the developer reason about edge cases will under-test the cases the developer dismissed. `feature-team` is reserved for the rare case where a downstream stage genuinely needs prior context that artifacts cannot capture — and the lint script flags any new `feature-team` skill that doesn't justify the choice.
- **No new external dependencies.** No `uv add` required. The new substrate code uses Pydantic (already a dep) and the standard library. The new tests use pytest (already a dep).
- **Branch discipline.** Execute on `feature/team-orchestration-v0.4`. Do not merge to `main` until task 18 passes. Phase 1 + Phase 2 (tasks 1–7) form a coherent first PR; Phase 3+ can be a second PR if reviews want a smaller diff.
- **Memory budgets remain unchanged.** The 8 KB soft / 10 KB hard per-family limits are not touched. The new team-scoped storage uses the same limits per team namespace. Curation policy applies identically.
- **Parallelism callout.** Tasks 8, 9, 10, 11, 12, 14 can all run in parallel after task 7 completes. A competent team lead dispatches them as a wave, not sequentially. Phase 1 (tasks 1–4) also has internal parallelism: tasks 1, 2, 4 run in parallel; task 3 depends on 1 and 2.
- **Risk callout.** The `parallel-panel` dedup behavior depends on teammates DMing peers when they spot overlap. If that emergent behavior is unreliable, fall back to a "dedup-arbiter" role: one teammate explicitly claims a final pass over all findings before consolidation. This is documented in `_shared/team-protocol.md` after task 7's lessons-learned update.
