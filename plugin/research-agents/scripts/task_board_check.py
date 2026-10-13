"""Direct consistency checks for a local task board and task records."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys


TASK_FILENAME = re.compile(r"^(T-\d{3})-.+\.md$")
TASK_ID = re.compile(r"\bT-\d{3}\b")
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} \(([^()]+)\)$")
STATES = {"backlog", "active", "paused", "in_review", "completed", "canceled"}
# Read historical records without inventing pause reasons or review evidence.
LEGACY_STATES = {"planned", "blocked", "awaiting-confirmation"}
READINESS = {
    "ready",
    "not-ready",
    "blocked-by-task",
    "awaiting-input",
    "awaiting-confirmation",
    "high-cost-gated",
    "completed",
}
PRIORITIES = {"P0", "P1", "P2", "P3"}


@dataclass(frozen=True)
class Diagnostic:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def _field(text: str, name: str) -> str | None:
    match = re.search(rf"^- \*\*{re.escape(name)}:\*\*\s*(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def _project_timezone(root: Path) -> str | None:
    context = root / "PROJECT_CONTEXT.md"
    if not context.is_file():
        return None
    text = context.read_text(encoding="utf-8")
    match = re.search(r"^- \*\*Project timezone:\*\*\s*(.+)$", text, re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip().strip("`")
    return value if value and not value.startswith("<") else None


def _record_diagnostics(path: Path, strict: bool, project_timezone: str | None) -> list[Diagnostic]:
    text = path.read_text(encoding="utf-8")
    diagnostics: list[Diagnostic] = []
    filename_match = TASK_FILENAME.match(path.name)
    filename_id = filename_match.group(1) if filename_match else None
    declared_id = _field(text, "ID")
    if filename_id and declared_id and filename_id != declared_id.strip("`"):
        diagnostics.append(Diagnostic(str(path), f"filename ID {filename_id} differs from declared ID {declared_id}"))
    state_value = _field(text, "State")
    for name, allowed in (("State", STATES if strict else STATES | LEGACY_STATES), ("Priority", PRIORITIES)):
        value = _field(text, name)
        if value is None:
            diagnostics.append(Diagnostic(str(path), f"missing {name}"))
        elif value.strip("`") not in allowed:
            diagnostics.append(Diagnostic(str(path), f"invalid {name}: {value}"))
    readiness = _field(text, "Readiness")
    if readiness is None and (strict or state_value not in {"`completed`", "`canceled`"}):
        diagnostics.append(Diagnostic(str(path), "missing Readiness"))
    elif readiness and readiness.strip("`") not in READINESS:
        diagnostics.append(Diagnostic(str(path), f"invalid Readiness: {readiness}"))
    for name in ("Objective", "Scope", "Acceptance"):
        if _field(text, name) is None and strict:
            diagnostics.append(Diagnostic(str(path), f"missing {name}"))
    last_updated = _field(text, "Last updated")
    if strict and last_updated is None:
        diagnostics.append(Diagnostic(str(path), "missing Last updated"))
    elif last_updated and (strict or state_value not in {"`completed`", "`canceled`"}):
        timestamp = TIMESTAMP.match(last_updated)
        if not timestamp:
            diagnostics.append(Diagnostic(str(path), "Last updated must use YYYY-MM-DD HH:mm (<project timezone>)"))
        elif project_timezone and timestamp.group(1) != project_timezone:
            diagnostics.append(Diagnostic(str(path), f"Last updated must use the project timezone ({project_timezone})"))
    if strict:
        if _field(text, "Taskboard ID") is None and _field(text, "External tracker ID") is None:
            diagnostics.append(Diagnostic(str(path), "missing Taskboard ID or External tracker ID"))
        for name in ("Resume entry", "Current step", "Implementation plan version", "Next action", "Blocker"):
            if _field(text, name) is None:
                diagnostics.append(Diagnostic(str(path), f"missing {name}"))
        if "### Implementation plan" not in text:
            diagnostics.append(Diagnostic(str(path), "missing Implementation plan"))
    return diagnostics


def check_project(root: Path, strict: bool = False, require_board: bool = True) -> list[Diagnostic]:
    board_path = root / "tasks" / "TASK_BOARD.md"
    task_dir = root / "tasks"
    diagnostics: list[Diagnostic] = []
    if require_board and not board_path.is_file():
        return [Diagnostic("tasks/TASK_BOARD.md", "missing Board")]
    if not task_dir.is_dir():
        return [Diagnostic("tasks", "missing task directory")]

    project_timezone = _project_timezone(root)
    records = sorted(task_dir.glob("T-*.md"))
    record_ids: dict[str, Path] = {}
    for path in records:
        match = TASK_FILENAME.match(path.name)
        if not match:
            continue
        text = path.read_text(encoding="utf-8")
        if "- **ID:**" not in text:
            # Task implementation plans and other task-scoped documents may
            # share the T-NNN filename prefix without being task records.
            continue
        task_id = match.group(1)
        if task_id in record_ids:
            diagnostics.append(Diagnostic(str(path), f"duplicate task record ID {task_id}"))
        record_ids[task_id] = path
        diagnostics.extend(_record_diagnostics(path, strict, project_timezone))

    if not board_path.is_file():
        return diagnostics

    board_text = board_path.read_text(encoding="utf-8")
    board_ids = set(TASK_ID.findall(board_text))
    for task_id in sorted(board_ids - set(record_ids)):
        diagnostics.append(Diagnostic("tasks/TASK_BOARD.md", f"Board references unregistered task {task_id}"))
    for task_id, path in sorted(record_ids.items()):
        state = _field(path.read_text(encoding="utf-8"), "State")
        if task_id not in board_ids and state not in {"`completed`", "`canceled`"}:
            diagnostics.append(Diagnostic(str(path), f"nonterminal task is not registered on Board: {task_id}"))
    if "main_line" not in board_text.lower() and "Main line" not in board_text:
        diagnostics.append(Diagnostic("tasks/TASK_BOARD.md", "missing main_line control entry"))
    if "current_line" not in board_text.lower() and "Current line" not in board_text:
        diagnostics.append(Diagnostic("tasks/TASK_BOARD.md", "missing current_line control entry"))
    return diagnostics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--strict", action="store_true", help="require the full v1 task-record fields")
    args = parser.parse_args(argv)
    diagnostics = check_project(args.root.resolve(), strict=args.strict)
    for diagnostic in diagnostics:
        print(diagnostic, file=sys.stderr)
    if diagnostics:
        print(f"task board check failed: {len(diagnostics)} diagnostic(s)", file=sys.stderr)
        return 1
    print("task board check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
