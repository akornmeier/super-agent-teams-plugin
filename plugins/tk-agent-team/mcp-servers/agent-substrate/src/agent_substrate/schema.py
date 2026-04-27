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

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    related: list[str] | None = None
    lens: str | None = None
    protected: bool = False


class Pitfall(_ItemBase):
    """Something the agent should avoid."""

    summary: str
    why: str | None = None
    related: list[str] | None = None
    lens: str | None = None
    protected: bool = False


class Decision(_ItemBase):
    """A standing decision the agent has made."""

    choice: str
    rationale: str | None = None
    supersedes: str | None = None
    related: list[str] | None = None
    lens: str | None = None
    protected: bool = False


class OpenQuestion(_ItemBase):
    """Something the agent is uncertain about."""

    question: str
    related: list[str] | None = None
    lens: str | None = None
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


# --- Findings wire format ---------------------------------------------------

# Mapping from FindingItem.kind to the section it must be filed under.
# The substrate enforces that section and kind agree (see Finding._validate_*).
KIND_TO_SECTION: dict[str, str] = {
    "pattern": "patterns",
    "pitfall": "pitfalls",
    "decision": "decisions",
    "open_question": "open_questions",
}


class FindingItem(BaseModel):
    """Inner payload of a Finding submitted by a teammate.

    Universal handle is `summary` — for `decision` kinds it maps to `choice`
    on the existing `Decision` model, and for `open_question` kinds the body
    can be supplied via `question` (with `summary` as a fallback). The
    substrate translation lives in `finding_item_to_section_dict`.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["pattern", "pitfall", "decision", "open_question"]
    summary: str
    id: str | None = None
    evidence: str | None = None
    why: str | None = None
    rationale: str | None = None
    supersedes: str | None = None
    question: str | None = None
    protected: bool = False
    related: list[str] | None = None
    lens: str | None = None


class Finding(BaseModel):
    """Wire format for `memory_findings_submit`.

    See `skills/_shared/findings-schema.md` for the contract document. The
    `agent` slug is validated against the same regex as `validate_agent_name`
    so findings cannot escape the per-agent memory namespace.
    """

    model_config = ConfigDict(extra="forbid")

    agent: str
    section: SectionName
    item: FindingItem

    @field_validator("agent")
    @classmethod
    def _validate_agent_slug(cls, v: str) -> str:
        validate_agent_name(v)  # raises ValueError on bad slug
        return v

    @model_validator(mode="after")
    def _validate_kind_section_consistency(self) -> "Finding":
        # Vocabulary consistency rule from findings-schema.md: the
        # parent section and the inner kind must express the same
        # vocabulary in two places, and they MUST agree.
        expected = KIND_TO_SECTION[self.item.kind]
        if expected != self.section:
            raise ValueError(
                f"Vocabulary mismatch: section={self.section!r} but "
                f"item.kind={self.item.kind!r}; kind={self.item.kind!r} "
                f"requires section={expected!r}"
            )
        return self


# --- Helpers for translating FindingItem -> per-section item dict -----------

# Slug pattern reused from ITEM_ID_PATTERN above. Used to derive a
# deterministic id from a summary when the caller did not provide one.
_ID_SLUG_NONALNUM = re.compile(r"[^a-z0-9]+")


def _slugify_id(text: str, max_len: int = 32) -> str:
    """Best-effort deterministic id from a free-form summary string.

    Lowercases, replaces non-alnum runs with hyphens, strips leading/trailing
    hyphens, and trims to `max_len`. Falls back to "item" if the input has no
    alphanumeric characters at all (matches `ITEM_ID_PATTERN` requirement that
    ids start with an alphanumeric).
    """
    lowered = text.lower()
    slugged = _ID_SLUG_NONALNUM.sub("-", lowered).strip("-")
    if not slugged:
        return "item"
    slugged = slugged[:max_len].rstrip("-")
    if not slugged:
        return "item"
    # If after trimming we ended up starting with a hyphen-derived nothing,
    # ensure first char is alnum (ITEM_ID_PATTERN requires it).
    if not slugged[0].isalnum():
        slugged = "item-" + slugged
        slugged = slugged[:max_len].rstrip("-")
    return slugged


def finding_item_to_section_dict(item: FindingItem) -> dict:
    """Convert a FindingItem to the dict shape expected by SECTION_MODELS[section].

    The per-section item models (Pattern, Pitfall, Decision, OpenQuestion) do
    not carry a `kind` field — that's redundant once the item is filed under
    its section. This helper drops `kind`, picks only the optional fields
    that belong to the target section, and remaps the universal `summary`
    handle to the section-specific field name (`choice` for decisions,
    `question` for open questions).

    A deterministic id is generated from the summary if `item.id` is None.
    """
    item_id = item.id or _slugify_id(item.summary)

    if item.kind == "pattern":
        # Pattern: id, summary, evidence, related, lens, protected
        return {
            "id": item_id,
            "summary": item.summary,
            "evidence": item.evidence,
            "related": item.related,
            "lens": item.lens,
            "protected": item.protected,
        }
    if item.kind == "pitfall":
        # Pitfall: id, summary, why, related, lens, protected
        return {
            "id": item_id,
            "summary": item.summary,
            "why": item.why,
            "related": item.related,
            "lens": item.lens,
            "protected": item.protected,
        }
    if item.kind == "decision":
        # Decision: id, choice (<- summary), rationale, supersedes, related, lens, protected
        return {
            "id": item_id,
            "choice": item.summary,
            "rationale": item.rationale,
            "supersedes": item.supersedes,
            "related": item.related,
            "lens": item.lens,
            "protected": item.protected,
        }
    if item.kind == "open_question":
        # OpenQuestion: id, question (<- question or summary fallback), related, lens, protected
        return {
            "id": item_id,
            "question": item.question or item.summary,
            "related": item.related,
            "lens": item.lens,
            "protected": item.protected,
        }
    # Should be unreachable thanks to the Literal on FindingItem.kind.
    raise ValueError(f"Unknown FindingItem.kind: {item.kind!r}")
