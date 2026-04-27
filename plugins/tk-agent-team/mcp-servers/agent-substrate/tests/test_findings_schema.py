"""Tests for the `Finding` Pydantic schema and `memory_findings_submit` tool.

Covers schema validation (kind enum, vocabulary consistency, extra=forbid,
slug regex), the FindingItem -> section dict translation (decision -> choice,
open_question -> question), and the findings durability invariant: any valid
Finding submitted via `memory_findings_submit` must round-trip through
`memory_read` byte-for-byte on `summary` and `kind` (Acceptance Criteria
"Findings durability invariant").
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_substrate.schema import (
    Finding,
    FindingItem,
    finding_item_to_section_dict,
)
from agent_substrate.storage import MemoryStorage


# ============================================================================
# Pydantic validation
# ============================================================================


class TestValidFinding:
    def test_pattern_finding_accepted(self):
        f = Finding.model_validate(
            {
                "agent": "reviewer-security",
                "section": "patterns",
                "item": {
                    "kind": "pattern",
                    "summary": "always run linter before commit",
                },
            }
        )
        assert f.agent == "reviewer-security"
        assert f.section == "patterns"
        assert f.item.kind == "pattern"
        assert f.item.summary == "always run linter before commit"

    def test_pitfall_finding_accepted(self):
        f = Finding.model_validate(
            {
                "agent": "reviewer-security",
                "section": "pitfalls",
                "item": {
                    "kind": "pitfall",
                    "summary": "hard-coded creds",
                    "evidence": "auth.py:42",
                    "why": "rotates with deploys",
                },
            }
        )
        assert f.item.evidence == "auth.py:42"
        assert f.item.why == "rotates with deploys"

    def test_decision_finding_accepted(self):
        f = Finding.model_validate(
            {
                "agent": "reviewer-security",
                "section": "decisions",
                "item": {
                    "kind": "decision",
                    "summary": "creds from env or secret manager",
                    "rationale": "post auth.py:42 incident",
                    "protected": True,
                },
            }
        )
        assert f.item.rationale == "post auth.py:42 incident"
        assert f.item.protected is True

    def test_open_question_finding_accepted(self):
        f = Finding.model_validate(
            {
                "agent": "researcher",
                "section": "open_questions",
                "item": {
                    "kind": "open_question",
                    "summary": "should we use RSC?",
                    "question": "should we use React Server Components?",
                },
            }
        )
        assert f.item.question == "should we use React Server Components?"


class TestInvalidFinding:
    def test_missing_kind_rejected(self):
        with pytest.raises(ValidationError):
            Finding.model_validate(
                {
                    "agent": "x",
                    "section": "patterns",
                    "item": {"summary": "no kind"},
                }
            )

    def test_unknown_kind_rejected(self):
        with pytest.raises(ValidationError):
            Finding.model_validate(
                {
                    "agent": "x",
                    "section": "patterns",
                    "item": {"kind": "bug", "summary": "x"},
                }
            )

    def test_vocabulary_mismatch_rejected(self):
        # section=patterns + kind=pitfall is the canonical example.
        with pytest.raises(ValidationError) as excinfo:
            Finding.model_validate(
                {
                    "agent": "x",
                    "section": "patterns",
                    "item": {"kind": "pitfall", "summary": "x"},
                }
            )
        # Sanity: the consistency-rule message is informative.
        msg = str(excinfo.value)
        assert "Vocabulary mismatch" in msg
        assert "section=" in msg
        assert "kind=" in msg

    def test_extra_field_on_finding_rejected(self):
        with pytest.raises(ValidationError):
            Finding.model_validate(
                {
                    "agent": "x",
                    "section": "patterns",
                    "item": {"kind": "pattern", "summary": "y"},
                    "severity": "high",  # not in schema
                }
            )

    def test_extra_field_on_finding_item_rejected(self):
        with pytest.raises(ValidationError):
            Finding.model_validate(
                {
                    "agent": "x",
                    "section": "patterns",
                    "item": {
                        "kind": "pattern",
                        "summary": "y",
                        "severity": "high",  # not in schema
                    },
                }
            )

    def test_invalid_agent_slug_rejected(self):
        with pytest.raises(ValidationError):
            Finding.model_validate(
                {
                    "agent": "../etc/passwd",
                    "section": "patterns",
                    "item": {"kind": "pattern", "summary": "x"},
                }
            )

    def test_unknown_section_rejected(self):
        with pytest.raises(ValidationError):
            Finding.model_validate(
                {
                    "agent": "x",
                    "section": "notes",  # not in section enum
                    "item": {"kind": "pattern", "summary": "x"},
                }
            )


# ============================================================================
# FindingItem -> section dict translation
# ============================================================================


class TestTranslation:
    def test_pattern_translation(self):
        item = FindingItem(
            kind="pattern",
            summary="virt large tables",
            id="virt-tables",
            evidence="dashboard render +80%",
        )
        out = finding_item_to_section_dict(item)
        assert out == {
            "id": "virt-tables",
            "summary": "virt large tables",
            "evidence": "dashboard render +80%",
            "related": None,
            "lens": None,
            "protected": False,
        }

    def test_pitfall_translation(self):
        item = FindingItem(
            kind="pitfall",
            summary="don't use aria-live=assertive",
            id="aria-live-overuse",
            why="interrupts screen reader flow",
            protected=True,
        )
        out = finding_item_to_section_dict(item)
        assert out == {
            "id": "aria-live-overuse",
            "summary": "don't use aria-live=assertive",
            "why": "interrupts screen reader flow",
            "related": None,
            "lens": None,
            "protected": True,
        }

    def test_decision_summary_maps_to_choice(self):
        item = FindingItem(
            kind="decision",
            summary="use Tailwind for new components",
            id="prefer-tailwind",
            rationale="smaller bundle when purged",
        )
        out = finding_item_to_section_dict(item)
        assert "choice" in out
        assert "summary" not in out
        assert out["choice"] == "use Tailwind for new components"
        assert out["rationale"] == "smaller bundle when purged"
        assert out["id"] == "prefer-tailwind"

    def test_open_question_question_field_preferred(self):
        item = FindingItem(
            kind="open_question",
            summary="rsc-strategy",
            question="should we use React Server Components?",
            id="rsc-strategy",
        )
        out = finding_item_to_section_dict(item)
        assert "question" in out
        assert "summary" not in out
        assert out["question"] == "should we use React Server Components?"

    def test_open_question_falls_back_to_summary(self):
        # When `question` is None, fall back to summary so the
        # universal handle still reaches the OpenQuestion model.
        item = FindingItem(
            kind="open_question",
            summary="should we adopt RSC?",
            id="rsc-strategy",
        )
        out = finding_item_to_section_dict(item)
        assert out["question"] == "should we adopt RSC?"

    def test_id_generated_when_omitted(self):
        item = FindingItem(
            kind="pattern",
            summary="Use Linter X for all Python files!",
        )
        out = finding_item_to_section_dict(item)
        # Slugified, lowercase, hyphenated, max 32 chars, alnum-leading.
        assert "id" in out
        assert isinstance(out["id"], str)
        assert len(out["id"]) <= 32
        assert out["id"][0].isalnum()
        # Non-alnum runs collapsed to hyphens.
        assert " " not in out["id"]


# ============================================================================
# Findings durability — round-trip property test
# ============================================================================


@pytest.fixture
def storage(tmp_path):
    return MemoryStorage(tmp_path / "memory")


def _submit_via_helper(storage, finding_dicts):
    """Mirror `memory_findings_submit` against an isolated storage.

    The server module reads a module-level `storage` bound to BASE_DIR at
    import time, so we replicate the small validation-then-append loop here
    against a tmp-path-isolated MemoryStorage. This exercises the same
    schema + translation + append codepath used by the MCP tool.
    """
    from agent_substrate.schema import Finding, finding_item_to_section_dict

    results = []
    for index, raw in enumerate(finding_dicts):
        finding = Finding.model_validate(raw)
        section_item = finding_item_to_section_dict(finding.item)
        write = storage.append(finding.agent, finding.section, section_item)
        assert write.ok, write.error
        results.append({"index": index, "agent": finding.agent, "section": finding.section, "item_id": section_item["id"]})
    return results


_ROUND_TRIP_FIXTURES = [
    # kind, section, agent, summary, optional kwargs
    pytest.param(
        "pattern", "patterns", "developer-frontend",
        "use react-virtual for tables > 500 rows",
        {"id": "virt-tables", "evidence": "dashboard"},
        id="pattern-1",
    ),
    pytest.param(
        "pattern", "patterns", "developer-frontend",
        "memo expensive selectors",
        {"id": "memo-selectors"},
        id="pattern-2",
    ),
    pytest.param(
        "pattern", "patterns", "developer-frontend",
        "use react-virtual for tables > 500 rows",
        {"id": "virt-tables-rel", "related": ["item-a", "item-b"]},
        id="pattern-related",
    ),
    pytest.param(
        "pattern", "patterns", "developer-frontend",
        "use react-virtual for tables > 500 rows",
        {"id": "virt-tables-lens", "lens": "reviewer-architecture"},
        id="pattern-lens",
    ),
    pytest.param(
        "pitfall", "pitfalls", "reviewer-security",
        "hard-coded credentials in auth.py",
        {"id": "hard-coded-creds", "evidence": "auth.py:42", "why": "rotates with deploys"},
        id="pitfall-1",
    ),
    pytest.param(
        "pitfall", "pitfalls", "reviewer-correctness",
        "off-by-one on retry counter",
        {"id": "retry-off-by-one"},
        id="pitfall-2",
    ),
    pytest.param(
        "pitfall", "pitfalls", "reviewer-security",
        "secrets in logs",
        {"id": "secrets-in-logs", "related": ["creds-via-env"]},
        id="pitfall-related",
    ),
    pytest.param(
        "pitfall", "pitfalls", "reviewer-security",
        "secrets in logs",
        {"id": "secrets-in-logs-lens", "lens": "reviewer-security"},
        id="pitfall-lens",
    ),
    pytest.param(
        "decision", "decisions", "reviewer-security",
        "all credentials must come from env or secret manager",
        {"id": "creds-via-env", "rationale": "post auth.py:42 incident", "protected": True},
        id="decision-1",
    ),
    pytest.param(
        "decision", "decisions", "developer-backend",
        "use postgres for new services",
        {"id": "postgres-default"},
        id="decision-2",
    ),
    pytest.param(
        "decision", "decisions", "developer-backend",
        "use postgres for new services",
        {"id": "postgres-default-rel", "related": ["secrets-in-logs", "creds-via-env"]},
        id="decision-related",
    ),
    pytest.param(
        "decision", "decisions", "reviewer-security",
        "creds via env",
        {"id": "creds-via-env-lens", "lens": "reviewer-architecture"},
        id="decision-lens",
    ),
    pytest.param(
        "open_question", "open_questions", "researcher",
        "rsc-strategy",
        {"id": "rsc-strategy", "question": "should we use React Server Components?"},
        id="open-question-1",
    ),
    pytest.param(
        "open_question", "open_questions", "researcher",
        "edge-cache strategy",
        {"id": "edge-cache"},  # falls back to summary for question
        id="open-question-2",
    ),
    pytest.param(
        "open_question", "open_questions", "researcher",
        "ssr-strategy",
        {"id": "ssr-strategy", "related": ["rsc-strategy"]},
        id="open-question-related",
    ),
    pytest.param(
        "open_question", "open_questions", "researcher",
        "rsc-strategy-lens",
        {"id": "rsc-strategy-lens", "lens": "reviewer-architecture"},
        id="open-question-lens",
    ),
]


@pytest.mark.parametrize("kind,section,agent,summary,extras", _ROUND_TRIP_FIXTURES)
def test_findings_round_trip(storage, kind, section, agent, summary, extras):
    """Findings durability invariant.

    For each kind, build a valid Finding, submit via the helper that mirrors
    `memory_findings_submit`, then read back via `memory_read(agent_name=...)`
    and assert the round-tripped item carries the original `summary` (or
    `choice`/`question`) and lands in the right section. `kind` is implicit
    in the section the item lives under (per-section models drop the redundant
    `kind` field by design).
    """
    item: dict = {"kind": kind, "summary": summary}
    item.update(extras)
    finding = {"agent": agent, "section": section, "item": item}

    _submit_via_helper(storage, [finding])

    read = storage.read(agent)
    assert read.exists, f"Memory file for {agent!r} should exist after submit"
    items = read.parsed[section]
    assert len(items) == 1, f"expected exactly one item in {section!r}, got {items}"

    stored = items[0]
    # The universal `summary` handle survives:
    if kind == "decision":
        assert stored["choice"] == summary
    elif kind == "open_question":
        # `question` field holds either the explicit question or the summary fallback.
        expected = extras.get("question") or summary
        assert stored["question"] == expected
    else:
        assert stored["summary"] == summary

    # Section placement implies kind survived the translation.
    expected_section = {
        "pattern": "patterns",
        "pitfall": "pitfalls",
        "decision": "decisions",
        "open_question": "open_questions",
    }[kind]
    assert section == expected_section

    # `related` must survive byte-for-byte (or be None on both sides).
    expected_related = extras.get("related")
    assert stored.get("related") == expected_related

    # `lens` must survive byte-for-byte (or be None on both sides).
    expected_lens = extras.get("lens")
    assert stored.get("lens") == expected_lens


def test_findings_round_trip_full_batch(storage):
    """Submit the full batch in one call, then read each agent back.

    Verifies that submitting many findings in a single call (across multiple
    agents and kinds) lands every item in its correct namespace and section.
    """
    findings = []
    for kind, section, agent, summary, extras in [
        ("pattern", "patterns", "developer-frontend", "p1 summary", {"id": "p1"}),
        ("pitfall", "pitfalls", "reviewer-security", "pf1 summary", {"id": "pf1"}),
        ("decision", "decisions", "developer-backend", "d1 choice", {"id": "d1"}),
        ("open_question", "open_questions", "researcher", "q1 body", {"id": "q1"}),
    ]:
        item: dict = {"kind": kind, "summary": summary}
        item.update(extras)
        findings.append({"agent": agent, "section": section, "item": item})

    _submit_via_helper(storage, findings)

    assert (
        storage.read("developer-frontend").parsed["patterns"][0]["summary"]
        == "p1 summary"
    )
    assert (
        storage.read("reviewer-security").parsed["pitfalls"][0]["summary"]
        == "pf1 summary"
    )
    assert (
        storage.read("developer-backend").parsed["decisions"][0]["choice"]
        == "d1 choice"
    )
    assert (
        storage.read("researcher").parsed["open_questions"][0]["question"]
        == "q1 body"
    )


# ============================================================================
# Related-field unit tests on the per-section models
# ============================================================================


class TestRelatedFieldOnSectionModels:
    """`related: list[str] | None` was added to all four per-section models in
    Task 19. These tests pin the contract: list[str] accepted, None is the
    default, non-list values are rejected.
    """

    def test_pattern_constructs_with_related(self):
        from agent_substrate.schema import Pattern

        p = Pattern(id="x", summary="y", related=["a", "b"])
        assert p.related == ["a", "b"]

    def test_pitfall_constructs_with_related(self):
        from agent_substrate.schema import Pitfall

        p = Pitfall(id="x", summary="y", related=["a"])
        assert p.related == ["a"]

    def test_decision_constructs_with_related(self):
        from agent_substrate.schema import Decision

        d = Decision(id="x", choice="y", related=["a", "b"])
        assert d.related == ["a", "b"]

    def test_open_question_constructs_with_related(self):
        from agent_substrate.schema import OpenQuestion

        q = OpenQuestion(id="x", question="y?", related=["a"])
        assert q.related == ["a"]

    def test_pattern_model_dump_round_trips_through_yaml(self):
        import yaml

        from agent_substrate.schema import Pattern

        p = Pattern(id="x", summary="y", related=["a", "b"])
        dumped = yaml.safe_dump(p.model_dump(exclude_none=False), sort_keys=False)
        reloaded = yaml.safe_load(dumped)
        p2 = Pattern.model_validate(reloaded)
        assert p2 == p
        assert p2.related == ["a", "b"]

    def test_pattern_related_not_a_list_rejected(self):
        from agent_substrate.schema import Pattern

        with pytest.raises(ValidationError):
            Pattern(id="x", summary="y", related="not-a-list")

    def test_pitfall_related_not_a_list_rejected(self):
        from agent_substrate.schema import Pitfall

        with pytest.raises(ValidationError):
            Pitfall(id="x", summary="y", related="not-a-list")

    def test_decision_related_not_a_list_rejected(self):
        from agent_substrate.schema import Decision

        with pytest.raises(ValidationError):
            Decision(id="x", choice="y", related="not-a-list")

    def test_open_question_related_not_a_list_rejected(self):
        from agent_substrate.schema import OpenQuestion

        with pytest.raises(ValidationError):
            OpenQuestion(id="x", question="y?", related="not-a-list")

    def test_related_defaults_to_none(self):
        from agent_substrate.schema import (
            Decision,
            OpenQuestion,
            Pattern,
            Pitfall,
        )

        assert Pattern(id="x", summary="y").related is None
        assert Pitfall(id="x", summary="y").related is None
        assert Decision(id="x", choice="y").related is None
        assert OpenQuestion(id="x", question="y?").related is None


def test_yaml_serializes_none_related_as_null(storage, tmp_path):
    """Verify on-disk YAML form: `related: null` (not omitted) when None.

    `_serialize` calls `model_dump(exclude_none=False)`, so None should land
    in the file as an explicit `null`. This guards against future drift
    toward `exclude_none=True` which would silently drop the field.
    """
    finding = {
        "agent": "developer-frontend",
        "section": "patterns",
        "item": {"kind": "pattern", "summary": "no related set", "id": "p-none"},
    }
    _submit_via_helper(storage, [finding])

    yaml_path = storage.base_dir / "developer-frontend.yaml"
    raw = yaml_path.read_text(encoding="utf-8")
    # Serialized form must contain an explicit null for `related`.
    assert "related: null" in raw, (
        f"expected `related: null` in serialized YAML, got:\n{raw}"
    )


def test_yaml_serializes_related_list(storage):
    """List form should serialize as a YAML sequence and round-trip."""
    finding = {
        "agent": "developer-frontend",
        "section": "patterns",
        "item": {
            "kind": "pattern",
            "summary": "with related",
            "id": "p-rel",
            "related": ["item-a", "item-b"],
        },
    }
    _submit_via_helper(storage, [finding])

    parsed = storage.read("developer-frontend").parsed
    assert parsed["patterns"][0]["related"] == ["item-a", "item-b"]


# ============================================================================
# Lens-field unit tests on the per-section models (Task 20)
# ============================================================================


class TestLensFieldOnSectionModels:
    """`lens: str | None` was added to all four per-section models in
    Task 20 to capture the running-teammate slug from `parallel-panel` skills.
    These tests pin the contract: str accepted, None default, round-trips
    through YAML, and `extra="forbid"` still rejects unknown fields.
    """

    def test_pattern_constructs_with_lens(self):
        from agent_substrate.schema import Pattern

        p = Pattern(id="x", summary="y", lens="reviewer-architecture")
        assert p.lens == "reviewer-architecture"

    def test_pitfall_constructs_with_lens(self):
        from agent_substrate.schema import Pitfall

        p = Pitfall(id="x", summary="y", lens="reviewer-security")
        assert p.lens == "reviewer-security"

    def test_decision_constructs_with_lens(self):
        from agent_substrate.schema import Decision

        d = Decision(id="x", choice="y", lens="reviewer-architecture")
        assert d.lens == "reviewer-architecture"

    def test_open_question_constructs_with_lens(self):
        from agent_substrate.schema import OpenQuestion

        q = OpenQuestion(id="x", question="y?", lens="reviewer-architecture")
        assert q.lens == "reviewer-architecture"

    def test_pattern_model_dump_round_trips_through_yaml(self):
        import yaml

        from agent_substrate.schema import Pattern

        p = Pattern(id="x", summary="y", lens="reviewer-architecture")
        dumped = yaml.safe_dump(p.model_dump(exclude_none=False), sort_keys=False)
        reloaded = yaml.safe_load(dumped)
        p2 = Pattern.model_validate(reloaded)
        assert p2 == p
        assert p2.lens == "reviewer-architecture"

    def test_lens_defaults_to_none(self):
        from agent_substrate.schema import (
            Decision,
            OpenQuestion,
            Pattern,
            Pitfall,
        )

        assert Pattern(id="x", summary="y").lens is None
        assert Pitfall(id="x", summary="y").lens is None
        assert Decision(id="x", choice="y").lens is None
        assert OpenQuestion(id="x", question="y?").lens is None

    def test_finding_item_accepts_lens(self):
        from agent_substrate.schema import FindingItem

        item = FindingItem(
            kind="pattern", summary="y", lens="reviewer-architecture"
        )
        assert item.lens == "reviewer-architecture"

    def test_finding_item_lens_defaults_to_none(self):
        from agent_substrate.schema import FindingItem

        assert FindingItem(kind="pattern", summary="y").lens is None


def test_finding_item_persists_lens_via_submit(storage):
    """Submitting a Finding with `item.lens` set must persist and read back."""
    finding = {
        "agent": "reviewer-security",
        "section": "pitfalls",
        "item": {
            "kind": "pitfall",
            "summary": "secrets in logs",
            "id": "secrets-in-logs-persist",
            "lens": "reviewer-security",
        },
    }
    _submit_via_helper(storage, [finding])

    parsed = storage.read("reviewer-security").parsed
    assert parsed["pitfalls"][0]["lens"] == "reviewer-security"


def test_yaml_serializes_none_lens_as_null(storage):
    """On-disk YAML must contain `lens: null` (not omitted) when None.

    Mirrors the `related: null` guard — `_serialize` calls
    `model_dump(exclude_none=False)`, so None lands in the file as an explicit
    `null`. Guards against future drift toward `exclude_none=True`.
    """
    finding = {
        "agent": "developer-frontend",
        "section": "patterns",
        "item": {"kind": "pattern", "summary": "no lens set", "id": "p-no-lens"},
    }
    _submit_via_helper(storage, [finding])

    yaml_path = storage.base_dir / "developer-frontend.yaml"
    raw = yaml_path.read_text(encoding="utf-8")
    assert "lens: null" in raw, (
        f"expected `lens: null` in serialized YAML, got:\n{raw}"
    )


def test_extra_field_still_rejected_after_lens_addition():
    """Regression guard: adding `lens` must not relax `extra=forbid`.

    A field that is NOT `lens` (and not in the schema) must still be rejected
    by the `model_config = ConfigDict(extra="forbid")` on FindingItem and on
    each per-section model.
    """
    from agent_substrate.schema import (
        Decision,
        FindingItem,
        OpenQuestion,
        Pattern,
        Pitfall,
    )

    # FindingItem still rejects unknown fields.
    with pytest.raises(ValidationError):
        FindingItem.model_validate(
            {"kind": "pattern", "summary": "y", "severity": "high"}
        )

    # Per-section models still reject unknown fields.
    with pytest.raises(ValidationError):
        Pattern.model_validate({"id": "x", "summary": "y", "severity": "high"})
    with pytest.raises(ValidationError):
        Pitfall.model_validate({"id": "x", "summary": "y", "severity": "high"})
    with pytest.raises(ValidationError):
        Decision.model_validate({"id": "x", "choice": "y", "severity": "high"})
    with pytest.raises(ValidationError):
        OpenQuestion.model_validate(
            {"id": "x", "question": "y?", "severity": "high"}
        )

    # And the full Finding still rejects unknowns at the item level.
    with pytest.raises(ValidationError):
        Finding.model_validate(
            {
                "agent": "x",
                "section": "patterns",
                "item": {
                    "kind": "pattern",
                    "summary": "y",
                    "lens": "reviewer-architecture",
                    "bogus": True,
                },
            }
        )
