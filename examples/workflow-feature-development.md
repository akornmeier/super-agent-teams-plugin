# Workflow: Feature Development with Developer + Reviewer Loop

This walkthrough shows the full build→review→fix cycle using the developer and reviewer
families together. It demonstrates how memory flows between the two families — reviewers'
known complaints become developers' pre-applied fixes, and developers' discovered patterns
become shared team knowledge.

---

## The loop

```
Orchestrator assigns task
        │
        ▼
Developer (frontend or backend) reads:
  ├── shared memory       (project conventions)
  ├── developer memory    (patterns and pitfalls from prior builds)
  └── reviewer memory     (known complaints to pre-apply)
        │
        ▼
Developer implements + tests + self-reviews
        │
        ▼
Reviewer family reviews:
  ├── architecture.md     (layer violations, abstraction cost)
  ├── correctness.md      (logic errors, edge cases)
  └── security.md         (trust boundaries, input handling)
        │
        ▼
Developer addresses feedback
        │
        ▼
Memory updated on both sides — next iteration starts smarter
```

The key property: **both sides learn**. Reviewers append newly discovered vulnerability
classes and architectural patterns. Developers read those before the next build, so the
same issue doesn't get flagged twice.

---

## The scenario

The team needs to add a user profile update feature:
- `PUT /users/:id` backend endpoint
- A profile edit form on the frontend
- Auth required; users can only update their own profile

---

## Step 1 — Backend implementation

**Activate:** `developer` (backend persona)

**Hand off context:**
> Implement PUT /users/:id. Users can update their own displayName and avatarUrl. Auth required — users may only update their own profile (not others). Follow existing patterns for user routes.

**What the developer does:**

1. Loads shared + developer + reviewer memory
2. Finds in reviewer memory: pitfall `sec-002` — "unsanitized search params reach queries"; decision `arch-003` — "validation in route handler, not service"
3. Finds in developer memory: pattern `be-001` — "user routes use `requireOwnership(req.user.id, req.params.id)` middleware for ownership checks"
4. Implements:
   - Route with input validation (displayName max 100 chars, avatarUrl is valid URL or empty)
   - `requireAuth` + `requireOwnership` middleware applied from memory pattern
   - Service: `userService.updateProfile(userId, { displayName, avatarUrl })`
   - Repository: parameterized UPDATE query (applied from reviewer pitfall memory)
   - Tests: happy path, auth failure (401), ownership violation (403), invalid displayName (422)

5. Self-reviews against reviewer memory before handing off:
   - Architecture: is validation in the route layer? ✓ (per `arch-003`)
   - Security: parameterized query? ✓ Auth + ownership check? ✓
   - Correctness: empty `displayName` handled? — gaps noted for reviewer

6. Appends to developer memory: "URL validation for avatarUrl: use `new URL(value)` constructor in a try/catch — fails gracefully on empty string"

**Output to orchestrator:**
```
Implemented PUT /users/:id
- Layers: route (validation + auth) → service → repository
- Applied: arch-003 (validation in route), sec-002 (parameterized query), be-001 (requireOwnership)
- Tests: happy path, 401, 403, 422 (bad displayName), 422 (bad avatarUrl)
- Open for reviewer: what happens when displayName is all whitespace? I validated non-empty but not non-whitespace.
- Memory updated with avatarUrl validation pattern
```

---

## Step 2 — Frontend implementation

**Activate:** `developer` (frontend persona)

**Hand off context:**
> Implement the profile edit form. Fields: displayName (text input), avatarUrl (URL input). Submits to PUT /users/:id. Show success/error feedback inline. Follow the FormField component pattern.

**What the developer does:**

1. Loads shared + developer + reviewer memory
2. Finds in developer memory: pattern `fe-001` — "all forms use FormField wrapper for consistent error state"; pattern `fe-002` — "async form submissions use the `useFormState` hook"
3. Finds in reviewer memory: no specific frontend items, but architectural decision about not leaking persistence types through to the UI layer
4. Implements:
   - `ProfileEditForm` component using `FormField` (per `fe-001`) and `useFormState` (per `fe-002`)
   - Validation: non-empty displayName, valid URL or empty for avatarUrl
   - Accessible: `aria-invalid` on error state, error messages associated via `aria-describedby`
   - Tests: render, submit happy path, submit error (422), submit network failure

5. Self-reviews before handing off:
   - Does the form reset after successful submit? Yes
   - Is the submit button disabled during in-flight request? Yes (via `useFormState`)
   - ARIA roles verified

**Output to orchestrator:**
```
Implemented ProfileEditForm
- Applied: fe-001 (FormField wrapper), fe-002 (useFormState)
- Accessibility: aria-invalid, aria-describedby for errors, button disabled during request
- Tests: render, submit success, 422 validation error, network failure
- No reviewer memory items were directly applicable
- Memory updated with avatarUrl regex pattern used for client-side validation
```

---

## Step 3 — Review pass

**Activate:** `reviewer` (all three personas, sequentially or in parallel)

**Architecture review output (abbreviated):**
```
🟡 Suggestion — ProfileEditForm validates avatarUrl client-side with a regex but the service
  validates with new URL() constructor. Two different validators for the same field will drift.
  Consider: extract to a shared validation utility used by both.

💭 Nit — userService.updateProfile accepts a plain object. Consider a typed DTO so the
  compiler catches if a caller passes unexpected fields.
```
→ Appends to reviewer memory: "Client/server validation drift on URL fields — extract shared validators"

**Correctness review output (abbreviated):**
```
🔴 Blocker — displayName whitespace case: PUT /users/:id with displayName="   " passes
  validation (non-empty) but stores three spaces. Validation should trim and then check non-empty.

🟡 Suggestion — Repository UPDATE returns rows affected but the service doesn't check if
  it's 0 (user not found). Should return 404 if no rows updated.
```
→ Appends to reviewer memory: "Always check rows-affected on UPDATE — 0 means not found"

**Security review output (abbreviated):**
```
💭 Low — avatarUrl is stored and later rendered in an <img src>. Confirm the renderer
  sanitizes or CSP restricts external image sources. Not a code bug, but a defense-in-depth note.
```
→ Appends to reviewer memory: "User-supplied URLs rendered as <img src> — verify CSP covers external images"

---

## Step 4 — Developer addresses feedback

**Activate:** `developer` (backend persona)

**Hand off context:**
> Address the reviewer's correctness blockers on PUT /users/:id: (1) trim displayName before validating non-empty, (2) return 404 when UPDATE affects 0 rows.

**What the developer does:**

1. Loads memory — now includes the new reviewer pitfall about rows-affected check
2. Fixes both issues
3. Updates tests to cover whitespace-only displayName (now 422) and unknown user ID (now 404)
4. Appends to developer memory: "Trim strings before non-empty validation — whitespace-only passes length check"

---

## After the cycle

**Developer memory now contains:**
- avatarUrl validation pattern
- Shared validator extraction note (from architecture review)
- String trimming before non-empty validation
- rows-affected 404 check pattern

**Reviewer memory now contains:**
- Client/server validation drift on URL fields
- rows-affected on UPDATE = 0 means not found
- User-supplied URLs in `<img src>` → verify CSP

**The next feature involving user input or URL storage** will have these patterns pre-applied by the developer, and the reviewer will have context to check them faster — without either team re-discovering them from scratch.

---

## When to dispatch the curator

If any developer or reviewer write returns `warning` during this cycle:

**Activate:** `curator`

**Hand off context:**
> The developer memory file returned a warning during the last session. Run memory-curate on agent_name="developer" and report.

The curator runs dedupe → score-drop → summarize and reports chars before/after and what was consolidated.

---

## Key takeaways

1. **Cross-family memory reads close the feedback loop** — developers read reviewer memory before building; common issues become pre-applied fixes
2. **Memory compounds both directions** — reviewers' discoveries become developers' checklists; developers' discoveries become reviewers' validation patterns
3. **The self-review step reduces cycle time** — a developer who has read the reviewer's known complaints will catch the easy issues before review, leaving reviewers to find the subtle ones
4. **Curation keeps the signal-to-noise ratio high** — without the curator, both families' memory files eventually bloat with low-value entries and the useful patterns get harder to find
