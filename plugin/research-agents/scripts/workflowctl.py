"""Run bounded checks and reports for an initialized research project."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys

from relationctl import load_registry, validate_registry
from workflow_records import WorkflowError, fields, local_path, task_show, text_file


@dataclass(frozen=True)
class Diagnostic:
    code: str
    path: str
    message: str
    severity: str = "error"
    entity: str | None = None

    @property
    def is_error(self) -> bool:
        return self.severity == "error"

    def as_dict(self) -> dict[str, str]:
        result = {
            "code": self.code,
            "path": self.path,
            "message": self.message,
            "severity": self.severity,
        }
        if self.entity is not None:
            result["entity"] = self.entity
        return result

    def __str__(self) -> str:
        suffix = f" [{self.severity}]" if self.severity != "error" else ""
        return f"{self.code} {self.path}: {self.message}{suffix}"


@dataclass(frozen=True)
class Task:
    task_id: str
    path: Path
    state: str | None
    readiness: str | None
    external_id: str | None
    depends_on: tuple[str, ...]


FIELD = re.compile(r"^- \*\*(.+?):\*\*\s*(.+)$", re.MULTILINE)
TASK_ID = re.compile(r"\bT-\d{3}\b")
DEPENDENCY_GRAPH_ERRORS = {
    'RELATION_INVALID', 'RELATION_ID_INVALID', 'RELATION_TARGET_MISSING',
    'RELATION_TARGET_DUPLICATE', 'RELATION_KIND_INVALID', 'RELATION_BASIS_INVALID',
    'DEPENDENCY_CYCLE', 'DEPENDENCY_MISSING_TARGET', 'DEPENDENCY_AUTHORITY_MISSING',
    'DEPENDENCY_VIEW_DRIFT', 'TASK_RECORD_INVALID', 'VIEW_DRIFT',
    'VIEW_DUPLICATE_ROW', 'VIEW_UNKNOWN_TASK',
}


def _relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _fields(text: str) -> dict[str, str]:
    return fields(text)


def load_tasks(root: Path) -> tuple[dict[str, Task], list[Diagnostic]]:
    tasks: dict[str, Task] = {}
    diagnostics: list[Diagnostic] = []
    for path in sorted((root / "tasks").glob("T-*.md")):
        match = re.match(r"^(T-\d{3})-.+\.md$", path.name)
        if not match:
            continue
        fields = _fields(text_file(root, path))
        if "id" not in fields:
            continue
        task_id = fields["id"]
        if not re.fullmatch(r'T-\d{3}', task_id) or task_id != match.group(1):
            diagnostics.append(Diagnostic('TASK_RECORD_INVALID', _relative(root, path), 'declared ID and filename disagree', entity=task_id))
            continue
        if task_id in tasks:
            diagnostics.append(Diagnostic("TASK_RECORD_INVALID", _relative(root, path), f"duplicate task ID {task_id}", entity=task_id))
            continue
        dependencies = tuple(dict.fromkeys(TASK_ID.findall(fields.get("depends on", ""))))
        external_id = fields.get("external tracker id") or fields.get("taskboard id") or fields.get("taskboard")
        tasks[task_id] = Task(
            task_id=task_id,
            path=path,
            state=fields.get("state"),
            readiness=fields.get("readiness"),
            external_id=external_id if external_id and external_id != "—" else None,
            depends_on=dependencies,
        )
    return tasks, diagnostics


def _board_dependencies(root: Path) -> dict[str, tuple[str, ...]]:
    path = root / "tasks" / "TASK_BOARD.md"
    if not path.is_file():
        return {}
    rows: dict[str, tuple[str, ...]] = {}
    header: list[str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if header is None:
            if "task_id" in cells:
                header = [cell.lower() for cell in cells]
            continue
        if set(cells) <= {"---", ""} or len(cells) != len(header):
            continue
        row = dict(zip(header, cells))
        if row.get("task_id"):
            rows[row["task_id"]] = tuple(dict.fromkeys(TASK_ID.findall(row.get("depends_on", ""))))
    return rows


def _registry_edges(root: Path) -> tuple[list[dict], list[Diagnostic], bool]:
    path = local_path(root, "relations/RELATIONS.yaml")
    if not path.is_file():
        return [], [], False
    try:
        data = load_registry(path)
    except ValueError as exc:
        return [], [Diagnostic("RELATION_INVALID", _relative(root, path), str(exc))], True
    diagnostics = [Diagnostic("RELATION_INVALID", _relative(root, path), error) for error in validate_registry(data)]
    items = data.get('relations', [])
    safe = [item for item in items if isinstance(item, dict) and all(isinstance(item.get(key), str) for key in ['source', 'target', 'relation'])] if isinstance(items, list) else []
    edges = [item for item in safe if item['relation'] == 'depends_on']
    if not diagnostics:
        from workflow_relations import target_errors
        diagnostics.extend(Diagnostic(**item) for item in target_errors(root, {'relations': edges}))
    return edges, diagnostics, True


def _cycles(edges: list[tuple[str, str]]) -> list[list[str]]:
    graph: dict[str, list[str]] = {}
    for source, target in edges:
        graph.setdefault(source, []).append(target)
    state: dict[str, int] = {}
    stack: list[str] = []
    found: list[list[str]] = []

    def visit(node: str) -> None:
        state[node] = 1
        stack.append(node)
        for target in graph.get(node, []):
            if state.get(target, 0) == 0:
                visit(target)
            elif state.get(target) == 1:
                start = stack.index(target)
                found.append(stack[start:].copy())
        stack.pop()
        state[node] = 2

    for node in graph:
        if state.get(node, 0) == 0:
            visit(node)
    unique: dict[tuple[str, ...], list[str]] = {}
    for cycle in found:
        rotations = [tuple(cycle[i:] + cycle[:i]) for i in range(len(cycle))]
        unique[min(rotations)] = cycle
    return list(unique.values())


def _registry_dependencies(edges: list[dict]) -> list[tuple[str, str]]:
    return [(edge.get("source"), edge.get("target")) for edge in edges]


def dependency_diagnostics(root: Path, external_status: dict | None = None) -> tuple[list[Diagnostic], dict[str, Task]]:
    from workflow_records import projection_diagnostics
    tasks, diagnostics = load_tasks(root)
    diagnostics.extend(Diagnostic(**item) for item in projection_diagnostics(root))
    registry_edges, relation_diagnostics, registry_configured = _registry_edges(root)
    diagnostics.extend(relation_diagnostics)
    graph_edges = _registry_dependencies(registry_edges)

    if not registry_configured:
        declared = {dependency for task in tasks.values() for dependency in task.depends_on}
        declared.update(dependency for values in _board_dependencies(root).values() for dependency in values)
        if declared:
            diagnostics.append(
                Diagnostic(
                    "DEPENDENCY_AUTHORITY_MISSING",
                    "relations/RELATIONS.yaml",
                    "task or Board dependency views exist but the canonical relation registry is not configured",
                )
            )
        else:
            diagnostics.append(
                Diagnostic(
                    "DEPENDENCY_NOT_CONFIGURED",
                    "relations/RELATIONS.yaml",
                    "optional dependency registry is not configured",
                    severity="info",
                )
            )

    seen: set[tuple[str, str]] = set()
    for source, target in graph_edges:
        pair = (source, target)
        if pair in seen:
            diagnostics.append(Diagnostic("DEPENDENCY_DUPLICATE", "relations/RELATIONS.yaml", f"duplicate depends_on edge {source} -> {target}"))
        seen.add(pair)
        if source == target:
            diagnostics.append(Diagnostic("DEPENDENCY_SELF_RELATION", "relations/RELATIONS.yaml", f"self dependency {source}", entity=source))
        if source not in tasks or target not in tasks:
            diagnostics.append(Diagnostic("DEPENDENCY_MISSING_TARGET", "relations/RELATIONS.yaml", f"unknown task in dependency {source} -> {target}"))
    for cycle in _cycles(graph_edges):
        diagnostics.append(Diagnostic("DEPENDENCY_CYCLE", "relations/RELATIONS.yaml", "cycle: " + " -> ".join(cycle + [cycle[0]])))

    for source, target in graph_edges:
        prerequisite = tasks.get(target)
        if prerequisite is None:
            continue
        if prerequisite.state == "canceled":
            diagnostics.append(Diagnostic("DEPENDENCY_CANCELED_PREREQUISITE", _relative(root, prerequisite.path), f"{source} depends on canceled task {target}", entity=target))
        elif prerequisite.state != "completed" or prerequisite.readiness != "completed":
            diagnostics.append(Diagnostic("DEPENDENCY_NOT_ELIGIBLE", _relative(root, prerequisite.path), f"{target} must be completed with readiness completed before {source} can run", entity=target))
        elif prerequisite.external_id and (external_status or {}).get(prerequisite.external_id) != 'done':
            diagnostics.append(
                Diagnostic(
                    "DEPENDENCY_EXTERNAL_NOT_DONE" if (external_status or {}).get(prerequisite.external_id) else "DEPENDENCY_LIVE_STATUS_UNVERIFIED",
                    _relative(root, prerequisite.path),
                    f"live external status for {target} ({prerequisite.external_id}): {(external_status or {}).get(prerequisite.external_id, 'not checked')}",
                    entity=target,
                )
            )

    if registry_configured:
        board = _board_dependencies(root)
        registry_deps: dict[str, tuple[str, ...]] = {}
        for source, target in graph_edges:
            registry_deps[source] = tuple(sorted(set(registry_deps.get(source, ())) | {target}))
        record_deps = {task_id: task.depends_on for task_id, task in tasks.items()}
        for task_id in set(record_deps) | set(board) | set(registry_deps):
            expected = tuple(sorted(registry_deps.get(task_id, ())))
            views = [("task record", record_deps.get(task_id, ()))]
            if task_id in board:
                views.append(("Board", board[task_id]))
            for label, view in views:
                if tuple(sorted(view)) != expected:
                    diagnostics.append(
                        Diagnostic(
                            "DEPENDENCY_VIEW_DRIFT",
                            task_id,
                            f"{label} declares {list(view)}, registry declares {list(expected)}",
                            entity=task_id,
                        )
                    )
    return diagnostics, tasks


def _result(diagnostics: list[Diagnostic], as_json: bool) -> int:
    payload = {
        "schema_version": 1,
        "ok": not any(item.is_error for item in diagnostics),
        "diagnostics": [item.as_dict() for item in diagnostics],
    }
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for diagnostic in diagnostics:
            print(diagnostic, file=sys.stderr if diagnostic.is_error else sys.stdout)
        if not diagnostics:
            print("check passed")
    return 1 if any(item.is_error for item in diagnostics) else 0


def focus(root: Path, task_id: str | None = None, external_status: dict | None = None) -> dict:
    from workflow_handoff import handoff
    diagnostics, tasks = dependency_diagnostics(root, external_status)
    registry_edges, _, registry_configured = _registry_edges(root)
    board_dependencies = _board_dependencies(root)
    dependencies: dict[str, tuple[str, ...]] = {}
    for source, target in _registry_dependencies(registry_edges):
        dependencies[source] = tuple(sorted(set(dependencies.get(source, ())) | {target}))

    def explanations(task_id: str) -> list[str]:
        # One witness path per reachable prerequisite keeps shared DAGs bounded.
        pending = [[task_id]]
        seen = {task_id}
        result: list[str] = []
        while pending:
            path = pending.pop(0)
            for dependency in dependencies.get(path[-1], ()):
                if dependency in seen:
                    continue
                seen.add(dependency)
                chain = path + [dependency]
                result.append(" -> ".join(chain))
                pending.append(chain)
        return result

    selected_id = task_id
    eligible = []
    for task_id, task in sorted(tasks.items()):
        if task.state not in {"backlog", "planned", "active", "paused"} or task.readiness != "ready":
            continue
        values = _fields(text_file(root, task.path))
        if values.get('blocker') not in {None, '', '—'}:
            continue
        if not registry_configured and (task.depends_on or board_dependencies.get(task_id)):
            continue
        direct_dependencies = dependencies.get(task_id, ()) if registry_configured else ()
        prerequisites = [tasks.get(dep) for dep in direct_dependencies]
        if all(item and item.state == "completed" and item.readiness == "completed" and (not item.external_id or (external_status or {}).get(item.external_id) == 'done') for item in prerequisites):
            eligible.append(
                {
                    "task_id": task_id,
                    "detail": _relative(root, task.path),
                    "next_action": values.get('next action'),
                    "resume_entry": values.get('resume entry'),
                    "direct_dependencies": list(direct_dependencies),
                    "dependency_explanations": explanations(task_id) or ["no direct dependencies"],
                }
            )
    control = {}
    board = local_path(root, 'tasks/TASK_BOARD.md')
    if board.is_file():
        control = _fields(text_file(root, board))
    declared = control.get('current task')
    if not selected_id and declared and declared.casefold() not in {'—', 'none'}:
        matches = set(TASK_ID.findall(declared))
        if len(matches) != 1:
            raise WorkflowError('FOCUS_SELECTION_INVALID', 'Current task must identify one task; selection is not inferred', 'tasks/TASK_BOARD.md')
        selected_id = matches.pop()
    current = {'main_line': control.get('main line'), 'current_line': control.get('current line'),
               'current_milestone': control.get('current milestone'), 'task_id': selected_id,
               'next_action': None, 'resume_entry': None, 'detail': None,
               'state': None, 'readiness': None, 'gated': None}
    if selected_id:
        report = task_show(root, selected_id)
        context = handoff(root, selected_id, report)
        for key in ['next_action', 'resume_entry', 'current_result', 'blocker', 'current_step',
                    'state', 'readiness', 'gated', 'allowed_scope']:
            current[key] = context[key]
        current['detail'] = report['detail']
        diagnostics.extend(Diagnostic(**item) for item in context['diagnostics'])
        if context['diagnostics']:
            eligible = [item for item in eligible if item['task_id'] != selected_id]
    invalid = any(item.code in DEPENDENCY_GRAPH_ERRORS for item in diagnostics)
    if invalid:
        eligible = []
    return {'schema_version': 1, 'ok': not any(item.is_error for item in diagnostics),
            'diagnostics': [item.as_dict() for item in diagnostics], 'current_focus': current,
            'eligible_tasks': eligible,
            'non_claim': 'Candidate and navigation reports do not authorize execution or certify restored sessions.'}


def emit(payload: dict, as_json: bool, root: Path | None = None) -> int:
    from workflow_relations import entity_kind
    diagnostics = payload.setdefault('diagnostics', [])
    for item in diagnostics:
        item.setdefault('severity', 'error')
        code = item['code']
        category = 'invalid-local-data'
        if item['severity'] != 'error':
            category = 'information'
        elif code in {'WRITE_CONFLICT', 'SYNC_VERSION_CONFLICT', 'SYNC_LOCAL_CONFLICT'}:
            category = 'conflict'
        elif code in {'SYNC_SERVICE_UNAVAILABLE', 'SYNC_API_ERROR', 'SYNC_RESPONSE_INVALID', 'DEPENDENCY_LIVE_STATUS_UNVERIFIED'}:
            category = 'external-evidence-unavailable'
        elif any(word in code for word in ['REQUIRED', 'NOT_CONFIGURED', 'ATTRIBUTION_MISSING', 'BINDING_INCOMPLETE', 'AUTHORITY_MISSING', 'TIMEZONE_MISSING']):
            category = 'required-input'
        item.setdefault('failure_class', category)
        path = item.get('path', '')
        if entity_kind(path):
            item.setdefault('entity', path)
            item['path'] = 'tasks' if path.startswith('T-') else 'relations/RELATIONS.yaml'
        elif root and Path(path).is_absolute():
            try:
                item['path'] = Path(path).relative_to(root).as_posix()
            except ValueError:
                item['path'] = '<input>'
        elif '..' in Path(path).parts:
            item['path'] = '<input>'
    payload['schema_version'] = 1
    payload['ok'] = not any(item['severity'] == 'error' for item in diagnostics)
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for item in diagnostics:
            print(f"{item['code']} {item['path']}: {item['message']}", file=sys.stderr if item['severity'] == 'error' else sys.stdout)
        content = {key: value for key, value in payload.items() if key not in {'diagnostics', 'schema_version', 'ok'}}
        if content:
            print(json.dumps(content, indent=2, ensure_ascii=False))
        elif payload['ok']:
            print('check passed')
    return 0 if payload['ok'] else 1


def build_parser() -> argparse.ArgumentParser:
    from datetime import date
    from task_board_check import READINESS, PRIORITIES
    from relationctl import RELATION_TYPES
    from workflow_task_lifecycle import ACTION_EDGES
    from task_board_check import STATES, LEGACY_STATES
    from workflow_artifact_cli import CORE, configure_parser
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--json', action='store_true')
    groups = parser.add_subparsers(dest='command', required=True)
    catalog = {'project': ['check'], 'task': ['check', 'list', 'show', 'new', 'update', 'start', 'pause', 'resume', 'submit', 'revise', 'complete', 'cancel', 'reopen', 'refresh', 'sync'],
               'relation': ['check', 'validate', 'target-check', 'show', 'path', 'add'],
               'dependency': ['check'], 'focus': ['show'], 'view': ['refresh'],
               'handoff': ['check', 'report'], 'sync': ['external-readback'],
               'work-package': ['preflight', 'create', 'report'], 'run': ['check', 'new', 'submit', 'status', 'monitor', 'stop', 'retry', 'schedule'],
               'evidence': ['list', 'check'], 'formula': ['check', 'allocate'],
               'artifact': [*CORE, 'register', 'show', 'references', 'archive', 'reconcile', 'verify', 'recovery-complete']}
    for name, actions in catalog.items():
        group = groups.add_parser(name)
        group.add_argument('--root', type=Path, default=argparse.SUPPRESS)
        group.add_argument('--json', action='store_true', default=argparse.SUPPRESS)
        leaves = group.add_subparsers(dest='action', required=True,
                                      **({'metavar': '{new,list,update,store,check,cleanup}'} if name == 'artifact' else {}))
        for action in actions:
            command = leaves.add_parser(action)
            command.add_argument('--root', type=Path, default=argparse.SUPPRESS)
            command.add_argument('--json', action='store_true', default=argparse.SUPPRESS)
            if name == 'artifact':
                configure_parser(command, action)
                continue
            if name == 'task' and action in set(ACTION_EDGES) | {'refresh', 'sync'} or (name, action) in {('task', 'new'), ('task', 'update'), ('relation', 'add'), ('view', 'refresh'), ('sync', 'external-readback'), ('work-package', 'create'), ('run', 'new')}:
                command.add_argument('--apply', action='store_true')
            if name == 'task' and action in set(ACTION_EDGES) | {'show', 'update', 'sync'} or name == 'handoff':
                command.add_argument('task_id')
            if name == 'task' and action == 'check':
                command.add_argument('task_id', nargs='?')
                command.add_argument('--strict', action='store_true')
                command.add_argument('--area', choices=['record', 'handoff', 'lifecycle', 'review', 'relations', 'dependencies', 'views', 'all'], default='all')
            if name == 'task' and action == 'list':
                command.add_argument('task_id', nargs='?')
                command.add_argument('--view', choices=['full', 'snapshot', 'plan', 'history', 'evidence', 'context', 'handoff', 'review'])
                command.add_argument('--state', choices=sorted(STATES | LEGACY_STATES))
                command.add_argument('--readiness', choices=sorted(READINESS))
                command.add_argument('--priority', choices=sorted(PRIORITIES))
                command.add_argument('--query')
                command.add_argument('--eligible', action='store_true')
            if name == 'task' and action == 'refresh':
                command.add_argument('task_id', nargs='?')
                command.add_argument('--all', action='store_true')
            if name == 'task' and action in ACTION_EDGES:
                command.add_argument('--reason', required=True)
                command.add_argument('--input', type=Path)
                command.add_argument('--if-hash')
                if action in {'start', 'resume', 'revise', 'reopen'}:
                    command.add_argument('--taskctl', type=Path, help='Explicit executable for live prerequisite checks.')
                if action == 'pause':
                    command.add_argument('--resume-when', required=True)
                if action == 'revise':
                    command.add_argument('--feedback-ref', required=True)
                if action == 'complete':
                    command.add_argument('--review-ref', required=True)
                    command.add_argument('--review-version', required=True)
            if name == 'task' and action == 'new':
                for field in ['task-id', 'topic', 'title', 'objective', 'scope', 'acceptance', 'deliverable', 'next-action']:
                    command.add_argument('--' + field, required=True)
                command.add_argument('--exclusions', default='Not applicable — no additional exclusions supplied')
                command.add_argument('--readiness', choices=sorted(READINESS - {'completed'}), default='not-ready')
                command.add_argument('--priority', choices=sorted(PRIORITIES), required=True)
                command.add_argument('--external-id')
                command.add_argument('--depends-on', action='append', default=[])
                command.add_argument('--contract-applicability', choices=['required', 'not applicable'], required=True)
                command.add_argument('--contract-reason', help='Required explanation when the comparison Contract is not applicable.')
            if name == 'task' and action == 'update':
                command.add_argument('--input', type=Path)
                command.add_argument('--set', action='append', default=[], metavar='FIELD=VALUE')
                command.add_argument('--depends-on', action='append', default=None)
                command.add_argument('--clear-dependencies', action='store_true')
                command.add_argument('--reason', required=True)
                command.add_argument('--if-hash')
            if name == 'relation' and action == 'show':
                command.add_argument('entity')
            if name == 'relation' and action in {'add', 'path'}:
                command.add_argument('source')
                if action == 'add':
                    command.add_argument('relation', choices=sorted(RELATION_TYPES))
                    command.add_argument('--basis', required=True)
                    command.add_argument('--reason', required=True)
                    command.add_argument('--date', default=date.today().isoformat())
                command.add_argument('target')
            if name in {'focus', 'view'}:
                command.add_argument('--task', dest='task_id')
            if name in {'focus', 'dependency', 'sync'} or name == 'task' and action == 'sync':
                command.add_argument('--taskctl', type=Path, help='Explicit optional Taskboard executable; no endpoint guessing.')
            if name == 'sync' or name == 'task' and action == 'sync':
                if name == 'sync':
                    command.add_argument('--task', dest='task_id', required=True)
                command.add_argument('--thread-id')
                for option in ['binding-thread-id', 'binding-codex-project-id', 'binding-codex-project-kind', 'binding-codex-host-id', 'binding-workspace-path']:
                    command.add_argument('--' + option)
                command.add_argument('--status', choices=['backlog', 'todo', 'in_progress', 'in_review', 'blocked', 'canceled', 'done'])
                command.add_argument('--accept-completion', action='store_true')
                command.add_argument('--sync-relations', action='store_true')
                command.add_argument('--after-comments')
                command.add_argument('--after-attachments')
                command.add_argument('--comment-file', type=Path, help='Explicit local outcome/verification comment; required when moving into review.')
            if name == 'work-package':
                command.add_argument('--task', required=True)
                command.add_argument('--id', help='Explicit unique WP-NNN; required if the default task-derived ID already exists.')
                command.add_argument('--topic', required=True)
                command.add_argument('--mode', choices=['minimal', 'full', 'extend'], default='minimal')
                command.add_argument('--purpose')
                command.add_argument('--module', action='append', default=[])
                command.add_argument('--date', default=date.today().isoformat())
            if name == 'run':
                if action == 'new':
                    command.add_argument('--record-file', type=Path, required=True, help='JSON mapping of explicit template fields.')
                    command.add_argument('--id', dest='entity_id', required=True)
                    command.add_argument('--topic', required=True)
                    command.add_argument('--work-package', required=True, help='Project-relative leaf directory with enabled runs/.')
                elif action == 'check':
                    command.add_argument('--path', required=True)
                else:
                    command.add_argument('--path', required=True)
                    if action in {'submit'}:
                        command.add_argument('--command', dest='executable_command', required=True)
                        command.add_argument('--cwd')
                        command.add_argument('--stdout')
                        command.add_argument('--stderr')
                        command.add_argument('--progress-file')
                    if action == 'retry':
                        command.add_argument('--cwd')
                    if action == 'schedule':
                        command.add_argument('--interval', type=int, default=30)
                    if action in {'submit', 'monitor', 'stop', 'retry'}:
                        command.add_argument('--apply', action='store_true')
                    if action == 'schedule':
                        command.add_argument('--apply', action='store_true')
            if name == 'evidence':
                command.add_argument('--kind', choices=['comparison', 'derivation', 'source-audit', 'literature', 'formula-index'])
                if action == 'check':
                    command.add_argument('--path')
            if name == 'formula':
                if action == 'allocate':
                    command.add_argument('--id', dest='formula_id')
                    command.add_argument('--description', required=True)
                    command.add_argument('--location', required=True)
                    command.add_argument('--basis', required=True)
                    command.add_argument('--status', default='active')
                    command.add_argument('--apply', action='store_true')
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == 'project':
            from research_init.catalog import ROOT_REQUIRED_DIRS, ROOT_STANDARD_EXTRA_DIRS
            required = {'README.md': 'file', 'AGENTS.md': 'file', 'RESEARCH_WORKFLOW.md': 'file', 'PROJECT_CONTEXT.md': 'file',
                        'PROJECT_STATUS.md': 'file', 'BASELINE_MANIFEST.md': 'file'}
            required['templates/'] = 'directory'
            required.update({f'templates/{name}': 'file' for name in ('TASK.md', 'RUN.md', 'ARTIFACT.md', 'WORK_PACKAGE.md')})
            required.update({directory: 'directory' for directory in (*ROOT_REQUIRED_DIRS, *ROOT_STANDARD_EXTRA_DIRS)})
            diagnostics = []
            for path, kind in required.items():
                target = local_path(root, path)
                if not target.exists():
                    diagnostics.append({'code': 'PROJECT_MISSING_PATH', 'path': path, 'message': f'missing required {kind}'})
                elif not (target.is_file() if kind == 'file' else target.is_dir()):
                    diagnostics.append({'code': 'PROJECT_WRONG_KIND', 'path': path, 'message': f'expected required {kind}'})
                elif kind == 'file' and not target.read_text(encoding='utf-8').strip():
                    diagnostics.append({'code': 'PROJECT_EMPTY_FILE', 'path': path, 'message': 'required file is empty'})
            payload = {'diagnostics': diagnostics}
        elif args.command == 'task':
            from workflow_records import task_new, task_update
            from workflow_task_lifecycle import ACTION_EDGES, lifecycle, task_check, task_list
            if args.action == 'check':
                payload = task_check(root, args)
            elif args.action == 'list':
                payload = task_list(root, args)
            elif args.action in ACTION_EDGES:
                payload = lifecycle(root, args)
            elif args.action == 'refresh':
                from workflow_records import view_refresh
                if bool(args.task_id) == args.all:
                    raise WorkflowError('INPUT_INVALID', 'refresh requires one task ID or --all')
                payload = view_refresh(root, args.apply, args.task_id)
            elif args.action == 'sync':
                from workflow_sync import synchronize
                payload = synchronize(root, args)
            elif args.action == 'show':
                payload = task_show(root, args.task_id)
            elif args.action == 'new':
                payload = task_new(root, args)
            else:
                if args.clear_dependencies:
                    if args.depends_on:
                        raise WorkflowError('INPUT_INVALID', '--clear-dependencies conflicts with --depends-on')
                    args.depends_on = []
                payload = task_update(root, args)
        elif args.command == 'relation':
            from workflow_relations import relation_operation
            payload = relation_operation(root, args)
            if not local_path(root, 'relations/RELATIONS.yaml').exists() and args.action in {'check', 'validate', 'target-check'}:
                payload['diagnostics'].append({'code': 'RELATION_NOT_CONFIGURED', 'path': 'relations/RELATIONS.yaml', 'message': 'optional registry is not configured', 'severity': 'info'})
        elif args.command in {'focus', 'dependency'}:
            external = None
            external_errors = []
            if args.taskctl:
                from workflow_sync import live_statuses
                external, external_errors = live_statuses(root, args.taskctl)
            if args.command == 'focus':
                payload = focus(root, args.task_id, external)
            else:
                diagnostics, _ = dependency_diagnostics(root, external)
                payload = {'diagnostics': [item.as_dict() for item in diagnostics]}
            payload['diagnostics'].extend(external_errors)
        elif args.command == 'view':
            from workflow_records import view_refresh
            payload = view_refresh(root, args.apply, args.task_id)
        elif args.command == 'handoff':
            from workflow_handoff import handoff
            payload = handoff(root, args.task_id)
        elif args.command == 'sync':
            from workflow_sync import synchronize
            payload = synchronize(root, args)
        elif args.command == 'run' and args.action in {'submit', 'status', 'monitor', 'stop', 'retry', 'schedule'}:
            from workflow_run import run_operation
            payload = run_operation(root, args)
        elif args.command in {'evidence', 'formula'}:
            from workflow_evidence import evidence_operation
            payload = evidence_operation(root, args)
        else:
            from workflow_domain import domain_operation
            payload = domain_operation(root, args)
        return emit(payload, args.json, root)
    except WorkflowError as error:
        return emit({'diagnostics': [{'code': error.code, 'path': error.path, 'message': str(error)}]}, args.json, root)
    except (OSError, ValueError) as error:
        return emit({'diagnostics': [{'code': 'INPUT_INVALID', 'path': '', 'message': str(error)}]}, args.json, root)


if __name__ == '__main__':
    raise SystemExit(main())
