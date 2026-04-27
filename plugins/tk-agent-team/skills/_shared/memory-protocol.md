<!-- Canonical memory protocol for tk-agent-team v0.4. Single source of truth — -->
<!-- SKILL.md and agent files reference sections here via: <!-- @ref _shared/memory-protocol.md#<anchor> --> -->
<!-- DO NOT copy this prose into individual SKILL.md files. Reference it. -->

# Memory Protocol (canonical)

Three layers, three responsibilities. Never duplicate a read across layers.

## Layer responsibilities

<!-- @ref _shared/memory-protocol.md#layer-orchestrator -->
### Orchestrator layer
- Reads `_shared` ALWAYS.
- Reads the **routed family only** (per `routing.yaml` lookup) — not all 12 families.
- Reads augmentation families if the prompt matched augmentation triggers (`framework`, `design`, `engineering`, `marketing`).
- Owns serialized writes to `_shared.yaml` via `memory_append_shared(section, item)`. No teammate writes `_shared` directly — teammates DM the team-lead (or surface the proposal back to the orchestrator for solo skills) with the proposed item; the team-lead/orchestrator validates and commits via `memory_append_shared`. (`memory_findings_submit` cannot target `_shared` because the `agent` slug must match `^[a-z][a-z0-9-]{0,63}$`.)
- Does NOT pre-load specialist cross-family memory — that lives at the teammate layer.

<!-- @ref _shared/memory-protocol.md#layer-skill -->
### Skill layer
- Reads anything the skill body explicitly needs to seed teammate context (typically nothing — teammates self-load).
- Composes the brief artifact path; teammates read the brief, not parent prose.
- For team-based skills, the skill calls `TeamCreate` then hands control to the team-lead. The skill itself does not own ongoing memory reads after that.

<!-- @ref _shared/memory-protocol.md#layer-teammate -->
### Teammate layer
- Reads own family memory at task start: `mcp__agent-substrate__memory_read(agent_name="<own-family>")`.
- Reads cross-family memory per the matrix in `specs/foundation-notes.md` section 5 (e.g., tester reads `developer` + `reviewer`; debugger reads `reviewer` + `researcher`; docs-writer reads every family). These reads stay at the teammate layer — they did not move to the orchestrator and did not move to the skill.
- Reads team scratch: `mcp__agent-substrate__team_memory_read(team_name="<team>")` if part of a team.
- Submits findings at task end via `memory_findings_submit` — see below.

## `_shared` write serialization

Only the team-lead (or the orchestrator, for solo skills) writes to `_shared` — and they do it via `memory_append_shared(section, item)`, which is the only tool that writes the shared namespace. This prevents two teammates appending the same standing decision concurrently and racing the lock file. Teammates that want to propose a `_shared` update DM the team-lead with the proposed `{section, item}`; the team-lead reviews and commits via `memory_append_shared`. (`memory_findings_submit` rejects `agent="_shared"` because the agent slug must match `^[a-z][a-z0-9-]{0,63}$`.)

## Findings submission (load-bearing)

<!-- @ref _shared/memory-protocol.md#findings-current -->
### Current pattern (v0.4 — required for new code)

Every teammate calls `mcp__agent-substrate__memory_findings_submit` directly at task end. Schema is enforced at the substrate boundary (Pydantic, `extra="forbid"`). Invalid findings are rejected loudly with actionable error. See `_shared/findings-schema.md` for the contract.

```python
mcp__agent-substrate__memory_findings_submit(
    agent="reviewer-security",
    findings=[
        {
            "agent": "reviewer",
            "section": "pitfalls",
            "item": {
                "kind": "pitfall",
                "summary": "Hard-coded credentials in auth.py",
                "evidence": "auth.py:42",
                "why": "Triggers our standing security policy violation",
            },
        },
    ],
)
```

<!-- @ref _shared/memory-protocol.md#findings-deprecated -->
### Legacy pattern (DEPRECATED — grandfathered in v0.4, removed in v0.5)

Older agents emit a `## Memory findings` YAML block in their final response. The substrate parses it for backward compatibility. **Do not use this in new code.** It fails open: a missing or malformed block silently drops the learning, which contradicts the plugin's compound-knowledge thesis.

```markdown
## Memory findings

- agent: reviewer-security
  section: pitfalls
  item:
    kind: pitfall
    summary: Hard-coded credentials in auth.py
```

The v0.5 cutover will remove the prose parser. Tracker: see `specs/team-orchestration-v0.4.md` migration safety net section.

## Direct teammate MCP access

With `TeamCreate`, teammates spawned via `Agent(team_name=..., name=...)` are full agents with full tool allowlists, **including `mcp__agent-substrate__*`**. They read and submit memory directly. The "skill is the broker" rule from v0.3 only applies to legacy one-shot subagent dispatches that never received MCP tool grants. New team-based code MUST NOT add a parent-broker hop.

## Worked example: a teammate task lifecycle

```python
# Task start — load context.
shared = mcp__agent-substrate__memory_read(agent_name="_shared")
own    = mcp__agent-substrate__memory_read(agent_name="tester")
xref_dev = mcp__agent-substrate__memory_read(agent_name="developer")   # per matrix
xref_rev = mcp__agent-substrate__memory_read(agent_name="reviewer")    # per matrix
team_scratch = mcp__agent-substrate__team_memory_read(team_name="ship-2026-04-26-user-profiles")

# ... do the work (write tests, identify coverage gaps, etc.) ...

# Task end — submit findings via the validated tool.
mcp__agent-substrate__memory_findings_submit(
    agent="tester-unit",
    findings=[
        {
            "agent": "tester",
            "section": "patterns",
            "item": {
                "kind": "pattern",
                "summary": "Avatar upload tests must mock S3 client at module-level, not call site",
                "evidence": "tests/test_avatar_upload.py:24",
            },
        },
    ],
)

# Acknowledge shutdown_request only AFTER findings are submitted.
```

## Side-by-side: deprecated vs current

| Aspect              | Deprecated prose YAML            | Current `memory_findings_submit`          |
|---------------------|----------------------------------|-------------------------------------------|
| Wire format         | Markdown `## Memory findings`    | MCP tool call with Pydantic body          |
| Validation          | Best-effort YAML parse           | Schema-enforced, `extra="forbid"`         |
| Failure mode        | Silent loss on malformed block   | Loud rejection with actionable error      |
| Caller              | Subagent emits, parent parses    | Teammate calls directly                   |
| Status in v0.4      | Parsed for backward compat       | Required for new code                     |
| Status in v0.5      | Removed                          | Required                                  |
