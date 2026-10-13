"""Fail-closed deterministic root-project initialization."""

from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from typing import Iterable

from .catalog import (
    PACKAGE_FILES,
    PACKAGE_TEMPLATE_DIR,
    PROJECT_INSTANCE_TEMPLATES,
    ROOT_OPTIONAL_DIRS,
    ROOT_STANDARD_EXTRA_DIRS,
    ROOT_STANDARD_EXTRA_ROLES,
    ROOT_REQUIRED_DIRS,
    BASELINE_METADATA_DIRS,
)
from .common import ApplyResult, PathPlan, plan_digest, same_file, same_tree, validate_iso_date
from .baseline import mixed_inventory_entries
from .local_time import local_timezone
from .root_transaction import RootWrite, apply_writes, path_state


MANIFEST_MARKER = "<!-- research-baseline-manifest:v1 -->"
OPTIONAL_MODULE_BEGIN = "<!-- BEGIN INITIALIZER-MANAGED OPTIONAL MODULES v1 -->"
OPTIONAL_MODULE_END = "<!-- END INITIALIZER-MANAGED OPTIONAL MODULES v1 -->"
RESERVED_FILES = (*PACKAGE_FILES, *PROJECT_INSTANCE_TEMPLATES)
DEFAULT_BACKGROUND = "Project background has not been specified; use the standard structure to organize project materials."
DEFAULT_TASK_DESCRIPTION = "Initial task has not been specified; define it in the root task records before starting work."


@dataclass(frozen=True)
class RootPlan:
    source_root: Path
    target: Path
    mode: str
    date: str
    optional_dirs: tuple[str, ...]
    paths: tuple[PathPlan, ...]
    conflicts: tuple[str, ...]
    confirmation_required: bool
    installation_route: str
    optional_modules_for_records: tuple[str, ...]
    project_name: str
    background: str
    task_description: str
    timezone: str
    source_revision: str
    source_state: dict
    target_state: dict
    file_writes: tuple[RootWrite, ...]
    directory_writes: tuple[str, ...]
    plan_id: str

    @property
    def has_conflict(self) -> bool:
        return bool(self.conflicts)

    @property
    def planned_writes(self) -> tuple[str, ...]:
        return tuple(item.path for item in self.paths if item.disposition in ("create", "patch-managed"))

    def path_disposition(self, path: str) -> str | None:
        for item in self.paths:
            if item.path == path:
                return item.disposition
        return None


def _normal_optional_dirs(optional_dirs: Iterable[str]) -> tuple[str, ...]:
    selected = tuple(optional_dirs)
    if len(set(selected)) != len(selected):
        raise ValueError("optional directories must not contain duplicates")
    unknown = tuple(item for item in selected if item not in ROOT_OPTIONAL_DIRS)
    if unknown:
        raise ValueError(f"unknown optional directory: {', '.join(unknown)}")
    return ROOT_OPTIONAL_DIRS


def _validate_source(source_root: Path) -> Path:
    source = source_root.resolve()
    missing = [name for name in PACKAGE_FILES if not (source / name).is_file()]
    if not (source / PACKAGE_TEMPLATE_DIR).is_dir():
        missing.append(f"{PACKAGE_TEMPLATE_DIR}/")
    for template in PROJECT_INSTANCE_TEMPLATES.values():
        if not (source / PACKAGE_TEMPLATE_DIR / template).is_file():
            missing.append(f"{PACKAGE_TEMPLATE_DIR}/{template}")
    if missing:
        raise ValueError(f"source does not contain a complete release payload: {', '.join(missing)}")
    for path in (source / name for name in PACKAGE_FILES):
        if path.is_symlink():
            raise ValueError(f"source symlinks are not supported: {path}")
    for path in (source / PACKAGE_TEMPLATE_DIR, *(source / PACKAGE_TEMPLATE_DIR).rglob("*")):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError(f"source must contain regular files/directories: {path}")
    return source


def _is_recognized(target: Path) -> bool:
    manifest = target / "BASELINE_MANIFEST.md"
    required_files = (
        "AGENTS.md",
        "RESEARCH_WORKFLOW.md",
        "PROJECT_CONTEXT.md",
        "PROJECT_STATUS.md",
    )
    return (
        manifest.is_file()
        and MANIFEST_MARKER in manifest.read_text(encoding="utf-8", errors="replace")
        and all((target / item).is_file() for item in required_files)
        and (target / "templates").is_dir()
    )


def _add(plans: list[PathPlan], path: str, kind: str, disposition: str, reason: str) -> None:
    plans.append(PathPlan(path=path, kind=kind, disposition=disposition, reason=reason))


def _project_text(value: str | None, default: str, label: str) -> str:
    text = default if value is None else value
    if not text.strip() or any(character in text for character in ("\n", "\r", "\x00", "\u2028", "\u2029")):
        raise ValueError(f"{label} must be non-empty single-line text")
    return text.strip()


def build_root_plan(
    source_root: Path,
    target: Path,
    *,
    optional_dirs: Iterable[str] = (),
    date: str,
    project_name: str | None = None,
    background: str | None = None,
    task_description: str | None = None,
) -> RootPlan:
    """Classify a root target without creating or changing any path."""
    source = _validate_source(Path(source_root))
    source_state = _source_state(source)
    target_path = Path(target).resolve()
    chosen_optional = _normal_optional_dirs(optional_dirs)
    valid_date = validate_iso_date(date)
    project_display_name = _project_text(project_name, target_path.name, "project name")
    project_background = _project_text(background, DEFAULT_BACKGROUND, "background")
    initial_task = _project_text(task_description, DEFAULT_TASK_DESCRIPTION, "task description")
    timezone = local_timezone()
    plans: list[PathPlan] = []
    conflicts: list[str] = []
    optional_modules_for_records: tuple[str, ...] = ()

    if target_path.exists() and not target_path.is_dir():
        _add(plans, ".", "directory", "conflict", "target is not a directory")
        conflicts.append("target path is not a directory")
        mode = "conflict"
    else:
        entries = tuple(target_path.iterdir()) if target_path.exists() else ()
        if not entries:
            mode = "fresh"
        elif _is_recognized(target_path):
            mode = "extend"
        else:
            mode = "adopt"

    if mode == "fresh":
        for name in PACKAGE_FILES:
            _add(plans, name, "file", "create", "release payload")
        _add(plans, "templates/", "directory", "create", "complete template library")
        for destination in PROJECT_INSTANCE_TEMPLATES:
            _add(plans, destination, "file", "create", "instantiated project entry point")
        for name in ROOT_REQUIRED_DIRS:
            _add(plans, f"{name}/", "directory", "create", "required root directory")
        for name in (*ROOT_STANDARD_EXTRA_DIRS, *BASELINE_METADATA_DIRS):
            _add(plans, f"{name}/", "directory", "create", "standard precreated directory")
        confirmation_required = False
        route = "fresh initialization"
        optional_modules_for_records = ROOT_STANDARD_EXTRA_DIRS

    elif mode == "adopt":
        planned_files = set(RESERVED_FILES)
        planned_dirs = set(ROOT_REQUIRED_DIRS) | set(chosen_optional) | {PACKAGE_TEMPLATE_DIR}
        for name in PACKAGE_FILES:
            path = target_path / name
            if path.exists():
                _add(plans, name, "file", "conflict", "existing baseline authority file")
                conflicts.append(f"{name}: existing baseline authority file")
            else:
                _add(plans, name, "file", "create", "release payload")
        template_path = target_path / PACKAGE_TEMPLATE_DIR
        if template_path.exists():
            _add(plans, "templates/", "directory", "conflict", "existing baseline template directory")
            conflicts.append("templates/: existing baseline template directory")
        else:
            _add(plans, "templates/", "directory", "create", "complete template library")
        for destination in PROJECT_INSTANCE_TEMPLATES:
            path = target_path / destination
            if path.exists() and destination == "README.md" and path.is_file():
                _add(plans, destination, "file", "retain-unvalidated", "existing project overview is preserved")
            elif path.exists():
                _add(plans, destination, "file", "conflict", "existing project entry file")
                conflicts.append(f"{destination}: existing project entry file")
            else:
                _add(plans, destination, "file", "create", "instantiated project entry point")
        for name in ROOT_REQUIRED_DIRS:
            path = target_path / name
            rel = f"{name}/"
            if not path.exists():
                _add(plans, rel, "directory", "create", "required root directory")
            elif path.is_dir():
                _add(plans, rel, "directory", "retain-unvalidated", "existing expected directory is preserved")
            else:
                _add(plans, rel, "directory", "conflict", "required directory occupied by non-directory")
                conflicts.append(f"{rel}: required directory occupied by non-directory")
        for name in (*ROOT_STANDARD_EXTRA_DIRS, *BASELINE_METADATA_DIRS):
            path = target_path / name
            rel = f"{name}/"
            if not path.exists():
                _add(plans, rel, "directory", "create", "standard precreated directory")
            elif path.is_dir():
                _add(plans, rel, "directory", "retain-unvalidated", "existing standard directory is preserved")
            else:
                _add(plans, rel, "directory", "conflict", "optional directory occupied by non-directory")
                conflicts.append(f"{rel}: optional directory occupied by non-directory")
        for entry in sorted(target_path.iterdir(), key=lambda item: item.name):
            if entry.name not in planned_files and entry.name not in planned_dirs:
                suffix = "/" if entry.is_dir() else ""
                _add(plans, f"{entry.name}{suffix}", "directory" if entry.is_dir() else "file", "outside-plan", "existing unrelated content")
        confirmation_required = True
        route = "confirmed adoption application"
        optional_modules_for_records = ROOT_STANDARD_EXTRA_DIRS

    elif mode == "extend":
        if any(value is not None for value in (project_name, background, task_description)):
            raise ValueError("project information is only written during fresh initialization or adoption; existing project entry files are preserved during extend")
        for name in PACKAGE_FILES:
            destination = target_path / name
            if same_file(source / name, destination):
                _add(plans, name, "file", "skip-compatible", "release payload matches source")
            else:
                _add(plans, name, "file", "conflict", "local divergence or incompatible payload")
                conflicts.append(f"{name}: local divergence or incompatible payload")
        template_destination = target_path / PACKAGE_TEMPLATE_DIR
        if same_tree(source / PACKAGE_TEMPLATE_DIR, template_destination):
            _add(plans, "templates/", "directory", "skip-compatible", "template library matches source")
        else:
            _add(plans, "templates/", "directory", "conflict", "local divergence or incompatible template library")
            conflicts.append("templates/: local divergence or incompatible template library")
        for name in ("README.md", "PROJECT_CONTEXT.md", "PROJECT_STATUS.md", "BASELINE_MANIFEST.md"):
            path = target_path / name
            if name == "BASELINE_MANIFEST.md":
                compatible = path.is_file() and MANIFEST_MARKER in path.read_text(encoding="utf-8", errors="replace")
            elif name == "README.md":
                compatible = path.is_file()
            else:
                compatible = path.is_file()
            if compatible:
                reason = "existing project overview is preserved" if name == "README.md" else "recognized project entry point"
                _add(plans, name, "file", "skip-compatible", reason)
            else:
                _add(plans, name, "file", "conflict", "recognized project entry point is missing or incompatible")
                conflicts.append(f"{name}: recognized project entry point is missing or incompatible")
        for name in ROOT_REQUIRED_DIRS:
            path = target_path / name
            rel = f"{name}/"
            if path.is_dir():
                _add(plans, rel, "directory", "skip-compatible", "recognized required directory")
            else:
                _add(plans, rel, "directory", "conflict", "recognized required directory is missing or incompatible")
                conflicts.append(f"{rel}: recognized required directory is missing or incompatible")
        missing_optional: list[str] = []
        for name in (*ROOT_STANDARD_EXTRA_DIRS, *BASELINE_METADATA_DIRS):
            path = target_path / name
            rel = f"{name}/"
            if path.is_dir():
                _add(plans, rel, "directory", "skip-compatible", "recognized standard directory")
            elif not path.exists():
                _add(plans, rel, "directory", "create", "confirmed standard-directory completion")
                missing_optional.append(name)
            else:
                _add(plans, rel, "directory", "conflict", "optional directory occupied by non-directory")
                conflicts.append(f"{rel}: optional directory occupied by non-directory")
        records = {name: (target_path / name).read_text(encoding="utf-8", errors="replace")
                   for name in ("BASELINE_MANIFEST.md", "PROJECT_CONTEXT.md")
                   if (target_path / name).is_file()}
        unrecorded = [name for name in ROOT_STANDARD_EXTRA_DIRS
                      if any(f"| `{name}/` |" not in text for text in records.values())]
        optional_modules_for_records = tuple(name for name in ROOT_STANDARD_EXTRA_DIRS
                                             if name in missing_optional or name in unrecorded)
        if optional_modules_for_records:
            for record_name, record_text in records.items():
                if not _has_single_optional_module_region(record_text):
                    conflicts.append(f"{record_name}: missing or malformed optional-module managed region")
                    existing = next(item for item in plans if item.path == record_name)
                    plans[plans.index(existing)] = PathPlan(
                        path=existing.path,
                        kind=existing.kind,
                        disposition="conflict",
                        reason="missing or malformed optional-module managed region",
                    )
        confirmation_required = bool(optional_modules_for_records)
        route = "confirmed extend application"

    else:
        confirmation_required = False
        route = ""

    for index, item in enumerate(plans):
        current = target_path
        for part in Path(item.path).parts:
            current = current / part
            if current.is_symlink():
                conflicts.append(f"{item.path}: symlink paths are not supported")
                plans[index] = PathPlan(item.path, item.kind, "conflict", "symlink path")
                break

    target_state = _target_state(target_path, tuple(plans))
    revision = _source_revision(source)
    plan = RootPlan(
        source_root=source, target=target_path, mode=mode, date=valid_date,
        optional_dirs=chosen_optional, paths=tuple(plans), conflicts=tuple(conflicts),
        confirmation_required=confirmation_required, installation_route=route,
        optional_modules_for_records=optional_modules_for_records,
        project_name=project_display_name, background=project_background,
        task_description=initial_task, timezone=timezone, source_revision=revision,
        source_state=source_state, target_state=target_state,
        file_writes=(), directory_writes=(), plan_id="pending",
    )
    if not plan.has_conflict:
        writes, directories = _prepare_writes(plan)
        for write in writes:
            if write.previous is not None:
                index = next(index for index, item in enumerate(plans) if item.path == write.path)
                plans[index] = PathPlan(write.path, "file", "patch-managed", "bounded directory-inventory patch; unrelated text is preserved")
        plan = replace(plan, paths=tuple(plans))
    else:
        writes, directories = (), ()
    payload = {
        "source": source.as_posix(),
        "target": target_path.as_posix(),
        "mode": mode,
        "date": valid_date,
        "optional_dirs": chosen_optional,
        "paths": [(item.path, item.kind, item.disposition, item.reason) for item in plan.paths],
        "conflicts": conflicts,
        "optional_modules_for_records": optional_modules_for_records,
        "project_name": project_display_name,
        "background": project_background,
        "task_description": initial_task,
        "timezone": timezone,
        "source_revision": revision,
        "source_state": source_state,
        "target_state": target_state,
        "writes": [(write.path, sha256(write.content).hexdigest(), write.mode) for write in writes],
        "directories": directories,
    }
    plan = replace(plan, plan_id=plan_digest(payload))
    if not plan.has_conflict:
        writes, directories = _prepare_writes(plan)
    _check_state(plan)
    return replace(plan, file_writes=writes, directory_writes=directories)


def _source_state(source: Path) -> dict:
    return {name: path_state(source / name, tree=name == PACKAGE_TEMPLATE_DIR)
            for name in (*PACKAGE_FILES, PACKAGE_TEMPLATE_DIR)}


def _target_state(target: Path, paths: tuple[PathPlan, ...]) -> dict:
    return {"root": path_state(target, content=False),
            "paths": {item.path: path_state(target / item.path, tree=item.path == "templates/",
                                             content=item.disposition != "outside-plan") for item in paths}}


def _check_state(plan: RootPlan) -> None:
    if local_timezone() != plan.timezone:
        raise ValueError("machine timezone changed after planning; re-run preflight")
    if _source_state(plan.source_root) != plan.source_state or _source_revision(plan.source_root) != plan.source_revision:
        raise ValueError("baseline source changed after planning; re-run preflight")
    if _target_state(plan.target, plan.paths) != plan.target_state:
        raise ValueError("target changed after planning; re-run preflight")


def _verify_preserved(plan: RootPlan) -> None:
    for item in plan.paths:
        if item.disposition not in ("create", "patch-managed"):
            current = path_state(plan.target / item.path, tree=item.path == "templates/",
                                 content=item.disposition != "outside-plan")
            expected = plan.target_state["paths"][item.path]
            if item.kind == "directory" and item.path != "templates/":
                current = {key: value for key, value in current.items() if key != "children"}
                expected = {key: value for key, value in expected.items() if key != "children"}
            if current != expected:
                raise OSError(f"protected path changed during apply: {item.path}")


def _has_single_optional_module_region(text: str) -> bool:
    return (
        text.count(OPTIONAL_MODULE_BEGIN) == 1
        and text.count(OPTIONAL_MODULE_END) == 1
        and text.index(OPTIONAL_MODULE_BEGIN) < text.index(OPTIONAL_MODULE_END)
    )


def _replace_optional_module_region(text: str, interior: str) -> str:
    if not _has_single_optional_module_region(text):
        raise ValueError("missing or malformed optional-module managed region")
    begin = text.index(OPTIONAL_MODULE_BEGIN) + len(OPTIONAL_MODULE_BEGIN)
    end = text.index(OPTIONAL_MODULE_END)
    return text[:begin] + "\n" + interior.rstrip() + "\n" + text[end:]


def _render_optional_manifest_modules(modules: tuple[str, ...], date: str, route: str) -> str:
    if not modules:
        return "- **Precreated standard directories:** none"
    rows = [
        "| Path | Classification | Enabled on | Enablement route | Role / primary entry point | Record |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    rows.extend(
        f"| `{name}/` | precreated directory | {date} | `{route}` | {ROOT_STANDARD_EXTRA_ROLES[name]} | [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) |"
        for name in modules
    )
    return "\n".join(rows)


def _render_optional_context_modules(modules: tuple[str, ...]) -> str:
    if not modules:
        return "- **Precreated standard directories:** none"
    rows = [
        "| Path | Role / primary entry point |",
        "| --- | --- |",
    ]
    rows.extend(
        f"| `{name}/` | {ROOT_STANDARD_EXTRA_ROLES[name]}; no primary entry point recorded. |"
        for name in modules
    )
    return "\n".join(rows)


def _source_revision(source_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "--short", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return "unavailable"
    revision = result.stdout.strip()
    return revision if result.returncode == 0 and revision else "unavailable"


def _render_instance_template(plan: RootPlan, destination_name: str) -> str:
    template_name = PROJECT_INSTANCE_TEMPLATES[destination_name]
    text = (plan.source_root / PACKAGE_TEMPLATE_DIR / template_name).read_text(encoding="utf-8")
    fields = {
        "<Project Name>": plan.project_name,
        "<Project Background>": plan.background,
        "<Initial Task Description>": plan.task_description,
        "<IANA timezone>": plan.timezone,
    }
    text = re.sub(r"<Project Name>|<Project Background>|<Initial Task Description>|<IANA timezone>",
                  lambda match: fields[match.group()], text)
    if destination_name == "README.md":
        return text
    if destination_name == "PROJECT_CONTEXT.md":
        return _replace_optional_module_region(
            text,
            _render_optional_context_modules(plan.optional_modules_for_records),
        )
    if destination_name == "PROJECT_STATUS.md":
        return text
    revision = plan.source_revision
    text = text.replace("YYYY-MM-DD", plan.date)
    text = text.replace("- **Source repository or distribution:**", f"- **Source repository or distribution:** `{plan.source_root}`")
    text = text.replace("- **Source revision:** unavailable", f"- **Source revision:** {revision}")
    text = text.replace(
        "- **Baseline source path or identity:**",
        f"- **Baseline source path or identity:** `{plan.source_root}`",
    )
    text = text.replace(
        "- **Installation route:** `fresh initialization` | `confirmed adoption application` | `confirmed extend application`",
        f"- **Installation route:** {plan.installation_route}",
    )
    text = text.replace("- **Initializer / invocation record:**", "- **Initializer / invocation record:** `research_init root`")
    confirmation = "not required for clean fresh initialization" if not plan.confirmation_required else f"confirmed plan `{plan.plan_id}`"
    text = text.replace("- **Confirmation record (if required):", f"- **Confirmation record (if required):** {confirmation}")
    return _replace_optional_module_region(
        text,
        _render_optional_manifest_modules(plan.optional_modules_for_records, plan.date, "initial-standard"),
    )


def _append_existing_region(text: str, interior: str) -> str:
    begin = text.index(OPTIONAL_MODULE_BEGIN) + len(OPTIONAL_MODULE_BEGIN)
    end = text.index(OPTIONAL_MODULE_END)
    previous = text[begin:end].strip()
    old_rows = [line for line in previous.splitlines() if line.startswith("| `")]
    if old_rows:
        new_rows = [line for line in interior.splitlines() if line.startswith("| `")
                    and not any(line.split("|", 2)[1] == old.split("|", 2)[1] for old in old_rows)]
        interior = previous + ("\n" + "\n".join(new_rows) if new_rows else "")
    return _replace_optional_module_region(text, interior)


def _prepare_writes(plan: RootPlan) -> tuple[tuple[RootWrite, ...], tuple[str, ...]]:
    writes = []
    directories = set()
    if not plan.target.exists():
        directories.add(".")
    for item in plan.paths:
        if item.disposition == "create":
            if item.kind == "directory":
                directories.add(item.path.rstrip("/"))
                if item.path == "templates/":
                    for source in sorted((plan.source_root / PACKAGE_TEMPLATE_DIR).rglob("*")):
                        relative = source.relative_to(plan.source_root).as_posix()
                        if source.is_dir():
                            directories.add(relative)
                        else:
                            writes.append(RootWrite(relative, source.read_bytes(), source.stat().st_mode & 0o777))
            elif item.path in PACKAGE_FILES:
                source = plan.source_root / item.path
                writes.append(RootWrite(item.path, source.read_bytes(), source.stat().st_mode & 0o777))
            else:
                writes.append(RootWrite(item.path, _render_instance_template(plan, item.path).encode("utf-8"), 0o644))
    if plan.mode in ("fresh", "adopt") and not (plan.target / ".baseline/inventory/current.json").exists():
        inventory_files = []
        template_paths = [path for path in sorted((plan.source_root / PACKAGE_TEMPLATE_DIR).rglob("*")) if path.is_file()]
        for relative in (*PACKAGE_FILES, *(path.relative_to(plan.source_root).as_posix() for path in template_paths)):
            source_path = plan.source_root / relative
            target_path = plan.target / relative
            content = source_path.read_bytes() if not target_path.exists() else target_path.read_bytes()
            inventory_files.append({
                "path": relative,
                "kind": "file",
                "ownership": "template" if relative.startswith("templates/") else "normative-baseline",
                "comparison": "file",
                "sourcePath": relative,
                "size": len(content),
                "sha256": sha256(content).hexdigest(),
            })
        inventory_files.extend(mixed_inventory_entries(
            plan.target,
            overrides={write.path: write.content for write in writes if write.path in PROJECT_INSTANCE_TEMPLATES},
        ))
        inventory = {"schemaVersion": 1, "snapshotId": plan.plan_id, "createdAt": plan.date,
                     "baseline": {"sourceRevision": plan.source_revision, "sourceState": plan.source_state},
                     "digestAlgorithm": "sha256", "files": inventory_files}
        writes.append(RootWrite(".baseline/inventory/current.json", (json.dumps(inventory, indent=2, sort_keys=True) + "\n").encode(), 0o644))
    if plan.mode == "extend" and plan.optional_modules_for_records:
        for name, interior in (
            ("BASELINE_MANIFEST.md", _render_optional_manifest_modules(plan.optional_modules_for_records, plan.date, "confirmed-extend")),
            ("PROJECT_CONTEXT.md", _render_optional_context_modules(plan.optional_modules_for_records)),
        ):
            path = plan.target / name
            previous = path.read_bytes()
            content = _append_existing_region(previous.decode("utf-8"), interior).encode("utf-8")
            if content != previous:
                writes.append(RootWrite(name, content, path.stat().st_mode & 0o777, previous))
    return tuple(writes), tuple(sorted(directories, key=lambda item: (len(Path(item).parts), item)))


def apply_root_plan(
    plan: RootPlan,
    *,
    apply: bool,
    confirmation_plan_id: str | None,
) -> ApplyResult:
    """Apply only a conflict-free, explicitly authorized root plan."""
    if plan.has_conflict:
        return ApplyResult("conflict", (), "conflict detected during preflight; zero writes")
    if not apply:
        return ApplyResult("dry-run", (), "preflight completed; dry-run makes zero writes")
    if (plan.confirmation_required or confirmation_plan_id is not None) and confirmation_plan_id != plan.plan_id:
        return ApplyResult(
            "awaiting-confirmation",
            (),
            "apply requires the exact current plan identifier; zero writes",
        )

    try:
        _check_state(plan)
    except (ValueError, OSError) as error:
        return ApplyResult("conflict", (), f"{error}; zero writes")
    return apply_writes(plan.target, plan.file_writes, plan.directory_writes,
                        plan_id=plan.plan_id, check_state=lambda: _check_state(plan),
                        verify_preserved=lambda: _verify_preserved(plan),
                        verify_restored=lambda: _verify_restored(plan))


def _verify_restored(plan: RootPlan) -> None:
    if _target_state(plan.target, plan.paths) != plan.target_state:
        raise OSError("target does not match its pre-apply state; retained backup requires inspection")


def render_root_report(plan: RootPlan, result: ApplyResult | None) -> str:
    """Render the stable nine-section human-readable root-initializer report."""
    apply_outcome = "not requested" if result is None else result.outcome
    record_updates = "none"
    if result and result.outcome == "applied":
        records = [name for name in PROJECT_INSTANCE_TEMPLATES if name in result.written_paths]
        record_updates = ", ".join(records) if records else "none"
    path_lines = [
        f"- `{item.path}` — **{item.disposition}** ({item.reason})"
        for item in plan.paths
    ] or ["- No paths were planned."]
    conflicts = [f"- {item}" for item in plan.conflicts] or ["- None."]
    confirmation = (
        "not applicable: preflight conflict cannot be overridden"
        if plan.has_conflict
        else (
            f"required: re-run with matching plan ID `{plan.plan_id}`"
            if plan.confirmation_required
            else "not required for clean fresh creation or compatible no-op extension"
        )
    )
    information = (
        ["- **Project information:** existing entry files are retained; no project-information update is planned."]
        if plan.mode == "extend"
        else [
            f"- **Project name:** {plan.project_name}",
            f"- **Background:** {plan.background}",
            f"- **Initial task description:** {plan.task_description}",
            "- **Information destinations:** new PROJECT_CONTEXT.md and, where absent, README.md; the display name also titles new PROJECT_STATUS.md. Existing README.md is preserved.",
        ]
    )
    return "\n".join(
        [
            "# Root Project Initializer Report",
            "",
            "## 1. Invocation summary",
            f"- **Target:** `{plan.target}`",
            f"- **Source:** `{plan.source_root}`",
            f"- **Plan ID:** `{plan.plan_id}`",
            f"- **Machine timezone:** `{plan.timezone}`",
            *information,
            "",
            "## 2. Target classification",
            f"- **Mode:** `{plan.mode}`",
            "",
            "## 3. Preflight result",
            f"- **Outcome:** {'conflict' if plan.has_conflict else 'ready'}",
            "",
            "## 4. Path plan",
            *path_lines,
            "",
            "## 5. Confirmation state",
            f"- **State:** {confirmation}",
            "",
            "## 6. Apply result",
            f"- **Outcome:** {apply_outcome}",
            f"- **Detail:** {result.message if result else 'No apply attempt.'}",
            f"- **Recovery backup:** `{result.recovery_path}`" if result and result.recovery_path else "- **Recovery backup:** none retained",
            "",
            "## 7. Record updates",
            f"- **Result:** {record_updates}",
            "",
            "## 8. Conflicts and manual resolution",
            *conflicts,
            "",
            "## 9. Boundaries and limitations",
            "- The initializer precreates the standard directory catalog, including the empty artifacts/ home; it does not allocate artifact IDs, register content, infer project science, overwrite existing content or update an existing baseline payload.",
            "- Recognized optional-directory expansion is limited to the exact optional-module managed regions in `BASELINE_MANIFEST.md` and `PROJECT_CONTEXT.md`; malformed or legacy records fail closed.",
            "",
        ]
    )
