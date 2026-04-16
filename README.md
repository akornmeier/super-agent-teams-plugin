# tk-agent-team

A Claude Code plugin for building Agent Teams with durable, curated,
per-agent memory.

## What's in the box

| Piece | Location | Purpose |
| --- | --- | --- |
| `agent-substrate` MCP server | `mcp-servers/agent-substrate/` | YAML-backed memory storage for each teammate, with file locks, atomic writes, and a hard character cap. |
| `.mcp.json` | repo root | Wires `agent-substrate` into the plugin; memory lives at `${CLAUDE_PROJECT_DIR}/.agent-memory/`. |
| `memory-curate` skill | `skills/memory-curate/` | Three-stage curator (dedupe → score-drop → summarize) dispatched when the hard limit trips. |
| Teammate definitions | `agents/` | Domain-specialist agents. Start from `agents/_TEMPLATE.md`. |
| Plugin manifest | `.claude-plugin/plugin.json` | Required Claude Code plugin metadata. |

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
cd mcp-servers/agent-substrate
uv pip install -e ".[dev]"
cd ../..

# 2. Verify tests pass from the new layout
cd mcp-servers/agent-substrate
pytest
cd ../..

# 3. Enable Agent Teams in your Claude Code settings if not already:
#    export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

The plugin's `.mcp.json` auto-registers the server when the plugin is
active.

## Build your team

See `agents/README.md` for how to add a teammate. The `_TEMPLATE.md`
file has a **required memory protocol section** — keep it verbatim so
every teammate shares the same read-at-start / append-at-end contract.

## Tune the curator

The scoring rubric that decides which memory items survive Stage 2 of
curation lives in `skills/memory-curate/scoring.md`. That file is
designed to be edited — weights and the drop threshold are policy, not
code. Tune it to match what your specific teammates need to remember.

## Layout

```
.
├── .claude-plugin/plugin.json     # plugin manifest
├── .mcp.json                      # registers agent-substrate
├── agents/                        # teammate definitions (one .md per teammate)
│   ├── _TEMPLATE.md
│   └── README.md
├── skills/
│   └── memory-curate/
│       ├── SKILL.md               # three-stage pipeline
│       └── scoring.md             # tunable scoring rubric
└── mcp-servers/
    └── agent-substrate/
        ├── src/agent_substrate/   # MCP server package
        ├── tests/
        ├── pyproject.toml
        └── README.md              # MCP server's own docs
```
