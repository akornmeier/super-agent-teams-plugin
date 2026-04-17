# agent-substrate

An MCP server providing per-agent YAML memory with curation hygiene, designed for use with Claude Code Agent Teams.

## What it does

Five tools:

- `memory_read(agent_name)` — load an agent's expertise file
- `memory_write(agent_name, content)` — replace the entire file (validated, size-capped)
- `memory_append(agent_name, section, item)` — add one item without rewriting
- `memory_read_shared()` — load the project-wide shared memory file
- `memory_append_shared(section, item)` — add one item to the shared file

Every write is schema-validated, character-count enforced (soft 6000, hard 8000), atomic, and protected by a file lock.

## Why it exists

Agent Teams in Claude Code spawn each teammate as a fresh Claude Code session with no memory of previous runs. This MCP server gives each teammate a durable expertise file it can read at the start of a task and update at the end. Files live on disk as YAML so they're git-trackable, human-editable, and amenable to review.

The hard size cap is the load-bearing feature: it forces agents to consolidate rather than hoard, and it routes curation through a separate dispatch (the orchestrator) instead of letting an agent self-edit in the same turn it just used the memory.

## Install

```bash
cd mcp-servers/agent-substrate
pip install -e .
```

Or with `uv`:

```bash
uv pip install -e .
```

## Wire into Claude Code

Add to your project's `.claude/settings.json`:

```json
{
  "experimental": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "mcpServers": {
    "agent-substrate": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "agent_substrate"]
    }
  }
}
```

If you want a custom location for memory files (default is `./.agent-memory` relative to wherever Claude Code is launched):

```json
{
  "mcpServers": {
    "agent-substrate": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "agent_substrate"],
      "env": {
        "AGENT_SUBSTRATE_BASE_DIR": "/absolute/path/to/.agent-memory"
      }
    }
  }
}
```

The tool names exposed to agents will be `mcp__agent-substrate__memory_read`, `mcp__agent-substrate__memory_write`, etc. Reference these in each agent's `tools` allowlist.

> **Note on `experimental` settings key:** I'm ~70% confident on the exact JSON shape for the experimental flag. The official docs consistently show it as the env var form `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. If putting it in `settings.json` doesn't take effect, set it as an environment variable in your shell before launching Claude Code: `export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.

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

- **Soft limit: 6000 characters** — writes succeed but return a `warning` field.
- **Hard limit: 8000 characters** — writes are rejected with `needs_curation: true`.

Measured in Unicode code points (Python `len()` on a `str`), not bytes or tokens. 8000 characters is roughly 2000–2500 tokens depending on content density.

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
pip install -e ".[dev]"
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
