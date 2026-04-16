# agents/

Each `.md` file in this directory is a teammate definition. The filename
(without extension) must match the `name:` in the frontmatter and the
slug passed to `mcp__agent-substrate__memory_read(agent_name=...)`.

## Adding a new teammate

1. Copy `_TEMPLATE.md` to `<teammate-name>.md`
2. Fill in the frontmatter `name`, `description`, and `tools` allowlist
3. Fill in the `## Your specialty` section at the bottom
4. Keep the `## Memory protocol` section **verbatim** — it's load-bearing
   for how the team shares durable knowledge via agent-substrate.

## Naming rules

Teammate names must match `^[a-z][a-z0-9-]{0,63}$` (enforced by the MCP
server as a path-traversal defense):

- lowercase letters, digits, hyphens
- must start with a letter
- max 64 chars
- no dots, underscores, or path separators

The `_TEMPLATE.md` file is excluded from the team because it starts with
an underscore, which is not a valid agent name slug.

## Tool allowlist

The template grants the five agent-substrate tools plus the standard
read/edit/bash set. Tighten per-teammate — e.g. a pure-research agent
might have only `Read, Grep, Glob, WebFetch` plus the memory tools and
no `Edit`/`Write`/`Bash` at all. Narrower allowlists make teammate
behavior more predictable.
