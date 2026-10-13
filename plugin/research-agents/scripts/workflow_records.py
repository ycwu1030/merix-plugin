"""Project-local records, safe file plans, and maintained Markdown views."""
from __future__ import annotations

from datetime import datetime
import hashlib
import difflib
import json
import os
from pathlib import Path
import re
import tempfile
from zoneinfo import ZoneInfo

TICK = chr(96)
FIELD = re.compile(r'^- \*\*(.+?):\*\*[ \t]*([^\n]*)$', re.MULTILINE)
TASK_ID = re.compile(r'^T-\d{3}$')
SLUG = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')


class WorkflowError(ValueError):
    def __init__(self, code: str, message: str, path: str = ''):
        super().__init__(message)
        self.code, self.path = code, path


def fields(text: str) -> dict[str, str]:
    result = {}
    for name, value in FIELD.findall(text):
        value = value.strip()
        if value.startswith(TICK) and value.endswith(TICK) and value.count(TICK) == 2:
            value = value[1:-1]
        result.setdefault(name.lower(), value)
    return result


def local_path(root: Path, value: str | Path) -> Path:
    original_root = root.absolute()
    root = root.resolve()
    path = Path(value)
    if path.is_absolute() and path.is_relative_to(original_root):
        path = root / path.relative_to(original_root)
    path = path if path.is_absolute() else root / path
    try:
        relative = path.relative_to(root)
    except ValueError:
        raise WorkflowError('PATH_OUTSIDE_PROJECT', 'path must be inside the selected project', str(value))
    current = root
    for part in relative.parts:
        if part == '..':
            raise WorkflowError('PATH_OUTSIDE_PROJECT', 'parent traversal is not allowed', str(value))
        current = current / part
        if current.is_symlink():
            raise WorkflowError('PATH_SYMLINK', 'symlink paths are not supported', str(value))
    if not path.resolve().is_relative_to(root):
        raise WorkflowError('PATH_OUTSIDE_PROJECT', 'path resolves outside the project', str(value))
    return path


def text_file(root: Path, value: str | Path) -> str:
    path = local_path(root, value)
    if not path.is_file():
        raise WorkflowError('RECORD_MISSING', 'record file does not exist', str(value))
    return path.read_text(encoding='utf-8')


def timestamp(root: Path) -> str:
    context = fields(text_file(root, 'PROJECT_CONTEXT.md'))
    timezone = context.get('project timezone', '')
    try:
        zone = ZoneInfo(timezone)
    except (ValueError, KeyError):
        raise WorkflowError('PROJECT_TIMEZONE_MISSING', 'declare a valid IANA Project timezone in PROJECT_CONTEXT.md', 'PROJECT_CONTEXT.md')
    return datetime.now(zone).strftime('%Y-%m-%d %H:%M') + f' ({timezone})'


def digest(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def one_line(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or '\n' in value or '\r' in value:
        raise WorkflowError('INPUT_INVALID', 'field values must be nonempty single-line strings')
    return value.strip()


def replace_field(text: str, name: str, value: str, *, section: str | None = None) -> str:
    value = one_line(value)
    pattern = re.compile(r'^- \*\*' + re.escape(name) + r':\*\*[^\n]*$', re.MULTILINE)
    matches = list(pattern.finditer(text))
    if matches:
        match = matches[0]
        return text[:match.start()] + f'- **{name}:** {value}' + text[match.end():]
    if not section:
        raise WorkflowError('FIELD_MISSING', f'missing editable field: {name}')
    match = re.search(r'^## ' + re.escape(section) + r'[^\n]*\n', text, re.MULTILINE)
    if not match:
        raise WorkflowError('TASK_SECTION_MISSING', f'missing section {section}')
    return text[:match.end()] + f'\n- **{name}:** {value}\n' + text[match.end():]


def task_records(root: Path) -> dict[str, Path]:
    root = root.resolve()
    records = {}
    for path in sorted(local_path(root, 'tasks').glob('T-*.md')):
        if not path.is_file():
            continue
        value = fields(text_file(root, path)).get('id', '')
        if not TASK_ID.fullmatch(value):
            continue
        if value in records:
            raise WorkflowError('TASK_DUPLICATE_ID', f'duplicate declared ID {value}', path.relative_to(root).as_posix())
        if not path.name.startswith(value + '-'):
            raise WorkflowError('TASK_ID_MISMATCH', f'filename and declared ID disagree: {value}', path.relative_to(root).as_posix())
        records[value] = path
    return records


def task_path(root: Path, task_id: str) -> Path:
    if not TASK_ID.fullmatch(task_id):
        raise WorkflowError('TASK_ID_INVALID', 'task ID must use T-NNN')
    records = task_records(root)
    if task_id not in records:
        raise WorkflowError('TASK_MISSING', f'unknown task: {task_id}', 'tasks')
    return records[task_id]


def sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r'^## ([^\n]+)\n', text, re.MULTILINE))
    return {match.group(1): text[match.end():matches[index + 1].start() if index + 1 < len(matches) else len(text)].strip()
            for index, match in enumerate(matches)}


def task_show(root: Path, task_id: str) -> dict:
    root = root.resolve()
    path = task_path(root, task_id)
    text = text_file(root, path)
    return {'task_id': task_id, 'detail': path.relative_to(root).as_posix(), 'hash': digest(text),
            'fields': fields(text), 'sections': sections(text), 'record': text}


def registry(root: Path) -> dict:
    from relationctl import load_registry, validate_registry
    path = local_path(root, 'relations/RELATIONS.yaml')
    if not path.exists():
        return {'version': 1, 'relations': []}
    data = load_registry(path)
    errors = validate_registry(data)
    if errors:
        raise WorkflowError('RELATION_INVALID', '; '.join(errors), 'relations/RELATIONS.yaml')
    return data


def direct_dependencies(data: dict) -> dict[str, list[str]]:
    result = {}
    for edge in data['relations']:
        if edge['relation'] == 'depends_on':
            result.setdefault(edge['source'], []).append(edge['target'])
    return {key: sorted(set(value)) for key, value in result.items()}


def append_log(text: str, stamp: str, reason: str) -> str:
    match = re.search(r'^## (?:4\. )?Work log[^\n]*\n', text, re.MULTILINE)
    if not match:
        raise WorkflowError('TASK_WORK_LOG_MISSING', 'task record must have a Work log section')
    end = re.search(r'^## ', text[match.end():], re.MULTILINE)
    position = match.end() + end.start() if end else len(text)
    entry = f'\n### {stamp} — CLI record update\n\n- **Outcome:** {one_line(reason)}\n\n'
    return text[:position].rstrip() + '\n' + entry + text[position:]


class FilePlan:
    """Optimistic, locked, staged multi-file updates with rollback on failure."""
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.before: dict[Path, bytes | None] = {}
        self.after: dict[Path, bytes | None] = {}
        self.directories: dict[Path, tuple[str, ...]] = {}
        self.modes: dict[Path, int] = {}
        self.directory_creates: set[Path] = set()

    def add_directory(self, value: str | Path) -> None:
        path = local_path(self.root, value)
        if path.exists():
            if not path.is_dir():
                raise WorkflowError('PATH_CONFLICT', 'directory path is occupied by a non-directory', str(value))
            self.watch_directory(path)
        else:
            self.directory_creates.add(path)

    def add(self, value: str | Path, text: str, *, create: bool = False) -> None:
        self.add_bytes(value, text.encode('utf-8'), create=create)

    def add_bytes(self, value: str | Path, content: bytes, *, create: bool = False, mode: int | None = None) -> None:
        path = local_path(self.root, value)
        if path.exists() and not path.is_file():
            raise WorkflowError('PATH_CONFLICT', 'destination is not a regular file', str(value))
        if create and path.exists():
            raise WorkflowError('RECORD_EXISTS', 'refusing to overwrite an existing record', str(value))
        self.before.setdefault(path, path.read_bytes() if path.exists() else None)
        self.after[path] = content
        if mode is not None:
            self.modes[path] = mode & 0o777

    def remove(self, value: str | Path) -> None:
        path = local_path(self.root, value)
        if not path.is_file():
            raise WorkflowError('PATH_CONFLICT', 'removal requires an existing regular file', str(value))
        self.watch(path)
        self.modes[path] = path.stat().st_mode & 0o777
        self.after[path] = None

    def watch_directory(self, value: str | Path) -> None:
        path = local_path(self.root, value)
        self.directories.setdefault(path, tuple(sorted(child.name for child in path.iterdir()
                                                      if child.name != '.workflowctl.lock')))

    def watch(self, value: str | Path) -> None:
        """Protect a read dependency without making it a write target."""
        path = local_path(self.root, value)
        self.before.setdefault(path, path.read_bytes() if path.exists() else None)

    def report(self, apply: bool = False) -> dict:
        changes = [path for path, content in self.after.items() if content != self.before[path]]
        report = []
        for path in changes:
            before, after = self.before[path], self.after[path]
            try:
                old, new = (before or b'').decode('utf-8'), (after or b'').decode('utf-8')
                if '\x00' in old or '\x00' in new:
                    raise UnicodeError('binary content')
                diff = ''.join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                                   fromfile=path.relative_to(self.root).as_posix(),
                                                   tofile=path.relative_to(self.root).as_posix()))
            except UnicodeError:
                diff = None
            report.append({'path': path.relative_to(self.root).as_posix(),
                           'operation': 'delete' if after is None else 'create' if before is None else 'update',
                           'before_hash': hashlib.sha256(before).hexdigest() if before is not None else None,
                           'after_hash': hashlib.sha256(after).hexdigest() if after is not None else None,
                           'diff': diff})
        report.extend({'path': path.relative_to(self.root).as_posix(), 'operation': 'create-directory',
                       'before_hash': None, 'after_hash': None, 'diff': None}
                      for path in sorted(self.directory_creates))
        if not apply or not (changes or self.directory_creates):
            return {'outcome': 'planned' if changes or self.directory_creates else 'no-op', 'changes': report}
        lock = local_path(self.root, '.workflowctl.lock')
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise WorkflowError('WRITE_CONFLICT', 'another local operation holds .workflowctl.lock')
        os.close(descriptor)
        staged: dict[Path, Path] = {}
        created_dirs = []
        applied = []
        committed = False
        try:
            for path in self.directory_creates:
                local_path(self.root, path)
                if path.exists():
                    raise WorkflowError('WRITE_CONFLICT', 'planned directory appeared after planning', path.relative_to(self.root).as_posix())
            for path, expected in self.directories.items():
                local_path(self.root, path)
                if not path.is_dir() or tuple(sorted(child.name for child in path.iterdir()
                                                     if child.name != '.workflowctl.lock')) != expected:
                    raise WorkflowError('WRITE_CONFLICT', 'directory membership changed after planning', path.relative_to(self.root).as_posix())
            for path in self.before:
                local_path(self.root, path)
                actual = path.read_bytes() if path.exists() else None
                if actual != self.before[path]:
                    raise WorkflowError('WRITE_CONFLICT', 'record changed after planning', path.relative_to(self.root).as_posix())
            for path in sorted(self.directory_creates, key=lambda item: (len(item.parts), item.as_posix())):
                missing = []
                parent = path
                while not parent.exists():
                    missing.append(parent)
                    parent = parent.parent
                for directory in reversed(missing):
                    directory.mkdir()
                    created_dirs.append(directory)
            for path in changes:
                if self.after[path] is None:
                    continue
                missing = []
                parent = path.parent
                while not parent.exists():
                    missing.append(parent)
                    parent = parent.parent
                for directory in reversed(missing):
                    directory.mkdir()
                    created_dirs.append(directory)
                with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                    stream.write(self.after[path])
                    staged[path] = Path(stream.name)
                if path in self.modes:
                    os.chmod(staged[path], self.modes[path])
                elif path.exists():
                    os.chmod(staged[path], path.stat().st_mode & 0o777)
            for path in self.before:
                if (path.read_bytes() if path.exists() else None) != self.before[path]:
                    raise WorkflowError('WRITE_CONFLICT', 'record changed during staging', path.relative_to(self.root).as_posix())
            for path in sorted(changes, key=lambda item: self.after[item] is None):
                if self.after[path] is None:
                    path.unlink()
                else:
                    os.replace(staged[path], path)
                applied.append(path)
            committed = True
        except Exception:
            for path in reversed(applied):
                if self.before[path] is None:
                    path.unlink()
                else:
                    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                        stream.write(self.before[path])
                        recovery = Path(stream.name)
                    os.chmod(recovery, self.modes[path] if self.after[path] is None else path.stat().st_mode & 0o777)
                    os.replace(recovery, path)
            raise
        finally:
            for path in staged.values():
                path.unlink(missing_ok=True)
            if not committed:
                for directory in reversed(created_dirs):
                    try:
                        directory.rmdir()
                    except OSError:
                        pass
            lock.unlink(missing_ok=True)
        return {'outcome': 'applied', 'changes': report}


def markdown_rows(text: str, id_column: str) -> list[dict[str, str]]:
    rows = []
    header = None
    for line in text.splitlines():
        if not line.startswith('|'):
            header = None
            continue
        cells = re.split(r'(?<!\\)\|', line.strip()[1:-1])
        cells = [cell.strip() for cell in cells]
        if id_column in cells:
            header = cells
        elif header and len(cells) == len(header) and not all(re.fullmatch(r':?-+:?', cell) for cell in cells):
            rows.append(dict(zip(header, cells)))
    return rows


def task_view(root: Path, path: Path, text: str, data: dict) -> dict[str, str]:
    value = fields(text)
    task_id = value['id']
    deps = direct_dependencies(data)
    if not local_path(root, 'relations/RELATIONS.yaml').exists():
        board = local_path(root, 'tasks/TASK_BOARD.md')
        board_deps = any(row.get('task_id') == task_id and TASK_ID.search(row.get('depends_on', ''))
                         for row in markdown_rows(text_file(root, board), 'task_id')) if board.is_file() else False
        if board_deps or value.get('depends on', '—') not in {'', '—', 'none', 'None'}:
            raise WorkflowError('DEPENDENCY_AUTHORITY_MISSING', 'declared dependency views require a configured registry', path.relative_to(root).as_posix())
    blocks = sorted(source for source, targets in deps.items() if task_id in targets)
    title = text.splitlines()[0].split(':', 1)[-1].strip()
    rel = path.relative_to(root).as_posix()
    return {'task_id': task_id, 'title': title, 'state': value.get('state', '—'),
            'readiness': value.get('readiness', '—'), 'priority': value.get('priority', '—'),
            'current_result': value.get('current result', '—'), 'next_action': value.get('next action', '—'),
            'depends_on': ', '.join(deps.get(task_id, [])) or '—', 'blocks': ', '.join(blocks) or '—',
            'blocker': value.get('blocker', '—'), 'resume_entry': value.get('resume entry', '—'),
            'last_updated': value.get('last updated', '—'), 'detail': rel,
            'taskboard_id': value.get('external tracker id') or value.get('taskboard id') or value.get('taskboard') or '—'}


BOARD_COLUMNS = ['task_id', 'title', 'state', 'readiness', 'priority', 'current_result', 'next_action',
                 'depends_on', 'blocks', 'blocker', 'resume_entry', 'last_updated', 'detail', 'taskboard_id']
STATUS_MAP = {'ID': 'task_id', 'Priority': 'priority', 'State': 'state', 'Current result': 'current_result',
              'Next action': 'next_action', 'Related task(s)': 'depends_on', 'Blocker': 'blocker',
              'Detail': 'detail', 'Last updated': 'last_updated'}


def _cell(value: str) -> str:
    return value.replace('|', '\\|').replace('\n', ' ')


def _view_cell(column: str, value: str, view: dict, board: bool) -> str:
    if column == 'detail':
        rel = view['detail'].removeprefix('tasks/') if board else view['detail']
        return f'[record]({rel})'
    if column == 'resume_entry' and value.startswith('#'):
        rel = view['detail'].removeprefix('tasks/') if board else view['detail']
        return f'[resume]({rel}{value})'
    return _cell(value)


def refresh_table(text: str, views: dict[str, dict], *, board: bool) -> str:
    id_column = 'task_id' if board else 'ID'
    lines = text.splitlines(keepends=True)
    header = None
    found = set()
    for index, line in enumerate(lines):
        if not line.startswith('|'):
            header = None
            continue
        cells = [cell.strip() for cell in re.split(r'(?<!\\)\|', line.strip()[1:-1])]
        if id_column in cells:
            header = cells
            continue
        if not header or len(cells) != len(header):
            continue
        task_id = cells[header.index(id_column)].strip(TICK)
        if task_id not in views:
            continue
        if task_id in found:
            raise WorkflowError('VIEW_DUPLICATE_ROW', f'duplicate view row {task_id}')
        found.add(task_id)
        view = views[task_id]
        updated = []
        for key, old in zip(header, cells):
            field = key if board else STATUS_MAP.get(key)
            # Related tasks are broader than prerequisites; keep that manual column.
            if not board and key == 'Related task(s)':
                field = None
            updated.append(_view_cell(field, view[field], view, board) if field in view else old)
        lines[index] = '| ' + ' | '.join(updated) + ' |\n'
    rendered = ''.join(lines)
    if not board:
        rendered, found = status_sections(rendered, views, found)
    missing = sorted(set(views) - found)
    if not board:
        # Completed recently is a curated subset, not the historical task archive.
        missing = [key for key in missing if views[key]['state'] not in {'completed', 'canceled'}]
    if missing:
        begin, end = '<!-- BEGIN WORKFLOWCTL TASK VIEW v1 -->', '<!-- END WORKFLOWCTL TASK VIEW v1 -->'
        if begin in text or end in text:
            if text.count(begin) != 1 or text.count(end) != 1:
                raise WorkflowError('VIEW_MARKER_INVALID', 'invalid owned view markers')
            # Existing managed rows are included in the refreshed output above.
        columns = BOARD_COLUMNS if board else list(STATUS_MAP)
        table = '| ' + ' | '.join(columns) + ' |\n| ' + ' | '.join(['---'] * len(columns)) + ' |\n'
        for task_id in missing:
            view = views[task_id]
            table += '| ' + ' | '.join(_view_cell(key if board else STATUS_MAP[key], view[key if board else STATUS_MAP[key]], view, board) for key in columns) + ' |\n'
        if begin in rendered:
            if rendered.index(begin) >= rendered.index(end):
                raise WorkflowError('VIEW_MARKER_INVALID', 'reversed owned view markers')
            position = rendered.index(end)
            # Append rows only, retaining the existing owned table header.
            rendered = rendered[:position].rstrip() + '\n' + '\n'.join(table.splitlines()[2:]) + '\n' + rendered[position:]
        else:
            rendered = rendered.rstrip() + '\n\n## CLI-maintained tasks\n\n' + begin + '\n' + table + end + '\n'
        return rendered
    return rendered


def status_sections(text: str, views: dict[str, dict], found: set[str]) -> tuple[str, set[str]]:
    groups = {'active': 'Current work', 'in_review': 'Current work',
              'blocked': 'Current work', 'awaiting-confirmation': 'Current work',
              'backlog': 'Planned and paused', 'planned': 'Planned and paused',
              'paused': 'Planned and paused', 'completed': 'Completed recently'}
    titles = re.findall(r'^## (.+)$', text, re.MULTILINE)
    if not set(groups.values()).issubset(titles):
        return text, found
    pieces = re.split(r'(?=^## )', text, flags=re.MULTILINE)
    sections = {piece.splitlines()[0][3:]: index for index, piece in enumerate(pieces) if piece.startswith('## ')}
    headers = {}
    for title in set(groups.values()):
        rows = pieces[sections[title]].splitlines(keepends=True)
        headers[title] = next((line for line in rows if line.startswith('| ID |')), None)
    for task_id, view in views.items():
        destination = groups.get(view['state'])
        if not destination or not headers.get(destination):
            continue
        row = None
        source = None
        for index, piece in enumerate(pieces):
            lines = piece.splitlines(keepends=True)
            for position, line in enumerate(lines):
                if re.match(r'^\|\s*`?' + re.escape(task_id) + r'`?\s*\|', line):
                    source = index
                    row = line
                    if index != sections[destination]:
                        lines.pop(position)
                        pieces[index] = ''.join(lines)
                    break
            if row:
                break
        if source == sections[destination]:
            continue
        if row is None:
            if view['state'] == 'completed':
                continue
            columns = [cell.strip() for cell in headers[destination].strip().strip('|').split('|')]
            row = '| ' + ' | '.join(_view_cell(STATUS_MAP[key], view[STATUS_MAP[key]], view, False) if key in STATUS_MAP else '—' for key in columns) + ' |\n'
        elif source is not None:
            source_header = next((line for line in pieces[source].splitlines() if line.startswith('| ID |')), None)
            if source_header and source_header.strip() != headers[destination].strip():
                raise WorkflowError('VIEW_HEADER_CONFLICT', 'status sections have incompatible columns; review before moving a row')
        lines = pieces[sections[destination]].splitlines(keepends=True)
        positions = [index for index, line in enumerate(lines) if line.startswith('|')]
        lines.insert(positions[-1] + 1, row)
        pieces[sections[destination]] = ''.join(lines)
        found.add(task_id)
    return ''.join(pieces), found


def plan_views(root: Path, plan: FilePlan, records: dict[str, str], data: dict) -> None:
    views = {task_id: task_view(root, path, text, data) for task_id, (path, text) in records.items()}
    for name, board in [('PROJECT_STATUS.md', False), ('tasks/TASK_BOARD.md', True)]:
        path = local_path(root, name)
        if path.exists():
            original = plan.after.get(path, path.read_bytes()).decode('utf-8')
            plan.add(path, refresh_table(original, views, board=board))


def projection_diagnostics(root: Path, overrides: dict[Path, bytes] | None = None, task_id: str | None = None) -> list[dict]:
    overrides = overrides or {}
    records = task_records(root)
    def read(path):
        return overrides[path].decode('utf-8') if path in overrides else text_file(root, path)
    values = {key: fields(read(path)) for key, path in records.items()}
    diagnostics = []
    for name, board in [('PROJECT_STATUS.md', False), ('tasks/TASK_BOARD.md', True)]:
        path = local_path(root, name)
        if not path.exists():
            continue
        seen = set()
        for row in markdown_rows(read(path), 'task_id' if board else 'ID'):
            entity = row.get('task_id' if board else 'ID', '').strip(TICK)
            if not TASK_ID.fullmatch(entity) or task_id and entity != task_id:
                continue
            if entity not in values or entity in seen:
                diagnostics.append({'code': 'VIEW_UNKNOWN_TASK' if entity not in values else 'VIEW_DUPLICATE_ROW', 'path': name, 'entity': entity, 'message': 'view row must identify one declared task'})
                continue
            seen.add(entity)
            for column, actual in row.items():
                field = column if board else STATUS_MAP.get(column)
                if field not in {'state', 'readiness', 'priority', 'current_result', 'next_action', 'blocker', 'last_updated'}:
                    continue
                expected = values[entity].get(field.replace('_', ' '))
                if expected is None:
                    continue
                normalize = lambda value: value.replace('\\|', '|').strip().strip(TICK)
                if normalize(actual) != normalize(expected):
                    diagnostics.append({'code': 'VIEW_DRIFT', 'path': name, 'entity': entity, 'message': f'{column} differs from the authoritative task record'})
    return diagnostics


def set_dependencies(root: Path, data: dict, task_id: str, dependencies: list[str], basis: str, date: str) -> dict:
    from relationctl import new_relation, validate_registry
    from workflow_relations import dependency_cycle
    records = task_records(root)
    for target in dependencies:
        if target == task_id or target not in records:
            raise WorkflowError('DEPENDENCY_TARGET_INVALID', f'unknown/self prerequisite: {target}')
    if len(set(dependencies)) != len(dependencies):
        raise WorkflowError('DEPENDENCY_DUPLICATE', 'duplicate prerequisite')
    candidate = {'version': 1, 'relations': [edge.copy() for edge in data['relations']]}
    candidate['relations'] = [edge for edge in candidate['relations'] if not (edge['source'] == task_id and edge['relation'] == 'depends_on')]
    for target in dependencies:
        old = next((edge for edge in data['relations'] if edge['source'] == task_id and edge['relation'] == 'depends_on' and edge['target'] == target), None)
        candidate['relations'].append(old or new_relation(candidate, task_id, 'depends_on', target, basis, date))
    errors = validate_registry(candidate)
    if errors or dependency_cycle(candidate):
        raise WorkflowError('DEPENDENCY_CYCLE' if dependency_cycle(candidate) else 'RELATION_INVALID', '; '.join(errors) or 'proposed dependencies create a cycle')
    return candidate


def task_new(root: Path, args) -> dict:
    if not TASK_ID.fullmatch(args.task_id) or not SLUG.fullmatch(args.topic):
        raise WorkflowError('TASK_INPUT_INVALID', 'supply T-NNN and a lowercase hyphenated topic')
    if args.task_id in task_records(root):
        raise WorkflowError('TASK_DUPLICATE_ID', f'task already exists: {args.task_id}')
    stamp = timestamp(root)
    path = local_path(root, f'tasks/{args.task_id}-{args.topic}.md')
    template = text_file(root, 'templates/TASK.md')
    text = template.replace('T-NNN', args.task_id).replace('<Task Title>', one_line(args.title))
    for name, value in [('ID', TICK + args.task_id + TICK), ('State', 'backlog'), ('Readiness', args.readiness),
                        ('Priority', args.priority), ('Created', stamp[:10]), ('Last updated', stamp),
                        ('Objective', args.objective), ('Scope', args.scope), ('Out of scope', args.exclusions),
                        ('Acceptance', args.acceptance), ('Deliverable / intended audience', args.deliverable),
                        ('External tracker ID', args.external_id or '—'), ('Current result', 'provisional — not started'),
                        ('Current step', 'S1'), ('Implementation plan version', 'v1'), ('Resume entry', '#8-handoff'),
                        ('Next action', args.next_action), ('Blocker', '—')]:
        text = replace_field(text, name, value, section='1. Task identity and scope' if name == 'Acceptance' else None)
    text = text.replace('<bounded step and completion condition>', one_line(args.next_action), 1)
    text = re.sub(r'^- \[ \] ' + TICK + r'S2' + TICK + r':.*\n', '', text, flags=re.MULTILINE)
    applicability = args.contract_applicability
    if applicability == 'not applicable':
        if not args.contract_reason:
            raise WorkflowError('TASK_CONTRACT_REASON_MISSING', 'not applicable requires an explicit --contract-reason')
        applicability += ' — ' + one_line(args.contract_reason)
    text = replace_field(text, 'Applicability', applicability)
    text = replace_field(text, 'Recommended next entry point', args.next_action)
    text = append_log(text, stamp, 'Created from explicit task inputs; no research work executed.')
    data = registry(root)
    if args.depends_on and not local_path(root, 'relations/RELATIONS.yaml').is_file():
        raise WorkflowError('DEPENDENCY_AUTHORITY_MISSING', 'enable the relation registry before creating dependent tasks')
    if args.depends_on:
        data = set_dependencies(root, data, args.task_id, args.depends_on, path.relative_to(root).as_posix(), stamp[:10])
    text = replace_field(text, 'Depends on', ', '.join(args.depends_on) or '—', section='1. Task identity and scope')
    plan = FilePlan(root)
    plan.add(path, text, create=True)
    if args.depends_on:
        plan.add('relations/RELATIONS.yaml', json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    affected = {args.task_id: (path, text)}
    for task_id in args.depends_on:
        record = task_path(root, task_id)
        affected[task_id] = (record, text_file(root, record))
    plan_views(root, plan, affected, data)
    return plan.report(args.apply)


EDITABLE = {'Priority', 'Readiness', 'Objective', 'Scope', 'Out of scope', 'Acceptance',
            'Deliverable / intended audience', 'Current result', 'Current step', 'Implementation plan version',
            'Resume entry', 'Next action', 'Blocker', 'External tracker ID'}


def task_update(root: Path, args) -> dict:
    from workflow_task_lifecycle import patch_record, validate_patch
    path = task_path(root, args.task_id)
    original = text_file(root, path)
    if not args.set and not args.input and args.depends_on is None:
        raise WorkflowError('TASK_INPUT_REQUIRED', 'supply --set, --input or an explicit dependency edit')
    if args.if_hash and args.if_hash != digest(original):
        raise WorkflowError('WRITE_CONFLICT', 'task hash differs from --if-hash', path.relative_to(root).as_posix())
    plan = FilePlan(root)
    plan.watch(path)
    if text_file(root, path) != original:
        raise WorkflowError('WRITE_CONFLICT', 'task changed while loading', str(path))
    plan.watch('relations/RELATIONS.yaml')
    plan.watch('PROJECT_CONTEXT.md')
    text, _ = patch_record(root, original, args, plan)
    if text == original and args.depends_on is None:
        return {'outcome': 'no-op', 'changes': []}
    stamp = timestamp(root)
    data = registry(root)
    old_dependencies = direct_dependencies(data).get(args.task_id, [])
    if args.depends_on is not None:
        if not local_path(root, 'relations/RELATIONS.yaml').exists():
            raise WorkflowError('DEPENDENCY_AUTHORITY_MISSING', 'relation registry is not configured')
        data = set_dependencies(root, data, args.task_id, args.depends_on, path.relative_to(root).as_posix(), stamp[:10])
        text = replace_field(text, 'Depends on', ', '.join(args.depends_on) or '—', section='1. Task identity and scope')
    if text == original:
        return {'outcome': 'no-op', 'changes': []}
    text = replace_field(text, 'Last updated', stamp)
    text = append_log(text, stamp, args.reason)
    validate_patch(root, path, text)
    plan.add(path, text)
    if args.depends_on is not None:
        plan.add('relations/RELATIONS.yaml', json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    affected = {args.task_id: (path, text)}
    if args.depends_on is not None:
        for task_id in sorted(set(old_dependencies) | set(args.depends_on)):
            record = task_path(root, task_id)
            affected[task_id] = (record, text_file(root, record))
    plan_views(root, plan, affected, data)
    return plan.report(args.apply)


def view_refresh(root: Path, apply: bool, task_id: str | None = None) -> dict:
    data = registry(root)
    from workflow_relations import dependency_cycle, target_errors
    errors = target_errors(root, data)
    if errors:
        raise WorkflowError(errors[0]['code'], errors[0]['message'], errors[0]['path'])
    if dependency_cycle(data):
        raise WorkflowError('DEPENDENCY_CYCLE', 'direct dependencies contain a cycle')
    records = task_records(root)
    if task_id and task_id not in records:
        raise WorkflowError('TASK_MISSING', f'unknown task {task_id}')
    plan = FilePlan(root)
    changed = {}
    for value, path in records.items():
        if task_id and task_id != value:
            continue
        text = text_file(root, path)
        if local_path(root, 'relations/RELATIONS.yaml').exists():
            deps = direct_dependencies(data).get(value, [])
            updated = replace_field(text, 'Depends on', ', '.join(deps) or '—', section='1. Task identity and scope')
            if updated != text:
                text = updated
                plan.add(path, text)
        changed[value] = (path, text)
    plan_views(root, plan, changed, data)
    before = projection_diagnostics(root, task_id=task_id)
    after = projection_diagnostics(root, plan.after, task_id)
    result = plan.report(apply)
    result.update(drift_before=before, drift_after=after, diagnostics=after)
    return result
