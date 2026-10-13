"""Small deterministic helpers shared by initializer commands."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import shutil
from typing import Any


@dataclass(frozen=True)
class PathPlan:
    """One planned root-relative path and its preflight disposition."""

    path: str
    kind: str
    disposition: str
    reason: str


@dataclass(frozen=True)
class ApplyResult:
    """Outcome of a plan application attempt."""

    outcome: str
    written_paths: tuple[str, ...]
    message: str
    recovery_path: str | None = None


def validate_iso_date(value: str) -> str:
    """Validate the fixed date shape used in records and deterministic tests."""
    import datetime as datetime_module

    try:
        datetime_module.date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("date must use YYYY-MM-DD") from error
    return value


def plan_digest(payload: dict[str, Any]) -> str:
    """Create a stable short identifier for an exact, recomputed plan."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(canonical.encode("utf-8")).hexdigest()[:16]


def copy_file_exclusive(source: Path, destination: Path) -> None:
    """Copy a regular file only when the destination is absent."""
    with source.open("rb") as source_handle, destination.open("xb") as target_handle:
        shutil.copyfileobj(source_handle, target_handle)
    shutil.copystat(source, destination, follow_symlinks=False)


def copy_tree_new(source: Path, destination: Path) -> None:
    """Copy a directory only when its destination is absent."""
    shutil.copytree(source, destination, symlinks=False, copy_function=shutil.copy2)


def same_file(left: Path, right: Path) -> bool:
    return left.is_file() and right.is_file() and left.read_bytes() == right.read_bytes()


def same_tree(left: Path, right: Path) -> bool:
    """Return true only for byte-identical regular-file directory trees."""
    if not left.is_dir() or not right.is_dir():
        return False
    left_paths = sorted(path.relative_to(left) for path in left.rglob("*") if path.is_file())
    right_paths = sorted(path.relative_to(right) for path in right.rglob("*") if path.is_file())
    if left_paths != right_paths:
        return False
    return all(same_file(left / relative, right / relative) for relative in left_paths)


def relative_display(path: Path) -> str:
    """Use POSIX-like paths in portable reports."""
    return path.as_posix()
