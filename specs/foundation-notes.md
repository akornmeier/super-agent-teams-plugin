# Foundation Notes — Super Agent Team Orchestration

Build-time scaffolding for `agent-author` and `skill-author`. Not shipped in the plugin. Copy values from this doc verbatim — every field here is intentional.

---

## 1. Orchestrator classification decision table

The orchestrator embeds this table in its `## Core mission` section and uses it to classify every user prompt before dispatch. Match on any signal phrase (case-insensitive, substring). Ambiguous prompts fall through to the `exploration` row.

| Signal phrases | Task type | Skill to dispatch | Families pre-loaded |
|---|---|---|---|
| "fix", "broken", "not working", "can't", "won't", "unable", "error", "bug", "crash", "failing", "regression" | bugfix | `/debug` | `_shared`, `researcher`, `debugger`, `reviewer`, `developer` |
| "add", "implement", "build", "new", "create", "support for" | feature | `/ship` (if plan exists) else `/ideate` | `_shared`, `planner`, `developer`, `reviewer`, `tester` |
| "clean up", "refactor", "restructure", "rename", "extract", "simplify" | refactor | `/plan` then `/work` | `_shared`, `planner`, `developer`, `reviewer` |
| "what does", "how does", "where is", "why does", "explain" | exploration | researcher directly (no skill) | `_shared`, `researcher` |
| "plan", "design", "architect", "spec", "propose" | planning | `/plan` | `_shared`, `planner`, `reviewer` |
| "review", "check", "audit", "lint", "critique", "PR" | review | `/review` | `_shared`, `reviewer`, `developer` |
| "ship", "compound", "end-to-end", "full cycle", "cradle to grave" | compound-cycle | `/compound` | `_shared` + every family |

Notes for the orchestrator:
- If the prompt contains a `docs/plans/*.md` path, skip `/ideate` and `/plan` and jump to `/work` or `/ship`.
- If the prompt contains a stack trace or log excerpt, force `bugfix` regardless of other signals.
- If no signal matches, treat as `exploration`.

---

## 2. Skill-dispatch contract

Every skill invocation is a file-mediated handoff. The orchestrator writes a brief to a canonical path, names that path in the dispatch message, and the skill is guaranteed to find everything it needs in-file plus its memory reads.

### What the orchestrator passes to every skill

1. **User prompt** (verbatim) — embedded in the brief file header under `## Original prompt`.
2. **Pre-loaded memory excerpts** — the orchestrator reads the relevant family memories and writes a `## Relevant memory` section in the brief with bullet-point excerpts (pattern summaries, standing decisions). Keeps the skill's context window small.
3. **Input artifact file path** — absolute path to the prior-stage artifact (e.g., the `/plan` skill receives the path to a `docs/brainstorms/*.md` file). If none, the field reads `none`.

### What every skill guarantees back

1. **Named output artifact** — a single markdown file at the canonical path for its stage (see section 3). Path is returned in the structured summary.
2. **Structured summary** — a short YAML block with keys: `artifact_path`, `status` (`complete` | `blocked` | `needs_human`), `memory_appends` (list of agent names whose memory was appended), `next_skill_hint` (optional).
3. **Memory-append calls** — every agent the skill dispatched must have called `memory_append` for any discovered patterns/pitfalls/decisions before the skill returns.

### Concrete example

Orchestrator dispatches `/plan` after a brainstorm exists:

```
Skill: plan
Brief: docs/plans/2026-04-17-user-profiles-plan.md (to be created by skill)
Input artifact: docs/brainstorms/2026-04-17-user-profiles-requirements.md
Relevant memory (pre-loaded):
  - reviewer/architecture: "Standing decision: all new entities go through repository layer (ADR-004)"
  - planner: "Pattern: break plans into <=5 implementation phases"
User prompt: "Plan user profiles with avatar upload"
```

Skill returns:

```yaml
artifact_path: docs/plans/2026-04-17-user-profiles-plan.md
status: complete
memory_appends: [planner, reviewer]
next_skill_hint: /work
```

---

## 3. Artifact directory schema

Naming: `<YYYY-MM-DD>-<slug>.md` at every level. Slug is kebab-case derived from the prompt's noun phrase. Solutions add a category subdirectory.

### `docs/ideation/`
- **Purpose**: divergent exploration; 3–5 ranked ideas with tradeoffs.
- **Naming**: `<YYYY-MM-DD>-<slug>.md` (slug = topic, not a single idea).
- **Required sections**: `## Context`, `## Ideas` (each with `### Idea N: <title>`, `**Value**`, `**Cost**`, `**Tradeoff**`, `**Score**`), `## Recommendation`, `## Open questions`.
- **Written by**: `/ideate`.
- **Read by**: `/brainstorm`.

### `docs/brainstorms/`
- **Purpose**: one idea expanded into requirements.
- **Naming**: `<YYYY-MM-DD>-<slug>-requirements.md`.
- **Required sections**: `## Selected idea`, `## User stories` (As-a/I-want/So-that), `## Acceptance criteria` (Given/When/Then), `## Out of scope`, `## Open questions`.
- **Written by**: `/brainstorm`.
- **Read by**: `/plan`.

### `docs/plans/`
- **Purpose**: technical design ready to implement.
- **Naming**: `<YYYY-MM-DD>-<slug>-plan.md`.
- **Required sections**: `## Context`, `## Approach`, `## Layers affected`, `## Data-model changes`, `## Migration steps`, `## Test strategy`, `## Risks`, `## Rollback plan`, `## Implementation phases`.
- **Written by**: `/plan`.
- **Read by**: `/work`, `/ship`, `/test`.

### `docs/solutions/<category>/`
- **Purpose**: durable record of a solved problem; feeds future routing.
- **Categories** (canonical): `bug-fixes`, `features`, `refactors`, `integrations`, `performance`, `security`.
- **Naming**: `docs/solutions/<category>/<YYYY-MM-DD>-<slug>.md`.
- **Required sections**: `## Problem`, `## Root cause` (or `## Motivation` for non-bug), `## Solution`, `## Related patterns`, `## Applies to`.
- **Written by**: `/compound` (and `/debug` writes bug-fix entries as a side-effect).
- **Read by**: future orchestrator routing; `/ideate` consults for prior art; `curator` consults when consolidating.

---

## 4. Frontmatter recommendation

**Recommendation: do NOT add new required frontmatter keys to agents.** Keep the lint script simple and the authoring surface low-friction.

Rationale:
- The existing agent frontmatter (`name`, `description`, `tools`, `color`, `emoji`, `vibe`) is the complete contract for agent identity.
- Skill dispatch logic and artifact I/O are *behavior*, not *identity*. Behavior belongs in the agent body prose, specifically:
  - `## Workflow process` — encodes when to dispatch which skill and what artifact path to expect.
  - `## Your specialty` — encodes the routing examples and the "what I refuse to do" boundaries.
- Adding `dispatches_to:`, `artifact_inputs:`, or `artifact_outputs:` keys would duplicate prose, invite drift between frontmatter and body, and complicate the lint script.

**The single recommended extension**: `scripts/lint-agents.sh` should additionally validate every `plugins/tk-agent-team/skills/*/SKILL.md` requires frontmatter keys `name` and `description` (mirroring the `memory-curate` example). No other skill frontmatter keys are required.

---

## 5. Per-agent memory-read matrix

Every row is the set of memory files the agent reads at task start. `_shared` is implicit for all agents and not listed per-row.

| Agent | Own family read | Cross-family reads |
|---|---|---|
| orchestrator | (none — solo with no own memory; reads shared + every family below) | `planner`, `tester`, `researcher`, `debugger`, `docs-writer`, `reviewer`, `developer`, `curator` |
| planner/product | `planner` | — |
| planner/technical | `planner` | `reviewer` (for standing architectural decisions) |
| researcher | `researcher` | — (reads `_shared` only beyond own) |
| tester/unit | `tester` | `developer`, `reviewer` |
| tester/integration | `tester` | `developer`, `reviewer` |
| debugger | `debugger` | `reviewer`, `researcher` |
| docs-writer | `docs-writer` | `planner`, `tester`, `researcher`, `debugger`, `reviewer`, `developer`, `curator` (every family) |

Implementation note: cross-family reads are called out explicitly in each agent's `## Memory protocol` section as additional `mcp__agent-substrate__memory_read(agent_name="<family>")` calls at task start.

---

## 6. Agent frontmatter metadata table

Copy these verbatim into each agent's frontmatter. Vibes are single sentences designed to be memorable.

| Agent | Emoji | Color | Vibe |
|---|---|---|---|
| orchestrator | 🧭 | `#EC4899` | "Reads the prompt, reads the room, assembles the right team." |
| planner/product | 📋 | `#8B5CF6` | "Turns hand-waves into acceptance criteria you can verify." |
| planner/technical | 🏗️ | `#8B5CF6` | "Where hand-waves go to become ADRs and migration steps." |
| researcher | 🔬 | `#14B8A6` | "Never guesses — greps, reads, and returns receipts." |
| tester/unit | 🧪 | `#10B981` | "If it isn't covered, it isn't done." |
| tester/integration | 🧫 | `#10B981` | "Two services shaking hands under adversarial load." |
| debugger | 🐛 | `#EF4444` | "The bug is always in the last place you refused to look." |
| docs-writer | 📝 | `#F97316` | "Writes the README future-you will actually thank them for." |

(Family personas share the family color; distinct emojis per persona.)

---

## 7. Skill stage templates

Each skill-author expands these into the full `memory-curate`-style SKILL.md (frontmatter → inputs → stages → invariants → write-back).

### `/ideate`
Stage 1: dispatch `researcher` to produce a context brief (prior art, constraints, related `docs/solutions/` entries). Stage 2: dispatch `planner/product` to generate 3–5 ideas scored against `references/rubric.md`. Stage 3: write `docs/ideation/<YYYY-MM-DD>-<slug>.md` and append ranked list to `planner` memory.

### `/brainstorm`
Stage 1: load selected idea from the input ideation doc. Stage 2: dispatch `planner/product` to expand into user stories, acceptance criteria, out-of-scope, open questions. Stage 3: write `docs/brainstorms/<slug>-requirements.md` and append novel story patterns to `planner` memory.

### `/plan`
Stage 1: dispatch `planner/technical` to draft against `references/plan-schema.md`. Stage 2: dispatch `reviewer/architecture` to flag standing-decision conflicts. Stage 3: `planner/technical` revises; write `docs/plans/<slug>-plan.md` and append decisions to `planner` and `reviewer` memory.

### `/work`
Stage 1: parse plan doc; classify as frontend / backend / full-stack. Stage 2: dispatch `developer/frontend` and/or `developer/backend` in parallel (full-stack forks both). Stage 3: collect diffs, summarize applied patterns, append to `developer` memory.

### `/review`
Stage 1: dispatch `reviewer/architecture`, `reviewer/correctness`, `reviewer/security` in parallel against the diff. Stage 2: merge findings, dedupe overlaps, group by severity. Stage 3: emit consolidated report; optional autofix mode dispatches `developer` on safe fixes then re-runs stage 1.

### `/test`
Stage 1: dispatch `tester/unit` and `tester/integration` in parallel against the implementation diff. Stage 2: each tester writes test files and flags coverage gaps. Stage 3: produce a merged coverage-gap report and append novel edge-case patterns to `tester` memory.

### `/debug`
Stage 1: dispatch `researcher` for context brief. Stage 2: dispatch `debugger` for reproduction plan + root-cause hypothesis. Stage 3: dispatch `reviewer/correctness` to validate hypothesis against code. Stage 4: hand off to `developer` for fix; write `docs/solutions/bug-fixes/<slug>.md`.

### `/ship`
Composite. Stage 1: run `/work` against plan. Stage 2: run `/review` on resulting diff — halt and report if blockers surface in report-only mode, else loop once through `/work` in autofix mode. Stage 3: run `/test`; return a combined summary with artifact paths from every sub-skill.

### `/compound`
Stage 1: dispatch `docs-writer` to author `docs/solutions/<category>/<slug>.md` against `references/solution-schema.md` using `references/categories.md`. Stage 2: dispatch the existing `curator` agent against every family memory touched during the cycle to consolidate newly-appended patterns. Stage 3: return consolidated summary plus a list of curated memory files.

---

## Cross-references

- Agent template: `plugins/tk-agent-team/agents/_TEMPLATE.md`
- Canonical skill format: `plugins/tk-agent-team/skills/memory-curate/SKILL.md`
- Reference-doc pattern: `plugins/tk-agent-team/skills/memory-curate/references/scoring.md`
- Existing family memory namespaces: `reviewer`, `developer`, `curator` (do not touch).
- New family memory namespaces to be created on first append: `planner`, `tester`, `researcher`, `debugger`, `docs-writer`.
