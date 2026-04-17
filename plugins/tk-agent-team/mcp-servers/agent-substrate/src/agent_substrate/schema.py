"""Schema definitions and validation for agent memory files.

The memory file format is a YAML document with four sections of expertise items:
patterns, pitfalls, decisions, and open_questions. Each item has an id, a small
set of required fields, and an optional `protected` flag that the curator skill
should respect.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# --- Identifiers ------------------------------------------------------------

# Slug pattern for agent names: lowercase, alphanumeric + hyphens, must start
# with a letter, max 64 chars. Strict by design — used in file paths.
AGENT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,63}$")

# Slug pattern for item ids — slightly more permissive (digits allowed first).
ITEM_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,127}$")

VALID_SECTIONS = ("patterns", "pitfalls", "decisions", "open_questions")
SectionName = Literal["patterns", "pitfalls", "decisions", "open_questions"]


def validate_agent_name(name: object) -> None:
    """Raise ValueError if agent_name is not a valid slug.

    Defends against path traversal: rejects slashes, dots, and any character
    not in the slug pattern.
    """
    if not isinstance(name, str):
        raise ValueError(
            f"agent_name must be a string, got {type(name).__name__}"
        )
    if not AGENT_NAME_PATTERN.match(name):
        raise ValueError(
            f"Invalid agent_name: {name!r}. Must match {AGENT_NAME_PATTERN.pattern}. "
            "Use lowercase letters, digits, and hyphens; must start with a letter; "
            "max 64 characters. No path separators allowed."
        )


def validate_section(section: object) -> None:
    """Raise ValueError if section is not one of the four allowed values."""
    if section not in VALID_SECTIONS:
        raise ValueError(
            f"Invalid section: {section!r}. Must be one of {VALID_SECTIONS}."
        )


# --- Item models ------------------------------------------------------------


class _ItemBase(BaseModel):
    """Common base for memory items. Forbids unknown fields, validates id.

    `protected` is intentionally NOT defined here so subclasses can declare
    it last and have it serialize at the end of each item for readability.
    """

    model_config = ConfigDict(extra="forbid")

    id: str

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not ITEM_ID_PATTERN.match(v):
            raise ValueError(
                f"Invalid id: {v!r}. Must match {ITEM_ID_PATTERN.pattern}"
            )
        return v


class Pattern(_ItemBase):
    """A reusable pattern the agent has learned."""

    summary: str
    evidence: str | None = None
    protected: bool = False


class Pitfall(_ItemBase):
    """Something the agent should avoid."""

    summary: str
    why: str | None = None
    protected: bool = False


class Decision(_ItemBase):
    """A standing decision the agent has made."""

    choice: str
    rationale: str | None = None
    supersedes: str | None = None
    protected: bool = False


class OpenQuestion(_ItemBase):
    """Something the agent is uncertain about."""

    question: str
    protected: bool = False


# Map section name -> Pydantic model. Used by storage to validate
# items being appended to a particular section.
SECTION_MODELS: dict[str, type[_ItemBase]] = {
    "patterns": Pattern,
    "pitfalls": Pitfall,
    "decisions": Decision,
    "open_questions": OpenQuestion,
}


# --- Top-level memory file model -------------------------------------------


class MemoryFile(BaseModel):
    """The full memory file schema."""

    model_config = ConfigDict(extra="forbid")

    version: int = 1
    updated: str  # ISO 8601 timestamp; set automatically on every write
    patterns: list[Pattern] = Field(default_factory=list)
    pitfalls: list[Pitfall] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)

    @field_validator("version")
    @classmethod
    def _validate_version(cls, v: int) -> int:
        if v != 1:
            raise ValueError(
                f"Unsupported memory file version: {v}. Expected 1."
            )
        return v

    @field_validator("updated")
    @classmethod
    def _validate_updated(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(f"Invalid ISO 8601 timestamp: {v!r}") from e
        return v


def empty_memory() -> MemoryFile:
    """Construct a fresh, empty MemoryFile with the current timestamp."""
    return MemoryFile(version=1, updated=now_iso())


def now_iso() -> str:
    """Current UTC time as an ISO 8601 string with Z suffix."""
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
