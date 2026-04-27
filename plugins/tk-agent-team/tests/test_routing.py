"""Fixture-driven tests for `agents/routing.yaml`.

These tests load `agents/routing.yaml` once per session and assert that a pure
Python `classify()` helper (mirroring the orchestrator's planned classification
flow) returns the expected `(skill, task_type, team_pattern, families)` for a
representative set of historical prompts.

The helper lives in this test file (not production code) until Task 13 wires
the orchestrator agent to consume `routing.yaml` directly.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROUTING_YAML = (
    Path(__file__).resolve().parents[1] / "agents" / "routing.yaml"
)

# Augmentation trigger -> substring list. Mirrors the cross-cutting augmentation
# rules in `agents/orchestrator.md` lines 71-76.
AUGMENTATION_TRIGGERS: dict[str, list[str]] = {
    "framework": [
        "react",
        "vue",
        "astro",
        "motion.dev",
        "framer motion",
        "hooks",
        "composition api",
        "server component",
        "islands",
    ],
    "design": [
        "design system",
        "component library",
        "design tokens",
        "accessibility",
        "aria",
        "visual regression",
    ],
    "engineering": [
        "deploy",
        "container",
        "observability",
        "data pipeline",
        "embeddings",
        "rag",
    ],
    "marketing": [
        "blog",
        "copy",
        "seo",
        "social",
        "growth",
        "campaign",
    ],
}

# Regex patterns for override conditions. Documented in the task brief.
_STACK_TRACE_PATTERNS = [
    re.compile(r'\bFile "[^"]+", line \d+'),
    re.compile(r"Traceback", re.IGNORECASE),
    re.compile(r"at .* \([^)]+:\d+\)"),
]
_PLAN_PATH_PATTERN = re.compile(r"docs/plans/[^\s]+\.md", re.IGNORECASE)


@pytest.fixture(scope="session")
def routing() -> dict:
    with ROUTING_YAML.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert "rules" in data and "overrides" in data, "routing.yaml malformed"
    return data


def _signal_matches(signal: str, prompt_lower: str, prompt: str) -> bool:
    """A signal is either a literal substring (case-insensitive) or a `re:/.../` regex.

    Regex form is matched case-insensitively as well, mirroring the substring
    semantics in the schema doc.
    """
    if signal.startswith("re:/") and signal.endswith("/"):
        pattern = signal[4:-1]
        return re.search(pattern, prompt, flags=re.IGNORECASE) is not None
    return signal.lower() in prompt_lower


def _augmentation_fires(trigger: str, prompt_lower: str) -> bool:
    """True if any substring registered to `trigger` appears in the lowercased prompt."""
    return any(s in prompt_lower for s in AUGMENTATION_TRIGGERS.get(trigger, []))


def _stack_trace_present(prompt: str) -> bool:
    return any(p.search(prompt) for p in _STACK_TRACE_PATTERNS)


def _plan_path_present(prompt: str) -> bool:
    return _PLAN_PATH_PATTERN.search(prompt) is not None


def _condition_met(condition: str, prompt: str) -> bool:
    if condition == "stack_trace_present":
        return _stack_trace_present(prompt)
    if condition == "plan_path_present":
        return _plan_path_present(prompt)
    raise AssertionError(f"unknown override condition: {condition}")


def classify(prompt: str, routing: dict) -> dict:
    """Return {skill, task_type, team_pattern, families} for `prompt`.

    Mirrors the orchestrator's planned classification flow per
    `routing.yaml.schema.md` "Stacking and precedence semantics":
      1. First matching rule wins (file order).
      2. Augmentations stack additively (set union).
      3. Overrides apply AFTER rule match; first matching override wins.
    """
    prompt_lower = prompt.lower()

    matched_rule: dict | None = None
    for rule in routing["rules"]:
        for signal in rule["signals"]:
            if _signal_matches(signal, prompt_lower, prompt):
                matched_rule = rule
                break
        if matched_rule is not None:
            break

    if matched_rule is None:
        # No signal matched: per orchestrator override "treat as exploration".
        # Surface that as a synthetic exploration result.
        result = {
            "skill": "researcher",
            "task_type": "exploration",
            "team_pattern": "solo",
            "families": {"_shared", "researcher"},
        }
    else:
        families = set(matched_rule["families"])
        for aug in matched_rule.get("augmentations") or []:
            if _augmentation_fires(aug["trigger"], prompt_lower):
                families.update(aug["families"])
        result = {
            "skill": matched_rule["skill"],
            "task_type": matched_rule["task_type"],
            "team_pattern": matched_rule["team_pattern"],
            "families": families,
        }

    for override in routing["overrides"]:
        if _condition_met(override["condition"], prompt):
            if "force_skill" in override:
                result["skill"] = override["force_skill"]
            if "force_task_type" in override:
                result["task_type"] = override["force_task_type"]
            break

    return result


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

# Each case: (prompt, expected_skill, expected_task_type, expected_team_pattern,
#             expected_families_set).

HAPPY_PATH_CASES = [
    # bugfix
    (
        "fix the broken signup flow",
        "/debug",
        "bugfix",
        "pipeline",
        {"_shared", "researcher", "debugger", "reviewer", "developer"},
    ),
    # review
    (
        "please review this PR",
        "/review",
        "review",
        "parallel-panel",
        {"_shared", "reviewer", "developer"},
    ),
    # planning
    (
        "draft a spec for the new auth flow",
        "/plan",
        "planning",
        "solo",
        {"_shared", "planner", "reviewer"},
    ),
    # design
    (
        "draft wireframes for the new onboarding flow",
        "/plan",
        "planning",
        "solo",
        {"_shared", "design", "planner", "reviewer"},
    ),
    # platform
    (
        "deploy the worker fleet to Kubernetes with monitoring",
        "/work",
        "feature",
        "solo",
        {"_shared", "engineering", "planner", "developer", "reviewer"},
    ),
    # marketing
    (
        "write a blog post for the Q3 launch",
        "/ideate",
        "feature",
        "solo",
        {"_shared", "marketing", "planner"},
    ),
    # compound-cycle
    (
        "run a full cycle compound knowledge pass on the codebase",
        "/compound",
        "compound-cycle",
        "solo",
        {
            "_shared",
            "planner",
            "tester",
            "researcher",
            "debugger",
            "docs-writer",
            "reviewer",
            "developer",
            "curator",
            "design",
            "framework",
            "engineering",
            "marketing",
        },
    ),
    # refactor
    (
        "clean up the duplicated email validators",
        "/plan",
        "refactor",
        "solo",
        {"_shared", "planner", "developer", "reviewer"},
    ),
    # feature (catch-all)
    (
        "add user profiles with avatar upload",
        "/ship",
        "feature",
        "staged-team",
        {"_shared", "planner", "developer", "reviewer", "tester"},
    ),
    # exploration
    (
        "explain how routing works in this codebase",
        "researcher",
        "exploration",
        "solo",
        {"_shared", "researcher"},
    ),
]


OVERRIDE_CASES = [
    # Stack trace forces /debug even though surface words say "feature".
    (
        'I want to add a new feature but first: Traceback (most recent call last):\n'
        '  File "app.py", line 42, in main\n    raise ValueError("nope")',
        "/debug",
        "bugfix",
        "staged-team",  # team_pattern stays from the matched rule (feature)
        {"_shared", "planner", "developer", "reviewer", "tester"},
    ),
    # JS-style stack trace also triggers stack_trace_present.
    (
        "build the integration. Got: at handler (/srv/app.js:101)",
        "/debug",
        "bugfix",
        "staged-team",
        {"_shared", "planner", "developer", "reviewer", "tester"},
    ),
    # docs/plans/*.md path forces /work even though words say "implement".
    (
        "implement the work outlined in docs/plans/2026-04-foo.md",
        "/work",
        "feature",
        "staged-team",
        {"_shared", "planner", "developer", "reviewer", "tester"},
    ),
]


AUGMENTATION_CASES = [
    # ship + React + growth → feature row + framework + marketing.
    # "deploy" not present so engineering does NOT stack here. The user-spec
    # example mentions framework + marketing + engineering on top of feature
    # defaults, but engineering only fires when an engineering-trigger
    # substring appears (e.g. "growth tracking" alone doesn't carry an
    # engineering trigger). We split that into two cases below to keep the
    # contract honest.
    (
        "ship the React landing page with growth tracking",
        "/ship",
        "feature",
        "staged-team",
        {
            "_shared",
            "planner",
            "developer",
            "reviewer",
            "tester",
            "framework",
            "marketing",
        },
    ),
    # Multi-augmentation on the feature row: framework + design + marketing.
    # We deliberately avoid engineering-augmentation triggers (deploy, container,
    # observability, data pipeline, embeddings, rag) here because every one of
    # those is ALSO a primary signal in the platform rule, which precedes
    # feature in file order — so a prompt that mentions any of them gets routed
    # to /work, not /ship. Stacking engineering-augmentation on top of the
    # feature row would require a routing precedence change beyond Task 12's
    # scope; tracked as an open question.
    (
        "build a new Vue admin panel with growth metrics and accessibility instrumentation",
        "/ship",
        "feature",
        "staged-team",
        {
            "_shared",
            "planner",
            "developer",
            "reviewer",
            "tester",
            "framework",
            "design",
            "marketing",
        },
    ),
    # review + design tokens → adds design augmentation on top of review row.
    (
        "review the design tokens PR",
        "/review",
        "review",
        "parallel-panel",
        {"_shared", "reviewer", "developer", "design"},
    ),
    # platform deploy + observability → engineering already in base; family
    # set unchanged but still asserted.
    (
        "deploy the service with observability dashboards",
        "/work",
        "feature",
        "solo",
        {"_shared", "engineering", "planner", "developer", "reviewer"},
    ),
    # marketing campaign → marketing rule families.
    (
        "social campaign for the Q3 product launch",
        "/ideate",
        "feature",
        "solo",
        {"_shared", "marketing", "planner"},
    ),
    # Marketing-only augmentation on the feature row (without framework/design):
    # "build" hits the feature rule and "growth" alone fires the marketing aug.
    (
        "build a new pricing experiment with growth metrics",
        "/ship",
        "feature",
        "staged-team",
        {
            "_shared",
            "planner",
            "developer",
            "reviewer",
            "tester",
            "marketing",
        },
    ),
]


EDGE_CASES = [
    # No signal match → defaults to exploration/researcher.
    (
        "thoughts?",
        "researcher",
        "exploration",
        "solo",
        {"_shared", "researcher"},
    ),
    # Ambiguous: "review" + "fix" — first-matching-rule (bugfix is earlier in
    # file order) must win. The user-spec ordering puts bugfix first.
    (
        "fix the review pipeline",
        "/debug",
        "bugfix",
        "pipeline",
        {"_shared", "researcher", "debugger", "reviewer", "developer"},
    ),
]


ALL_CASES = HAPPY_PATH_CASES + OVERRIDE_CASES + AUGMENTATION_CASES + EDGE_CASES


@pytest.mark.parametrize(
    "prompt,skill,task_type,team_pattern,families",
    ALL_CASES,
    ids=[c[0][:60] for c in ALL_CASES],
)
def test_classify(prompt, skill, task_type, team_pattern, families, routing):
    result = classify(prompt, routing)
    assert result["skill"] == skill, f"skill mismatch for: {prompt!r}"
    assert result["task_type"] == task_type, f"task_type mismatch for: {prompt!r}"
    assert (
        result["team_pattern"] == team_pattern
    ), f"team_pattern mismatch for: {prompt!r}"
    assert result["families"] == families, (
        f"families mismatch for: {prompt!r}\n"
        f"  expected: {sorted(families)}\n"
        f"  got:      {sorted(result['families'])}"
    )


def test_routing_has_minimum_rules(routing):
    """Sanity: ensure the file declares the 10 historical rules + 2 overrides."""
    assert len(routing["rules"]) >= 10, "expected >= 10 rules"
    assert len(routing["overrides"]) >= 2, "expected >= 2 overrides"


def test_every_rule_includes_shared_first(routing):
    """`_shared` must always be the first family in every rule."""
    for rule in routing["rules"]:
        assert rule["families"][0] == "_shared", (
            f"rule for {rule['skill']!r} must list `_shared` first"
        )


def test_team_patterns_are_in_catalog(routing):
    catalog = {"solo", "pair", "parallel-panel", "pipeline", "staged-team", "feature-team"}
    for rule in routing["rules"]:
        assert rule["team_pattern"] in catalog, (
            f"rule for {rule['skill']!r} has invalid team_pattern: {rule['team_pattern']!r}"
        )
