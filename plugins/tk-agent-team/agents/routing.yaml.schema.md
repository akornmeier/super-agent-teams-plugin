<!-- Schema contract for the future `agents/routing.yaml` data file. -->
<!-- This document defines the shape only. Task 12 (orchestrator-author) populates -->
<!-- the actual data. Lint and `tests/test_routing.py` validate against this schema. -->

# `routing.yaml` Schema (contract)

The orchestrator's classification table moves from markdown prose in `orchestrator.md` to a data file at `plugins/tk-agent-team/agents/routing.yaml`. This document is the contract Task 12 implements against.

## Top-level shape

```yaml
rules: [Rule, ...]
overrides: [Override, ...]
```

Both keys are required (use `[]` if empty). No other top-level keys are permitted.

## `Rule`

A rule maps user-prompt signals to a dispatched skill plus its team configuration.

```yaml
- signals: [string, ...]            # required; list of regex or substring patterns (case-insensitive)
  task_type: string                  # required; one of: bugfix | feature | refactor | exploration | planning | review | compound-cycle
  skill: string                      # required; e.g. "/debug", "/ship", or "researcher" for a direct-agent path
  team_pattern: string               # required; one of: solo | pair | parallel-panel | pipeline | staged-team | feature-team
  families: [string, ...]            # required; pre-loaded family memory namespaces (always includes "_shared")
  augmentations:                     # optional; additive families gated on extra triggers
    - trigger: string                # e.g. "framework", "marketing", "design", "engineering"
      families: [string, ...]
```

Field semantics:
- `signals` — phrases or regexes. The orchestrator matches case-insensitive substring by default; an entry wrapped in `re:/.../` is interpreted as a regex.
- `task_type` — coarse classification used in metrics and downstream skill routing decisions.
- `skill` — the canonical skill or direct-agent dispatch target. A literal skill command (`/debug`) or a bare agent name (`researcher`) are both valid.
- `team_pattern` — the catalog value from `_shared/team-protocol.md` (one of: `solo`, `pair`, `parallel-panel`, `pipeline`, `staged-team`, `feature-team`). The lint script validates each SKILL.md's frontmatter `team_pattern` against this catalog. Cross-checking that a rule's `team_pattern` agrees with the dispatched skill's frontmatter `team_pattern` is the responsibility of `tests/test_routing.py` (Task 12), not lint.
- `families` — the minimum pre-load set for this rule. Always include `_shared`. Specialist cross-family reads remain at the teammate layer (per `_shared/memory-protocol.md`) and MUST NOT be duplicated here.
- `augmentations` — additive family pre-loads gated on additional prompt signals. Stack ON TOP of `families`, never replace.

## `Override`

An override forces classification when a strong signal is present, regardless of the matching rule.

```yaml
- condition: string                  # required; named condition (e.g. "stack_trace_present", "plan_path_present")
  force_skill: string                # optional; overrides the matched rule's skill
  force_task_type: string            # optional; overrides the matched rule's task_type
```

At least one of `force_skill` or `force_task_type` is required per override.

## Stacking and precedence semantics

1. **Rule match.** The first rule whose `signals` match the prompt is selected. Rules are tried top-to-bottom — order in the file is the precedence order.
2. **Augmentation stacking.** If the prompt also matches one or more `augmentations[*].trigger` values on the selected rule, those augmentation families are **added** to the rule's `families` (set union, not replacement). Multiple augmentations stack.
3. **Override application.** All `overrides` are evaluated AFTER rule match. If an override `condition` is met, its `force_*` fields replace the corresponding fields from the rule. Overrides win against rules. If multiple overrides match, the first wins (file order is precedence).
4. **Final pre-load.** The orchestrator pre-loads `_shared` + the resolved `families` + any augmentation additions. No other family memory is read at the orchestrator layer.

## Worked example (illustrative — Task 12 owns the real data)

```yaml
rules:
  - signals: ["fix", "broken", "not working", "bug", "crash", "regression"]
    task_type: bugfix
    skill: /debug
    team_pattern: pipeline
    families: [researcher, debugger, reviewer, developer]

  - signals: ["add", "implement", "build", "new feature"]
    task_type: feature
    skill: /ship
    team_pattern: staged-team
    families: [planner, developer, reviewer, tester]
    augmentations:
      - trigger: framework
        families: [framework]
      - trigger: marketing
        families: [marketing]

  - signals: ["review", "audit", "PR"]
    task_type: review
    skill: /review
    team_pattern: parallel-panel
    families: [reviewer, developer]

overrides:
  - condition: stack_trace_present
    force_skill: /debug
    force_task_type: bugfix

  - condition: plan_path_present
    force_skill: /work
```

## Validation expectations (for lint and tests)

- `rules[*].team_pattern` MUST be one of the six catalog values.
- `rules[*].families[*]` and `augmentations[*].families[*]` MUST be either `_shared` or a real family directory under `agents/`.
- `rules[*].skill` MUST resolve to either a real `skills/<skill>/SKILL.md` or a real agent name.
- `overrides[*].force_skill` MUST resolve as above.
- The dispatched skill's frontmatter `team_pattern` MUST equal the rule's `team_pattern` (cross-checked by `tests/test_routing.py`; lint validates each SKILL.md's `team_pattern` against the catalog independently).
- `tests/test_routing.py` (Task 12) loads this file and asserts `(skill, team_pattern, families)` for ≥20 historical prompt fixtures, including: happy paths per rule, override paths (stack-trace force), and augmentation stacking ("ship the React landing page with growth tracking" → base `families` + `framework` + `marketing`).
