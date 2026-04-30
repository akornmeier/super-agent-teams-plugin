"""Resolution of `AGENT_SUBSTRATE_BASE_DIR` to an absolute filesystem path.

Extracted from `server.py` so it can be unit-tested without triggering the
server's module-load bootstrap (which binds storage to BASE_DIR).
"""

from __future__ import annotations

from pathlib import Path


def resolve_base_dir(env_value: str | None, project_dir: str | None) -> Path:
    """Resolve the value of `AGENT_SUBSTRATE_BASE_DIR` to an absolute Path.

    Substitutes the literal token `${CLAUDE_PROJECT_DIR}` with `project_dir`
    as a workaround for claude-code #9427: in plugin-rooted `.mcp.json`,
    Claude Code does not expand `${CLAUDE_PROJECT_DIR}` inside `env` values,
    so the unexpanded literal reaches this process.

    Raises RuntimeError if the value is missing, unsubstitutable, or
    resolves to a non-absolute path.
    """
    if not env_value:
        raise RuntimeError(
            "AGENT_SUBSTRATE_BASE_DIR environment variable must be set. "
            "Configure it in .mcp.json or your environment."
        )
    if "${CLAUDE_PROJECT_DIR}" in env_value:
        if not project_dir:
            raise RuntimeError(
                "Cannot resolve ${CLAUDE_PROJECT_DIR}: PWD is unset. "
                "Set AGENT_SUBSTRATE_BASE_DIR to an absolute path explicitly."
            )
        env_value = env_value.replace("${CLAUDE_PROJECT_DIR}", project_dir)
    base_dir = Path(env_value).expanduser()
    if not base_dir.is_absolute():
        raise RuntimeError(
            f"AGENT_SUBSTRATE_BASE_DIR must be an absolute path, got {env_value!r}"
        )
    return base_dir.resolve()
