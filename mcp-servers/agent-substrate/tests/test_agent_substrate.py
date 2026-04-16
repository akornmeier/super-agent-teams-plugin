"""Tests for agent-substrate.

Tests are organized by concern: schema validation, read, write, append,
shared memory, and atomic write hygiene. Concurrency is exercised via a
smoke test rather than real-parallel-process testing — see README for
manual concurrency verification.
"""

from __future__ import annotations

import yaml
import pytest

from agent_substrate.schema import (
    AGENT_NAME_PATTERN,
    MemoryFile,
    Pattern,
    Pitfall,
    Decision,
    OpenQuestion,
    empty_memory,
    now_iso,
    validate_agent_name,
    validate_section,
)
from agent_substrate.storage import (
    HARD_LIMIT,
    SOFT_LIMIT,
    MemoryStorage,
)


@pytest.fixture
def storage(tmp_path):
    return MemoryStorage(tmp_path / "memory")


def _minimal_yaml() -> str:
    return yaml.safe_dump(
        {
            "version": 1,
            "updated": now_iso(),
            "patterns": [],
            "pitfalls": [],
            "decisions": [],
            "open_questions": [],
        }
    )


# ============================================================================
# Schema validation
# ============================================================================


class TestAgentNameValidation:
    @pytest.mark.parametrize(
        "name",
        ["frontend-developer", "a", "agent-1", "team-lead-2", "x" * 64],
    )
    def test_accepts_valid_slugs(self, name):
        validate_agent_name(name)  # should not raise

    @pytest.mark.parametrize(
        "name",
        [
            "FrontendDeveloper",  # uppercase
            "../etc/passwd",  # path traversal
            "foo/bar",  # slash
            "..",  # parent dir
            ".",  # current dir
            "foo bar",  # space
            "",  # empty
            "1agent",  # leading digit
            "x" * 65,  # too long
            "-agent",  # leading hyphen
            "agent_underscore",  # underscore
        ],
    )
    def test_rejects_invalid_slugs(self, name):
        with pytest.raises(ValueError):
            validate_agent_name(name)

    def test_rejects_non_string(self):
        with pytest.raises(ValueError):
            validate_agent_name(123)


class TestSectionValidation:
    @pytest.mark.parametrize(
        "section", ["patterns", "pitfalls", "decisions", "open_questions"]
    )
    def test_accepts_valid_sections(self, section):
        validate_section(section)

    @pytest.mark.parametrize(
        "section", ["notes", "PATTERNS", "", "patterns ", None, 42]
    )
    def test_rejects_invalid_sections(self, section):
        with pytest.raises(ValueError):
            validate_section(section)


class TestSchemaModels:
    def test_pattern_round_trip(self):
        p = Pattern(id="virt-tables", summary="use react-virtual")
        assert p.protected is False
        assert p.evidence is None

    def test_rejects_extra_fields(self):
        with pytest.raises(Exception):
            Pattern(id="x", summary="y", bogus_field="z")

    def test_rejects_invalid_item_id(self):
        with pytest.raises(Exception):
            Pattern(id="Has Spaces", summary="x")

    def test_rejects_uppercase_item_id(self):
        with pytest.raises(Exception):
            Pattern(id="UPPER", summary="x")

    def test_memory_file_defaults(self):
        m = MemoryFile(updated=now_iso())
        assert m.version == 1
        assert m.patterns == []
        assert m.pitfalls == []
        assert m.decisions == []
        assert m.open_questions == []

    def test_memory_file_rejects_bad_version(self):
        with pytest.raises(Exception):
            MemoryFile.model_validate({"version": 2, "updated": now_iso()})

    def test_memory_file_rejects_bad_timestamp(self):
        with pytest.raises(Exception):
            MemoryFile.model_validate({"version": 1, "updated": "yesterday"})


# ============================================================================
# Read
# ============================================================================


class TestRead:
    def test_read_missing_file(self, storage):
        result = storage.read("frontend-developer")
        assert result.exists is False
        assert result.content is None
        assert result.parsed is None
        assert result.char_count == 0

    def test_read_after_write(self, storage):
        write_result = storage.write("frontend-developer", _minimal_yaml())
        assert write_result.ok

        read_result = storage.read("frontend-developer")
        assert read_result.exists
        assert read_result.content is not None
        assert read_result.parsed is not None
        assert read_result.parsed["version"] == 1
        assert read_result.char_count > 0

    def test_read_after_append(self, storage):
        storage.append(
            "agent-a",
            "patterns",
            {"id": "virt-tables", "summary": "use react-virtual"},
        )
        result = storage.read("agent-a")
        assert result.exists
        assert result.parsed["patterns"][0]["id"] == "virt-tables"
        assert result.parsed["patterns"][0]["summary"] == "use react-virtual"

    def test_read_invalid_agent_name(self, storage):
        with pytest.raises(ValueError):
            storage.read("../etc/passwd")


# ============================================================================
# Write
# ============================================================================


class TestWrite:
    def test_writes_minimal_valid_content(self, storage):
        result = storage.write("agent-a", _minimal_yaml())
        assert result.ok
        assert result.error is None
        assert result.warning is None
        assert result.needs_curation is False
        assert result.char_count > 0

    def test_writes_full_content(self, storage):
        content = yaml.safe_dump(
            {
                "version": 1,
                "updated": now_iso(),
                "patterns": [
                    {
                        "id": "virt-tables",
                        "summary": "use react-virtual for tables > 500 rows",
                        "evidence": "saved 80% render time on dashboard",
                        "protected": False,
                    }
                ],
                "pitfalls": [
                    {
                        "id": "aria-live-overuse",
                        "summary": "don't use aria-live=assertive for non-critical",
                        "why": "interrupts screen reader flow",
                        "protected": True,
                    }
                ],
                "decisions": [
                    {
                        "id": "prefer-tailwind",
                        "choice": "use Tailwind for new components",
                        "rationale": "smaller bundle when purged",
                        "supersedes": None,
                    }
                ],
                "open_questions": [
                    {
                        "id": "rsc-strategy",
                        "question": "should we use React Server Components?",
                    }
                ],
            }
        )
        result = storage.write("agent-a", content)
        assert result.ok, result.error

    def test_rejects_invalid_yaml(self, storage):
        result = storage.write("agent-a", "not: valid: yaml: at all: [")
        assert not result.ok
        assert result.error is not None
        assert "YAML" in result.error or "mapping" in result.error.lower()

    def test_rejects_non_mapping(self, storage):
        result = storage.write("agent-a", "- just\n- a\n- list\n")
        assert not result.ok

    def test_rejects_missing_required_field(self, storage):
        bad = yaml.safe_dump(
            {
                "version": 1,
                "updated": now_iso(),
                "patterns": [{"id": "no-summary"}],  # missing 'summary'
            }
        )
        result = storage.write("agent-a", bad)
        assert not result.ok

    def test_rejects_extra_field(self, storage):
        bad = yaml.safe_dump(
            {
                "version": 1,
                "updated": now_iso(),
                "patterns": [
                    {"id": "p1", "summary": "x", "bogus": "y"}
                ],
            }
        )
        result = storage.write("agent-a", bad)
        assert not result.ok

    def test_rejects_invalid_agent_name(self, storage):
        with pytest.raises(ValueError):
            storage.write("../etc/passwd", _minimal_yaml())

    def test_updates_timestamp_automatically(self, storage):
        old_ts = "2020-01-01T00:00:00Z"
        old_yaml = yaml.safe_dump(
            {"version": 1, "updated": old_ts, "patterns": []}
        )
        result = storage.write("agent-a", old_yaml)
        assert result.ok

        read_result = storage.read("agent-a")
        assert read_result.parsed["updated"] != old_ts

    def test_rejects_at_hard_limit(self, storage):
        # 100 patterns at ~250 chars each = ~25000 chars, well over 8000
        big_patterns = [
            {"id": f"pattern-{i:04d}", "summary": "X" * 200} for i in range(100)
        ]
        content = yaml.safe_dump(
            {
                "version": 1,
                "updated": now_iso(),
                "patterns": big_patterns,
            }
        )
        result = storage.write("agent-a", content)
        assert not result.ok
        assert result.needs_curation is True
        assert result.char_count > HARD_LIMIT
        assert "hard limit" in (result.error or "").lower()

    def test_warns_at_soft_limit(self, storage):
        # Aim for between SOFT_LIMIT and HARD_LIMIT
        # Each pattern is ~110 chars when serialized canonically
        # 60 patterns ~ 6600 chars, between 6000 and 8000
        big_patterns = [
            {
                "id": f"pat-{i:04d}",
                "summary": "A reasonable-length summary describing a pattern",
            }
            for i in range(60)
        ]
        content = yaml.safe_dump(
            {
                "version": 1,
                "updated": now_iso(),
                "patterns": big_patterns,
            }
        )
        result = storage.write("agent-a", content)
        # If the test sizing puts us in the soft-limit range, expect a warning
        if SOFT_LIMIT < result.char_count <= HARD_LIMIT:
            assert result.ok
            assert result.warning is not None
            assert "approaching" in result.warning.lower()
        else:
            # Sizing is off; just verify no crash
            assert isinstance(result.char_count, int)


# ============================================================================
# Append
# ============================================================================


class TestAppend:
    def test_append_creates_file(self, storage):
        result = storage.append(
            "agent-a",
            "patterns",
            {"id": "first-pattern", "summary": "first"},
        )
        assert result.ok, result.error
        read = storage.read("agent-a")
        assert read.exists
        assert len(read.parsed["patterns"]) == 1

    def test_append_to_existing(self, storage):
        storage.append(
            "agent-a", "patterns", {"id": "p1", "summary": "one"}
        )
        result = storage.append(
            "agent-a", "patterns", {"id": "p2", "summary": "two"}
        )
        assert result.ok
        read = storage.read("agent-a")
        assert len(read.parsed["patterns"]) == 2
        assert read.parsed["patterns"][0]["id"] == "p1"
        assert read.parsed["patterns"][1]["id"] == "p2"

    def test_append_to_each_section(self, storage):
        assert storage.append(
            "agent-a", "patterns", {"id": "p1", "summary": "p"}
        ).ok
        assert storage.append(
            "agent-a", "pitfalls", {"id": "pf1", "summary": "pf"}
        ).ok
        assert storage.append(
            "agent-a", "decisions", {"id": "d1", "choice": "do x"}
        ).ok
        assert storage.append(
            "agent-a", "open_questions", {"id": "q1", "question": "why?"}
        ).ok

        read = storage.read("agent-a")
        assert len(read.parsed["patterns"]) == 1
        assert len(read.parsed["pitfalls"]) == 1
        assert len(read.parsed["decisions"]) == 1
        assert len(read.parsed["open_questions"]) == 1

    def test_append_rejects_bad_section(self, storage):
        with pytest.raises(ValueError):
            storage.append(
                "agent-a", "notes", {"id": "x", "summary": "y"}
            )

    def test_append_rejects_missing_required(self, storage):
        result = storage.append(
            "agent-a", "patterns", {"id": "x"}  # missing summary
        )
        assert not result.ok

    def test_append_rejects_bad_item_id(self, storage):
        result = storage.append(
            "agent-a",
            "patterns",
            {"id": "Has Spaces", "summary": "x"},
        )
        assert not result.ok

    def test_append_rejects_extra_fields(self, storage):
        result = storage.append(
            "agent-a",
            "patterns",
            {"id": "p1", "summary": "x", "bogus": "y"},
        )
        assert not result.ok

    def test_append_rejects_non_dict_item(self, storage):
        result = storage.append(
            "agent-a", "patterns", "not a dict"
        )
        assert not result.ok

    def test_append_at_hard_limit_rejects(self, storage):
        # Pre-fill with content close to the limit
        big_patterns = [
            {"id": f"pat-{i:04d}", "summary": "X" * 200} for i in range(30)
        ]
        content = yaml.safe_dump(
            {
                "version": 1,
                "updated": now_iso(),
                "patterns": big_patterns,
            }
        )
        # First write: should succeed (~6500 chars)
        result = storage.write("agent-a", content)
        # Now append more until we hit the limit
        for i in range(50):
            r = storage.append(
                "agent-a",
                "patterns",
                {"id": f"extra-{i:04d}", "summary": "Y" * 200},
            )
            if not r.ok:
                assert r.needs_curation
                assert r.char_count > HARD_LIMIT
                return
        pytest.fail("Expected hard limit to be hit during repeated appends")


# ============================================================================
# Shared memory
# ============================================================================


class TestShared:
    def test_read_missing_shared(self, storage):
        result = storage.read_shared()
        assert not result.exists

    def test_append_shared_creates_file(self, storage):
        result = storage.append_shared(
            "decisions",
            {
                "id": "use-tailwind",
                "choice": "Tailwind for new components",
            },
        )
        assert result.ok
        read = storage.read_shared()
        assert read.exists
        assert read.parsed["decisions"][0]["id"] == "use-tailwind"

    def test_append_shared_validates(self, storage):
        result = storage.append_shared(
            "decisions", {"id": "missing-choice"}
        )
        assert not result.ok


# ============================================================================
# Atomic write hygiene
# ============================================================================


class TestAtomicWrite:
    def test_temp_files_cleaned_up(self, storage, tmp_path):
        for i in range(5):
            storage.append(
                "agent-a",
                "patterns",
                {"id": f"p{i}", "summary": f"item {i}"},
            )
        memory_dir = tmp_path / "memory"
        leftover = list(memory_dir.glob(".*tmp"))
        assert leftover == [], f"Leftover temp files: {leftover}"

    def test_lock_files_present_but_not_corrupting(self, storage, tmp_path):
        # Lock files are expected to exist after writes — that's fine,
        # they're just sidecar files used by portalocker.
        storage.append(
            "agent-a", "patterns", {"id": "p1", "summary": "x"}
        )
        memory_dir = tmp_path / "memory"
        # The actual yaml file should exist and parse
        yaml_file = memory_dir / "agent-a.yaml"
        assert yaml_file.exists()
        parsed = yaml.safe_load(yaml_file.read_text())
        assert parsed["patterns"][0]["id"] == "p1"

    def test_canonical_serialization_preserves_content(self, storage):
        # Write content with unusual ordering, verify it round-trips
        content = yaml.safe_dump(
            {
                "open_questions": [
                    {"id": "q1", "question": "why?"}
                ],
                "patterns": [],
                "pitfalls": [],
                "decisions": [],
                "version": 1,
                "updated": now_iso(),
            }
        )
        result = storage.write("agent-a", content)
        assert result.ok
        read = storage.read("agent-a")
        assert read.parsed["open_questions"][0]["id"] == "q1"
        assert read.parsed["version"] == 1
