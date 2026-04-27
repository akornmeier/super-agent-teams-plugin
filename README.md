# tk-agent-team

> An orchestrated team of specialist Claude Code agents with durable, curated memory — and a file-mediated workflow that turns "ship this feature" into a single prompt.

## The pitch

Most agent plugins give you one of three things: a clean workflow, deep specialists, or persistent memory. `tk-agent-team` gives you all three in one plugin. A single `orchestrator` agent reads your prompt, checks what the team already knows, and dispatches the right specialists in the right order — product planner, technical planner, developers across web/platform/data/AI, designers, framework experts, marketers, three flavors of reviewer, unit and integration testers, researcher, debugger, docs writer. Each one has its own durable YAML memory that survives sessions, so reviewers' complaints become developers' pre-applied fixes and debuggers remember the bug class they chased last week.

Handoffs are file-based, not in-context. The orchestrator writes a brief to `docs/ideation/`, `docs/brainstorms/`, `docs/plans/`, or `docs/solutions/`; the specialist reads that file, does its work, writes an artifact to the next directory, and appends what it learned to memory. The result is a system where workflow is durable (artifacts are committed to the repo), specialization is deep (every agent follows an 8-section personality template), and knowledge compounds across sessions (memory is curated, not discarded).

## How the skills work

The plugin ships ten **skills**, not traditional slash commands. Claude Code auto-invokes a skill when your prompt matches its description — saying "ideate on real-time collab" or "plan the auth rewrite" is usually enough. You can also invoke one explicitly via the `Skill` tool or by prefixing with the skill name (e.g. `/ideate ...`). Each skill dispatches a sequence of agents, writes an artifact to `docs/`, and requires every dispatched agent to append learnings to its family memory before returning.

| Skill | Trigger phrasing | What it produces |
|---|---|---|
| `ideate` | "explore options", "brainstorm", "ideas for", "what could we do about…" | 3–5 ranked, scored ideas with tradeoffs in `docs/ideation/` |
| `brainstorm` | "expand this idea", "flesh out", "acceptance criteria for…" | User stories + Given/When/Then criteria in `docs/brainstorms/` |
| `plan` | "technical plan", "design doc", "ADR for…", "how would we build…" | Layered plan with data model, migration, and risks in `docs/plans/` |
| `work` | "implement the plan", "build it", "write the code for…" | Working code — routes to frontend, backend, or parallel both |
| `review` | "review this code", "check for issues", "architecture/security review" | Merged, severity-ranked findings from architecture + correctness + security reviewers |
| `test` | "write tests", "cover this code", "add coverage for…" | Unit + integration tests in parallel, plus a coverage-gap report |
| `debug` | "this is broken", "stack trace", "why does X fail…" | Root-cause doc in `docs/solutions/bug-fixes/`: researcher → debugger → reviewer → developer |
| `ship` | "take this to done", "implement + review + test", "ship it" | Composite: `work` → `review` → `test` with halt-on-blocker |
| `compound` | end of a cycle; "capture what we learned" | Solution doc in `docs/solutions/` + curation of every touched family memory |
| `memory-curate` | auto-fires when a memory file approaches its soft limit | Shrunk memory file: dedupe → score-and-drop → summarize |

## The team

**30 personas across 8 families and 5 solos.** Every persona uses the same 8-section personality template and participates in the shared memory system.

**Dispatcher (solo)**
- 🧭 `orchestrator` — Reads the prompt, reads the room, assembles the right team. The only agent that reads every family's memory on every invocation.

**Planning** (`planner.yaml`)
- 📋 `planner/product` — Turns hand-waves into acceptance criteria you can verify.
- 🏗️ `planner/technical` — Where hand-waves go to become ADRs and migration steps.

**Implementation** (`developer.yaml`)
- 🎨 `developer/frontend` — UI, accessibility, form state, client validation.
- 🔧 `developer/backend` — Routes, services, repositories, migrations.

**Design** (`design.yaml`) — *added in v0.3.0*
- 🖼️ `design/ui-designer` — Visual systems, component libraries, tokens.
- 🔎 `design/ux-researcher` — User research synthesis and usability findings.
- 🗺️ `design/ux-architect` — Information architecture and interaction flows.
- 🛡️ `design/brand-guardian` — Brand coherence across surfaces.

**Framework specialists** (`framework.yaml`) — *added in v0.3.0*
- ⚛️ `framework/react` — Idiomatic React patterns, hooks, server components.
- 💚 `framework/vue` — Composition API, reactivity, Vue ecosystem.
- 🎞️ `framework/motion` — motion.dev / Framer Motion animation work.
- 🚀 `framework/astro` — Astro islands, content collections, SSR/SSG.

**Platform engineering** (`engineering.yaml`) — *added in v0.3.0*
- 🚢 `engineering/devops` — CI/CD, containers, deploy pipelines.
- 📟 `engineering/sre` — SLOs, observability, reliability engineering.
- 🗄️ `engineering/data-engineer` — Pipelines, warehouses, transformations.
- 🤖 `engineering/ai-engineer` — LLM integration, embeddings, evals, RAG.

**Review** (`reviewer.yaml`)
- 🏛️ `reviewer/architecture` — Layer violations, abstraction cost, coupling.
- ✅ `reviewer/correctness` — Logic, edge cases, error paths.
- 🔒 `reviewer/security` — Trust boundaries, input handling, auth.

**Testing** (`tester.yaml`)
- 🧪 `tester/unit` — If it isn't covered, it isn't done.
- 🧫 `tester/integration` — Two services shaking hands under adversarial load.

**Marketing** (`marketing.yaml`) — *added in v0.3.0*
- ✍️ `marketing/content-creator` — Editorial, long-form, multi-channel copy.
- 📈 `marketing/growth-hacker` — Experiment design, funnels, viral loops.
- 🔍 `marketing/seo-specialist` — Technical + content SEO and SERP strategy.
- 📣 `marketing/social-strategist` — Cross-platform social campaigns.

**Investigation (solos)**
- 🔬 `researcher` — Never guesses; greps, reads, and returns receipts. (`researcher.yaml`)
- 🐛 `debugger` — The bug is always in the last place you refused to look. (`debugger.yaml`)

**Writing & memory (solos)**
- 📝 `docs-writer` — Writes the README future-you will actually thank them for. Cross-reads every family. (`docs-writer.yaml`)
- 🗃️ `curator` — Memory gardener; runs dedupe → score-drop → summarize when a file overflows. (`curator.yaml`)

## The memory model

**Per-agent YAML files.** Each agent (or family) has its own YAML file under `.agent-memory/`. Families share a namespace — all three `reviewer` personas contribute to `reviewer.yaml`, so their knowledge is pooled.

**Skill-layer memory brokering.** Subagents (dispatched via the Agent tool) do not have direct MCP server access. Instead, the **skill layer** (running in the parent session) handles all memory I/O: it calls `memory_read` before dispatching a subagent and passes the content as `## Memory context` in the prompt, then parses the `## Memory findings` YAML block from the subagent's response and calls `memory_append` to persist it. This ensures memory is always read and written reliably, regardless of subagent capabilities.

**A shared file for project conventions.** `_shared.yaml` holds the whole-team facts: language, framework, house style, standing decisions. Every skill reads it before dispatching agents. The orchestrator is the only agent that writes to it — for consensus decisions the team converged on mid-cycle.

**Curation on overflow, not on schedule.** Every memory file has an 8000-char soft limit and a 10000-char hard limit. When a write approaches the soft limit, the MCP server returns a `warning`; once a write hits the hard limit, it returns `needs_curation: true` and the write is rejected. The skill then dispatches the `curator` via `memory-curate`: three stages (dedupe → score-and-drop → summarize) that shrink the file while protecting load-bearing items. Storage is dumb; curation is policy.

## Quickstart

```bash
# 1. Create a virtualenv and install the MCP server
cd plugins/tk-agent-team/mcp-servers/agent-substrate
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cd ../../../..

# 2. Confirm tests pass
cd plugins/tk-agent-team/mcp-servers/agent-substrate
source .venv/bin/activate
pytest
cd ../../../..

# 3. Register the plugin marketplace (one-time, in ~/.claude/settings.json)
#    Add to "extraKnownMarketplaces":
#      "tk-agent-team": {
#        "source": { "source": "directory", "path": "/path/to/tk-agent-team" }
#      }
#    Add to "enabledPlugins":
#      "tk-agent-team@tk-agent-team": true

# 4. Ensure the agent teams flag is set (in ~/.claude/settings.json "env" block
#    or in your shell profile):
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1

# 5. Open Claude Code in any project and try it:
#    "ideate on real-time collaborative editing"
#    "what could we do about real-time collab"
#    /ideate real-time collaborative editing
```

The MCP server creates `.agent-memory/` in whatever project directory Claude Code is opened in. Each project gets its own isolated memory. Verify the MCP server is connected by running `/mcp` in your Claude Code session — you should see `plugin:tk-agent-team:agent-substrate` with a green checkmark.

From there, `brainstorm` → `plan` → `ship` takes one ranked idea to shipped code. Run `compound` at the end of a cycle to capture the solution and consolidate what the team learned.

## Tips for users

- **Skills trigger on intent, not exact wording.** Each skill's description lists the phrasing that fires it (see the frontmatter `description` field in each `plugins/tk-agent-team/skills/*/SKILL.md`). If auto-detection misses, prefix with the skill name: `/plan migrate to Postgres`.
- **Every run writes an artifact.** Check `docs/ideation/`, `docs/brainstorms/`, `docs/plans/`, or `docs/solutions/` after each skill — that file is the handoff for the next stage.
- **Memory lives in `.agent-memory/`.** Inspect `<family>.yaml` to see what a team remembers; `_shared.yaml` holds project-wide conventions. Delete a file if you want a clean slate.
- **Don't call individual agents directly for end-to-end work.** Let the skill dispatch them — skills handle all memory I/O (reading before dispatch, writing after return) that makes the team get smarter. Subagents don't have direct MCP access; the skill layer brokers it. Use direct `Agent` invocations only for one-off specialist questions (but note: those won't read or write memory).
- **Cross-cycle learning is opt-in.** Run `compound` when a feature or fix lands to promote scattered learnings into a durable solution doc + curated memory.

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
│       │   ├── developer/    { frontend.md, backend.md }
│       │   ├── reviewer/     { architecture.md, correctness.md, security.md }
│       │   ├── planner/      { product.md, technical.md }
│       │   ├── tester/       { unit.md, integration.md }
│       │   ├── design/       { ui-designer.md, ux-researcher.md, ux-architect.md, brand-guardian.md }
│       │   ├── framework/    { react.md, vue.md, motion.md, astro.md }
│       │   ├── engineering/  { devops.md, sre.md, data-engineer.md, ai-engineer.md }
│       │   └── marketing/    { content-creator.md, growth-hacker.md, seo-specialist.md, social-strategist.md }
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
