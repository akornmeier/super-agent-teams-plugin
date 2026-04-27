"""FastMCP server exposing the agent-substrate memory tools.

Tools:
  - memory_read(agent_name)
  - memory_write(agent_name, content)
  - memory_append(agent_name, section, item)
  - memory_read_shared()
  - memory_append_shared(section, item)
  - team_memory_read(team_name)
  - team_memory_append(team_name, section, item)
  - team_memory_summary(team_name)
  - memory_findings_submit(agent, findings)

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
from pydantic import ValidationError

from .schema import Finding, finding_item_to_section_dict
from .storage import HARD_LIMIT, SOFT_LIMIT, MemoryStorage
from .team_storage import TeamMemoryStorage

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
team_storage = TeamMemoryStorage(BASE_DIR)


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


# --- Team-scoped tools ------------------------------------------------------


@mcp.tool()
def team_memory_read(team_name: str) -> dict[str, Any]:
    """Read a team's scratch memory file.

    Team scratch lives at <base>/teams/<team-name>/scratch.yaml — a separate
    namespace from family memory. Used for ephemeral coordination between
    teammates within a single team's lifetime.

    Args:
        team_name: The team's slug, matching ^[a-z][a-z0-9-]{0,63}$

    Returns:
        Same shape as memory_read.
    """
    try:
        result = team_storage.read(team_name)
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
def team_memory_append(
    team_name: str,
    section: str,
    item: dict[str, Any],
) -> dict[str, Any]:
    """Append a single item to a team's scratch memory file.

    Same schema as memory_append. The file is created on first append.

    Args:
        team_name: The team's slug
        section: One of "patterns", "pitfalls", "decisions", "open_questions"
        item: The item to append (same shape as memory_append)

    Returns:
        Same shape as memory_append.
    """
    try:
        result = team_storage.append(team_name, section, item)
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
def team_memory_summary(team_name: str) -> dict[str, Any]:
    """Return per-section counts and char_count for a team's scratch memory.

    Cheap pre-flight that does not return body content. Lets a team-lead
    decide whether to append or curate before reading the full scratch.

    Args:
        team_name: The team's slug

    Returns:
        {
          "exists": bool,
          "team_name": str,
          "char_count": int,
          "soft_limit": int,
          "hard_limit": int,
          "counts": {"patterns": int, "pitfalls": int, "decisions": int, "open_questions": int},
        }
    """
    try:
        return team_storage.summary(team_name)
    except ValueError as e:
        return {
            "exists": False,
            "team_name": team_name,
            "char_count": 0,
            "soft_limit": SOFT_LIMIT,
            "hard_limit": HARD_LIMIT,
            "counts": {
                "patterns": 0,
                "pitfalls": 0,
                "decisions": 0,
                "open_questions": 0,
            },
            "error": str(e),
        }


@mcp.tool()
def memory_findings_submit(
    agent: str,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Submit a batch of structured findings.

    Each finding is validated against the `Finding` Pydantic schema and, if
    valid, appended to the corresponding agent's family memory via the same
    code path as `memory_append`. Replaces the v0.3 prose-parsed
    `## Memory findings` block, which silently dropped malformed YAML.

    Each input dict must conform to:
      {
        "agent":   str,                                      # slug
        "section": "patterns"|"pitfalls"|"decisions"|"open_questions",
        "item": {
          "kind":    "pattern"|"pitfall"|"decision"|"open_question",
          "summary": str,
          # optional: id, evidence, why, rationale, supersedes,
          #           question, protected, related
        },
      }

    The top-level `agent` argument is informational (typically the caller's
    own slug). Each finding carries its own `agent` field — that's the slug
    actually used for routing the append. This lets a team-lead submit a
    batch on behalf of multiple teammates if needed.

    Args:
        agent: Slug of the agent submitting the batch (informational).
        findings: List of finding dicts (see schema above).

    Returns:
        {
          "results": [
            {"index": 0, "ok": True, "agent": "...", "section": "...",
             "item_id": "...", "warning": str | None},
            {"index": 1, "ok": False, "error": "..."},
            ...
          ],
          "summary": {"submitted": int, "succeeded": int, "failed": int},
        }
    """
    results: list[dict[str, Any]] = []
    succeeded = 0
    failed = 0

    for index, raw in enumerate(findings):
        # Pydantic validation: agent slug, section enum, kind enum,
        # extra="forbid", and the kind/section consistency rule.
        try:
            finding = Finding.model_validate(raw)
        except ValidationError as e:
            results.append(
                {"index": index, "ok": False, "error": str(e)}
            )
            failed += 1
            continue
        except ValueError as e:
            # field_validator on `agent` raises plain ValueError; pydantic
            # wraps it but keep this branch defensive.
            results.append(
                {"index": index, "ok": False, "error": str(e)}
            )
            failed += 1
            continue

        # Translate FindingItem -> per-section item dict and append via
        # the existing MemoryStorage.append code path (same atomic-write,
        # same lock, same limit enforcement).
        section_item = finding_item_to_section_dict(finding.item)
        try:
            write = storage.append(finding.agent, finding.section, section_item)
        except ValueError as e:
            results.append(
                {"index": index, "ok": False, "error": str(e)}
            )
            failed += 1
            continue

        if not write.ok:
            results.append(
                {
                    "index": index,
                    "ok": False,
                    "agent": finding.agent,
                    "section": finding.section,
                    "needs_curation": write.needs_curation,
                    "error": write.error,
                }
            )
            failed += 1
            continue

        results.append(
            {
                "index": index,
                "ok": True,
                "agent": finding.agent,
                "section": finding.section,
                "item_id": section_item.get("id"),
                "warning": write.warning,
            }
        )
        succeeded += 1

    return {
        "results": results,
        "summary": {
            "submitted": len(findings),
            "succeeded": succeeded,
            "failed": failed,
        },
    }


# --- Entry point ------------------------------------------------------------


def main() -> None:
    """Entry point for `agent-substrate` console script and `python -m`."""
    mcp.run()


if __name__ == "__main__":
    main()
