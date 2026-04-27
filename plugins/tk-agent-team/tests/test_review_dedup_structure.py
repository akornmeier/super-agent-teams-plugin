"""Structural compliance test for /review parallel-panel migration.

Does NOT execute /review — verifies the skill body and reviewer agents are wired
to produce the expected dedup behavior. Runtime verification is manual; see
fixtures/review-dedup/README.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "review" / "SKILL.md"
REVIEWERS = [REPO / "agents" / "reviewer" / f"{p}.md" for p in ("architecture", "correctness", "security")]


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


class TestReviewSkillFrontmatter:
    def test_team_pattern_is_parallel_panel(self):
        assert "team_pattern: parallel-panel" in _read(SKILL)

    def test_references_shared_team_protocol(self):
        body = _read(SKILL)
        assert "@ref _shared/team-protocol.md" in body
        assert "@ref _shared/memory-protocol.md" in body

    def test_no_legacy_broker_prose(self):
        body = _read(SKILL)
        # The legacy phrase from v0.3 must not appear in the migrated SKILL body.
        assert "Subagents do NOT have MCP tool access" not in body


class TestReviewSkillWorkflow:
    def test_creates_team(self):
        assert "TeamCreate" in _read(SKILL)

    def test_spawns_three_named_teammates(self):
        body = _read(SKILL)
        for name in ("reviewer-architecture", "reviewer-correctness", "reviewer-security"):
            assert name in body, f"workflow missing reference to teammate {name}"

    def test_uses_memory_findings_submit(self):
        assert "memory_findings_submit" in _read(SKILL)

    def test_teardown_calls_TeamDelete(self):
        assert "TeamDelete" in _read(SKILL)


class TestReviewerAgents:
    @pytest.mark.parametrize("agent_file", REVIEWERS)
    def test_tools_include_findings_submit(self, agent_file):
        # tools: line in frontmatter contains memory_findings_submit
        text = _read(agent_file)
        # crude but effective: scan for the tools: line
        tools_lines = [ln for ln in text.splitlines() if ln.startswith("tools:")]
        assert tools_lines, f"{agent_file.name} missing tools: frontmatter"
        assert "memory_findings_submit" in tools_lines[0]

    @pytest.mark.parametrize("agent_file", REVIEWERS)
    def test_memory_protocol_describes_direct_mcp(self, agent_file):
        text = _read(agent_file)
        # The migrated reviewer documents direct MCP access — should reference
        # the canonical shared protocol and the findings tool.
        assert "memory_findings_submit" in text
        assert "memory_read_shared" in text or "@ref _shared/memory-protocol.md" in text


class TestFixtureCorpus:
    def test_overlap_fixture_exists(self):
        fx = REPO / "tests" / "fixtures" / "review-dedup" / "auth.py"
        assert fx.exists()
        assert "ADMIN_API_KEY" in fx.read_text(encoding="utf-8")

    def test_diff_patch_exists(self):
        patch = REPO / "tests" / "fixtures" / "review-dedup" / "diff.patch"
        assert patch.exists()
        text = patch.read_text(encoding="utf-8")
        assert "+++ " in text and "@@" in text

    def test_readme_documents_manual_check(self):
        readme = REPO / "tests" / "fixtures" / "review-dedup" / "README.md"
        text = readme.read_text(encoding="utf-8")
        assert "exactly once" in text
        assert "/review" in text
        assert "mode: report-only" in text
