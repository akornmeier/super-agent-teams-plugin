# agents/

Each `.md` file in this directory is a teammate definition. There are two
layouts: **solo teammates** (a single `.md` at this level) and **agent
families** (a subdirectory of related personas that share one memory
namespace).

## Solo teammate

The filename (without extension) must match the `name:` in the frontmatter
and the slug passed to `mcp__agent-substrate__memory_read(agent_name=...)`.

1. Copy `_TEMPLATE.md` to `<teammate-name>.md`
2. Fill in the frontmatter `name`, `description`, and `tools` allowlist
3. Fill in the `## Your specialty` section at the bottom
4. Keep the `## Memory protocol` section **verbatim** — it's load-bearing
   for how the team shares durable knowledge via agent-substrate.

## Agent family

An agent family is a subdirectory (`agents/<family>/`) where multiple
personas share a single memory namespace. All personas in the family use
the **family slug** (not their filename) as `agent_name` in memory calls.

For example, all files under `agents/reviewer/` call:
```
mcp__agent-substrate__memory_read(agent_name="reviewer")
```

This means a lesson the security persona learns on Monday is available to
the correctness persona on Tuesday — collective intelligence, not siloed
knowledge.

### Adding a persona to an existing family

1. Copy any existing persona file within the family directory
2. Update frontmatter `name` to the **family slug** (not the filename)
3. Update `description` to describe this persona's specific trigger conditions
4. Fill in `## Your specialty` to define the persona's focus area
5. Keep `## Memory protocol` verbatim — change only the `agent_name` string
   to the family slug

### Creating a new family

1. Create `agents/<family-name>/`
2. Add at least one persona `.md` file using the family slug as `name:`
3. All personas in the family use `agent_name="<family-name>"` in memory calls

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
