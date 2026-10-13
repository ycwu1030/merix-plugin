"""Command-line boundary for deterministic initializer plans."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys
from typing import Sequence

from .root_project import apply_root_plan, build_root_plan, render_root_report
from .work_package import apply_work_package_plan, build_work_package_plan, render_work_package_report
from .baseline import apply_baseline_plan, build_baseline_plan, inspect_baseline, write_plan


DEFAULT_SOURCE_ROOT = Path(__file__).resolve().parents[2] / "assets" / "baseline"


def _parse_passive_fields(values: Sequence[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for value in values:
        label, separator, content = value.partition("=")
        if not separator or not label:
            raise argparse.ArgumentTypeError("passive fields must use LABEL=VALUE")
        if label in parsed:
            raise argparse.ArgumentTypeError(f"duplicate passive field: {label}")
        parsed[label] = content
    return parsed


def _root_command(arguments: argparse.Namespace) -> int:
    plan = build_root_plan(
        Path(arguments.source),
        Path(arguments.target),
        optional_dirs=arguments.optional_dir,
        date=arguments.date,
        project_name=arguments.project_name,
        background=arguments.background,
        task_description=arguments.task_description,
    )
    result = apply_root_plan(
        plan,
        apply=arguments.apply,
        confirmation_plan_id=arguments.confirm_plan,
    )
    print(render_root_report(plan, result))
    return 2 if result.outcome in ("conflict", "failed-rolled-back", "recovery-required") else 0


def _work_package_command(arguments: argparse.Namespace) -> int:
    plan = build_work_package_plan(
        Path(arguments.project),
        task_id=arguments.task,
        topic=arguments.topic,
        mode=arguments.mode,
        modules=arguments.module,
        purpose=arguments.purpose,
        date=arguments.date,
        passive_updates=_parse_passive_fields(arguments.passive_field),
        work_package_id=arguments.id,
    )
    result = apply_work_package_plan(plan, apply=arguments.apply)
    print(render_work_package_report(plan, result))
    return 2 if result.outcome == "conflict" else 0


def _read_decisions(path: str | None) -> dict[str, str]:
    if not path:
        return {}
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(value, dict) and isinstance(value.get("decisions"), dict):
        value = value["decisions"]
    if not isinstance(value, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
        raise ValueError("decisions file must contain a path-to-choice JSON object")
    return value


def _baseline_command(arguments: argparse.Namespace) -> int:
    source = Path(arguments.source)
    target = Path(arguments.project)
    if arguments.baseline_command == "inspect":
        result = inspect_baseline(source, target)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["outcome"] in {"ok", "needs_decision"} else 3
    if arguments.baseline_command == "plan":
        plan = build_baseline_plan(source, target, decisions=_read_decisions(arguments.decisions))
        output = write_plan(plan, Path(arguments.output) if arguments.output else None)
        result = dict(plan.payload)
        result["planFile"] = str(output)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if plan.outcome == "ready" else 4
    result = apply_baseline_plan(source, target, Path(arguments.plan_file), arguments.confirm_plan)
    print(json.dumps(result, indent=2, sort_keys=True))
    return {"applied": 0, "plan_not_found": 2, "plan_id_mismatch": 4,
            "stale_plan": 4, "decision_missing": 4, "failed-rolled-back": 5,
            "recovery-required": 6}.get(result.get("outcome"), 3)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="research_init",
        description="Plan and apply a bounded research-project or work-package initialization.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    root = commands.add_parser("root", help="Plan or initialize a project root.")
    root.add_argument("--source", default=str(DEFAULT_SOURCE_ROOT), help="Release-form baseline source root.")
    root.add_argument("--target", required=True, help="Target project directory.")
    root.add_argument("--project-name", help="Project display name (defaults to the target directory name).")
    root.add_argument("--background", help="Brief project background prepared by the caller; defaults to generic guidance.")
    root.add_argument("--task-description", help="Brief initial task description; does not create a task record or start work.")
    root.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Record date in YYYY-MM-DD form (defaults to today).",
    )
    root.add_argument(
        "--optional-dir",
        action="append",
        default=[],
        metavar="NAME",
        help="Legacy compatibility input; all standard root/reference directories are always planned.",
    )
    root.add_argument("--apply", action="store_true", help="Apply a conflict-free plan.")
    root.add_argument(
        "--confirm-plan",
        help="Exact plan ID required for recognized extend and bounded adoption writes.",
    )
    root.set_defaults(handler=_root_command)

    package = commands.add_parser("work-package", help="Plan or initialize one root-governed work package.")
    package.add_argument("--project", required=True, help="Initialized project root containing workspaces/ and tasks/.")
    package.add_argument("--task", required=True, help="Authoritative root task ID (T-NNN).")
    package.add_argument("--id", help="Explicit unique work package ID (defaults to WP- plus the task suffix).")
    package.add_argument("--topic", required=True, help="Lowercase hyphenated path-safe topic slug.")
    package.add_argument("--mode", choices=("minimal", "full", "extend"), required=True)
    package.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="Record date in YYYY-MM-DD form (defaults to today).",
    )
    package.add_argument("--module", action="append", default=[], metavar="NAME", help="Explicit work-package module; may be repeated for extend.")
    package.add_argument("--purpose", required=True, help="Grounded one-line purpose supplied by the caller.")
    package.add_argument(
        "--passive-field",
        action="append",
        default=[],
        metavar="LABEL=VALUE",
        help="Explicit whitelisted one-line WORK_PACKAGE.md field update; may be repeated.",
    )
    package.add_argument("--apply", action="store_true", help="Apply a conflict-free plan.")
    package.set_defaults(handler=_work_package_command)

    baseline = commands.add_parser("baseline", help="Inspect, plan, or apply an existing-project baseline update.")
    baseline_commands = baseline.add_subparsers(dest="baseline_command", required=True)
    for name in ("inspect", "plan"):
        command = baseline_commands.add_parser(name)
        command.add_argument("--project", required=True, help="Initialized research-project root.")
        command.add_argument("--source", default=str(DEFAULT_SOURCE_ROOT), help="Current canonical Plugin baseline.")
        command.add_argument("--json", action="store_true", help="Emit JSON output.")
        if name == "plan":
            command.add_argument("--decisions", help="Temporary JSON path-to-choice decision file.")
            command.add_argument("--output", help="Temporary plan output path.")
        command.set_defaults(handler=_baseline_command)
    apply = baseline_commands.add_parser("apply")
    apply.add_argument("--project", required=True, help="Initialized research-project root.")
    apply.add_argument("--source", default=str(DEFAULT_SOURCE_ROOT), help="Current canonical Plugin baseline.")
    apply.add_argument("--plan-file", required=True, help="Temporary plan JSON produced by baseline plan.")
    apply.add_argument("--confirm-plan", required=True, help="Exact planId from the reviewed plan.")
    apply.add_argument("--json", action="store_true", help="Emit JSON output.")
    apply.set_defaults(handler=_baseline_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        return arguments.handler(arguments)
    except (ValueError, OSError) as error:
        parser.error(str(error))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
