"""Smoke tests pinning the Path A architectural fix (PR-resync target).

Every team-pattern slash command MUST dispatch to the `orchestrator` agent
rather than calling `Skill` directly — otherwise deferred tools (`TeamCreate`,
`TaskCreate`, `SendMessage`, `Agent`) never load, the team flow silently
collapses to plain `Agent` calls, no findings are submitted, and `.agent-memory/`
stays empty (see commit history for the pono debug session that surfaced this).

These tests are intentionally string-level: command and agent files are markdown
prompts, not code, so structural regressions are caught by checking the
prescribed prompt text.
"""

from __future__ import annotations

from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
COMMANDS_DIR = PLUGIN_ROOT / "commands"
ORCHESTRATOR = PLUGIN_ROOT / "agents" / "orchestrator.md"

# Every slash command file the user can invoke as `/tk-agent-team:<name>`.
EXPECTED_COMMANDS = {
    "ideate.md",
    "brainstorm.md",
    "plan.md",
    "work.md",
    "review.md",
    "test.md",
    "ship.md",
}


@pytest.fixture(scope="module")
def command_files() -> dict[str, str]:
    found = {p.name for p in COMMANDS_DIR.glob("*.md")}
    missing = EXPECTED_COMMANDS - found
    assert not missing, f"Missing expected command files: {missing}"
    return {p.name: p.read_text(encoding="utf-8") for p in COMMANDS_DIR.glob("*.md")}


class TestCommandsDispatchToOrchestrator:
    """Each command's primary dispatch step must spawn the orchestrator."""

    @pytest.mark.parametrize("cmd", sorted(EXPECTED_COMMANDS))
    def test_command_dispatches_via_agent_to_orchestrator(
        self, cmd: str, command_files: dict[str, str]
    ):
        body = command_files[cmd]
        assert 'subagent_type: "orchestrator"' in body, (
            f"{cmd} must dispatch to the orchestrator agent. "
            f"Calling Skill directly bypasses deferred-tool loading and "
            f"collapses team flows. See agents/orchestrator.md Step 0."
        )

    @pytest.mark.parametrize("cmd", sorted(EXPECTED_COMMANDS))
    def test_command_does_not_invoke_skill_directly_in_dispatch_step(
        self, cmd: str, command_files: dict[str, str]
    ):
        # Allow the phrase in `## See also` references and skill-path mentions,
        # but the primary numbered Steps section must not say "via the Skill tool".
        steps_block = body_section(command_files[cmd], "## Steps")
        assert "Skill tool" not in steps_block, (
            f"{cmd} Steps section still references the Skill tool. "
            f"Direct Skill invocation was the bug fixed by Path A — "
            f"the orchestrator now owns Skill dispatch."
        )


class TestOrchestratorReadyForDispatch:
    """The orchestrator agent must declare the tools its workflow now requires."""

    @pytest.fixture(scope="class")
    def orchestrator_text(self) -> str:
        return ORCHESTRATOR.read_text(encoding="utf-8")

    @pytest.mark.parametrize("tool", ["Skill", "Agent", "ToolSearch", "TeamCreate"])
    def test_orchestrator_declares_required_tool(
        self, tool: str, orchestrator_text: str
    ):
        tools_line = next(
            (ln for ln in orchestrator_text.splitlines() if ln.startswith("tools:")),
            "",
        )
        assert tool in tools_line, (
            f"orchestrator.md tools allowlist missing {tool!r}. "
            f"Required by the workflow's dispatch path."
        )

    def test_step_zero_loads_deferred_tool_schemas(self, orchestrator_text: str):
        assert "ToolSearch" in orchestrator_text and "deferred" in orchestrator_text, (
            "orchestrator.md must instruct ToolSearch loading of deferred tools "
            "(TeamCreate etc.) before any tool use, or team_pattern dispatches "
            "will raise InputValidationError on the first TeamCreate call."
        )


def body_section(text: str, heading: str) -> str:
    """Return the text between `heading` and the next `## ` heading (exclusive)."""
    lines = text.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip() == heading)
    except StopIteration:
        return ""
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    return "\n".join(lines[start + 1:end])
