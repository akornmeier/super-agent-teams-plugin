# Canonical solution categories

These are the only legal categories for `docs/solutions/<category>/` entries.
They are also the directory names on disk. `/compound` picks exactly one per
run — inventing a new category inline is forbidden (it would fragment the
corpus that future orchestrator routing depends on).

If no category fits, `/compound` returns `status: needs_human` and asks the
user to either pick one or propose an addition to this file.

## Categories

### `bug-fixes`
A defect in existing behavior was identified, reproduced, and corrected. Written primarily by `/debug`; enriched by `/compound` if the debug cycle produced notable patterns.

### `features`
A net-new capability was added to the product surface. Typically the output of a `/ideate → /brainstorm → /plan → /ship` cycle.

### `refactors`
Internal structure changed without altering external behavior (renames, layer extractions, pattern migrations). No new user-visible capability.

### `integrations`
A third-party service, SDK, or external API was newly wired in (or an existing integration was materially reconfigured). Covers auth flows, webhooks, and adapter-pattern work.

### `performance`
A measurable performance problem was diagnosed and improved (latency, throughput, memory, bundle size, cold-start). Solution doc must include before/after metrics in `## Applies to`.

### `security`
A vulnerability, authz gap, or hardening opportunity was addressed. Includes CVE responses, secrets-rotation fallout, and authz-model changes. Solution doc must name the threat model in `## Problem`.
