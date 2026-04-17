# Workflow: Bug debugging with `/debug`

This walkthrough follows a single prompt — `/debug "users can't update their display name"` — through the orchestrator's bug-fix pipeline. It shows how the file-mediated handoff between `researcher`, `debugger`, `reviewer/correctness`, and `developer` turns a vague complaint into a committed fix plus memory the team can reuse.

Every agent and skill named here is a real file in this plugin.

---

## Step 1 — Orchestrator classifies the prompt

**Activate:** `orchestrator`

The prompt contains the signal `"can't"` which matches the **bugfix** row in the orchestrator's classification table (`specs/foundation-notes.md` §1). Per that table, the orchestrator:

- Dispatches `/debug`
- Pre-loads `_shared`, `researcher`, `debugger`, `reviewer`, `developer` memory
- Writes a brief file naming the symptom

Brief:
```
docs/solutions/bug-fixes/2026-04-17-display-name-update.md  (to be created by /debug)

## Original prompt
users can't update their display name

## Relevant memory (pre-loaded)
- reviewer/correctness: "Pitfall — trim strings before non-empty validation"
- debugger: (empty on first run)
- researcher: "Pattern — user entity uses repository layer; PATCH /users/:id added 2026-04-17"

## Input artifact
none
```

---

## Step 2 — `/debug` stage 1: researcher returns context brief

`researcher` reads the repo, greps for the failing surface, and returns a structured summary. It never modifies code.

Researcher's output (appended into the brief file as `## Context`):

```markdown
## Context
- Route: `src/routes/users.ts` — `PATCH /users/:id` registered behind `requireAuth` + `requireOwnership`.
- Service: `src/services/userService.ts` — `updateProfile(userId, patch)` forwards the patch to the repository.
- Repository: `src/repositories/userRepository.ts` — `update(userId, patch)` uses an ORM that declares a **writable allowlist** on the User entity: `['avatarUrl']`. `displayName` is missing from the allowlist.
- Recent migration: 2026-04-10 tightened the writable allowlist to fix a separate mass-assignment concern.
- Relevant prior art: `docs/solutions/features/2026-04-17-user-profiles.md` — the PATCH endpoint that introduced this.

## Files touched in recent commits
- src/repositories/userRepository.ts (2026-04-10 — allowlist tightening)
- src/routes/users.ts (2026-04-17 — PATCH route added)
```

**Memory append:**
- `researcher`: "Writable allowlist on the User entity at `src/repositories/userRepository.ts` — any field added to the API must also be added here."

---

## Step 3 — `/debug` stage 2: debugger hypothesizes root cause

`debugger` reads its own memory plus the cross-family reads (`reviewer.yaml`, `researcher.yaml`). The researcher's context brief is already in the brief file.

Debugger output:

```markdown
## Reproduction
1. Sign in as user U.
2. PATCH `/users/<U's id>` with body `{"displayName": "new name"}`.
3. Response is **200 OK** but the database value is unchanged.

## Root cause hypothesis
The PATCH handler validates the input and the service forwards the patch unchanged, but the
repository layer's ORM **silently drops fields not declared in the writable allowlist**. The
allowlist on the User entity is `['avatarUrl']` — `displayName` is missing. The call succeeds
(200) because no error is raised; the field is simply filtered out before the UPDATE is built.

## Why it returned 200
The ORM's filter-then-update behavior is silent by design — it exists to defend against
mass-assignment. Without logging on drops, this class of bug is invisible at the handler layer.

## Recommended fix
Add `displayName` to the writable allowlist on the User entity. Simultaneously add an assertion
in `userService.updateProfile` that every key in the incoming patch appears in the allowlist —
so the next field added will fail loud, not silent.
```

**Memory appends:**
- `debugger`: "Pattern — if a PATCH returns 200 but the write does not persist, check the ORM's writable allowlist for the entity before checking anything else."

---

## Step 4 — `/debug` stage 3: reviewer/correctness validates the hypothesis

`reviewer/correctness` reads the hypothesis file and traces it against the actual code. The stage goal is to confirm the hypothesis is the root cause before any code changes.

Correctness review output:

```markdown
## Verdict
Confirmed. `src/repositories/userRepository.ts:47` declares the allowlist as `['avatarUrl']`.
Grep for writable-allowlist references shows only this one entity has the pattern applied.

## Secondary finding
The service-layer assertion the debugger recommends is a good defense, but should be a thrown
error in non-production and a logged warning in production. Silently re-validating defeats the
purpose.
```

**Memory append:**
- `reviewer`: "Pitfall — writable allowlists silently drop fields; always assert keys ⊆ allowlist at the service layer so new fields fail loud."

---

## Step 5 — `/debug` stage 4: developer applies the fix

`developer/backend` reads the confirmed hypothesis file and the new reviewer pitfall. It applies the fix:

1. Adds `displayName` to the User entity's writable allowlist.
2. Adds a `userService.updateProfile` guard: if any key in `patch` is missing from the allowlist, throw in development and log in production.
3. Adds a unit test that PATCHes a field not in the allowlist and asserts the guard fires.
4. Adds a unit test that PATCHes `displayName` and asserts the database value changes.

**Memory appends:**
- `developer`: "When adding a new field to a PATCH endpoint, update the ORM's writable allowlist and the service-layer allowlist guard in the same commit."

The fix is committed.

---

## Step 6 — `/debug` writes the solution artifact

`/debug` completes by writing the full record — prompt, context, hypothesis, verdict, fix — to the canonical bug-fix path. Writing the `docs/solutions/bug-fixes/` artifact is a direct side-effect of `/debug`. However, `/compound` should still be run after `/debug` to curate the memories that were appended across all affected agent families during the session (researcher, debugger, reviewer, developer).

**Artifact:** `docs/solutions/bug-fixes/2026-04-17-display-name-update.md`

```markdown
# Users can't update their display name

## Problem
PATCH /users/:id with `{"displayName": ...}` returned 200 OK but the value never persisted.

## Root cause
The User entity's writable allowlist at `src/repositories/userRepository.ts:47` was `['avatarUrl']`.
The ORM silently drops fields not in the allowlist before building the UPDATE, so the handler
appeared successful while no row was actually changed.

## Solution
1. Added `displayName` to the writable allowlist.
2. Added a service-layer assertion that every key in the incoming patch appears in the allowlist
   — throws in development, logs in production. Makes the next missing-allowlist bug loud.
3. Regression tests: one that PATCHes a known-allowed field and asserts persistence, one that
   PATCHes a non-allowlisted field and asserts the guard fires.

## Related patterns
- The PATCH endpoint from `docs/solutions/features/2026-04-17-user-profiles.md` that introduced
  this surface.
- Standing review pitfall — "writable allowlists silently drop fields; assert keys ⊆ allowlist
  at the service layer."

## Applies to
Any entity that uses the ORM's writable-allowlist pattern, which is the standard for all
user-facing write APIs in this codebase.
```

---

## Why this memory matters next time

The next prompt that lands on the orchestrator with a signal like "can't update X" — or "PATCH returns 200 but nothing happens" — will arrive into a different team than the one that started this cycle. The orchestrator will pre-load `debugger.yaml` and `reviewer.yaml`. The debugger's first hypothesis will be:

> "If a PATCH returns 200 but the write does not persist, check the ORM's writable allowlist for the entity before checking anything else."

…and the reviewer will already know to look for a service-layer allowlist guard. What took four stages and a researcher round-trip in this cycle will collapse into a one-line hypothesis next time. That is the compounding — stored not as documentation the team has to remember to consult, but as the first thing every relevant agent reads at task start.
