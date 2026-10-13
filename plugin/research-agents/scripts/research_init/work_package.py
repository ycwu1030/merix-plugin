"""Deterministic, root-governed work-package initialization."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, Mapping

from .catalog import WORK_PACKAGE_DIRS, WORK_PACKAGE_DIR_ROLES, render_managed_structure
from .common import ApplyResult, PathPlan, plan_digest, validate_iso_date


BEGIN_MARKER = "<!-- BEGIN INITIALIZER-MANAGED STRUCTURE v1 -->"
END_MARKER = "<!-- END INITIALIZER-MANAGED STRUCTURE v1 -->"
TIMESTAMP_COMMENT = "<!-- initializer-managed:last-updated -->"
PASSIVE_FIELDS = (
    "Purpose",
    "Scope-specific deliverable or non-claim",
    "Included execution material",
    "Environment manifest(s)",
    "Input manifest(s)",
    "Run record(s) (`R-NNN`)",
    "Comparison record(s) (`C-NNN`)",
    "Root artifact(s) (`A-NNN`)",
    "Relevant analysis, source-audit, derivation, and code records",
    "Known limitations / unresolved boundaries",
    "Local prerequisites and safe-use notes",
    "Do not infer / do not use for",
    "Safe continuation or recovery steps",
    "Related root task and record links",
)


@dataclass(frozen=True)
class WorkPackagePlan:
    project_root: Path
    task_id: str
    work_package_id: str
    task_path: Path | None
    topic: str
    package_name: str
    workspace_dir: Path
    mode: str
    date: str
    modules: tuple[str, ...]
    existing_modules: tuple[str, ...]
    final_modules: tuple[str, ...]
    purpose: str
    passive_updates: tuple[tuple[str, str], ...]
    paths: tuple[PathPlan, ...]
    conflicts: tuple[str, ...]
    patch_action: str
    plan_id: str

    @property
    def has_conflict(self) -> bool:
        return bool(self.conflicts)

    def path_disposition(self, path: str) -> str | None:
        for item in self.paths:
            if item.path == path:
                return item.disposition
        return None


def _normal_modules(modules: Iterable[str]) -> tuple[str, ...]:
    selected = tuple(modules)
    if len(set(selected)) != len(selected):
        raise ValueError("work-package modules must not contain duplicates")
    unknown = tuple(item for item in selected if item not in WORK_PACKAGE_DIR_ROLES)
    if unknown:
        raise ValueError(f"unknown work-package module: {', '.join(unknown)}")
    return tuple(item for item in WORK_PACKAGE_DIRS if item in selected)


def _normal_passive_updates(updates: Mapping[str, str] | None) -> tuple[tuple[str, str], ...]:
    if not updates:
        return ()
    rendered: list[tuple[str, str]] = []
    for label, value in updates.items():
        if label not in PASSIVE_FIELDS:
            raise ValueError(f"unsupported passive field: {label}")
        if "\n" in value or "\r" in value:
            raise ValueError(f"passive field must be one line: {label}")
        rendered.append((label, value))
    return tuple(sorted(rendered))


def _validate_task_id(task_id: str) -> None:
    if not re.fullmatch(r"T-\d{3,}", task_id):
        raise ValueError("task ID must use the form T-NNN")


def _validate_topic(topic: str) -> None:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", topic):
        raise ValueError("topic must be a lowercase hyphenated path-safe slug")


def _find_task(project_root: Path, task_id: str) -> tuple[Path | None, list[str]]:
    candidates = sorted((project_root / "tasks").glob(f"{task_id}-*.md"))
    if len(candidates) != 1:
        return None, [f"expected exactly one task record matching {task_id}-*.md"]
    candidate = candidates[0]
    text = candidate.read_text(encoding="utf-8", errors="replace")
    if not re.search(rf"^- \*\*ID:\*\* `{re.escape(task_id)}`$", text, flags=re.MULTILINE):
        return None, [f"{candidate.relative_to(project_root)} does not contain the matching task ID field"]
    return candidate, []


def _field_pattern(label: str) -> re.Pattern[str]:
    return re.compile(rf"^(- \*\*{re.escape(label)}:\*\*)(.*)$", flags=re.MULTILINE)


def _replace_field(text: str, label: str, value: str) -> str:
    pattern = _field_pattern(label)
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one supported field: {label}")
    return pattern.sub(rf"\1 {value}", text, count=1)


def _parse_enabled_modules(text: str) -> tuple[str, ...]:
    if text.count(BEGIN_MARKER) != 1 or text.count(END_MARKER) != 1:
        raise ValueError("expected exactly one complete managed structure marker pair")
    begin = text.index(BEGIN_MARKER)
    end = text.index(END_MARKER)
    if begin >= end:
        raise ValueError("managed structure markers are not ordered")
    interior = text[begin + len(BEGIN_MARKER) : end]
    if "- **Enabled local directories:** none" in interior:
        return ()
    found = tuple(re.findall(r"\| `([a-z]+)/` \|", interior))
    if not found:
        raise ValueError("managed structure does not declare valid local directories")
    if len(set(found)) != len(found) or any(name not in WORK_PACKAGE_DIRS for name in found):
        raise ValueError("managed structure contains duplicate or unknown local directories")
    return tuple(name for name in WORK_PACKAGE_DIRS if name in found)


def _validate_patchable_entry(text: str, *, task_id: str, topic: str, task_filename: str) -> tuple[str, ...]:
    package_name = f"{task_id}-{topic}"
    title = f"# Work Package: {task_id} — {topic}"
    expected_path = f"- **Work-package path:** `workspaces/{package_name}/`"
    expected_root_task = f"- **Root task:** [{task_id}](../../tasks/{task_filename})"
    if not text.startswith(title + "\n"):
        raise ValueError("work-package title does not match requested task identity/path")
    if expected_path not in text:
        raise ValueError("work-package path field does not match requested task identity/path")
    if expected_root_task not in text:
        raise ValueError("root task link does not match the authoritative task record")
    timestamp_pattern = re.compile(
        rf"^- \*\*Last updated:\*\* \d{{4}}-\d{{2}}-\d{{2}} {re.escape(TIMESTAMP_COMMENT)}$",
        flags=re.MULTILINE,
    )
    if len(timestamp_pattern.findall(text)) != 1:
        raise ValueError("expected exactly one initializer-managed Last updated field")
    return _parse_enabled_modules(text)


def _replace_timestamp(text: str, date: str) -> str:
    pattern = re.compile(
        rf"^- \*\*Last updated:\*\* \d{{4}}-\d{{2}}-\d{{2}} {re.escape(TIMESTAMP_COMMENT)}$",
        flags=re.MULTILINE,
    )
    if len(pattern.findall(text)) != 1:
        raise ValueError("expected exactly one initializer-managed Last updated field")
    return pattern.sub(f"- **Last updated:** {date} {TIMESTAMP_COMMENT}", text, count=1)


def _replace_structure(text: str, modules: tuple[str, ...]) -> str:
    if text.count(BEGIN_MARKER) != 1 or text.count(END_MARKER) != 1:
        raise ValueError("expected exactly one complete managed structure marker pair")
    begin = text.index(BEGIN_MARKER) + len(BEGIN_MARKER)
    end = text.index(END_MARKER)
    if begin > end:
        raise ValueError("managed structure markers are not ordered")
    return text[:begin] + "\n" + render_managed_structure(modules).rstrip() + "\n" + text[end:]


def _render_new_entry(
    template: str,
    *,
    task_id: str,
    work_package_id: str,
    topic: str,
    task_filename: str,
    date: str,
    modules: tuple[str, ...],
    purpose: str,
    passive_updates: tuple[tuple[str, str]],
) -> str:
    package_name = f"{task_id}-{topic}"
    rendered = template.replace("T-NNN-<topic>.md", task_filename)
    rendered = rendered.replace("T-NNN-<topic>", package_name)
    rendered = rendered.replace("T-NNN", task_id)
    rendered = rendered.replace("WP-NNN", work_package_id)
    rendered = rendered.replace("<Topic>", topic)
    rendered = rendered.replace("YYYY-MM-DD", date)
    rendered = _replace_structure(rendered, modules)
    rendered = _replace_field(rendered, "Purpose", purpose)
    for label, value in passive_updates:
        if label == "Purpose":
            continue
        rendered = _replace_field(rendered, label, value)
    _validate_patchable_entry(rendered, task_id=task_id, topic=topic, task_filename=task_filename)
    return rendered


def build_work_package_plan(
    project_root: Path,
    *,
    task_id: str,
    topic: str,
    mode: str,
    modules: Iterable[str] = (),
    purpose: str,
    date: str,
    passive_updates: Mapping[str, str] | None = None,
    work_package_id: str | None = None,
) -> WorkPackagePlan:
    """Build a zero-write plan for one root-governed work package."""
    _validate_task_id(task_id)
    _validate_topic(topic)
    if mode not in {"minimal", "full", "extend"}:
        raise ValueError("mode must be minimal, full, or extend")
    valid_date = validate_iso_date(date)
    root = Path(project_root).resolve()
    selected = _normal_modules(modules)
    passive = _normal_passive_updates(passive_updates)
    package_name = f"{task_id}-{topic}"
    workspace_root = root / "workspaces"
    workspace_dir = workspace_root / package_name
    identity = work_package_id or 'WP-' + task_id.removeprefix('T-')
    if not re.fullmatch(r'WP-\d{3,}', identity):
        raise ValueError('work package ID must use WP-NNN')
    task_path, task_errors = _find_task(root, task_id)
    conflicts = list(task_errors)
    identity_pattern = re.compile(r'^- \*\*Work package ID:\*\*\s*`?(WP-\d+)`?\s*$', re.MULTILINE)
    for entry in workspace_root.glob('*/WORK_PACKAGE.md'):
        declared = identity_pattern.search(entry.read_text(encoding='utf-8'))
        if entry.parent == workspace_dir and mode == 'extend' and declared:
            if work_package_id and declared.group(1) != work_package_id:
                conflicts.append('extend cannot change an established work package ID')
            identity = declared.group(1)
        elif declared and declared.group(1) == identity:
            conflicts.append('work package ID already exists; supply a distinct explicit --id')
    paths: list[PathPlan] = []

    if not root.is_dir():
        conflicts.append("project root is not a directory")
    if not workspace_root.is_dir():
        conflicts.append("workspaces/ is not enabled at the project root")
    template_path = root / "templates" / "WORK_PACKAGE.md"
    if not template_path.is_file():
        conflicts.append("templates/WORK_PACKAGE.md is unavailable")
    if not purpose.strip() and mode in {"minimal", "full"}:
        conflicts.append("creation requires an explicit grounded purpose")

    desired_initial = () if mode == "minimal" else WORK_PACKAGE_DIRS
    existing_modules: tuple[str, ...] = ()
    final_modules: tuple[str, ...] = ()
    patch_action = "none"

    if mode in {"minimal", "full"}:
        if workspace_dir.exists():
            conflicts.append("work-package target already exists; use extend only for a compatible entry point")
            paths.append(PathPlan(f"workspaces/{package_name}/", "directory", "conflict", "existing work-package target"))
        else:
            paths.append(PathPlan(f"workspaces/{package_name}/", "directory", "create", "new root-governed work package"))
            paths.append(PathPlan(f"workspaces/{package_name}/WORK_PACKAGE.md", "file", "create", "work-package entry point"))
            for name in desired_initial:
                paths.append(PathPlan(f"workspaces/{package_name}/{name}/", "directory", "create", "selected execution module"))
            final_modules = tuple(desired_initial)
    else:
        if not workspace_dir.is_dir():
            conflicts.append("work-package target does not exist for extend")
            paths.append(PathPlan(f"workspaces/{package_name}/", "directory", "conflict", "missing work-package target"))
        else:
            entry = workspace_dir / "WORK_PACKAGE.md"
            if not entry.is_file() or task_path is None:
                conflicts.append("compatible WORK_PACKAGE.md or root task identity is unavailable")
                paths.append(PathPlan(f"workspaces/{package_name}/WORK_PACKAGE.md", "file", "conflict", "missing entry point or task identity"))
            else:
                try:
                    existing_modules = _validate_patchable_entry(
                        entry.read_text(encoding="utf-8"),
                        task_id=task_id,
                        topic=topic,
                        task_filename=task_path.name,
                    )
                except ValueError as error:
                    conflicts.append(str(error))
                    paths.append(PathPlan(f"workspaces/{package_name}/WORK_PACKAGE.md", "file", "conflict", str(error)))
                else:
                    paths.append(PathPlan(f"workspaces/{package_name}/WORK_PACKAGE.md", "file", "skip", "compatible bounded entry point"))
                    missing: list[str] = []
                    for name in existing_modules:
                        directory = workspace_dir / name
                        if directory.is_dir():
                            paths.append(PathPlan(f"workspaces/{package_name}/{name}/", "directory", "skip", "enabled recorded module"))
                        else:
                            conflicts.append(f"enabled module directory is missing or incompatible: {name}/")
                            paths.append(PathPlan(f"workspaces/{package_name}/{name}/", "directory", "conflict", "enabled module path is missing or incompatible"))
                    for name in selected:
                        directory = workspace_dir / name
                        if name in existing_modules:
                            continue
                        if not directory.exists():
                            paths.append(PathPlan(f"workspaces/{package_name}/{name}/", "directory", "create", "explicitly selected extension module"))
                            missing.append(name)
                        elif directory.is_dir():
                            conflicts.append(f"unrecognized existing module directory: {name}/")
                            paths.append(PathPlan(f"workspaces/{package_name}/{name}/", "directory", "conflict", "existing directory is not declared by managed structure"))
                        else:
                            conflicts.append(f"module path is not a directory: {name}/")
                            paths.append(PathPlan(f"workspaces/{package_name}/{name}/", "directory", "conflict", "module path is not a directory"))
                    final_modules = tuple(name for name in WORK_PACKAGE_DIRS if name in set(existing_modules) | set(missing))
                    structural = bool(missing)
                    explicit = bool(passive)
                    if structural and explicit:
                        patch_action = "required bounded structural patch + explicitly requested grounded patch"
                    elif structural:
                        patch_action = "required bounded structural patch"
                    elif explicit:
                        patch_action = "explicitly requested grounded patch"

    payload = {
        "project": root.as_posix(),
        "task_id": task_id,
        "work_package_id": identity,
        "task_path": task_path.as_posix() if task_path else None,
        "topic": topic,
        "mode": mode,
        "date": valid_date,
        "modules": selected,
        "purpose": purpose,
        "passive_updates": passive,
        "paths": [(item.path, item.kind, item.disposition, item.reason) for item in paths],
        "conflicts": conflicts,
        "patch_action": patch_action,
    }
    return WorkPackagePlan(
        project_root=root,
        task_id=task_id,
        work_package_id=identity,
        task_path=task_path,
        topic=topic,
        package_name=package_name,
        workspace_dir=workspace_dir,
        mode=mode,
        date=valid_date,
        modules=selected,
        existing_modules=existing_modules,
        final_modules=final_modules,
        purpose=purpose,
        passive_updates=passive,
        paths=tuple(paths),
        conflicts=tuple(conflicts),
        patch_action=patch_action,
        plan_id=plan_digest(payload),
    )


def _patch_existing_entry(plan: WorkPackagePlan, text: str) -> str:
    rendered = text
    if plan.patch_action.startswith("required bounded structural patch"):
        rendered = _replace_structure(rendered, plan.final_modules)
    for label, value in plan.passive_updates:
        rendered = _replace_field(rendered, label, value)
    if plan.patch_action != "none":
        rendered = _replace_timestamp(rendered, plan.date)
    return rendered


def apply_work_package_plan(plan: WorkPackagePlan, *, apply: bool) -> ApplyResult:
    """Apply a conflict-free work-package plan without affecting root governance."""
    if plan.has_conflict:
        return ApplyResult("conflict", (), "conflict detected during preflight; zero writes")
    if not apply:
        return ApplyResult("dry-run", (), "preflight completed; dry-run makes zero writes")
    if plan.mode == "extend" and plan.patch_action == "none":
        return ApplyResult("no-op", (), "compatible extension has no selected missing module or requested passive update")

    written: list[str] = []
    if plan.mode in {"minimal", "full"}:
        assert plan.task_path is not None
        template = (plan.project_root / "templates" / "WORK_PACKAGE.md").read_text(encoding="utf-8")
        entry = _render_new_entry(
            template,
            task_id=plan.task_id,
            work_package_id=plan.work_package_id,
            topic=plan.topic,
            task_filename=plan.task_path.name,
            date=plan.date,
            modules=plan.final_modules,
            purpose=plan.purpose,
            passive_updates=plan.passive_updates,
        )
        plan.workspace_dir.mkdir(exist_ok=False)
        written.append(f"workspaces/{plan.package_name}/")
        (plan.workspace_dir / "WORK_PACKAGE.md").write_text(entry, encoding="utf-8", newline="")
        written.append(f"workspaces/{plan.package_name}/WORK_PACKAGE.md")
    for item in plan.paths:
        if item.disposition != "create" or item.path.endswith("WORK_PACKAGE.md") or item.path == f"workspaces/{plan.package_name}/":
            continue
        directory = plan.project_root / item.path.rstrip("/")
        directory.mkdir(exist_ok=False)
        written.append(item.path)
    if plan.mode == "extend":
        entry_path = plan.workspace_dir / "WORK_PACKAGE.md"
        patched = _patch_existing_entry(plan, entry_path.read_text(encoding="utf-8"))
        entry_path.write_text(patched, encoding="utf-8", newline="")
        written.append(f"workspaces/{plan.package_name}/WORK_PACKAGE.md [bounded patch]")
    return ApplyResult("applied", tuple(written), "applied only planned work-package paths and bounded document regions")


def render_work_package_report(plan: WorkPackagePlan, result: ApplyResult | None) -> str:
    """Render a stable readable report for work-package planning/apply."""
    path_lines = [f"- `{item.path}` — **{item.disposition}** ({item.reason})" for item in plan.paths] or ["- No paths were planned."]
    conflict_lines = [f"- {item}" for item in plan.conflicts] or ["- None."]
    outcome = result.outcome if result else "not requested"
    return "\n".join(
        [
            "# Work-Package Initializer Report",
            "",
            "## Invocation summary",
            f"- **Task:** `{plan.task_id}`",
            f"- **Path:** `workspaces/{plan.package_name}/`",
            f"- **Plan ID:** `{plan.plan_id}`",
            "",
            "## Preflight result",
            f"- **Mode:** `{plan.mode}`",
            f"- **Outcome:** {'conflict' if plan.has_conflict else 'ready'}",
            "",
            "## Path plan",
            *path_lines,
            "",
            "## Document patch action",
            f"- **Action:** {plan.patch_action}",
            "- **Preservation:** all non-authorized content remains unchanged.",
            "",
            "## Apply result",
            f"- **Outcome:** {outcome}",
            f"- **Detail:** {result.message if result else 'No apply attempt.'}",
            "",
            "## Conflicts and limitations",
            *conflict_lines,
            "- The initializer creates no nested project governance or artifact registry and infers no science/evidence/run data.",
            "",
        ]
    )
