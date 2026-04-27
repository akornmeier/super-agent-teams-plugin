"""Tests for team-scoped substrate storage.

Mirrors the per-agent storage tests but exercises `TeamMemoryStorage`
rooted at `<base>/teams/<team-name>/`. Covers: empty namespace reads,
append + read round-trip, soft/hard limits, slug rejection, concurrent
append serialization, summary, and delete.
"""

from __future__ import annotations

import threading

import pytest

from agent_substrate.schema import now_iso
from agent_substrate.storage import HARD_LIMIT, SOFT_LIMIT
from agent_substrate.team_storage import (
    TEAMS_DIRNAME,
    TeamMemoryStorage,
    validate_team_name,
)


@pytest.fixture
def team_storage(tmp_path):
    return TeamMemoryStorage(tmp_path / "memory")


# ============================================================================
# Slug validation
# ============================================================================


class TestTeamNameValidation:
    @pytest.mark.parametrize(
        "name",
        ["review-fix-auth", "ship-feature-x", "a", "team-1", "x" * 64],
    )
    def test_accepts_valid_slugs(self, name):
        validate_team_name(name)  # should not raise

    @pytest.mark.parametrize(
        "name",
        [
            "../etc/passwd",  # path traversal
            "foo/bar",  # slash
            "..",  # parent dir
            "",  # empty
            "1team",  # leading digit
            "x" * 65,  # too long
            "Team-Upper",  # uppercase
        ],
    )
    def test_rejects_invalid_slugs(self, name):
        with pytest.raises(ValueError):
            validate_team_name(name)

    def test_rejects_non_string(self):
        with pytest.raises(ValueError):
            validate_team_name(42)


# ============================================================================
# Read empty namespace
# ============================================================================


class TestReadEmpty:
    def test_read_missing_team(self, team_storage):
        result = team_storage.read("review-nonexistent")
        assert result.exists is False
        assert result.content is None
        assert result.parsed is None
        assert result.char_count == 0

    def test_read_invalid_team_name(self, team_storage):
        with pytest.raises(ValueError):
            team_storage.read("../etc/passwd")


# ============================================================================
# Append + read round-trip
# ============================================================================


class TestAppendReadRoundTrip:
    def test_append_creates_team_dir_and_file(self, team_storage, tmp_path):
        result = team_storage.append(
            "review-auth",
            "handoffs",
            {"id": "first-handoff", "summary": "stage 1 → stage 2"},
        )
        assert result.ok, result.error

        team_dir = tmp_path / "memory" / TEAMS_DIRNAME / "review-auth"
        scratch = team_dir / "scratch.yaml"
        assert team_dir.is_dir()
        assert scratch.is_file()

    def test_append_then_read(self, team_storage):
        assert team_storage.append(
            "review-auth",
            "handoffs",
            {"id": "h1", "summary": "stage 1 complete"},
        ).ok
        result = team_storage.read("review-auth")
        assert result.exists
        assert result.parsed["handoffs"][0]["id"] == "h1"
        assert result.parsed["handoffs"][0]["summary"] == "stage 1 complete"

    def test_append_to_each_section(self, team_storage):
        assert team_storage.append(
            "team-a", "decisions", {"id": "d1", "summary": "team chose X"}
        ).ok
        assert team_storage.append(
            "team-a",
            "dedup_decisions",
            {
                "id": "dd1",
                "summary": "correctness deferred to security",
                "peers": ["reviewer-correctness", "reviewer-security"],
            },
        ).ok
        assert team_storage.append(
            "team-a",
            "handoffs",
            {
                "id": "h1",
                "summary": "stage 1 → stage 2",
                "from_stage": "work",
                "to_stage": "review",
                "artifact_path": "docs/work/foo.md",
            },
        ).ok
        assert team_storage.append(
            "team-a",
            "escalations",
            {"id": "e1", "summary": "blocker", "severity": "blocker"},
        ).ok

        result = team_storage.read("team-a")
        assert len(result.parsed["decisions"]) == 1
        assert len(result.parsed["dedup_decisions"]) == 1
        assert len(result.parsed["handoffs"]) == 1
        assert len(result.parsed["escalations"]) == 1

    def test_append_rejects_agent_memory_sections(self, team_storage):
        # Agent-memory sections (patterns, pitfalls, open_questions) are NOT
        # valid for team scratch. The dedicated team-scratch validator must
        # reject them so callers don't accidentally use the wrong vocabulary.
        # Mirrors the per-agent storage behavior where `validate_section`
        # raises rather than returning a WriteResult.
        for bad_section in ("patterns", "pitfalls", "open_questions"):
            with pytest.raises(ValueError, match="Invalid team-scratch section"):
                team_storage.append(
                    "team-x",
                    bad_section,
                    {"id": "x", "summary": "y"},
                )

    def test_append_invalid_team_name(self, team_storage):
        with pytest.raises(ValueError):
            team_storage.append(
                "../etc/passwd",
                "handoffs",
                {"id": "x", "summary": "y"},
            )

    def test_append_isolates_teams(self, team_storage):
        team_storage.append(
            "team-a", "handoffs", {"id": "a-h", "summary": "team-a handoff"}
        )
        team_storage.append(
            "team-b", "handoffs", {"id": "b-h", "summary": "team-b handoff"}
        )
        a = team_storage.read("team-a")
        b = team_storage.read("team-b")
        assert a.parsed["handoffs"][0]["id"] == "a-h"
        assert b.parsed["handoffs"][0]["id"] == "b-h"
        assert len(a.parsed["handoffs"]) == 1
        assert len(b.parsed["handoffs"]) == 1


# ============================================================================
# Limits
# ============================================================================


class TestLimits:
    def test_warns_at_soft_limit(self, team_storage):
        # Repeated appends, each ~110 chars when canonicalized — push past
        # SOFT_LIMIT but stay under HARD_LIMIT.
        warning_seen = False
        for i in range(80):
            r = team_storage.append(
                "team-soft",
                "handoffs",
                {
                    "id": f"hand-{i:04d}",
                    "summary": "A reasonable-length summary describing a handoff",
                },
            )
            if r.warning is not None and SOFT_LIMIT < r.char_count <= HARD_LIMIT:
                warning_seen = True
                assert "approaching" in r.warning.lower()
                break
            if not r.ok:
                # Hit the hard limit before soft-warning showed up; sizing
                # was off for this run — accept and stop.
                break
        assert warning_seen, "Expected a soft-limit warning during repeated appends"

    def test_rejects_at_hard_limit(self, team_storage):
        for i in range(200):
            r = team_storage.append(
                "team-hard",
                "handoffs",
                {"id": f"hand-{i:04d}", "summary": "X" * 200},
            )
            if not r.ok:
                assert r.needs_curation
                assert r.char_count > HARD_LIMIT
                assert "hard limit" in (r.error or "").lower()
                return
        pytest.fail("Expected hard limit to be hit during repeated appends")


# ============================================================================
# Concurrent appends serialize correctly
# ============================================================================


class TestConcurrency:
    def test_threaded_appends_all_persisted(self, team_storage):
        # Two threads each append a different item to the same team. Both
        # appends must succeed and both items must be present after.
        team = "team-concurrent"
        errors: list[Exception] = []

        def append(item_id: str):
            try:
                r = team_storage.append(
                    team, "handoffs", {"id": item_id, "summary": item_id}
                )
                assert r.ok, r.error
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        t1 = threading.Thread(target=append, args=("thread-one",))
        t2 = threading.Thread(target=append, args=("thread-two",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert errors == [], f"Threaded appends raised: {errors}"
        result = team_storage.read(team)
        ids = sorted(p["id"] for p in result.parsed["handoffs"])
        assert ids == ["thread-one", "thread-two"]


# ============================================================================
# Summary
# ============================================================================


class TestSummary:
    def test_summary_missing_team(self, team_storage):
        s = team_storage.summary("review-nope")
        assert s["exists"] is False
        assert s["char_count"] == 0
        assert s["counts"] == {
            "decisions": 0,
            "dedup_decisions": 0,
            "handoffs": 0,
            "escalations": 0,
        }

    def test_summary_after_appends(self, team_storage):
        team_storage.append("t", "handoffs", {"id": "h1", "summary": "x"})
        team_storage.append("t", "handoffs", {"id": "h2", "summary": "y"})
        team_storage.append("t", "decisions", {"id": "d1", "summary": "z"})
        s = team_storage.summary("t")
        assert s["exists"] is True
        assert s["counts"]["handoffs"] == 2
        assert s["counts"]["dedup_decisions"] == 0
        assert s["counts"]["decisions"] == 1
        assert s["counts"]["escalations"] == 0
        assert s["char_count"] > 0

    def test_summary_invalid_team_name(self, team_storage):
        with pytest.raises(ValueError):
            team_storage.summary("../etc/passwd")


# ============================================================================
# Delete
# ============================================================================


class TestDelete:
    def test_delete_existing_team(self, team_storage, tmp_path):
        team_storage.append(
            "team-del", "handoffs", {"id": "h1", "summary": "x"}
        )
        team_dir = tmp_path / "memory" / TEAMS_DIRNAME / "team-del"
        assert team_dir.is_dir()

        removed = team_storage.delete("team-del")
        assert removed is True
        assert not team_dir.exists()

        # Subsequent read shows empty namespace.
        result = team_storage.read("team-del")
        assert result.exists is False

    def test_delete_missing_team(self, team_storage):
        assert team_storage.delete("never-existed") is False

    def test_delete_invalid_team_name(self, team_storage):
        with pytest.raises(ValueError):
            team_storage.delete("../etc/passwd")


# Avoid unused-import warning for now_iso while keeping the import handy
# for future tests that need to author canonical content.
_ = now_iso
