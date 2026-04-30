"""Tests for `resolve_base_dir` — the AGENT_SUBSTRATE_BASE_DIR resolver.

Pins the workaround for claude-code #9427: when `${CLAUDE_PROJECT_DIR}`
appears in `.mcp.json` env values for plugin-rooted manifests, Claude Code
passes it through unexpanded, so we substitute it ourselves at startup.

Imports `_paths` directly so these tests do not trigger the server's
module-load bootstrap.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_substrate._paths import resolve_base_dir


class TestAbsolutePathPassthrough:
    def test_absolute_path_returned_as_path(self, tmp_path: Path):
        result = resolve_base_dir(str(tmp_path), project_dir=None)
        assert result == tmp_path.resolve()

    def test_tilde_is_expanded(self):
        result = resolve_base_dir("~/.agent-memory-test", project_dir=None)
        assert result.is_absolute()
        assert str(result).startswith(str(Path.home()))


class TestProjectDirSubstitution:
    def test_literal_token_replaced_with_project_dir(self, tmp_path: Path):
        result = resolve_base_dir(
            "${CLAUDE_PROJECT_DIR}/.agent-memory",
            project_dir=str(tmp_path),
        )
        assert result == (tmp_path / ".agent-memory").resolve()

    def test_token_in_middle_of_path_replaced(self, tmp_path: Path):
        result = resolve_base_dir(
            "${CLAUDE_PROJECT_DIR}/sub/dir",
            project_dir=str(tmp_path),
        )
        assert result == (tmp_path / "sub" / "dir").resolve()

    def test_no_token_no_substitution_attempted(self, tmp_path: Path):
        # project_dir is irrelevant when token is absent
        result = resolve_base_dir(str(tmp_path), project_dir="/should/not/matter")
        assert result == tmp_path.resolve()


class TestFailureModes:
    def test_empty_value_raises(self):
        with pytest.raises(RuntimeError, match="must be set"):
            resolve_base_dir("", project_dir="/some/dir")

    def test_none_value_raises(self):
        with pytest.raises(RuntimeError, match="must be set"):
            resolve_base_dir(None, project_dir="/some/dir")

    def test_token_present_but_no_project_dir_raises(self):
        with pytest.raises(RuntimeError, match="PWD is unset"):
            resolve_base_dir(
                "${CLAUDE_PROJECT_DIR}/.agent-memory",
                project_dir=None,
            )

    def test_token_present_but_empty_project_dir_raises(self):
        with pytest.raises(RuntimeError, match="PWD is unset"):
            resolve_base_dir(
                "${CLAUDE_PROJECT_DIR}/.agent-memory",
                project_dir="",
            )

    def test_relative_literal_path_raises(self):
        with pytest.raises(RuntimeError, match="must be an absolute path"):
            resolve_base_dir("relative/path", project_dir=None)

    def test_substitution_with_relative_project_dir_raises(self):
        with pytest.raises(RuntimeError, match="must be an absolute path"):
            resolve_base_dir(
                "${CLAUDE_PROJECT_DIR}/.agent-memory",
                project_dir="relative/dir",
            )
