"""File storage for agent memory with locking, atomic writes, and size limits.

Each memory file lives at `<base_dir>/<agent_name>.yaml`. Writes are atomic
(temp file + fsync + rename) and protected by an exclusive file lock so that
concurrent teammate processes cannot corrupt the file.

The store is deliberately dumb: it validates schema and enforces limits, but
it does not curate. Curation lives in the curator skill that the orchestrator
dispatches separately.
"""

from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import portalocker
import yaml

from .schema import (
    SECTION_MODELS,
    MemoryFile,
    empty_memory,
    now_iso,
    validate_agent_name,
    validate_section,
)

# Character limits, measured in unicode code points (Python str length).
# Roughly correlates to tokens at ~3-4 chars/token for english + YAML.
SOFT_LIMIT = 8000
HARD_LIMIT = 10000

SHARED_FILENAME = "_shared.yaml"
LOCK_TIMEOUT_SECONDS = 10


@dataclass
class WriteResult:
    """Result of a write or append operation."""

    ok: bool
    char_count: int
    warning: str | None = None
    needs_curation: bool = False
    error: str | None = None


@dataclass
class ReadResult:
    """Result of a read operation."""

    exists: bool
    content: str | None
    parsed: dict[str, Any] | None
    char_count: int


class MemoryStorage:
    """Manages YAML memory files with locking and character-count enforcement."""

    def __init__(self, base_dir: Path | str) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    # --- Path resolution ---------------------------------------------------

    def _path_for(self, agent_name: str) -> Path:
        """Resolve an agent's memory file path. Validates the slug first."""
        validate_agent_name(agent_name)
        path = self.base_dir / f"{agent_name}.yaml"
        # Defense in depth: validate_agent_name already rejects slashes, but
        # double-check the parent matches base_dir.
        if path.parent != self.base_dir:
            raise ValueError(f"Path traversal detected for {agent_name!r}")
        return path

    def _shared_path(self) -> Path:
        return self.base_dir / SHARED_FILENAME

    # --- Locking and atomic write -----------------------------------------

    @contextmanager
    def _locked(self, path: Path) -> Iterator[None]:
        """Acquire an exclusive lock on a sidecar lock file."""
        lock_path = path.with_suffix(path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with portalocker.Lock(
            str(lock_path),
            mode="a",
            timeout=LOCK_TIMEOUT_SECONDS,
        ):
            yield

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        """Write content to path atomically via temp file + fsync + rename."""
        path.parent.mkdir(parents=True, exist_ok=True)
        # Temp file in the same directory so os.replace is atomic on the
        # same filesystem.
        fd, tmp_path = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    # --- Read -------------------------------------------------------------

    def read(self, agent_name: str) -> ReadResult:
        """Read an agent's memory file. Returns exists=False if missing."""
        return self._read_path(self._path_for(agent_name))

    def read_shared(self) -> ReadResult:
        """Read the project-wide shared memory file."""
        return self._read_path(self._shared_path())

    def _read_path(self, path: Path) -> ReadResult:
        if not path.exists():
            return ReadResult(
                exists=False, content=None, parsed=None, char_count=0
            )
        with self._locked(path):
            content = path.read_text(encoding="utf-8")
        # Tolerate malformed YAML on read so the agent can still see the raw
        # content and decide what to do.
        try:
            parsed = yaml.safe_load(content)
        except yaml.YAMLError:
            parsed = None
        if not isinstance(parsed, dict):
            parsed = None
        return ReadResult(
            exists=True,
            content=content,
            parsed=parsed,
            char_count=len(content),
        )

    # --- Write ------------------------------------------------------------

    def write(self, agent_name: str, content: str) -> WriteResult:
        """Validate and replace an entire memory file.

        - Parses YAML
        - Validates against MemoryFile schema
        - Sets `updated` to current timestamp
        - Re-serializes to canonical form
        - Enforces character limit
        - Atomic write under lock
        """
        path = self._path_for(agent_name)
        return self._write_to_path(path, content)

    def _write_to_path(self, path: Path, content: str) -> WriteResult:
        # Parse and schema-validate
        try:
            parsed = yaml.safe_load(content)
        except yaml.YAMLError as e:
            return WriteResult(
                ok=False, char_count=len(content), error=f"Invalid YAML: {e}"
            )
        if not isinstance(parsed, dict):
            return WriteResult(
                ok=False,
                char_count=len(content),
                error="Content must parse as a YAML mapping.",
            )

        # Always update the timestamp to now
        parsed["updated"] = now_iso()

        try:
            memory = MemoryFile.model_validate(parsed)
        except Exception as e:
            return WriteResult(
                ok=False,
                char_count=len(content),
                error=f"Schema validation failed: {e}",
            )

        # Re-serialize from validated model so we store a canonical form
        canonical = self._serialize(memory)
        char_count = len(canonical)

        # Hard limit: reject and signal curation
        if char_count > HARD_LIMIT:
            return WriteResult(
                ok=False,
                char_count=char_count,
                needs_curation=True,
                error=(
                    f"Memory exceeds hard limit ({char_count} > {HARD_LIMIT} chars). "
                    "Request curation from the orchestrator. Do not retry by "
                    "truncating yourself."
                ),
            )

        # Write under lock
        with self._locked(path):
            self._atomic_write(path, canonical)

        # Soft limit: succeed but warn
        if char_count > SOFT_LIMIT:
            return WriteResult(
                ok=True,
                char_count=char_count,
                warning=(
                    f"Memory is approaching the hard limit "
                    f"({char_count}/{HARD_LIMIT} chars). "
                    "Consider requesting curation from the orchestrator."
                ),
            )
        return WriteResult(ok=True, char_count=char_count)

    # --- Append -----------------------------------------------------------

    def append(
        self,
        agent_name: str,
        section: str,
        item: dict[str, Any],
    ) -> WriteResult:
        """Append a single item to a section of an agent's memory file."""
        return self._append_to_path(self._path_for(agent_name), section, item)

    def append_shared(
        self,
        section: str,
        item: dict[str, Any],
    ) -> WriteResult:
        """Append a single item to a section of the shared memory file."""
        return self._append_to_path(self._shared_path(), section, item)

    def _append_to_path(
        self,
        path: Path,
        section: str,
        item: dict[str, Any],
    ) -> WriteResult:
        validate_section(section)
        if not isinstance(item, dict):
            return WriteResult(
                ok=False,
                char_count=0,
                error=f"item must be a dict, got {type(item).__name__}",
            )

        with self._locked(path):
            # Load existing or start fresh
            if path.exists():
                try:
                    existing_content = path.read_text(encoding="utf-8")
                    existing_parsed = yaml.safe_load(existing_content) or {}
                except yaml.YAMLError as e:
                    return WriteResult(
                        ok=False,
                        char_count=0,
                        error=f"Existing memory file has invalid YAML: {e}",
                    )
                if not isinstance(existing_parsed, dict):
                    return WriteResult(
                        ok=False,
                        char_count=0,
                        error="Existing memory file is not a YAML mapping.",
                    )
                try:
                    memory = MemoryFile.model_validate(existing_parsed)
                except Exception as e:
                    return WriteResult(
                        ok=False,
                        char_count=0,
                        error=(
                            f"Existing memory file fails schema validation: {e}. "
                            "Use memory_write to repair."
                        ),
                    )
            else:
                memory = empty_memory()

            # Validate the new item against its section's model
            ItemModel = SECTION_MODELS[section]
            try:
                new_item = ItemModel.model_validate(item)
            except Exception as e:
                return WriteResult(
                    ok=False,
                    char_count=0,
                    error=f"Item failed schema validation for {section}: {e}",
                )

            # Append and update timestamp
            getattr(memory, section).append(new_item)
            memory.updated = now_iso()

            # Serialize, check size, write atomically
            canonical = self._serialize(memory)
            char_count = len(canonical)

            if char_count > HARD_LIMIT:
                return WriteResult(
                    ok=False,
                    char_count=char_count,
                    needs_curation=True,
                    error=(
                        f"Append would exceed hard limit "
                        f"({char_count} > {HARD_LIMIT} chars). Request curation."
                    ),
                )

            self._atomic_write(path, canonical)

            if char_count > SOFT_LIMIT:
                return WriteResult(
                    ok=True,
                    char_count=char_count,
                    warning=(
                        f"Memory is approaching the hard limit "
                        f"({char_count}/{HARD_LIMIT} chars). "
                        "Consider requesting curation from the orchestrator."
                    ),
                )
            return WriteResult(ok=True, char_count=char_count)

    # --- Serialization ----------------------------------------------------

    @staticmethod
    def _serialize(memory: MemoryFile) -> str:
        """Serialize a MemoryFile to canonical YAML.

        - Preserves the field order defined in the model
        - Uses block style (no flow style)
        - Wide line width to keep items on single lines for greppability
        - Preserves None as YAML null
        """
        data = memory.model_dump(exclude_none=False)
        return yaml.safe_dump(
            data,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
            width=1000,
        )
