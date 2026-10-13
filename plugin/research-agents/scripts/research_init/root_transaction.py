"""Backed-up, reversible writes for one root initialization."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Callable

from .common import ApplyResult


@dataclass(frozen=True)
class RootWrite:
    path: str
    content: bytes
    mode: int
    previous: bytes | None = None


def safe_path(path: Path) -> None:
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise OSError(f"symlink path is not supported: {path}")


def path_state(path: Path, *, tree: bool = False, content: bool = True) -> dict:
    if path.is_symlink():
        return {"kind": "symlink", "link": os.readlink(path)}
    if any(parent.is_symlink() for parent in path.parents):
        return {"kind": "symlink-parent"}
    if not path.exists():
        return {"kind": "absent"}
    mode = path.stat().st_mode & 0o777
    if path.is_file():
        state = {"kind": "file", "mode": mode}
        if content:
            state["hash"] = sha256(path.read_bytes()).hexdigest()
        return state
    if path.is_dir():
        children = sorted(path.iterdir(), key=lambda item: item.name)
        return {"kind": "directory", "mode": mode,
                "children": {child.name: path_state(child, tree=True) for child in children}
                if tree else [child.name for child in children]}
    return {"kind": "special", "mode": mode}


def atomic_write(path: Path, content: bytes, mode: int) -> None:
    staged = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            staged = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(staged, mode)
        os.replace(staged, path)
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)


def apply_writes(target: Path, writes: tuple[RootWrite, ...], directories: tuple[str, ...],
                 *, plan_id: str, check_state: Callable[[], None],
                 verify_preserved: Callable[[], None], verify_restored: Callable[[], None]) -> ApplyResult:
    if not writes and not directories:
        return ApplyResult("no-op", (), "current project already has the planned structure; zero writes")
    lock = Path(tempfile.gettempdir()) / ("research-init-" + sha256(str(target).encode()).hexdigest() + ".lock")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return ApplyResult("conflict", (), "another root initialization holds the target lock; zero writes")
    os.close(descriptor)
    backup = None
    created_directories: list[Path] = []
    applied: list[RootWrite] = []
    file_stats: dict[str, os.stat_result] = {}
    parent_stats: dict[Path, os.stat_result] = {}
    record = {"target": str(target), "plan_id": plan_id, "files": [],
              "created_directories": [], "applied_files": []}

    def save_record() -> None:
        atomic_write(backup / "recovery.json", json.dumps(record, indent=2).encode(), 0o600)

    def ensure_directory(path: Path) -> None:
        safe_path(path)
        missing = []
        while not path.exists():
            missing.append(path)
            path = path.parent
        if not path.is_dir() or path.is_symlink():
            raise OSError(f"parent is not a regular directory: {path}")
        for directory in reversed(missing):
            directory.mkdir()
            created_directories.append(directory)
            record["created_directories"].append(str(directory))
            save_record()

    try:
        check_state()
        backup = Path(tempfile.mkdtemp(prefix="research-init-backup-"))
        for write in writes:
            path = target / write.path
            if write.previous is not None:
                file_stats[write.path] = path.stat()
                original = backup / "previous" / write.path
                original.parent.mkdir(parents=True, exist_ok=True)
                original.write_bytes(write.previous)
            staged = backup / "staged" / write.path
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(write.content)
            record["files"].append({"path": write.path, "mode": write.mode,
                                    "before_hash": sha256(write.previous).hexdigest() if write.previous is not None else None,
                                    "after_hash": sha256(write.content).hexdigest(),
                                    "before_mode": file_stats[write.path].st_mode & 0o777 if write.previous is not None else None,
                                    "before_atime_ns": file_stats[write.path].st_atime_ns if write.previous is not None else None,
                                    "before_mtime_ns": file_stats[write.path].st_mtime_ns if write.previous is not None else None})
        for value in (*directories, *(write.path for write in writes)):
            parent = (target / value).parent
            while not parent.exists():
                parent = parent.parent
            parent_stats.setdefault(parent, parent.stat())
        record["parent_times"] = {str(path): [stat.st_atime_ns, stat.st_mtime_ns]
                                  for path, stat in parent_stats.items()}
        save_record()
        check_state()
        for value in directories:
            path = target / value
            if path.exists() and path not in created_directories:
                raise OSError(f"planned directory appeared before creation: {value}")
            ensure_directory(path)
        for write in writes:
            path = target / write.path
            ensure_directory(path.parent)
            safe_path(path)
            if write.previous is None:
                with path.open("xb") as stream:
                    applied.append(write)
                    record["applied_files"].append(write.path)
                    save_record()
                    stream.write(write.content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(path, write.mode)
            else:
                if path.is_symlink() or path.read_bytes() != write.previous:
                    raise OSError(f"record changed before replacement: {write.path}")
                applied.append(write)
                record["applied_files"].append(write.path)
                save_record()
                atomic_write(path, write.content, write.mode)
        for write in writes:
            path = target / write.path
            safe_path(path)
            if path.is_symlink() or path.read_bytes() != write.content:
                raise OSError(f"post-apply verification failed: {write.path}")
        verify_preserved()
    except (Exception, KeyboardInterrupt) as error:
        recovery_errors = []
        for write in reversed(applied):
            path = target / write.path
            try:
                safe_path(path)
                actual = path.read_bytes()
                if write.previous is None:
                    if not write.content.startswith(actual):
                        raise OSError("created content was changed by another writer")
                    path.unlink()
                else:
                    if actual == write.previous:
                        continue
                    if actual != write.content:
                        raise OSError("updated content was changed by another writer")
                    original = (backup / "previous" / write.path).read_bytes()
                    if original != write.previous:
                        raise OSError("backup integrity mismatch")
                    atomic_write(path, original, file_stats[write.path].st_mode & 0o777)
                    os.utime(path, ns=(file_stats[write.path].st_atime_ns, file_stats[write.path].st_mtime_ns))
            except OSError as recovery_error:
                recovery_errors.append(f"{path}: {recovery_error}")
        for directory in reversed(created_directories):
            try:
                safe_path(directory)
                directory.rmdir()
            except OSError as recovery_error:
                recovery_errors.append(f"{directory}: {recovery_error}")
        for path, stat in (parent_stats.items() if applied or created_directories else ()):
            try:
                safe_path(path)
                os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            except OSError as recovery_error:
                recovery_errors.append(f"{path}: {recovery_error}")
        if applied or created_directories:
            try:
                verify_restored()
            except OSError as recovery_error:
                recovery_errors.append(str(recovery_error))
        if recovery_errors:
            record["failure"] = str(error)
            record["recovery_errors"] = recovery_errors
            try:
                save_record()
            except OSError:
                pass
            result = ApplyResult("recovery-required", tuple(write.path for write in applied),
                                 f"apply failed: {error}; automatic recovery incomplete: " + "; ".join(recovery_errors),
                                 str(backup))
        else:
            retained = _remove_backup(backup)
            outcome = "conflict" if not applied and not created_directories and isinstance(error, ValueError) else "failed-rolled-back"
            result = ApplyResult(outcome, (), f"apply failed: {error}; this invocation's writes were rolled back", retained)
    else:
        retained = _remove_backup(backup)
        result = ApplyResult("applied", tuple(write.path for write in writes) + directories,
                             "planned writes verified; recovery backup retained for manual cleanup" if retained else
                             "planned writes verified; recovery backup removed after successful apply", retained)
    finally:
        try:
            lock.unlink(missing_ok=True)
        except OSError as error:
            result = ApplyResult(result.outcome, result.written_paths,
                                 result.message + f"; lock cleanup failed: {lock}: {error}", result.recovery_path)
    return result


def _remove_backup(backup: Path | None) -> str | None:
    if backup is not None:
        try:
            shutil.rmtree(backup)
        except OSError:
            return str(backup)
    return None
