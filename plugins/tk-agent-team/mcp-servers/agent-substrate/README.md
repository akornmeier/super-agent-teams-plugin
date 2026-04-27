# agent-substrate

An MCP server providing per-agent YAML memory with curation hygiene, designed for use with Claude Code Agent Teams.

## What it does

Five tools:

- `memory_read(agent_name)` — load an agent's expertise file
- `memory_write(agent_name, content)` — replace the entire file (validated, size-capped)
- `memory_append(agent_name, section, item)` — add one item without rewriting
- `memory_read_shared()` — load the project-wide shared memory file
- `memory_append_shared(section, item)` — add one item to the shared file

Every write is schema-validated, character-count enforced (soft 8000, hard 10000), atomic, and protected by a file lock.

## Why it exists

Agent Teams in Claude Code spawn each teammate as a fresh subagent with no memory of previous runs. This MCP server provides durable per-agent expertise files that persist across sessions. Files live on disk as YAML so they're git-trackable, human-editable, and amenable to review.

**Important architecture note:** Subagents dispatched via the Agent tool do NOT have access to MCP server tools — only the parent session does. The skill layer (running in the parent session) is responsible for all memory I/O: it calls `memory_read` before dispatching a subagent, passes the content in the prompt, then parses structured findings from the subagent's response and calls `memory_append` to persist them.

The hard size cap is the load-bearing feature: it forces consolidation rather than hoarding, and it routes curation through a separate dispatch (the `memory-curate` skill) instead of letting an agent self-edit.

## Install

```bash
cd mcp-servers/agent-substrate
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Wire into Claude Code

The plugin's `.mcp.json` handles this automatically. It uses [`uv run`](https://docs.astral.sh/uv/) so the server starts without manual venv management — `uv` resolves the environment from the project's `pyproject.toml` on demand. Requires `uv` to be installed ([install guide](https://docs.astral.sh/uv/)).

```json
{
  "mcpServers": {
    "agent-substrate": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "${CLAUDE_PLUGIN_ROOT}/mcp-servers/agent-substrate",
        "agent-substrate"
      ],
      "env": {
        "AGENT_SUBSTRATE_BASE_DIR": "${CLAUDE_PROJECT_DIR}/.agent-memory"
      }
    }
  }
}
```

The server defaults to `.agent-memory/` relative to the working directory (which Claude Code sets to the project root). To use a custom location, set the `AGENT_SUBSTRATE_BASE_DIR` environment variable to an absolute path.

The tool names exposed to the parent session are `mcp__agent-substrate__memory_read`, `mcp__agent-substrate__memory_write`, etc. Only the orchestrator agent and the skill layer call these directly — subagents receive memory context via their prompt and return findings in a structured format.

Verify the server is connected by running `/mcp` in Claude Code — you should see `plugin:tk-agent-team:agent-substrate` with a green checkmark.

To enable Agent Teams, set this in `~/.claude/settings.json` under `"env"`:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

## Memory file schema

```yaml
version: 1
updated: "2026-04-14T15:30:00Z"   # set automatically on every write
patterns:
  - id: virtualized-tables-for-large-data
    summary: Use react-virtual for tables with >500 rows
    evidence: Reduced render time 80% on Deque dashboard project
    protected: false
pitfalls:
  - id: aria-live-overuse
    summary: Don't use aria-live=assertive for non-critical updates
    why: Screen readers interrupt user reading flow
    protected: true
decisions:
  - id: prefer-tailwind
    choice: Use Tailwind utility classes over CSS modules for new components
    rationale: Faster iteration, smaller bundle when purged
    supersedes: null
    protected: false
open_questions:
  - id: server-components-ssr-strategy
    question: Should we use React Server Components for the marketing site?
    protected: false
```

`protected: true` is a hint for the curator agent — it should not delete or modify protected items during consolidation. **The MCP server itself does not enforce this**; it's enforced in the curation skill. This is intentional separation of concerns: the storage layer is dumb, the curator is smart.

## Character limits

- **Soft limit: 8000 characters** — writes succeed but return a `warning` field.
- **Hard limit: 10000 characters** — writes are rejected with `needs_curation: true`.

Measured in Unicode code points (Python `len()` on a `str`), not bytes or tokens. 10000 characters is roughly 2500–3300 tokens depending on content density.

When an agent receives `needs_curation: true`, it should **not** retry by truncating the content itself. It should instead message the orchestrator to dispatch the curator. The curation skill is the only place where deletion logic lives.

## Agent name rules

Agent names must match `^[a-z][a-z0-9-]{0,63}$`:

- Lowercase letters, digits, hyphens
- Must start with a letter
- Max 64 characters
- No path separators, dots, spaces, or underscores

Enforced both for slug consistency and as a defense against path traversal.

## File locking and concurrency

Each write acquires an exclusive file lock via `portalocker` with a 10-second timeout. Writes are atomic: content is written to a temp file in the same directory, fsynced, and renamed over the target. Concurrent writers serialize, not corrupt.

In Agent Teams, every teammate spawns its own copy of this MCP server as a stdio subprocess. They all read and write the same files on disk, so the locking matters even though the server itself is stateless.

**Manual concurrency check** (the test suite doesn't exercise real parallel processes):

```bash
# In two terminals, simultaneously hammer the same agent's memory:
python -c "
from agent_substrate.storage import MemoryStorage
s = MemoryStorage('./test-mem')
for i in range(100):
    r = s.append('agent-a', 'patterns', {'id': f'p{i}', 'summary': f'item {i}'})
    print(r.ok)
"
```

Run this in two terminals at once. Final file should have ~200 distinct items, no corruption, no duplicates.

## Run the tests

```bash
source .venv/bin/activate
pytest
```

## What this server deliberately does NOT do

- **It does not curate.** Curation is policy, not storage; it lives in the `memory-curate` skill and is dispatched by the orchestrator.
- **It does not enforce `protected: true`.** That's a curator concern.
- **It does not version history.** If you want history, commit `.agent-memory/` to git and let git track it.
- **It does not handle inter-agent messaging.** That's what `SendMessage` from Agent Teams is for.
- **It does not provide `memory_write_shared`.** The shared file is append-only via this server; wholesale rewrites should be done by humans or a privileged curator process. If you need that later, add it as a new tool with a different name (`memory_replace_shared`) so the privilege boundary stays explicit.
- **It does not preserve YAML comments.** Writes are re-serialized from the validated Pydantic model, which strips comments. If you want notes on individual items, use a field like `evidence` or `rationale` rather than YAML comments.

## License

MIT.
