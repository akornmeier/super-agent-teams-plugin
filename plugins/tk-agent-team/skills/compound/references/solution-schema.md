# Solution document schema

Every `docs/solutions/<category>/<YYYY-MM-DD>-<slug>.md` file written by
`/compound` (and `/debug` for the `bug-fixes` category) MUST contain these
sections in this order. These docs are durable routing signal for future
orchestrator runs — missing sections weaken the corpus and are treated as
a blocker.

## Required sections

### `## Problem` (bugs, security, performance) **or** `## Motivation` (features, refactors, integrations)

What was wrong or what prompted this work. For bugs: symptoms, reproduction, impact. For security: threat model and attack vector. For performance: the measured regression or target. For features/refactors/integrations: the user or system need and why now.

Expectation: concrete enough that a future reader grepping for the symptom recognizes this as the matching doc. Include stack traces, error messages, or ticket numbers verbatim where relevant.

### `## Root cause` (bugs only) **or** skip for other categories

The real underlying cause — not the symptom, not the surface-level code change. Cite file:line where the defect actually lived. For non-bug categories, this section is omitted (the prior `## Motivation` already covered the "why").

Expectation: one paragraph, specific. "Race condition between X and Y on request N" — not "concurrency issue."

### `## Solution`

What was actually done, at the level a future implementer could reproduce or adapt. Names files/modules changed, patterns applied, and any non-obvious design choices. Links to the cycle artifacts (`docs/plans/`, `docs/work/`, `docs/reviews/`, `docs/tests/`) where they exist.

Expectation: prose + bullets. Not a diff — a diff goes stale; prose describing the shape of the change does not.

### `## Related patterns`

Cross-references to other `docs/solutions/` entries and to `_shared` or family memory items reinforced by this work. Helps the curator and future orchestrators cluster related work.

Expectation: bulleted list of slug references (e.g. `bug-fixes/2025-11-03-stale-cache`, `shared:pattern-debounce-on-resize`). Empty is acceptable only if genuinely novel.

### `## Applies to`

The scope of recurrence: which projects, services, versions, or conditions this solution is relevant for. For `performance` entries, include before/after metrics here. For `security` entries, include affected versions.

Expectation: concrete. "All services using our shared auth SDK ≥ v2.3" — not "anywhere this might happen."
