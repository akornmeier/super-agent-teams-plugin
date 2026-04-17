# Workflow: Ideate → Ship with `/compound`

This example walks a single prompt — `/compound "Add user profiles with avatar upload"` — all the way from orchestrator classification through the final memory consolidation. Every artifact shown is at its real canonical path; every agent and skill named is a real file in this plugin.

Use this as the reference for what a full cycle produces: four artifact files, code + tests, and memory appends across five families.

---

## Step 1 — Orchestrator classifies the prompt

**Activate:** `orchestrator`

The prompt contains the signal phrase `"add"` — per the orchestrator's classification table (`specs/foundation-notes.md` §1) this is a **feature**. The prompt has no `docs/plans/*.md` path reference and no existing brainstorm, so the orchestrator begins at `/ideate` rather than jumping to `/ship`.

Before dispatch, the orchestrator reads `_shared.yaml` plus the pre-load set for feature work: `planner`, `developer`, `reviewer`, `tester`. It writes a brief:

```
docs/ideation/2026-04-17-user-profiles.md  (to be created by /ideate)

## Original prompt
Add user profiles with avatar upload

## Relevant memory (pre-loaded)
- planner: "Pattern — break features into <=5 ranked ideas before committing to one"
- reviewer/architecture: "Standing decision ADR-004 — all new entities go through the repository layer"
- developer: "Pattern fe-001 — forms use FormField wrapper"

## Input artifact
none
```

It dispatches `/ideate` with this brief path.

---

## Step 2 — `/ideate` produces ranked ideas

`/ideate` stages: researcher returns a context brief, then `planner/product` generates 3–5 scored ideas against `references/rubric.md`. Output lands at the canonical path.

**Artifact:** `docs/ideation/2026-04-17-user-profiles.md`

```markdown
# User profiles with avatar upload

## Context
Existing `users` table has `displayName`, `email`, `createdAt`. No profile surface yet.
Related prior art: `docs/solutions/features/2025-11-02-email-preferences.md` — same PATCH-style update pattern.

## Ideas

### Idea 1: Inline edit form on /me page
**Value**: 8/10 — shortest path to user-visible value
**Cost**: 3/10 — reuses FormField + useFormState patterns
**Tradeoff**: no avatar moderation pipeline; relies on CSP for XSS defense
**Score**: 7.5

### Idea 2: Dedicated /settings/profile with multi-step wizard
**Value**: 6/10 — over-engineered for three fields
**Cost**: 7/10 — new routing, new layout
**Tradeoff**: extensible if we add more profile fields later
**Score**: 4.5

### Idea 3: Profile-as-side-panel on every page
**Value**: 5/10 — convenient but visually noisy
**Cost**: 6/10 — global state changes
**Tradeoff**: faster edits but worse focus
**Score**: 4.0

## Recommendation
Idea 1 — inline edit on `/me`. Highest score, lowest risk, extends cleanly to Idea 2 later.

## Open questions
- Avatar storage: S3 or on-disk? Defer to /plan.
- Image size limits and format allowlist?
```

**Memory appends:**
- `planner`: "When storage backend is unknown at ideation time, defer to /plan — do not block ranking."
- `researcher`: "User entity pattern — `users` table uses UUID PKs, repository pattern via `UserRepository`."

The orchestrator surfaces the recommendation to the user, who confirms Idea 1. The orchestrator dispatches `/brainstorm` with the ideation doc as input.

---

## Step 3 — `/brainstorm` expands the selected idea

`/brainstorm` dispatches `planner/product` to convert Idea 1 into requirements.

**Artifact:** `docs/brainstorms/2026-04-17-user-profiles-requirements.md`

```markdown
# User profiles — requirements

## Selected idea
Inline profile edit form on `/me`. Fields: `displayName`, `avatarUrl`.

## User stories

**US-1** — As a signed-in user, I want to edit my display name and avatar URL, so that I can personalize my account.

**US-2** — As a signed-in user, I want to see my changes immediately after saving, so that I know the update succeeded.

**US-3** — As the system, I must prevent one user from updating another user's profile, so that accounts remain private.

## Acceptance criteria

**AC-1** (US-1) — Given I am on `/me`, when I submit the form with a valid displayName and avatarUrl, then a PATCH request is sent to `/users/:id`.

**AC-2** (US-1) — Given I submit with an empty or whitespace-only displayName, when the form is submitted, then the server returns 422 and the form shows an inline error.

**AC-3** (US-3) — Given I am user A, when a PATCH to `/users/<id of user B>` is sent, then the server returns 403.

**AC-4** (US-2) — Given a successful save, when the response returns, then the UI reflects the new values without a full page reload.

## Out of scope
- Avatar upload pipeline (just the URL field for now).
- Display name uniqueness checks.

## Open questions
- Should `avatarUrl` be validated against an allowlist of hosts? Defer to /plan.
```

**Memory appends:**
- `planner`: "Requirements pattern — keep AC Given/When/Then; one AC per user story minimum."

The orchestrator dispatches `/plan` next, passing the brainstorm path as input.

---

## Step 4 — `/plan` produces the technical plan

`/plan` runs three stages: `planner/technical` drafts against `references/plan-schema.md`; `reviewer/architecture` flags standing-decision conflicts; `planner/technical` revises.

**Artifact:** `docs/plans/2026-04-17-user-profiles-plan.md`

```markdown
# User profiles — plan

## Context
Implements the requirements in `docs/brainstorms/2026-04-17-user-profiles-requirements.md`.

## Approach
Add a `PATCH /users/:id` endpoint behind `requireAuth` + `requireOwnership`.
Add a `ProfileEditForm` component on `/me`. No schema changes — columns already exist.

## Layers affected
- Route: `src/routes/users.ts` — new PATCH handler
- Service: `src/services/userService.ts` — new `updateProfile` method
- Repository: `src/repositories/userRepository.ts` — new `update` method
- UI: `src/components/ProfileEditForm.tsx` (new), `src/pages/Me.tsx` (wire form)

## Data-model changes
None. Existing `users.displayName` and `users.avatarUrl` columns are reused.

## Migration steps
None.

## Test strategy
- Unit: validation rules, ownership middleware, form submit states.
- Integration: PATCH 200 happy path, 401 unauthenticated, 403 cross-user, 422 invalid displayName.

## Risks
- **R-1**: avatarUrl not sanitized before rendering in <img src>. Mitigation: CSP allowlist + server validates URL constructor parses.
- **R-2**: Client/server validation drift on URL format. Mitigation: shared validator utility.

## Rollback plan
Remove the PATCH route and the ProfileEditForm component — no data migration to reverse.

## Implementation phases
1. Backend route + service + repo + unit tests.
2. Frontend form + page wiring.
3. Integration tests covering all AC rows.
```

**Memory appends:**
- `planner`: "Technical plans must name the shared-validator mitigation when client + server both validate the same field."
- `reviewer`: (from review stage) — "Flagged before merge: ADR-004 repository-layer usage was already applied. No new standing decision."

The orchestrator dispatches `/ship` with this plan.

---

## Step 5 — `/ship` composite: work → review → test

`/ship` is a composite skill. It runs `/work`, then `/review`, then `/test`, stopping if a stage returns blockers in report-only mode.

### 5a. `/work`

`/work` parses the plan and sees it's full-stack. It dispatches `developer/frontend` and `developer/backend` in parallel.

- `developer/backend` implements the PATCH route, service, and repository. Reads `developer.yaml` and `reviewer.yaml` at task start — applies `sec-002` (parameterized query) and `arch-003` (validation in route handler).
- `developer/frontend` implements `ProfileEditForm` using `fe-001` (FormField) and `fe-002` (useFormState).

**Memory appends:**
- `developer`: "Shared URL validator utility — extract to `src/validation/url.ts` when client + server both validate the same URL field."

### 5b. `/review`

`/review` dispatches `reviewer/architecture`, `reviewer/correctness`, `reviewer/security` in parallel, merges findings, dedupes overlaps.

Output summary:
```
🟡 Suggestion (architecture) — ProfileEditForm and userService both parse URLs — extract shared validator.
🔴 Blocker (correctness) — displayName whitespace-only passes non-empty check; must trim before validating.
💭 Low (security) — avatarUrl rendered in <img src>; confirm CSP covers external hosts.
```

The blocker forces one loop: `/work` is re-dispatched in autofix mode. `developer/backend` adds the trim, updates unit tests. `/review` re-runs; all blockers cleared.

**Memory appends:**
- `reviewer`: "Pitfall — trim strings before non-empty validation; whitespace-only passes length check."

### 5c. `/test`

`/test` dispatches `tester/unit` and `tester/integration` in parallel. Each reads `developer.yaml` and `reviewer.yaml` at task start — the tester/unit persona sees the just-appended trim pitfall and writes a dedicated test for it.

Output: new test files plus a coverage gap report (zero gaps — all 4 ACs covered).

**Memory appends:**
- `tester`: "Every new PATCH endpoint needs four tests: 200 happy, 401 unauth, 403 cross-user, 422 invalid."

`/ship` returns a combined summary to the orchestrator.

---

## Step 6 — `/compound` captures the solution

`/compound` has two stages. `docs-writer` authors the solution doc against `references/solution-schema.md` under the `features/` category. Then `curator` is dispatched against every family memory touched in the cycle.

**Artifact:** `docs/solutions/features/2026-04-17-user-profiles.md`

```markdown
# User profiles with avatar upload

## Problem
Users had no way to edit displayName or avatarUrl. No profile surface existed.

## Motivation
Highest-scored idea from ideation; unblocks personalization without requiring new data model work.

## Solution
PATCH /users/:id behind requireAuth + requireOwnership; ProfileEditForm component on /me;
shared URL validator used by both route-handler and form.

## Related patterns
- ADR-004 (repository layer)
- fe-001 (FormField wrapper), fe-002 (useFormState)
- New pattern — trim before non-empty validation

## Applies to
Any future PATCH endpoint that accepts user-editable string fields.
```

Curation runs against `planner`, `developer`, `reviewer`, `tester`, `researcher`, `docs-writer` — any file above the soft limit is consolidated. The curator reports chars before/after per file.

---

## Summary — artifacts and memory

| Stage | Artifact file | Families appended |
|---|---|---|
| `/ideate` | `docs/ideation/2026-04-17-user-profiles.md` | `planner`, `researcher` |
| `/brainstorm` | `docs/brainstorms/2026-04-17-user-profiles-requirements.md` | `planner` |
| `/plan` | `docs/plans/2026-04-17-user-profiles-plan.md` | `planner`, `reviewer` |
| `/work` | (code + unit tests committed) | `developer` |
| `/review` | (report returned inline) | `reviewer` |
| `/test` | (test files + coverage report) | `tester` |
| `/compound` | `docs/solutions/features/2026-04-17-user-profiles.md` | `docs-writer`, plus `curator` consolidation of every touched family |

The next feature prompt that reaches the orchestrator will see all of this in memory — the trim-before-non-empty pitfall, the shared-URL-validator pattern, the four-test PATCH shape. None of it has to be re-discovered.
