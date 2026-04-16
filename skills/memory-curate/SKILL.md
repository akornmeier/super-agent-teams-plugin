---
name: memory-curate
description: Use when an agent's memory file has exceeded the soft or hard character limit and needs consolidation. Runs three stages in order — dedupe, score-and-drop, summarize — and stops as soon as the file is under the soft limit. Invoked by the orchestrator when `needs_curation: true` is returned from `mcp__agent-substrate__memory_write` or `mcp__agent-substrate__memory_append`, or proactively when a `warning` is returned near the soft limit.
---

# memory-curate

You are curating an agent's YAML memory file. The storage layer is dumb; **you are the policy**. Your job is to shrink the file below the 6000-character soft limit while losing as little real signal as possible.

## Inputs you will be given

- `agent_name` — the slug of the agent whose memory is being curated (or the literal string `_shared` for the shared file)
- Optionally: the last error from the MCP server (e.g. `"Memory exceeds hard limit (8213 > 8000 chars)"`)

## Read the current state

Call `mcp__agent-substrate__memory_read` with the `agent_name` (or `memory_read_shared` for the shared file). Parse the YAML. Note the current `char_count` and decide how much you need to trim. Target: **under 6000 chars after curation**, not merely under 8000.

## The three stages

Run these **in order**. After each stage, estimate the new character count. Stop as soon as you're under the soft limit. Never skip a stage — even if you think you're close, run dedupe first because it is loss-free.

### Stage 1: Dedupe and consolidate (loss-free)

- Collapse items with identical or near-identical `summary`/`choice`/`question` into a single item. Prefer the version with better `evidence`/`rationale`/`why`.
- Merge items where one is a strict superset of another.
- **Never touch items where `protected: true`** — these are load-bearing decisions the agent has marked as non-negotiable.

### Stage 2: Score and drop the weakest (lossy)

Score every unprotected item on a 0–10 scale using the rubric in `scoring.md` (in this skill directory). Drop the lowest-scoring items until you are under the soft limit.

**See `scoring.md` for the rubric.** Do not invent your own weights — the rubric is the policy and changing it is a deliberate act, not a per-curation decision.

### Stage 3: Summarize clusters (last resort, lossy with signal preservation)

If stages 1–2 can't get you under the soft limit without dropping protected items or items scoring above the drop threshold, cluster the remaining items by theme and replace each cluster of N items with a single meta-item whose `evidence`/`rationale` references the cluster members' signal.

- Give each meta-item a new id prefixed with `meta-` (e.g. `meta-aria-patterns`).
- Never summarize across sections (never merge a `pattern` with a `pitfall`).
- Never summarize protected items.

## Write back

Call `mcp__agent-substrate__memory_write` with the curated YAML. If the write still returns `needs_curation: true`, you have a bug in your stage-3 summarization; do not truncate — report the failure to the orchestrator with a diagnostic.

## Invariants (never violate)

- `protected: true` items survive all three stages.
- No section merging.
- `id` collisions are forbidden after curation. If dedupe produces duplicate ids, rename with a `-v2` suffix, not deletion.
- Never add information that was not derivable from the pre-curation state. Curation compresses; it does not invent.
