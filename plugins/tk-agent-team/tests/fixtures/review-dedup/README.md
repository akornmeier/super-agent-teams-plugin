# /review Dedup Smoke Test

Verifies that the `parallel-panel` team pattern correctly dedupes overlapping findings
between `reviewer-correctness` and `reviewer-security`. Introduced in Task 6 of the
v0.4 team-orchestration migration.

## What it tests

Hard-coded credential in `auth.py:8` is the **overlap target** — historically flagged
by BOTH the correctness lens (secret literals in source) and the security lens
(credential exposure). The `parallel-panel` dedup loop must produce exactly one
consolidated finding for this issue, with `rationale` crediting both reviewers OR
documenting which lens deferred to the other.

## Structural checks (automated, run via pytest)

`tests/test_review_dedup_structure.py` asserts the skill is correctly wired:
- `skills/review/SKILL.md` declares `team_pattern: parallel-panel` in frontmatter
- Workflow body references `TeamCreate` with a `review-<slug>` team_name
- Workflow spawns three teammates by name: `reviewer-architecture`, `reviewer-correctness`, `reviewer-security`
- Workflow ends with `TeamDelete`
- All three reviewer agent files include `memory_findings_submit` in their tools allowlist
- All three reviewer agent files document direct MCP access in their `## Memory protocol` section

These checks DO NOT actually run /review. They guarantee the skill is *capable of*
producing the documented behavior; the runtime check below verifies it *actually does*.

## Runtime check (manual, run interactively)

Run from the repo root:

```
/review tests/fixtures/review-dedup/auth.py mode: report-only
```

Expected outcome:
1. Three reviewer teammates spawn (visible in transcript: TeamCreate + 3× Agent calls).
2. The consolidated review report contains the credential finding **exactly once**.
   Either:
   - One reviewer (correctness or security) owns the finding; the rationale credits the other for raising it during peer-DM dedup.
   - OR both reviewers flag it independently and the consolidation merges them with a "merged from: correctness, security" note.
3. The report does NOT have two separate top-level findings for the same line.
4. `team_memory_read({team_name: "review-<slug>"})` shows at least one peer-DM-overlap decision logged before TeamDelete.

If criteria 2 or 3 fail, the dedup loop is broken — escalate per `_shared/team-protocol.md` (likely action: promote dedup-arbiter from fallback to default).

## Failure recovery

The smoke test is intentionally narrow — it tests dedup quality on ONE known pattern.
Broader dedup verification belongs in production rollout monitoring, not in this
fixture. If production shows >5% double-flag rate after dedup, treat as a regression
of this test.
