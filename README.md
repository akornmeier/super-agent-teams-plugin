# tk-agent-team

A Claude Code plugin for building Agent Teams with durable, curated,
per-agent memory.

## What's in the box

| Piece | Location | Purpose |
| --- | --- | --- |
| `agent-substrate` MCP server | `plugins/tk-agent-team/mcp-servers/agent-substrate/` | YAML-backed memory storage for each teammate, with file locks, atomic writes, and a hard character cap. |
| `.mcp.json` | `plugins/tk-agent-team/` | Wires `agent-substrate` into the plugin; memory lives at `${CLAUDE_PROJECT_DIR}/.agent-memory/`. |
| `memory-curate` skill | `plugins/tk-agent-team/skills/memory-curate/` | Three-stage curator (dedupe → score-drop → summarize) dispatched when the hard limit trips. |
| Teammate definitions | `plugins/tk-agent-team/agents/` | Domain-specialist agents. Start from `agents/_TEMPLATE.md`. |
| Plugin manifest | `plugins/tk-agent-team/.claude-plugin/plugin.json` | Required Claude Code plugin metadata. |
| Marketplace index | `.claude-plugin/marketplace.json` | Root registry listing all plugins in this repo. |

## Design in one paragraph

Agent Teams spawn each teammate as a fresh Claude Code process — no
memory carries over. `agent-substrate` gives each teammate a durable YAML
file it reads at task start and appends to at task end. A **hard 8000-char
limit** on each file forces consolidation: when the limit trips, the
MCP server returns `needs_curation: true` and the offending teammate
is expected to message the orchestrator, which dispatches the separate
`memory-curate` skill. **Storage is dumb; curation is policy.** Keeping
them in different processes means the curator is never pressured to
cheat to fit a pending write.

## Setup

```bash
# 1. Install the MCP server in editable mode
cd plugins/tk-agent-team/mcp-servers/agent-substrate
uv pip install -e ".[dev]"
cd ../../../..

# 2. Verify tests pass
cd plugins/tk-agent-team/mcp-servers/agent-substrate
pytest
cd ../../../..

# 3. Enable Agent Teams in your Claude Code settings if not already:
#    export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

The plugin's `.mcp.json` auto-registers the server when the plugin is
active.

## Build your team

See `plugins/tk-agent-team/agents/README.md` for how to add a teammate.
The `_TEMPLATE.md` file has a **required memory protocol section** —
keep it verbatim so every teammate shares the same read-at-start /
append-at-end contract.

Agent families live under `agents/<family>/` — each `.md` in a family
shares the same memory namespace (e.g. all files in `agents/reviewer/`
call `memory_read(agent_name="reviewer")`). Use families when multiple
personas need to pool their learnings.

## Tune the curator

The scoring rubric that decides which memory items survive Stage 2 of
curation lives in `plugins/tk-agent-team/skills/memory-curate/references/scoring.md`.
That file is designed to be edited — weights and the drop threshold are
policy, not code. Tune it to match what your specific teammates need to
remember.

## Layout

```
.
├── .claude-plugin/
│   └── marketplace.json           # root registry — lists all plugins
└── plugins/
    └── tk-agent-team/
        ├── .claude-plugin/
        │   └── plugin.json        # plugin manifest
        ├── .mcp.json              # registers agent-substrate
        ├── agents/                # teammate definitions
        │   ├── _TEMPLATE.md       # copy this to add a solo teammate
        │   ├── README.md
        │   └── <family>/          # agent families share a memory namespace
        │       └── <persona>.md
        ├── skills/
        │   └── memory-curate/
        │       ├── SKILL.md               # three-stage pipeline
        │       └── references/
        │           └── scoring.md         # tunable scoring rubric
        └── mcp-servers/
            └── agent-substrate/
                ├── src/agent_substrate/   # MCP server package
                ├── tests/
                ├── pyproject.toml
                └── README.md
```
