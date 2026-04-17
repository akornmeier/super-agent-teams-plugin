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

## Agent family registry

| Family | Personas | Memory namespace | Purpose |
|--------|----------|-----------------|---------|
| `reviewer` | architecture, correctness, security | `reviewer.yaml` | Code review — catches structural, logic, and security issues |
| `developer` | frontend, backend | `developer.yaml` | Implementation — builds features using established patterns with cross-family reviewer memory reads |
| `curator` | (solo) | `curator.yaml` | Memory management — runs the curation pipeline on demand |
| `planner` | product, technical | `planner.yaml` | Product requirements + technical design; the `technical` persona cross-reads `reviewer.yaml` for standing architectural decisions |
| `tester` | unit, integration | `tester.yaml` | Unit + integration test authoring; both personas cross-read `developer.yaml` and `reviewer.yaml` for applied patterns and flagged edge cases |
| `researcher` | (solo) | `researcher.yaml` | Codebase archaeology — maps patterns, dependencies, and constraints; produces context briefs the planner and debugger consume |
| `debugger` | (solo) | `debugger.yaml` | Root-cause investigation; cross-reads `reviewer.yaml` (known pitfalls) and `researcher.yaml` (context briefs); hands off the fix to `developer` |
| `docs-writer` | (solo) | `docs-writer.yaml` | Technical writing — READMEs, API refs, and `docs/solutions/` files; cross-reads **every** family's memory |
| `orchestrator` | (solo — dispatcher) | (no own file — reads all) | Prompt classification + skill routing; the only agent that reads every family memory on every invocation |

### Cross-family memory reads

Cross-family reads are how learnings propagate between teams. The full topology:

| Reader | Own memory | Also reads |
|--------|-----------|------------|
| `developer` | `developer.yaml` | `reviewer.yaml` — so reviewers' accumulated complaints become developers' pre-applied fixes |
| `planner/technical` | `planner.yaml` | `reviewer.yaml` — so standing architectural decisions shape every plan |
| `tester/unit` | `tester.yaml` | `developer.yaml`, `reviewer.yaml` — so tests mirror applied patterns and cover reviewer-flagged edges |
| `tester/integration` | `tester.yaml` | `developer.yaml`, `reviewer.yaml` — same reasoning as unit, scoped to cross-service contracts |
| `debugger` | `debugger.yaml` | `reviewer.yaml`, `researcher.yaml` — past pitfalls and current context brief accelerate root-cause work |
| `docs-writer` | `docs-writer.yaml` | `planner.yaml`, `tester.yaml`, `researcher.yaml`, `debugger.yaml`, `reviewer.yaml`, `developer.yaml`, `curator.yaml` — sees the whole system to document it |
| `orchestrator` | (none) | `_shared` plus every family file above — classification decisions get smarter over time |

Solo agents with no listed cross-reads (`researcher`, `curator`) read only their own file plus `_shared.yaml`. Family personas that share a namespace (e.g. all three `reviewer` personas) always read the same family file — so a lesson the security persona learns on Monday is available to the correctness persona on Tuesday.

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
