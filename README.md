# tk-agent-team

> An orchestrated team of specialist Claude Code agents with durable, curated memory — and a file-mediated workflow that turns "ship this feature" into a single prompt.

## The pitch

Most agent plugins give you one of three things: a clean workflow, deep specialists, or persistent memory. `tk-agent-team` gives you all three in one plugin. A single `orchestrator` agent reads your prompt, checks what the team already knows, and dispatches the right specialists in the right order — product planner, technical planner, frontend or backend developer, three flavors of reviewer, unit and integration testers, researcher, debugger, docs writer. Each one has its own durable YAML memory that survives sessions, so reviewers' complaints become developers' pre-applied fixes and debuggers remember the bug class they chased last week.

Handoffs are file-based, not in-context. The orchestrator writes a brief to `docs/ideation/`, `docs/brainstorms/`, `docs/plans/`, or `docs/solutions/`; the specialist reads that file, does its work, writes an artifact to the next directory, and appends what it learned to memory. The result is a system where workflow is durable (artifacts are committed to the repo), specialization is deep (every agent follows an 8-section personality template), and knowledge compounds across sessions (memory is curated, not discarded).

## User-facing commands

| Command | What it does |
|---|---|
| `/ideate` | Generate 3–5 ranked ideas with tradeoffs for a topic |
| `/brainstorm` | Expand one idea into user stories + acceptance criteria |
| `/plan` | Produce a technical plan with layers, data-model, migration, and risks |
| `/work` | Implement a plan — routes to frontend, backend, or both in parallel |
| `/review` | Architecture + correctness + security review, merged and severity-ranked |
| `/test` | Author unit and integration tests; report coverage gaps |
| `/debug` | Root-cause a failure: researcher → debugger → reviewer → developer |
| `/ship` | Composite — `/work` → `/review` → `/test` in sequence |
| `/compound` | Capture the solved problem to `docs/solutions/` and curate touched memory |

## The team

Ten agents across five families and five solos. Every persona uses the same 8-section personality template.

**Dispatcher**
- 🧭 `orchestrator` — Reads the prompt, reads the room, assembles the right team.

**Planning**
- 📋 `planner/product` — Turns hand-waves into acceptance criteria you can verify.
- 🏗️ `planner/technical` — Where hand-waves go to become ADRs and migration steps.

**Implementation**
- 🎨 `developer/frontend` — UI, accessibility, form state, client validation.
- 🔧 `developer/backend` — Routes, services, repositories, migrations.

**Review**
- 🏛️ `reviewer/architecture` — Layer violations, abstraction cost, coupling.
- ✅ `reviewer/correctness` — Logic, edge cases, error paths.
- 🔒 `reviewer/security` — Trust boundaries, input handling, auth.

**Testing**
- 🧪 `tester/unit` — If it isn't covered, it isn't done.
- 🧫 `tester/integration` — Two services shaking hands under adversarial load.

**Investigation**
- 🔬 `researcher` — Never guesses; greps, reads, and returns receipts.
- 🐛 `debugger` — The bug is always in the last place you refused to look.

**Writing & memory**
- 📝 `docs-writer` — Writes the README future-you will actually thank them for.
- 🗃️ `curator` — Memory gardener; runs dedupe → score-drop → summarize when a file overflows.

## The memory model

**Per-agent YAML files.** Each agent (or family) has its own YAML file under `.agent-memory/`. The agent reads it at task start and appends discovered patterns, pitfalls, and decisions at task end. Families share a namespace — all three `reviewer` personas read and write to `reviewer.yaml`, so their knowledge is pooled.

**A shared file for project conventions.** `_shared.yaml` holds the whole-team facts: language, framework, house style, standing decisions. Every agent reads it on every invocation. The orchestrator is the only agent that writes to it — for consensus decisions the team converged on mid-cycle.

**Curation on overflow, not on schedule.** Every memory file has a 6000-char soft limit and an 8000-char hard limit. When a write approaches the limit, the MCP server returns a warning and the orchestrator dispatches the `curator` to run `memory-curate`: three stages (dedupe → score-and-drop → summarize) that shrink the file while protecting load-bearing items. Storage is dumb; curation is policy.

## Quickstart

```bash
# 1. Install the MCP server in editable mode
cd plugins/tk-agent-team/mcp-servers/agent-substrate
uv pip install -e ".[dev]"
cd ../../../..

# 2. Confirm tests pass
cd plugins/tk-agent-team/mcp-servers/agent-substrate && pytest && cd ../../../..

# 3. Enable agent teams (one-time, in your shell profile)
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1

# 4. Try it
#    In Claude Code:
/ideate "real-time collaborative editing for our doc app"
```

From there, `/brainstorm` → `/plan` → `/ship` moves you from one ranked idea to shipped code. When the cycle completes, `/compound` captures the solution and consolidates what the team learned.

## Layout

```
.
├── .claude-plugin/
│   └── marketplace.json              # root registry — lists all plugins
├── docs/                             # file-mediated handoff artifacts
│   ├── ideation/                     # /ideate output
│   ├── brainstorms/                  # /brainstorm output
│   ├── plans/                        # /plan output
│   └── solutions/                    # /compound + /debug output
│       ├── bug-fixes/
│       ├── features/
│       ├── refactors/
│       ├── integrations/
│       ├── performance/
│       └── security/
├── examples/
│   ├── workflow-code-review.md
│   ├── workflow-feature-development.md
│   ├── workflow-ideate-to-ship.md
│   └── workflow-bug-debugging.md
├── plugins/
│   └── tk-agent-team/
│       ├── .claude-plugin/plugin.json
│       ├── .mcp.json                 # registers agent-substrate
│       ├── agents/
│       │   ├── _TEMPLATE.md
│       │   ├── README.md
│       │   ├── orchestrator.md
│       │   ├── curator.md
│       │   ├── researcher.md
│       │   ├── debugger.md
│       │   ├── docs-writer.md
│       │   ├── developer/ { frontend.md, backend.md }
│       │   ├── reviewer/  { architecture.md, correctness.md, security.md }
│       │   ├── planner/   { product.md, technical.md }
│       │   └── tester/    { unit.md, integration.md }
│       ├── skills/
│       │   ├── memory-curate/
│       │   ├── ideate/
│       │   ├── brainstorm/
│       │   ├── plan/
│       │   ├── work/
│       │   ├── review/
│       │   ├── test/
│       │   ├── debug/
│       │   ├── ship/
│       │   └── compound/
│       └── mcp-servers/agent-substrate/   # YAML memory substrate
└── scripts/lint-agents.sh
```

## Learn more

- [CONTRIBUTING.md](CONTRIBUTING.md) — how to add agents, families, and skills
- [plugins/tk-agent-team/agents/README.md](plugins/tk-agent-team/agents/README.md) — family registry and cross-family memory topology
- [specs/foundation-notes.md](specs/foundation-notes.md) — source of truth for orchestrator routing, skill-dispatch contract, and artifact schemas
- [examples/workflow-ideate-to-ship.md](examples/workflow-ideate-to-ship.md) — end-to-end feature walkthrough
- [examples/workflow-bug-debugging.md](examples/workflow-bug-debugging.md) — `/debug` walkthrough
