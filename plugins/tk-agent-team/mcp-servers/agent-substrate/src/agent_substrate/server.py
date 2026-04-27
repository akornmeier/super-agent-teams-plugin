"""FastMCP server exposing the agent-substrate memory tools.

Five tools:
  - memory_read(agent_name)
  - memory_write(agent_name, content)
  - memory_append(agent_name, section, item)
  - memory_read_shared()
  - memory_append_shared(section, item)

The server requires the AGENT_SUBSTRATE_BASE_DIR environment variable to
be set to an absolute path. The launcher (typically `.mcp.json`) is
responsible for configuring it; failing fast at module load avoids
silently writing memory under whatever cwd the process happened to start
in.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .storage import HARD_LIMIT, SOFT_LIMIT, MemoryStorage

# --- Server setup -----------------------------------------------------------

_base_dir_env = os.environ.get("AGENT_SUBSTRATE_BASE_DIR")
if not _base_dir_env:
    raise RuntimeError(
        "AGENT_SUBSTRATE_BASE_DIR environment variable must be set. "
        "Configure it in .mcp.json or your environment."
    )
BASE_DIR = Path(_base_dir_env).expanduser()
if not BASE_DIR.is_absolute():
    raise RuntimeError(
        f"AGENT_SUBSTRATE_BASE_DIR must be an absolute path, got {_base_dir_env!r}"
    )
BASE_DIR = BASE_DIR.resolve()

mcp = FastMCP("agent-substrate")
storage = MemoryStorage(BASE_DIR)


# --- Tools ------------------------------------------------------------------


@mcp.tool()
def memory_read(agent_name: str) -> dict[str, Any]:
    """Read an agent's expertise memory file.

    Returns the YAML content and a parsed structure. If the agent has no
    memory file yet, returns exists=False with content=None — this is not
    an error, it just means the agent is starting fresh.

    Args:
        agent_name: The agent's slug, matching ^[a-z][a-z0-9-]{0,63}$

    Returns:
        {
          "exists": bool,
          "content": str | None,    # raw YAML
          "parsed": dict | None,    # parsed structure (None if malformed)
          "char_count": int,
          "soft_limit": int,
          "hard_limit": int,
        }
    """
    try:
        result = storage.read(agent_name)
    except ValueError as e:
        return {
            "exists": False,
            "content": None,
            "parsed": None,
            "char_count": 0,
            "soft_limit": SOFT_LIMIT,
            "hard_limit": HARD_LIMIT,
            "error": str(e),
        }
    return {
        "exists": result.exists,
        "content": result.content,
        "parsed": result.parsed,
        "char_count": result.char_count,
        "soft_limit": SOFT_LIMIT,
        "hard_limit": HARD_LIMIT,
    }


@mcp.tool()
def memory_write(agent_name: str, content: str) -> dict[str, Any]:
    """Replace an agent's entire expertise memory file.

    The content must be a valid YAML document conforming to the memory file
    schema. The 'updated' timestamp will be set automatically. Character
    count is enforced: writes over the hard limit are rejected with
    needs_curation=True.

    Do NOT retry rejected writes by truncating the content yourself. Instead,
    request curation from the orchestrator.

    Args:
        agent_name: The agent's slug
        content: The full YAML content as a string

    Returns:
        {
          "ok": bool,
          "char_count": int,
          "warning": str | None,        # set if approaching soft limit
          "needs_curation": bool,       # set if hard limit exceeded
          "error": str | None,
        }
    """
    try:
        result = storage.write(agent_name, content)
    except ValueError as e:
        return {
            "ok": False,
            "char_count": 0,
            "warning": None,
            "needs_curation": False,
            "error": str(e),
        }
    return {
        "ok": result.ok,
        "char_count": result.char_count,
        "warning": result.warning,
        "needs_curation": result.needs_curation,
        "error": result.error,
    }


@mcp.tool()
def memory_append(
    agent_name: str,
    section: str,
    item: dict[str, Any],
) -> dict[str, Any]:
    """Append a single item to a section of an agent's memory file.

    This is the preferred way to add a single fact without rewriting the
    whole file. If the file doesn't exist, it's created. The item must
    conform to the schema for the given section.

    Args:
        agent_name: The agent's slug
        section: One of "patterns", "pitfalls", "decisions", "open_questions"
        item: The item to append. Required fields depend on section:
          - patterns: id, summary; optional: evidence, protected
          - pitfalls: id, summary; optional: why, protected
          - decisions: id, choice; optional: rationale, supersedes, protected
          - open_questions: id, question; optional: protected

    Returns:
        Same shape as memory_write.
    """
    try:
        result = storage.append(agent_name, section, item)
    except ValueError as e:
        return {
            "ok": False,
            "char_count": 0,
            "warning": None,
            "needs_curation": False,
            "error": str(e),
        }
    return {
        "ok": result.ok,
        "char_count": result.char_count,
        "warning": result.warning,
        "needs_curation": result.needs_curation,
        "error": result.error,
    }


@mcp.tool()
def memory_read_shared() -> dict[str, Any]:
    """Read the project-wide shared memory file.

    All agents in the team should read this at the start of their tasks
    to load common project context, conventions, and standing decisions.

    Returns:
        Same shape as memory_read.
    """
    result = storage.read_shared()
    return {
        "exists": result.exists,
        "content": result.content,
        "parsed": result.parsed,
        "char_count": result.char_count,
        "soft_limit": SOFT_LIMIT,
        "hard_limit": HARD_LIMIT,
    }


@mcp.tool()
def memory_append_shared(
    section: str,
    item: dict[str, Any],
) -> dict[str, Any]:
    """Append a single item to the project-wide shared memory file.

    Use sparingly — the shared file is for facts every agent needs. Most
    learning belongs in the agent's individual memory file.

    Args:
        section: One of "patterns", "pitfalls", "decisions", "open_questions"
        item: The item to append (same schema as memory_append)

    Returns:
        Same shape as memory_write.
    """
    try:
        result = storage.append_shared(section, item)
    except ValueError as e:
        return {
            "ok": False,
            "char_count": 0,
            "warning": None,
            "needs_curation": False,
            "error": str(e),
        }
    return {
        "ok": result.ok,
        "char_count": result.char_count,
        "warning": result.warning,
        "needs_curation": result.needs_curation,
        "error": result.error,
    }


# --- Entry point ------------------------------------------------------------


def main() -> None:
    """Entry point for `agent-substrate` console script and `python -m`."""
    mcp.run()


if __name__ == "__main__":
    main()
