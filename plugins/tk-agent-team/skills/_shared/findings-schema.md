<!-- Canonical schema reference for the `Finding` Pydantic model. -->
<!-- SKILL.md authors and substrate-engineer reference here via: <!-- @ref _shared/findings-schema.md#<anchor> --> -->
<!-- Contract document. Python implementation lives in -->
<!-- `mcp-servers/agent-substrate/src/agent_substrate/schema.py` (task 3). -->

# `Finding` Schema (canonical)

The wire format for `mcp__agent-substrate__memory_findings_submit`. Every teammate submits findings against this schema. Validation is enforced at the substrate boundary; invalid findings are rejected loudly with an actionable error (not silently dropped — that was the v0.3 prose-parsing bug).

## Vocabulary consistency rule (load-bearing)

`section` and `item.kind` express the same vocabulary in two places. They MUST agree:

| `section`         | `item.kind`       |
|-------------------|-------------------|
| `patterns`        | `pattern`         |
| `pitfalls`        | `pitfall`         |
| `decisions`       | `decision`        |
| `open_questions`  | `open_question`   |

The substrate validates this consistency. Mismatched (`section="patterns"` + `kind="pitfall"`) is rejected.

## Models

<!-- @ref _shared/findings-schema.md#model-finding -->
### `Finding`

Required fields:
- `agent: str` — must match `^[a-z][a-z0-9-]{0,63}$`. Identifies the family memory namespace this finding will be appended to. Use `_shared` only via team-lead-mediated submission.
- `section: Literal["patterns", "pitfalls", "decisions", "open_questions"]` — top-level memory section.
- `item: FindingItem` — the structured payload.

Pydantic config: `model_config = {"extra": "forbid"}`.

<!-- @ref _shared/findings-schema.md#model-finding-item -->
### `FindingItem`

Required fields:
- `kind: Literal["pattern", "pitfall", "decision", "open_question"]` — must agree with parent `section` per the consistency rule above.
- `summary: str` — one-line human-readable summary.

Optional fields (all default `None` unless noted):
- `id: str | None` — stable id; substrate generates one if omitted.
- `evidence: str | None` — file:line or other locator that grounds the finding.
- `why: str | None` — rationale for a `pattern` or `pitfall`.
- `rationale: str | None` — rationale for a `decision`.
- `supersedes: str | None` — id of a prior finding this one replaces.
- `question: str | None` — body of an `open_question`.
- `protected: bool = False` — if true, curator cannot consolidate this away.
- `related: list[str] | None` — ids of related findings.

Pydantic config: `model_config = {"extra": "forbid"}`.

## JSON-schema view

```json
{
  "Finding": {
    "type": "object",
    "additionalProperties": false,
    "required": ["agent", "section", "item"],
    "properties": {
      "agent":   { "type": "string", "pattern": "^[a-z][a-z0-9-]{0,63}$" },
      "section": { "enum": ["patterns", "pitfalls", "decisions", "open_questions"] },
      "item":    { "$ref": "#/FindingItem" }
    }
  },
  "FindingItem": {
    "type": "object",
    "additionalProperties": false,
    "required": ["kind", "summary"],
    "properties": {
      "kind":       { "enum": ["pattern", "pitfall", "decision", "open_question"] },
      "summary":    { "type": "string" },
      "id":         { "type": ["string", "null"] },
      "evidence":   { "type": ["string", "null"] },
      "why":        { "type": ["string", "null"] },
      "rationale":  { "type": ["string", "null"] },
      "supersedes": { "type": ["string", "null"] },
      "question":   { "type": ["string", "null"] },
      "protected":  { "type": "boolean", "default": false },
      "related":    { "type": ["array", "null"], "items": { "type": "string" } }
    }
  }
}
```

## Tool-call example

```python
mcp__agent-substrate__memory_findings_submit(
    agent="reviewer-security",
    findings=[
        {
            "agent": "reviewer-security",
            "section": "pitfalls",
            "item": {
                "kind": "pitfall",
                "summary": "Hard-coded credentials in auth.py",
                "evidence": "auth.py:42",
                "why": "Violates standing security policy; rotates with deploys",
            },
        },
        {
            "agent": "reviewer-security",
            "section": "decisions",
            "item": {
                "kind": "decision",
                "summary": "All credentials must come from env or secret manager",
                "rationale": "Codified after the auth.py:42 incident",
                "protected": True,
            },
        },
    ],
)
```

The substrate response is a structured per-finding result with `success | warning | error` state plus the appended item id, so the caller can detect partial failure deterministically (unlike the v0.3 prose parser, which logged a warning and moved on).

## Rejection examples

These are rejected by the schema:

- Missing `kind` — required.
- `kind="bug"` — not in the enum.
- `section="patterns"` with `kind="pitfall"` — vocabulary mismatch.
- `agent="../etc/passwd"` — fails slug regex.
- Extra field `severity: "high"` — `extra="forbid"`. Encode severity in `summary` or `evidence` instead, or propose a schema extension.
