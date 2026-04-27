---
name: memory-curate
description: Use when an agent's memory file has exceeded the soft or hard character limit and needs consolidation. Runs three stages in order — dedupe, score-and-drop, summarize — and stops as soon as the file is under the soft limit. Invoked by the orchestrator when `needs_curation: true` is returned from `mcp__agent-substrate__memory_write` or `mcp__agent-substrate__memory_append`, or proactively when a `warning` is returned near the soft limit.
team_pattern: solo
---

# memory-curate

You are curating an agent's YAML memory file. The storage layer is dumb; **you are the policy**. Your job is to shrink the file below the 8000-character soft limit while losing as little real signal as possible.

## Inputs you will be given

- `agent_name` — the slug of the agent whose memory is being curated (or the literal string `_shared` for the shared file)
- Optionally: the last error from the MCP server (e.g. `"Memory exceeds hard limit (10243 > 10000 chars)"`)

## Memory protocol (skill layer)

<!-- @ref _shared/memory-protocol.md -->

This skill follows the canonical memory protocol in `skills/_shared/memory-protocol.md`. See that file for the read-before / persist-after contract, the `_shared` write serialization rule, and the deprecated `## Memory findings` legacy path.

### Memory deltas for this skill

This skill is a **whole-file replacement** pipeline, not an append pipeline — it deviates from the canonical `memory_findings_submit` end-of-task contract intentionally.

- **Skill-layer read of the target file**: call `mcp__agent-substrate__memory_read(agent_name=TARGET)` (or `mcp__agent-substrate__memory_read_shared()` if `TARGET` is `_shared`) to obtain the current YAML content and `char_count`. Pass the full YAML to the curator subagent under `## Current memory YAML`.
- **Skill-layer write to replace the curated file**: after the curator returns, this skill calls `mcp__agent-substrate__memory_write(agent_name=TARGET, content=CURATED_YAML)` directly to overwrite the file with the curated YAML. This is the one place in the plugin where `memory_write` is called — every other skill uses `memory_append` or `memory_findings_submit`.
- **Curator subagent has no MCP access by design**: the curator is a pure YAML-to-YAML transformer. It receives the input YAML in its prompt and returns the output YAML in `## Curated YAML`. It does not submit findings via `memory_findings_submit` — its output *is* the curated file, not findings about a file.
- If the post-curation `memory_write` still returns `needs_curation: true`, report failure to the orchestrator with a diagnostic. Never truncate.

## The three stages (curator subagent instructions)

The curator subagent receives the full YAML content and performs these stages, returning the curated YAML. Run these **in order**. After each stage, estimate the new character count. Stop as soon as you're under the soft limit. Never skip a stage — even if you think you're close, run dedupe first because it is loss-free.

### Stage 1: Dedupe and consolidate (loss-free)

- Collapse items with identical or near-identical `summary`/`choice`/`question` into a single item. Prefer the version with better `evidence`/`rationale`/`why`.
- Merge items where one is a strict superset of another.
- **Never touch items where `protected: true`** — these are load-bearing decisions the agent has marked as non-negotiable.

### Stage 2: Score and drop the weakest (lossy)

Score every unprotected item on a 0–10 scale using the rubric in `references/scoring.md`. Drop the lowest-scoring items until you are under the soft limit.

**See `references/scoring.md` for the rubric.** Do not invent your own weights — the rubric is the policy and changing it is a deliberate act, not a per-curation decision.

### Stage 3: Summarize clusters (last resort, lossy with signal preservation)

If stages 1–2 can't get you under the soft limit without dropping protected items or items scoring above the drop threshold, cluster the remaining items by theme and replace each cluster of N items with a single meta-item whose `evidence`/`rationale` references the cluster members' signal.

- Give each meta-item a new id prefixed with `meta-` (e.g. `meta-aria-patterns`).
- Never summarize across sections (never merge a `pattern` with a `pitfall`).
- Never summarize protected items.

## Curator subagent output format

The curator subagent must return its response with these sections:
1. `## Curation summary` — what was deduped, dropped, or summarized, and the resulting char count
2. `## Curated YAML` — the complete curated YAML content, ready to be written back via `memory_write`

## Write back

This skill (not the subagent) calls `mcp__agent-substrate__memory_write(agent_name=TARGET, content=CURATED_YAML)` with the curated YAML extracted from the curator's response. If the write still returns `needs_curation: true`, you have a bug in the curator's stage-3 summarization; do not truncate — report the failure to the orchestrator with a diagnostic.

## Invariants (never violate)

- `protected: true` items survive all three stages.
- No section merging.
- `id` collisions are forbidden after curation. If dedupe produces duplicate ids, rename with a `-v2` suffix, not deletion.
- Never add information that was not derivable from the pre-curation state. Curation compresses; it does not invent.
