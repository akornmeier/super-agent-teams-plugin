# Workflow: Code Review with the Reviewer Family

This walkthrough shows how to use the reviewer family (architecture, correctness, security)
together to review a pull request. It demonstrates the memory substrate in action — each
reviewer reads shared learnings, and new patterns accumulate across the session.

---

## Setup

The reviewer family uses a **shared memory namespace**: all three personas read and write to
`reviewer.yaml`. This means architecture patterns, security pitfalls, and correctness rules
discovered in one review session are available to all three personas in the next.

---

## The Scenario

Your team has opened a PR that adds a new user search endpoint:
- Adds a `GET /users/search?q=` route
- Introduces a new `UserSearchService` abstraction
- Adds a cache layer in a new `CacheDecorator` class
- Touches the existing `UserRepository`

---

## Step 1 — Architecture Review

**Activate:** `reviewer` (architecture persona)

**Hand off context:**
> Review the diff for the user search PR. Focus on the new `UserSearchService` and `CacheDecorator` abstractions — do they belong at this layer? Does `CacheDecorator` couple persistence to caching in a way we'll regret?

**What the reviewer does:**
1. Loads `_shared.yaml` (project conventions) and `reviewer.yaml` (accumulated patterns)
2. Maps the new abstractions: `UserSearchService` wraps `UserRepository`; `CacheDecorator` wraps `UserSearchService`
3. Evaluates coupling: `CacheDecorator` is tightly coupled to `UserSearchService` — it can't be reused
4. Checks memory: finds a `decision` item — "caching belongs in the service layer, not in a decorator"
5. Flags the conflict with the standing decision

**Output example:**
```
🔴 Blocker — CacheDecorator conflicts with decision `arch-002`
  Standing decision: caching belongs in the service layer, not a wrapper.
  CacheDecorator wraps UserSearchService and cannot be reused for other services.
  Consider: move cache logic into UserSearchService directly.

🟡 Suggestion — UserSearchService adds a layer without reducing coupling
  UserSearchService delegates everything to UserRepository with no transformation.
  If the abstraction doesn't add behavior, it adds maintenance cost with no benefit.

💭 Nit — UserRepository's search method should return a domain type, not a persistence type
```

**Memory update:** Appends pattern: "CacheDecorators that wrap a single service are not reusable — prefer inline caching in the service."

---

## Step 2 — Security Review

**Activate:** `reviewer` (security persona)

**Hand off context:**
> Security review the same PR. New input: `q` query param on GET /users/search. New service layer and cache layer. Focus on input handling and auth.

**What the reviewer does:**
1. Loads `_shared.yaml` and `reviewer.yaml` — sees the architecture patterns but focuses on security pitfalls
2. Identifies the new input surface: `q` param reaching `UserRepository.search()`
3. Checks whether `q` is validated before reaching the query
4. Checks auth: is `/users/search` behind the auth middleware?
5. Checks cache poisoning: can an attacker manipulate the cache key via `q`?

**Output example:**
```
🔴 Critical (A03: Injection) — q param reaches UserRepository.search() without sanitization
  Attack vector: GET /users/search?q='; DROP TABLE users; --
  The q param is passed directly to a LIKE query with no escaping.
  Fix: use parameterized query, not string interpolation.

🟡 High — /users/search is not behind the auth middleware
  The route is registered before the auth middleware in routes.ts:42.
  Any unauthenticated caller can enumerate users.

🟠 Medium — Cache key includes raw q param
  A crafted q value could produce cache key collisions.
  Normalize and sanitize q before constructing the cache key.
```

**Memory update:** Appends pitfall: "New search endpoints are often registered before auth middleware — check route registration order."

---

## Step 3 — Correctness Review

**Activate:** `reviewer` (correctness persona)

**Hand off context:**
> Correctness review the same PR. The architecture and security reviewers have already flagged structural and security issues. Focus on: does the search logic handle empty queries, special characters, pagination edge cases?

**What the reviewer does:**
1. Loads `_shared.yaml` and `reviewer.yaml` — now has context from both prior passes
2. Traces the execution path for edge cases: empty `q`, whitespace-only `q`, very long `q`
3. Checks pagination: what happens when offset > total results?
4. Checks cache behavior on empty results: are empty result sets cached? For how long?

**Output example:**
```
🔴 Blocker — Empty q returns all users
  When q="" or q is whitespace, the LIKE query becomes LIKE '%%' which matches everything.
  This bypasses intended search semantics and could expose full user lists.

🟡 Suggestion — Pagination offset beyond total results returns 500
  UserRepository.search() throws when offset > count, not an empty page.
  Should return empty array with total count, not a 500.

💭 Nit — Empty result sets are cached with the same TTL as populated results
  Not a bug, but a stale empty cache could confuse users after data is added.
```

**Memory update:** Appends pitfall: "Empty-string wildcard queries — always validate that q has non-whitespace content before constructing LIKE."

---

## Step 4 — Memory after the session

After this review session, `reviewer.yaml` now contains:

- The architectural decision conflict about CacheDecorators
- The pattern that CacheDecorators wrapping a single service are not reusable
- The pitfall about route registration order and auth middleware
- The pitfall about empty-string wildcard queries

**The next time** any reviewer persona is activated on a PR that touches search, caching, or routing, these learnings are immediately available — without reading this document.

---

## Curation

If any write during this session returned `warning`, dispatch the curator:

**Activate:** `curator`

**Hand off context:**
> The reviewer memory file returned a warning during the last session. Please run the memory-curate pipeline on `agent_name="reviewer"` and report what was consolidated.

The curator runs dedupe → score-drop → summarize and reports:
- Chars before/after
- Items dropped and why
- Any rubric calibration signals

---

## Key takeaways

1. **Order matters** — architecture first surfaces structural decisions that inform security and correctness passes
2. **Memory compounds** — pitfalls found in one review are automatically applied in the next
3. **Personas share memory** — all three reviewer personas write to `reviewer.yaml`, so the team's collective knowledge grows as a unit
4. **Curator is reactive, not scheduled** — only dispatch when a write returns `warning` or `needs_curation: true`
