"""Team-scoped scratch memory storage.

Mirrors `MemoryStorage` but rooted at `<base_dir>/teams/<team-name>/scratch.yaml`
instead of `<base_dir>/<agent_name>.yaml`. Same atomic-write + lock-file
semantics, same Pydantic validation, same character-count limits.

Per-team scratch memory is a *new namespace alongside* family memory, not a
replacement. Lifecycle: created when `TeamCreate` runs, deleted when
`TeamDelete` runs. Purpose: ephemeral team coordination that today has nowhere
to live except the parent's transient context.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

import yaml

from .schema import (
    AGENT_NAME_PATTERN,
    SECTION_MODELS,
    MemoryFile,
    empty_memory,
    now_iso,
    validate_section,
)
from .storage import (
    HARD_LIMIT,
    SOFT_LIMIT,
    MemoryStorage,
    ReadResult,
    WriteResult,
)

# Team-name slug uses the same regex as agent name.
TEAM_NAME_PATTERN = AGENT_NAME_PATTERN
TEAMS_DIRNAME = "teams"
SCRATCH_FILENAME = "scratch.yaml"


def validate_team_name(name: object) -> None:
    """Raise ValueError if team_name is not a valid slug.

    Same rules as `validate_agent_name`: lowercase letters, digits, hyphens;
    must start with a letter; max 64 chars. Defends against path traversal.
    """
    if not isinstance(name, str):
        raise ValueError(
            f"team_name must be a string, got {type(name).__name__}"
        )
    if not TEAM_NAME_PATTERN.match(name):
        raise ValueError(
            f"Invalid team_name: {name!r}. Must match {TEAM_NAME_PATTERN.pattern}. "
            "Use lowercase letters, digits, and hyphens; must start with a letter; "
            "max 64 characters. No path separators allowed."
        )


class TeamMemoryStorage(MemoryStorage):
    """Team-scoped variant of MemoryStorage rooted at <base>/teams/<team-name>/.

    Inherits lock-file / atomic-write / serialization machinery from
    `MemoryStorage` and overrides only path resolution. Each team has a
    single `scratch.yaml` under its own directory, validated against the
    same `MemoryFile` schema as family memory.
    """

    def __init__(self, base_dir: Path | str) -> None:
        # base_dir is the substrate's BASE_DIR (parent of `teams/`).
        # Resolve it the same way MemoryStorage does, then ensure the
        # `teams/` subdir exists.
        self.base_dir = Path(base_dir).resolve()
        self.teams_root = self.base_dir / TEAMS_DIRNAME
        self.teams_root.mkdir(parents=True, exist_ok=True)

    # --- Path resolution --------------------------------------------------

    def _team_dir(self, team_name: str) -> Path:
        validate_team_name(team_name)
        path = (self.teams_root / team_name).resolve()
        # Defense in depth — validate_team_name already rejects slashes, but
        # double-check the parent matches teams_root.
        if path.parent != self.teams_root:
            raise ValueError(f"Path traversal detected for {team_name!r}")
        return path

    def _scratch_path(self, team_name: str) -> Path:
        return self._team_dir(team_name) / SCRATCH_FILENAME

    # --- Read -------------------------------------------------------------

    def read(self, team_name: str) -> ReadResult:  # type: ignore[override]
        """Read a team's scratch memory file. Returns exists=False if missing."""
        return self._read_path(self._scratch_path(team_name))

    # --- Append -----------------------------------------------------------

    def append(  # type: ignore[override]
        self,
        team_name: str,
        section: str,
        item: dict[str, Any],
    ) -> WriteResult:
        """Append a single item to a section of a team's scratch memory."""
        return self._append_to_path(self._scratch_path(team_name), section, item)

    # --- Summary ----------------------------------------------------------

    def summary(self, team_name: str) -> dict[str, Any]:
        """Return per-section counts and char_count for a team's scratch.

        Cheap pre-flight for team-leads to check team scratch state before
        deciding whether to append. Does not return body content.
        """
        path = self._scratch_path(team_name)
        if not path.exists():
            return {
                "exists": False,
                "team_name": team_name,
                "char_count": 0,
                "soft_limit": SOFT_LIMIT,
                "hard_limit": HARD_LIMIT,
                "counts": {section: 0 for section in SECTION_MODELS},
            }
        with self._locked(path):
            content = path.read_text(encoding="utf-8")
        try:
            parsed = yaml.safe_load(content)
        except yaml.YAMLError:
            parsed = None
        counts = {section: 0 for section in SECTION_MODELS}
        if isinstance(parsed, dict):
            for section in SECTION_MODELS:
                value = parsed.get(section)
                if isinstance(value, list):
                    counts[section] = len(value)
        return {
            "exists": True,
            "team_name": team_name,
            "char_count": len(content),
            "soft_limit": SOFT_LIMIT,
            "hard_limit": HARD_LIMIT,
            "counts": counts,
        }

    # --- Delete -----------------------------------------------------------

    def delete(self, team_name: str) -> bool:
        """Remove `<base>/teams/<team-name>/` entirely.

        Returns True if the directory existed and was removed, False if it
        was already absent. Validated by `validate_team_name` to prevent
        accidental traversal-driven destruction.
        """
        team_dir = self._team_dir(team_name)
        if not team_dir.exists():
            return False
        shutil.rmtree(team_dir)
        return True
