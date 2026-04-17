# Plan: Super Agent Team Orchestration — Three-Repo Synthesis

## Task Description

Synthesize three existing plugins into a single orchestrated agent-team system:

1. **`~/Code/compound-engineering-plugin`** — contributes the workflow: `ideate → brainstorm → plan → work → review → compound`, artifact directories (`docs/ideation/`, `docs/plans/`, `docs/solutions/`), and the pattern of chained skills that pass context through files
2. **`~/Code/agency-agents`** — contributes deep domain specialization (171 agents across 12 categories), the rich 8-section personality template, and the pattern of agent families organized by domain
3. **`this repo` (`tk-agent-team`)** — contributes the durable per-agent YAML memory substrate (`mcp__agent-substrate__*`), agent families sharing memory namespaces, the scored curation pipeline, and cross-family memory reads

The target state is a plugin where the user types a natural-language prompt such as "Add user profiles with avatar upload" and an **orchestrator agent** reads shared memory to classify the task, assemble the correct specialists (planner → developer → reviewer → tester), route context artifacts between them, and capture learnings back into memory — without the user manually activating individual agents.

This plan focuses exclusively on the additive work needed to reach that state: the new `orchestrator` agent, four new agent families (`planner`, `tester`, plus solos `researcher`, `debugger`, `docs-writer`), nine workflow skills, the artifact directory conventions, and updated manifests and examples. Existing agents (`reviewer`, `developer`, `curator`) and the `memory-curate` skill are left untouched — the orchestrator routes to them using their current contracts.

## Objective

When this plan is complete:

- The plugin exposes nine user-facing slash commands: `/ideate`, `/brainstorm`, `/plan`, `/work`, `/review`, `/test`, `/debug`, `/ship`, `/compound`
- An `orchestrator` agent exists and is the default dispatcher for every command — it reads shared memory plus the prompt to classify the task and assemble the right team
- Eight new agent definitions are in place: `orchestrator.md`, `planner/product.md`, `planner/technical.md`, `researcher.md`, `tester/unit.md`, `tester/integration.md`, `debugger.md`, `docs-writer.md` (eight files across six namespaces)
- Nine `SKILL.md` files define the workflow pipelines and declare which agents they dispatch, which memory files they read, and which artifact files they produce
- Artifact directory conventions are documented: `docs/ideation/`, `docs/brainstorms/`, `docs/plans/`, `docs/solutions/` — each with a README explaining its purpose and schema
- `plugin.json` and `marketplace.json` list every new agent and skill with color/emoji/vibe metadata
- `examples/workflow-ideate-to-ship.md` demonstrates the full cycle end-to-end
- `scripts/lint-agents.sh` passes with zero errors across all new agent files
- `CONTRIBUTING.md` documents the new family and skill creation patterns
- The root `README.md` presents the plugin's capability map (commands + agents + memory model) so new users can orient in under two minutes

## Problem Statement

The three source repos each solve a different piece of the autonomous-agent-team problem, but none solves the whole:

- **compound-engineering-plugin** delivers an excellent workflow (`ideate → plan → work → review → compound`) but its agents are lightweight personas without persistent memory. The same patterns get re-discovered every session.
- **agency-agents** delivers deep specialization (171 personas) but has no orchestrator — a user must manually pick and activate each agent. There is no memory, so specialists cannot learn from each other.
- **tk-agent-team** delivers durable memory and agent families with cross-family reads, but has only two families (`reviewer`, `developer`) and no command surface — every task requires the user to know which agent to activate and in what order.

The result today: a user who wants to ship a feature has to choose between predictable workflow without learning (compound), deep specialists without coordination (agency), or durable learning without workflow (tk-agent-team). There is no unified system that combines automatic orchestration, deep specialization, and cross-session memory in one plugin.

## Solution Approach

The synthesis assembles the three repos along three orthogonal dimensions:

1. **Workflow dimension** (from compound): the nine skills each define a pipeline — inputs, stages, outputs, and artifact files. Skills chain by reading each other's output artifacts from `docs/`.
2. **Specialization dimension** (from agency-agents): every agent uses the 8-section personality template already adopted in this repo (identity, core mission, critical rules, workflow process, communication style, success metrics, specialty, memory protocol). New families follow the same structure.
3. **Memory dimension** (from tk-agent-team): every agent reads its own family memory plus the shared file at task start and appends learnings at task end. The orchestrator additionally reads every relevant family's memory before dispatching — this is how routing decisions get smarter over time.

The integration point is the **orchestrator agent**. It is a solo agent that:

- Reads the user prompt
- Reads `_shared.yaml` plus every family memory file relevant to the prompt's domain (for a feature: planner, developer, reviewer, tester; for a bug: debugger, correctness reviewer, developer)
- Classifies the task type using a decision table encoded in its `## Core mission` section
- Dispatches the appropriate skill (or composite skill chain like `/ship`) with the context-window-friendly subset of memory already loaded
- After the skill completes, updates `_shared.yaml` with any project-level decisions that the team converged on
- Reports back to the user with a structured summary

Skills are dispatched as structured handoffs: the orchestrator writes a brief to `docs/<artifact-type>/<slug>.md`, tells the target agent "read this file and follow the `memory-curate`-style stage pipeline", and the target agent's output is another file in a different `docs/` directory. The file-based handoff (from compound-engineering) plus the memory substrate (from tk-agent-team) gives us the best of both: artifacts are durable across sessions, and agent memory is durable across projects.

## Relevant Files

Use these files to complete the task:

- [plugins/tk-agent-team/agents/\_TEMPLATE.md](plugins/tk-agent-team/agents/_TEMPLATE.md) — canonical 8-section agent template; every new agent file starts from this
- [plugins/tk-agent-team/agents/README.md](plugins/tk-agent-team/agents/README.md) — family registry; must be updated with five new family rows
- [plugins/tk-agent-team/agents/developer/frontend.md](plugins/tk-agent-team/agents/developer/frontend.md) — reference implementation showing how cross-family memory reads are declared in the `## Memory protocol` section
- [plugins/tk-agent-team/agents/reviewer/architecture.md](plugins/tk-agent-team/agents/reviewer/architecture.md) — reference implementation of a persona in a family sharing a memory namespace
- [plugins/tk-agent-team/agents/curator.md](plugins/tk-agent-team/agents/curator.md) — reference implementation of a solo agent
- [plugins/tk-agent-team/skills/memory-curate/SKILL.md](plugins/tk-agent-team/skills/memory-curate/SKILL.md) — canonical skill format; every new `SKILL.md` follows this structure (inputs, stages, invariants, write-back)
- [plugins/tk-agent-team/skills/memory-curate/references/scoring.md](plugins/tk-agent-team/skills/memory-curate/references/scoring.md) — reference-doc pattern for policy that skills consult but don't encode in prompts
- [plugins/tk-agent-team/.claude-plugin/plugin.json](plugins/tk-agent-team/.claude-plugin/plugin.json) — plugin manifest; must register every new agent and skill
- [.claude-plugin/marketplace.json](.claude-plugin/marketplace.json) — marketplace entry; must mirror plugin.json's new agent list
- [scripts/lint-agents.sh](scripts/lint-agents.sh) — frontmatter validator; may need extension for new required fields if the orchestrator uses a new frontmatter key (e.g., `dispatches_to:`)
- [CONTRIBUTING.md](CONTRIBUTING.md) — contribution guide; must gain a "Creating a new skill" section
- [examples/workflow-code-review.md](examples/workflow-code-review.md) — existing example; pattern for the new end-to-end example
- [examples/workflow-feature-development.md](examples/workflow-feature-development.md) — existing example; pattern for cross-family memory flow illustration
- [plugins/tk-agent-team/mcp-servers/agent-substrate/src/agent_substrate/server.py](plugins/tk-agent-team/mcp-servers/agent-substrate/src/agent_substrate/server.py) — MCP server; read-only reference — this plan does **not** modify the substrate, only uses its existing API
- [README.md](README.md) — root README; must be rewritten to present the full capability map

### New Files

**Agent definitions (8 files across 6 namespaces):**

- `plugins/tk-agent-team/agents/orchestrator.md` — solo agent; reads prompt + every relevant family memory; classifies task; dispatches skills with prepared context
- `plugins/tk-agent-team/agents/planner/product.md` — family persona; user stories, acceptance criteria, scope questions; writes to `docs/ideation/` and `docs/brainstorms/`
- `plugins/tk-agent-team/agents/planner/technical.md` — family persona; technical design, ADRs, implementation breakdown; writes to `docs/plans/`
- `plugins/tk-agent-team/agents/researcher.md` — solo agent; codebase archaeology, pattern identification, dependency mapping; produces context briefs that feed planner and debugger
- `plugins/tk-agent-team/agents/tester/unit.md` — family persona; unit test author; reads developer family memory for implementation context
- `plugins/tk-agent-team/agents/tester/integration.md` — family persona; integration and end-to-end scenario author; reads developer + reviewer family memory
- `plugins/tk-agent-team/agents/debugger.md` — solo agent; root cause investigation; reads researcher output, reviewer/correctness memory, and project logs; hands off to developer for the fix
- `plugins/tk-agent-team/agents/docs-writer.md` — solo agent; README, API reference, inline docs, and — critically — the `/compound` output files in `docs/solutions/`

**Skill definitions (9 files):**

- `plugins/tk-agent-team/skills/ideate/SKILL.md` — dispatches researcher + planner/product; output: `docs/ideation/<slug>.md`
- `plugins/tk-agent-team/skills/brainstorm/SKILL.md` — refines a selected idea into requirements; input: ideation doc, output: `docs/brainstorms/<slug>-requirements.md`
- `plugins/tk-agent-team/skills/plan/SKILL.md` — planner/technical + reviewer/architecture; input: brainstorm doc, output: `docs/plans/<slug>-plan.md`
- `plugins/tk-agent-team/skills/work/SKILL.md` — orchestrator routes to developer (frontend or backend or both in parallel); input: plan doc
- `plugins/tk-agent-team/skills/review/SKILL.md` — reviewer family (all three personas in parallel); input: branch/PR
- `plugins/tk-agent-team/skills/test/SKILL.md` — tester family; input: implementation diff; produces test files + coverage gap report
- `plugins/tk-agent-team/skills/debug/SKILL.md` — researcher → debugger → developer; input: failure description or error log
- `plugins/tk-agent-team/skills/ship/SKILL.md` — composite: `/work` → `/review` → `/test` sequentially
- `plugins/tk-agent-team/skills/compound/SKILL.md` — docs-writer + curator; captures solved problem to `docs/solutions/<category>/<slug>.md` and consolidates memory

**Skill reference docs (policy files consulted by skills, following `memory-curate/references/scoring.md` pattern):**

- `plugins/tk-agent-team/skills/ideate/references/rubric.md` — scoring rubric for ranking ideas
- `plugins/tk-agent-team/skills/plan/references/plan-schema.md` — required sections for a valid plan doc
- `plugins/tk-agent-team/skills/compound/references/categories.md` — canonical categories for `docs/solutions/`
- `plugins/tk-agent-team/skills/compound/references/solution-schema.md` — required sections for a solution doc

**Artifact directories (each with an explanatory README):**

- `docs/ideation/README.md`
- `docs/brainstorms/README.md`
- `docs/plans/README.md`
- `docs/solutions/README.md`

**Documentation and examples:**

- `examples/workflow-ideate-to-ship.md` — end-to-end walkthrough of `/compound "Add user profiles"`
- `examples/workflow-bug-debugging.md` — walkthrough of `/debug "users can't update their display name"`

## Implementation Phases

### Phase 1: Foundation

Establish the architectural primitives everything else depends on:

- Define the orchestrator's routing decision table — what prompt signals map to what skill, what skill maps to what team, and how memory reads are scoped per task type
- Define the artifact directory conventions — each `docs/<type>/` gets a README explaining its schema and naming
- Define the skill dispatch contract — what orchestrator writes to the brief file, what the target skill expects to find, and what the skill guarantees as output
- Extend the `_TEMPLATE.md` if any new frontmatter keys are required (e.g., `artifact_inputs:`, `artifact_outputs:`, `dispatches_to:`)
- Expand `scripts/lint-agents.sh` to validate any new required frontmatter

### Phase 2: Core Implementation

Build the agents and skills in parallel wherever possible. The orchestrator is the single sequential dependency — every skill references it, so it ships first inside this phase:

- Build the `orchestrator` agent with its full routing logic
- Build the five new agent families in parallel (planner, tester) and three solo agents (researcher, debugger, docs-writer) — all can run concurrently once the template conventions are locked
- Build the nine skills in parallel — each only depends on the orchestrator plus the specific family it dispatches
- Build the four `skills/*/references/*.md` policy files
- Update `plugin.json` and `marketplace.json` with the full agent + skill registry

### Phase 3: Integration & Polish

Wire the pieces together, document, and validate:

- Create the four `docs/` artifact directories with their READMEs
- Write the two new examples: end-to-end ideate→ship and bug-debugging
- Rewrite the root `README.md` to present the capability map (user-facing commands + agent families + memory model)
- Update `CONTRIBUTING.md` with the new "Creating a skill" and "Adding a new family" sections
- Update `agents/README.md` family registry with the five new rows
- Run the full validation suite: lint, pytest, manifest JSON validity, manual smoke test of each skill's frontmatter
- Commit with a clear message documenting what was added

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
  - Role: Designs the orchestrator's routing decision table, the skill-dispatch contract, and the artifact-directory conventions. Produces the foundation docs that every other task depends on. Does not write agent or skill markdown directly — their output is design notes the other team members consume.
  - Agent Type: Software Architect
  - Resume: true
- Builder
  - Name: agent-author
  - Role: Authors every new `.md` agent definition using the existing `_TEMPLATE.md` and the design notes from `architect`. Handles the orchestrator, both planner personas, both tester personas, the researcher, debugger, and docs-writer — eight files in total — with a consistent voice and memory-protocol compliance across all of them.
  - Agent Type: meta-agent
  - Resume: true
- Builder
  - Name: skill-author
  - Role: Authors every new `SKILL.md` plus the four reference-policy files under `skills/*/references/`. Follows the `memory-curate/SKILL.md` structure exactly — inputs, stages, invariants, write-back.
  - Agent Type: general-purpose
  - Resume: true
- Builder
  - Name: config-updater
  - Role: Updates `plugin.json`, `marketplace.json`, `scripts/lint-agents.sh`, and creates the four `docs/<type>/README.md` files. Handles structured configuration consistently.
  - Agent Type: general-purpose
  - Resume: true
- Builder
  - Name: docs-author
  - Role: Writes user-facing documentation: the two new `examples/workflow-*.md` files, the root `README.md` rewrite, and the `CONTRIBUTING.md` additions. Also updates `agents/README.md` family registry.
  - Agent Type: Technical Writer
  - Resume: true
- Builder
  - Name: validator
  - Role: Runs the full validation suite: `scripts/lint-agents.sh`, `pytest` in the MCP server directory, JSON validity checks on the manifests, and a manual walkthrough of each new skill's frontmatter contract. Reports any failures with specific file:line references. Starts fresh each run — no context carried between validation passes.
  - Agent Type: code-review
  - Resume: false

## Step by Step Tasks

- IMPORTANT: Execute every step in order, top to bottom. Each task maps directly to a `TaskCreate` call.
- Before you start, run `TaskCreate` to create the initial task list that all team members can see and execute.

### 1. Design Orchestrator Routing and Skill-Dispatch Contract

- **Task ID**: design-foundation
- **Depends On**: none
- **Assigned To**: architect
- **Agent Type**: Software Architect
- **Parallel**: false
- Define the orchestrator's prompt-classification decision table. Columns: signal phrases (e.g., "fix", "broken", "add", "implement"), inferred task type (bugfix / feature / refactor / exploration / planning / review / compound), skill to dispatch, families whose memory must be loaded before dispatch.
- Define the skill-dispatch contract. Every skill receives: (a) the user prompt, (b) relevant memory excerpts prepared by the orchestrator, (c) any input artifact files produced by prior skills. Every skill guarantees: (a) a named output artifact file, (b) a structured summary returned to the orchestrator, (c) memory-append calls for any discovered patterns.
- Define the artifact directory schema — for each of `docs/ideation/`, `docs/brainstorms/`, `docs/plans/`, `docs/solutions/`: required sections, naming convention (`<YYYY-MM-DD>-<slug>.md`), and what reads/writes each.
- Decide whether new frontmatter keys are needed (`dispatches_to:`, `artifact_inputs:`, `artifact_outputs:`). Recommend against them unless strictly required — inline prose in the agent's `## Workflow process` section is preferred for discoverability.
- Output: `specs/foundation-notes.md` — a single reference doc the agent-author and skill-author consult as their source of truth. Not shipped in the plugin; it is build-time scaffolding.

### 2. Create Artifact Directory Structure

- **Task ID**: create-artifact-dirs
- **Depends On**: design-foundation
- **Assigned To**: config-updater
- **Agent Type**: general-purpose
- **Parallel**: false
- Create `docs/ideation/`, `docs/brainstorms/`, `docs/plans/`, `docs/solutions/` directories at the repo root.
- For each, create a `README.md` that documents: purpose of the directory, required sections in documents, naming convention, which skills write here, which skills read here.
- Add a `.gitkeep` or sample placeholder file if needed to ensure the directories are tracked.
- Update `.gitignore` if any category of artifact should be excluded (recommended: none — artifacts are part of the project's durable record).

### 3. Extend Lint Script for New Conventions

- **Task ID**: extend-lint-script
- **Depends On**: design-foundation
- **Assigned To**: config-updater
- **Agent Type**: general-purpose
- **Parallel**: true (with create-artifact-dirs)
- Extend `scripts/lint-agents.sh` to: (a) validate `SKILL.md` files under `plugins/tk-agent-team/skills/` in addition to agent files, (b) check any new required frontmatter keys decided in `design-foundation`, (c) warn if a skill references an agent name that does not exist in `plugins/tk-agent-team/agents/`.
- Ensure the script continues to exit 0 on the current state (no regressions for existing agent files).
- Test locally against the current six agent files plus the one existing skill — must still return PASS.

### 4. Author the Orchestrator Agent

- **Task ID**: author-orchestrator
- **Depends On**: design-foundation
- **Assigned To**: agent-author
- **Agent Type**: meta-agent
- **Parallel**: false (every downstream skill references it)
- Create `plugins/tk-agent-team/agents/orchestrator.md`.
- Frontmatter: `name: orchestrator`, `color: "#EC4899"`, `emoji: 🧭`, `vibe: "Reads the prompt, reads the room, assembles the right team"`, tool allowlist includes all `mcp__agent-substrate__*` tools plus `Read, Grep, Glob, Bash`.
- Body follows the 8-section template. In `## Core mission`, embed the prompt-classification decision table from `design-foundation`. In `## Workflow process`, encode the step-by-step: load shared + every relevant family memory; classify; write a brief to `docs/<type>/<slug>.md`; dispatch the correct skill with that file path; receive the result; update `_shared.yaml` with project-level decisions.
- Include explicit examples of routing in the `## Your specialty` section: "fix X" → `/debug`, "add X" → `/ideate` or `/plan` or `/ship` depending on completeness signals, "review X" → `/review`, "what does X do" → researcher directly.

### 5. Author the Planner Family

- **Task ID**: author-planner-family
- **Depends On**: design-foundation
- **Assigned To**: agent-author
- **Agent Type**: meta-agent
- **Parallel**: true (with 6, 7, 8, 9)
- Create `plugins/tk-agent-team/agents/planner/product.md` and `plugins/tk-agent-team/agents/planner/technical.md`.
- Both use `name: planner` (shared family memory namespace). Distinct color/emoji/vibe per persona.
- product.md: identity is a PM who writes user stories with acceptance criteria; core mission covers scope definition, user-story decomposition, AC authoring; writes output to `docs/brainstorms/<slug>-requirements.md`.
- technical.md: identity is a staff engineer who translates requirements into a technical design with ADRs; core mission covers layer impact analysis, data-model changes, migration planning; writes output to `docs/plans/<slug>-plan.md`; memory protocol includes a cross-family read of `reviewer.yaml` for standing architectural decisions.
- Both follow the full 8-section template.

### 6. Author the Tester Family

- **Task ID**: author-tester-family
- **Depends On**: design-foundation
- **Assigned To**: agent-author
- **Agent Type**: meta-agent
- **Parallel**: true
- Create `plugins/tk-agent-team/agents/tester/unit.md` and `plugins/tk-agent-team/agents/tester/integration.md`.
- Both use `name: tester` (shared family memory).
- unit.md: authors unit tests for changed service/component logic; memory protocol includes cross-family reads of `developer.yaml` and `reviewer.yaml` (to know what edge cases reviewers flagged and what patterns developers applied).
- integration.md: authors integration and end-to-end scenarios; memory protocol includes the same cross-family reads.
- Both follow the full 8-section template.

### 7. Author the Researcher Agent

- **Task ID**: author-researcher
- **Depends On**: design-foundation
- **Assigned To**: agent-author
- **Agent Type**: meta-agent
- **Parallel**: true
- Create `plugins/tk-agent-team/agents/researcher.md` (solo).
- Identity: a specialist in codebase archaeology — traces patterns, maps dependencies, identifies constraints. Never implements.
- Core mission: produce context briefs that planner and debugger can consume. Outputs a structured summary: files touched, patterns in use, constraints that apply, open questions.
- Tool allowlist: `Read, Grep, Glob, WebSearch, WebFetch`, the memory tools, no `Edit/Write/Bash`.
- Follows the 8-section template.

### 8. Author the Debugger Agent

- **Task ID**: author-debugger
- **Depends On**: design-foundation
- **Assigned To**: agent-author
- **Agent Type**: meta-agent
- **Parallel**: true
- Create `plugins/tk-agent-team/agents/debugger.md` (solo).
- Identity: a root-cause investigator. Reads error logs, reproduces failures, traces execution paths. Produces a reproduction plan + root-cause hypothesis. Does not fix — hands off to developer family.
- Memory protocol: cross-family read of `reviewer.yaml` (for known pitfalls) and `researcher.yaml` (for context briefs if the researcher ran first).
- Follows the 8-section template.

### 9. Author the Docs-Writer Agent

- **Task ID**: author-docs-writer
- **Depends On**: design-foundation
- **Assigned To**: agent-author
- **Agent Type**: meta-agent
- **Parallel**: true
- Create `plugins/tk-agent-team/agents/docs-writer.md` (solo).
- Identity: a technical writer focused on durable documentation — READMEs, API references, inline docs, and the `docs/solutions/` files that the `/compound` skill produces.
- Memory protocol: cross-family read of **every** family's memory (this agent sees the whole system to document it).
- Follows the 8-section template.

### 10. Author the Ideate Skill

- **Task ID**: author-ideate-skill
- **Depends On**: author-orchestrator, author-planner-family, author-researcher
- **Assigned To**: skill-author
- **Agent Type**: general-purpose
- **Parallel**: true (with other skill tasks once dependencies clear)
- Create `plugins/tk-agent-team/skills/ideate/SKILL.md` plus `references/rubric.md`.
- SKILL.md: inputs (user prompt, optional domain hint); stage 1 — dispatch researcher for context; stage 2 — dispatch planner/product to generate 3–5 ranked ideas; stage 3 — write output to `docs/ideation/<YYYY-MM-DD>-<slug>.md`; invariants (every idea includes a tradeoff statement).
- references/rubric.md: scoring dimensions (user-value, engineering-cost, reversibility, alignment-with-memory), weights, and tie-breaking rules.

### 11. Author the Brainstorm Skill

- **Task ID**: author-brainstorm-skill
- **Depends On**: author-orchestrator, author-planner-family
- **Assigned To**: skill-author
- **Agent Type**: general-purpose
- **Parallel**: true
- Create `plugins/tk-agent-team/skills/brainstorm/SKILL.md`.
- Input: selected idea (typically an entry from a `docs/ideation/` file). Dispatches planner/product to write full requirements: user stories, acceptance criteria, out-of-scope statements, open questions. Output: `docs/brainstorms/<slug>-requirements.md`.

### 12. Author the Plan Skill

- **Task ID**: author-plan-skill
- **Depends On**: author-orchestrator, author-planner-family
- **Assigned To**: skill-author
- **Agent Type**: general-purpose
- **Parallel**: true
- Create `plugins/tk-agent-team/skills/plan/SKILL.md` plus `references/plan-schema.md`.
- Input: brainstorm doc path (or a raw spec). Stage 1 — dispatch planner/technical to draft the plan. Stage 2 — dispatch reviewer/architecture to review the draft and flag standing-decision conflicts. Stage 3 — planner/technical revises. Output: `docs/plans/<slug>-plan.md`.
- references/plan-schema.md: required sections (context, approach, layers affected, data-model changes, migration steps, test strategy, risks, rollback plan).

### 13. Author the Work Skill

- **Task ID**: author-work-skill
- **Depends On**: author-orchestrator
- **Assigned To**: skill-author
- **Agent Type**: general-purpose
- **Parallel**: true
- Create `plugins/tk-agent-team/skills/work/SKILL.md`.
- Input: plan doc path or a concrete task description. Orchestrator routes: frontend-only → developer/frontend; backend-only → developer/backend; full-stack → both in parallel. Output: committed code + a summary noting applied patterns and appended memory items.

### 14. Author the Review Skill

- **Task ID**: author-review-skill
- **Depends On**: author-orchestrator
- **Assigned To**: skill-author
- **Agent Type**: general-purpose
- **Parallel**: true
- Create `plugins/tk-agent-team/skills/review/SKILL.md`.
- Input: branch/PR identifier or an explicit diff. Dispatches reviewer/architecture, reviewer/correctness, reviewer/security in parallel. Stage 2 — merge findings, dedupe overlaps (e.g., if architecture and correctness both flag the same issue), produce a single structured report grouped by severity.
- Modes: report-only (default), autofix (dispatch developer family to apply safe fixes), interactive (pause for user decision on each finding).

### 15. Author the Test Skill

- **Task ID**: author-test-skill
- **Depends On**: author-orchestrator, author-tester-family
- **Assigned To**: skill-author
- **Agent Type**: general-purpose
- **Parallel**: true
- Create `plugins/tk-agent-team/skills/test/SKILL.md`.
- Input: implementation diff or a target path. Dispatches tester/unit and tester/integration in parallel. Output: new test files + a coverage gap report flagging untested branches.

### 16. Author the Debug Skill

- **Task ID**: author-debug-skill
- **Depends On**: author-orchestrator, author-researcher, author-debugger
- **Assigned To**: skill-author
- **Agent Type**: general-purpose
- **Parallel**: true
- Create `plugins/tk-agent-team/skills/debug/SKILL.md`.
- Input: failure description or error log. Stage 1 — dispatch researcher for context. Stage 2 — dispatch debugger for root-cause hypothesis. Stage 3 — dispatch reviewer/correctness to validate the hypothesis against the code. Stage 4 — hand off to developer for the fix. Output: `docs/solutions/bugs/<slug>.md` capturing the root cause and the fix (this feeds `/compound`).

### 17. Author the Ship Skill

- **Task ID**: author-ship-skill
- **Depends On**: author-work-skill, author-review-skill, author-test-skill
- **Assigned To**: skill-author
- **Agent Type**: general-purpose
- **Parallel**: false (composite — depends on the sub-skills existing)
- Create `plugins/tk-agent-team/skills/ship/SKILL.md`.
- Composite pipeline: `/work` → `/review` → `/test`. If `/review` returns blockers in report-only mode, halt and report back to the orchestrator for human input. If autofix mode, loop once through `/work` for fixes, then re-run `/review`.

### 18. Author the Compound Skill

- **Task ID**: author-compound-skill
- **Depends On**: author-orchestrator, author-docs-writer
- **Assigned To**: skill-author
- **Agent Type**: general-purpose
- **Parallel**: true
- Create `plugins/tk-agent-team/skills/compound/SKILL.md` plus `references/categories.md` and `references/solution-schema.md`.
- Input: a completed cycle or a solved problem. Stage 1 — dispatch docs-writer to author `docs/solutions/<category>/<slug>.md`. Stage 2 — dispatch the existing curator agent to consolidate patterns discovered during the cycle across every family whose memory was touched.
- references/categories.md: canonical solution categories (bug-fixes, features, refactors, integrations, performance, security).
- references/solution-schema.md: required sections (problem, root cause, solution, related patterns, applies-to).

### 19. Update Plugin and Marketplace Manifests

- **Task ID**: update-manifests
- **Depends On**: author-orchestrator, author-planner-family, author-tester-family, author-researcher, author-debugger, author-docs-writer, author-ideate-skill, author-brainstorm-skill, author-plan-skill, author-work-skill, author-review-skill, author-test-skill, author-debug-skill, author-ship-skill, author-compound-skill
- **Assigned To**: config-updater
- **Agent Type**: general-purpose
- **Parallel**: false
- Update `plugins/tk-agent-team/.claude-plugin/plugin.json`: register every new agent (orchestrator, planner, tester, researcher, debugger, docs-writer) with color/emoji/description; register every new skill under a `skills:` key if not already present.
- Update `.claude-plugin/marketplace.json`: mirror the plugin.json agent list with display metadata.
- Bump the plugin `version` to `0.2.0` to signal the major capability expansion.
- Validate JSON parses: `python -c "import json; json.load(open('plugins/tk-agent-team/.claude-plugin/plugin.json'))"`.

### 20. Update the Agents README Family Registry

- **Task ID**: update-agents-readme
- **Depends On**: author-orchestrator, author-planner-family, author-tester-family, author-researcher, author-debugger, author-docs-writer
- **Assigned To**: docs-author
- **Agent Type**: Technical Writer
- **Parallel**: true (with 19)
- Update `plugins/tk-agent-team/agents/README.md` family registry table with rows for: planner (family), tester (family), researcher (solo), debugger (solo), docs-writer (solo), orchestrator (solo — noted specially as the dispatcher for every skill).
- Add a short "Cross-family memory reads" expansion noting which new agents read from which memory files, so contributors can see the full topology at a glance.

### 21. Write the Ideate-to-Ship Example

- **Task ID**: write-ideate-to-ship-example
- **Depends On**: author-ship-skill, author-compound-skill
- **Assigned To**: docs-author
- **Agent Type**: Technical Writer
- **Parallel**: true
- Create `examples/workflow-ideate-to-ship.md` — walk through the prompt `/compound "Add user profiles with avatar upload"` from orchestrator classification through every skill step to final memory consolidation. Show the concrete files produced in each `docs/<type>/` directory and the memory items appended by each family.

### 22. Write the Bug-Debugging Example

- **Task ID**: write-debug-example
- **Depends On**: author-debug-skill
- **Assigned To**: docs-author
- **Agent Type**: Technical Writer
- **Parallel**: true
- Create `examples/workflow-bug-debugging.md` — walk through `/debug "users can't update their display name"` from orchestrator classification through researcher → debugger → developer → tester → compound. Emphasize how memory captured here accelerates future similar bugs.

### 23. Rewrite the Root README

- **Task ID**: rewrite-root-readme
- **Depends On**: update-manifests
- **Assigned To**: docs-author
- **Agent Type**: Technical Writer
- **Parallel**: true
- Rewrite `README.md` (repo root) to present the plugin's capability map: (a) user-facing commands with a one-line description of each, (b) the ten agents/families with their domain and vibe, (c) the memory model and why it matters, (d) a quickstart: "Install the plugin, run `/ideate 'your first feature'`, watch the team assemble."
- Keep it scannable — a two-minute read for a new user.

### 24. Update CONTRIBUTING.md

- **Task ID**: update-contributing
- **Depends On**: author-planner-family, author-tester-family, author-researcher, author-debugger, author-docs-writer, author-compound-skill
- **Assigned To**: docs-author
- **Agent Type**: Technical Writer
- **Parallel**: true
- Add a "Creating a new skill" section (parallel to the existing "Adding a new agent" section). Cover: the `SKILL.md` frontmatter contract, the stages pattern, the invariants list, when to add a `references/` file, how to register the skill in `plugin.json`.
- Add a short "Adding a new family" section expanding on the existing agent-family notes, with the new families as examples.

### 25. Final Validation

- **Task ID**: validate-all
- **Depends On**: update-agents-readme, write-ideate-to-ship-example, write-debug-example, rewrite-root-readme, update-contributing, update-manifests, create-artifact-dirs, extend-lint-script
- **Assigned To**: validator
- **Agent Type**: code-review
- **Parallel**: false
- Run `bash scripts/lint-agents.sh` — must exit 0 with zero errors across all fourteen agent files (six existing + eight new).
- Run `cd plugins/tk-agent-team/mcp-servers/agent-substrate && pytest` — must pass unchanged (this plan does not modify the substrate).
- Validate JSON: `python -c "import json; json.load(open('plugins/tk-agent-team/.claude-plugin/plugin.json')); json.load(open('.claude-plugin/marketplace.json'))"`.
- Grep for dangling references: every agent name referenced in a `SKILL.md` must correspond to a real agent file.
- Grep for artifact-directory references: every `docs/<type>/` mentioned in a skill or example must exist.
- Manually smoke-test each new `SKILL.md`: does the frontmatter have `name` and `description`? Does the body have stages and invariants?
- Report: PASS / FAIL per check, with file:line references for any failures.

## Acceptance Criteria

- `bash scripts/lint-agents.sh` returns PASS with 0 errors across all agent files
- `pytest` in the MCP server directory passes with no regressions
- `python -c "import json; json.load(open('plugins/tk-agent-team/.claude-plugin/plugin.json'))"` succeeds
- `python -c "import json; json.load(open('.claude-plugin/marketplace.json'))"` succeeds
- All eight new agent files exist, each under 6000 chars of body text, each following the 8-section template
- All nine new `SKILL.md` files exist, each following the `memory-curate/SKILL.md` structure (frontmatter + inputs + stages + invariants + write-back)
- `plugin.json` version is bumped to `0.2.0`
- `plugin.json` and `marketplace.json` register every new agent and skill with color + emoji metadata
- `docs/ideation/`, `docs/brainstorms/`, `docs/plans/`, `docs/solutions/` each exist with an explanatory `README.md`
- `examples/workflow-ideate-to-ship.md` and `examples/workflow-bug-debugging.md` exist and reference only real agent and skill names
- Root `README.md` presents the capability map and is under 300 lines
- `CONTRIBUTING.md` has a new "Creating a new skill" section with a worked example
- `plugins/tk-agent-team/agents/README.md` family registry lists every new family and solo
- No existing file was modified in a way that breaks the existing reviewer, developer, or curator contracts — the seven existing agent files parse identically before and after, aside from any cross-family read additions explicitly planned

## Validation Commands

Execute these commands to validate the task is complete:

- `bash scripts/lint-agents.sh` — validates every agent file's required frontmatter and recommended sections
- `cd plugins/tk-agent-team/mcp-servers/agent-substrate && pytest` — confirms MCP server tests still pass
- `python -c "import json; json.load(open('plugins/tk-agent-team/.claude-plugin/plugin.json'))"` — confirms plugin manifest parses
- `python -c "import json; json.load(open('.claude-plugin/marketplace.json'))"` — confirms marketplace manifest parses
- `ls -d docs/ideation docs/brainstorms docs/plans docs/solutions` — confirms all four artifact directories exist
- `find plugins/tk-agent-team/skills -name SKILL.md | wc -l` — expected output: `10` (one existing memory-curate + nine new)
- `find plugins/tk-agent-team/agents -name '*.md' -not -name '_*' -not -name 'README.md' | wc -l` — expected output: `14` (six existing + eight new)
- `grep -rl 'name: orchestrator' plugins/tk-agent-team/agents/` — expected to find exactly one file
- `grep -rln 'mcp__agent-substrate' plugins/tk-agent-team/agents/ | wc -l` — expected: every new agent file appears (proves memory protocol is included)
- Manual: open `examples/workflow-ideate-to-ship.md` and confirm every agent and skill named corresponds to a real file

## Notes

- **Scope discipline**: this plan intentionally does not modify the `agent-substrate` MCP server, the existing `reviewer`/`developer`/`curator` agents, or the existing `memory-curate` skill. The synthesis is purely additive — if any downstream task discovers a need to modify existing code, the validator must halt and escalate to the user for a scope decision.
- **Parallelism is the primary lever**: tasks 5 through 9 (the six new agents) can all run in parallel once task 4 completes. Tasks 10 through 18 (the nine skills) can mostly run in parallel once their agent dependencies clear. A competent team lead should dispatch in waves: wave 1 = foundation (1–3), wave 2 = agents (4 then 5–9 parallel), wave 3 = skills (10–16, 18 parallel; 17 after 13–15), wave 4 = integration (19–24 mostly parallel), wave 5 = validation (25).
- **Memory budget**: each new agent must stay under the 6000-char soft budget for its own memory file. The curator is configured to handle overflow, but designing for overflow means never hitting it.
- **Cross-family memory reads**: the new pattern introduced by the developer family (reading reviewer memory at task start) is extended here — planner/technical reads reviewer memory, tester reads developer+reviewer memory, debugger reads reviewer memory, docs-writer reads every family. The `## Memory protocol` section of each new agent must make these reads explicit.
- **Artifact durability**: the `docs/` directories are part of the project's durable record. They are committed. They are not regenerated from memory — memory captures patterns, artifacts capture specific decisions.
- **No new dependencies**: no `uv add` or `pnpm install` required. This plan ships pure Markdown plus JSON manifest updates plus shell-script extensions. If any task claims to need a new dependency, escalate.
- **Branch discipline**: execute the plan on a dedicated branch named `feature/super-agent-team-orchestration`. Do not merge to `main` until task 25 passes.
