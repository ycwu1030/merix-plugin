"""Explicit local payload archival and project-document path reconciliation."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
from urllib.parse import quote, unquote

from workflow_records import FilePlan, WorkflowError, fields, local_path, one_line, replace_field, text_file, timestamp

LOCATION = 'Canonical payload location or controlled access route'
DOCUMENT_SUFFIXES = {'.md', '.markdown', '.rst', '.txt', '.tex', '.json', '.yaml', '.yml', '.toml', '.html', '.htm'}
IGNORED_DIRS = {'.git', '.codex', '.agents', '.venv', 'venv', 'node_modules', '__pycache__'}
TOKENS = re.compile(r'`[^`\n]+`|<[^<>\n]+>|"(?:\\.|[^"\\\n])*"|\x27[^\x27\n]*\x27|[^\s`<>"\x27()\[\]{},;]+')
HISTORY_FIELDS = ('Exact invocation / entry point', 'Producer task / run or source locator',
                  'Creation, acquisition, or registration route')


def payload_location(root: Path, entry: Path, value: str, granularity: str) -> Path:
    target = local_path(root, value)
    if not target.is_relative_to(entry.parent / 'payload'):
        raise WorkflowError('ARTIFACT_PAYLOAD_LAYOUT', 'local payload must be inside this entry\'s payload/; use explicit archive or reconcile', value)
    if granularity == 'manifest-only reference':
        raise WorkflowError('ARTIFACT_PAYLOAD_INVALID', 'manifest-only references do not declare a local present payload')
    if target.exists() and granularity == 'single file' and not target.is_file():
        raise WorkflowError('ARTIFACT_PAYLOAD_INVALID', 'single file requires a regular file', value)
    return target


def _inside(path: Path, parent: Path) -> bool:
    return path == parent or path.is_relative_to(parent)


def _documents(root: Path, plan: FilePlan, excluded: tuple[Path, ...]) -> list[Path]:
    documents = []
    for directory, dirs, files in os.walk(root, followlinks=False):
        current = local_path(root, directory)
        plan.watch_directory(current)
        dirs[:] = sorted(name for name in dirs if name not in IGNORED_DIRS
                         and not any(_inside(current / name, item) for item in excluded)
                         and not (name == 'payload' and (current / name).is_relative_to(root / 'artifacts')))
        for name in dirs:
            local_path(root, current / name)
        for name in sorted(files):
            path = current / name
            if name == 'integrity.json' and current.is_relative_to(root / 'artifacts') and (current / 'ARTIFACT.md').is_file():
                continue  # Integrity observation history retains its original routes.
            if path.suffix.lower() not in DOCUMENT_SUFFIXES or any(_inside(path, item) for item in excluded):
                continue
            path = local_path(root, path)
            plan.watch(path)
            documents.append(path)
    return documents


def _replace_path(root: Path, document: Path, candidate: str, old: Path, new: Path) -> str:
    if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', candidate):
        return candidate
    base, *tail = re.split(r'(?=[?#])', candidate, maxsplit=1)
    trailing = '.' if base.endswith('.') and not base.endswith('..') else ''
    base = base[:-1] if trailing else base
    decoded = unquote(base)
    if not decoded or any(char in decoded for char in '\n\r\x00'):
        return candidate
    if old.name not in decoded and not document.parent.is_relative_to(old):
        return candidate
    supplied = Path(decoded)
    candidates = [(supplied if supplied.is_absolute() else root / supplied, 'root'),
                  (supplied if supplied.is_absolute() else document.parent / supplied, 'relative')]
    resolved = [(Path(os.path.abspath(path)), style) for path, style in candidates]
    matches = [(path, style) for path, style in resolved if _inside(path, old)]
    if not matches:
        return candidate
    if len({path for path, _ in matches}) > 1 or any(path.exists() and not _inside(path, old) for path, _ in resolved):
        raise WorkflowError('ARTIFACT_REFERENCE_AMBIGUOUS', 'root-relative and document-relative interpretations disagree: ' + candidate,
                            document.relative_to(root).as_posix())
    path, style = matches[0]
    if not supplied.is_absolute() and decoded.startswith(('./', '../')):
        style = 'relative'
    destination = new / path.relative_to(old) if path != old else new
    if supplied.is_absolute():
        rendered = destination.as_posix()
    elif style == 'relative':
        rendered = Path(os.path.relpath(destination, document.parent)).as_posix()
        if decoded.startswith('./') and not rendered.startswith('.'):
            rendered = './' + rendered
    else:
        rendered = destination.relative_to(root).as_posix()
    if '%' in base:
        rendered = quote(rendered, safe='/.-_~')
    return rendered + trailing + ''.join(tail)


def _rewrite(root: Path, document: Path, text: str, old: Path, new: Path) -> str:
    def token(match):
        raw = match.group()
        wrapped = raw[0] in '`<"\x27' and raw[-1] == {'`': '`', '<': '>', '"': '"', "'": "'"}.get(raw[0])
        content = raw[1:-1] if wrapped else raw
        if wrapped and raw[0] == '"':
            try:
                content = json.loads(raw)
            except ValueError:
                pass
        changed = _replace_path(root, document, content, old, new)
        if changed == content and wrapped and any(char.isspace() for char in content):
            changed = _rewrite(root, document, content, old, new)
        if changed == content:
            return raw
        if wrapped and raw[0] == '"':
            return json.dumps(changed, ensure_ascii=False)
        return raw[0] + changed + raw[-1] if wrapped else changed
    return TOKENS.sub(token, text)


def reconcile_documents(root: Path, plan: FilePlan, old: Path, new: Path, *, excluded: tuple[Path, ...] = ()) -> dict:
    changed, historical = [], []
    if old == new:
        return {'updated': changed, 'historical': historical}
    for path in _documents(root, plan, excluded):
        content = plan.after.get(path, plan.before[path])
        if content is None:
            continue
        try:
            text = content.decode('utf-8')
        except UnicodeError:
            raise WorkflowError('ARTIFACT_DOCUMENT_UNREADABLE', 'project document must be readable UTF-8 before reconciling references', path.relative_to(root).as_posix())
        if path.suffix.lower() == '.json' or path.suffix.lower() in {'.yaml', '.yml'} and text.lstrip().startswith(('{', '[')):
            def unique_keys(pairs):
                data = {}
                for key, value in pairs:
                    if key in data:
                        raise ValueError('duplicate JSON key')
                    data[key] = value
                return data
            try:
                data = json.loads(text, object_pairs_hook=unique_keys)
            except ValueError:
                if _rewrite(root, path, text, old, new) != text:
                    raise WorkflowError('ARTIFACT_DOCUMENT_INVALID', 'cannot safely update invalid or duplicate-key JSON references', path.relative_to(root).as_posix())
                continue
            retained = False
            def rewrite_value(value, key=''):
                nonlocal retained
                if isinstance(value, dict):
                    return {name: rewrite_value(item, name) for name, item in value.items()}
                if isinstance(value, list):
                    return [rewrite_value(item, key) for item in value]
                if isinstance(value, str):
                    updated = _rewrite(root, path, value, old, new)
                    if key in HISTORY_FIELDS and updated != value:
                        retained = True
                        return value
                    return updated
                return value
            updated_data = rewrite_value(data)
            if retained:
                historical.append(path.relative_to(root).as_posix())
            if updated_data != data:
                plan.add(path, json.dumps(updated_data, indent=2, ensure_ascii=False) + '\n')
                changed.append(path.relative_to(root).as_posix())
            continue
        lines, retained, annotate = [], False, False
        # Execution/source facts and earlier correction logs retain their original locators.
        in_history = False
        for line in text.splitlines(keepends=True):
            if re.match(r'^### .* — artifact (?:.* correction|archive|cleanup|recovery completion)', line):
                in_history = True
            updated = _rewrite(root, path, line, old, new)
            protected = any(f'**{name}:**' in line or f'"{name}"' in line for name in HISTORY_FIELDS)
            if updated != line and (protected or in_history):
                retained = True
                annotate = annotate or protected and not in_history
                lines.append(line)
            else:
                lines.append(updated)
        updated = ''.join(lines)
        if retained:
            historical.append(path.relative_to(root).as_posix())
            if annotate and path.suffix.lower() in {'.md', '.markdown', '.rst', '.txt', '.tex', '.html', '.htm'}:
                message = (f'artifact location: {old.relative_to(root).as_posix()} -> '
                           f'{new.relative_to(root).as_posix()}; original execution/source locators retained')
                suffix = path.suffix.lower()
                note = ('% ' + message if suffix == '.tex' else '.. ' + message if suffix == '.rst'
                        else message if suffix == '.txt' else '<!-- ' + message + ' -->')
                if note.strip() not in updated:
                    updated = updated.rstrip() + '\n\n' + note + '\n'
        if updated != text:
            plan.add(path, updated)
            changed.append(path.relative_to(root).as_posix())
    return {'updated': changed, 'historical': historical,
            'scope': 'Project UTF-8 Markdown, text, TeX, HTML, JSON, YAML and TOML references; payload contents, binary documents and external material are not rewritten.'}


def archive_payload(root: Path, plan: FilePlan, entry: Path, source_value: str, operation: str,
                    granularity: str) -> tuple[Path, Path, dict]:
    source = local_path(root, source_value)
    if not source.exists() or not (source.is_file() or source.is_dir()):
        raise WorkflowError('ARTIFACT_SOURCE_MISSING', 'archive source must be an existing local regular file or directory', source_value)
    if granularity == 'manifest-only reference' or granularity == 'single file' and not source.is_file():
        raise WorkflowError('ARTIFACT_PAYLOAD_INVALID', 'source must match the explicitly selected artifact granularity')
    destination = entry.parent / 'payload' / source.name if source.is_file() else entry.parent / 'payload'
    local_path(root, destination)
    if source == destination:
        return source, destination, {'updated': [], 'historical': []}
    if _inside(destination, source) or _inside(source, destination):
        raise WorkflowError('ARTIFACT_PATH_OVERLAP', 'source and destination trees must not overlap')
    from workflow_relations import entity_index
    for entity, records in entity_index(root).items():
        if not entity.startswith('A-'):
            continue
        for record, _ in records:
            if record == entry:
                continue
            plan.watch(record)
            data = fields(text_file(root, record))
            if data.get('payload status') == 'present':
                owner = local_path(root, data[LOCATION.lower()])
                if _inside(source, owner) or _inside(owner, source):
                    raise WorkflowError('ARTIFACT_SOURCE_REGISTERED', 'source belongs to another artifact; retain its references and register distinct derived content', source_value)
    if destination.exists():
        if destination == entry.parent / 'payload' and destination.is_dir():
            for scaffold in [destination, *sorted(destination.rglob('*'))]:
                local_path(root, scaffold)
                if not scaffold.is_dir():
                    raise WorkflowError('PATH_CONFLICT', 'payload scaffold contains actual files; refusing to merge or overwrite', scaffold.relative_to(root).as_posix())
                plan.watch_directory(scaffold)
        else:
            raise WorkflowError('PATH_CONFLICT', 'archive destination contains content or is not an empty payload scaffold; refusing to merge or overwrite', destination.relative_to(root).as_posix())
    files = [source] if source.is_file() else sorted(path for path in source.rglob('*') if not path.is_dir())
    if not files:
        raise WorkflowError('ARTIFACT_SOURCE_EMPTY', 'a local collection must contain actual files', source_value)
    if source.is_dir():
        for directory in [source, *sorted(path for path in source.rglob('*') if path.is_dir())]:
            plan.watch_directory(directory)
    for path in files:
        path = local_path(root, path)
        if not path.is_file():
            raise WorkflowError('ARTIFACT_SOURCE_INVALID', 'collection contains a non-regular file', path.relative_to(root).as_posix())
        if path.name in {'ARTIFACT.md', 'RUN.md', 'WORK_PACKAGE.md'}:
            raise WorkflowError('ARTIFACT_SOURCE_RECORD', 'archive payloads rather than moving authoritative workflow records', path.relative_to(root).as_posix())
        plan.watch(path)
        target = destination if source.is_file() else destination / path.relative_to(source)
        plan.add_bytes(target, plan.before[path], create=True, mode=path.stat().st_mode)
        if operation == 'move':
            plan.remove(path)
    documents = reconcile_documents(root, plan, source, destination, excluded=(source, destination))
    return source, destination, documents


def artifact_archive(root: Path, args) -> dict:
    from workflow_domain import record_check
    entry = local_path(root, args.path)
    if entry.is_dir():
        entry = entry / 'ARTIFACT.md'
    if not entry.is_relative_to(root / 'artifacts') or entry.name != 'ARTIFACT.md':
        raise WorkflowError('ARTIFACT_PATH_INVALID', 'archive requires an existing root artifact entry')
    reason, plan = one_line(args.reason), FilePlan(root)
    plan.watch(entry)
    checked = record_check(root, str(entry), 'artifact')
    errors = [item for item in checked['diagnostics'] if item.get('severity', 'error') == 'error'
              and item['code'] not in {'ARTIFACT_PAYLOAD_LAYOUT', 'ARTIFACT_PAYLOAD_MISSING',
                                       'ARTIFACT_INTEGRITY_MISMATCH', 'ARTIFACT_INTEGRITY_UNAVAILABLE'}]
    if errors:
        raise WorkflowError(errors[0]['code'], errors[0]['message'], errors[0]['path'])
    original = text_file(root, entry)
    data = fields(original)
    if data['payload status'] == 'restricted no-copy':
        raise WorkflowError('ARTIFACT_PAYLOAD_INVALID', 'restricted no-copy content cannot be archived; retain the access boundary')
    local = data['payload status'] == 'present'
    old_value = data[LOCATION.lower()]
    old = local_path(root, old_value) if local else None
    if args.action == 'archive':
        source = local_path(root, args.source)
        if local and source != old:
            if old.exists():
                raise WorkflowError('ARTIFACT_SOURCE_MISMATCH', 'source must match the registered unchanged object; changed content needs a new ID')
            plan.watch(old)
        _, destination, documents = archive_payload(root, plan, entry, args.source, args.operation, data['artifact granularity'])
        if local and source != old:
            retained = reconcile_documents(root, plan, old, destination, excluded=(source, destination))
            for key in ('updated', 'historical'):
                documents[key] = sorted(set(documents[key] + retained[key]))
    else:
        destination = payload_location(root, entry, args.location, data['artifact granularity'])
        if not destination.exists():
            raise WorkflowError('ARTIFACT_PAYLOAD_MISSING', 'manually archived destination does not exist', args.location)
        documents = (reconcile_documents(root, plan, old, destination, excluded=(old, entry.parent / 'payload'))
                     if local else {'updated': [], 'historical': []})
    base = (plan.after.get(entry) or original.encode('utf-8')).decode('utf-8')
    text = replace_field(base, LOCATION, destination.relative_to(root).as_posix())
    text = replace_field(text, 'Payload status', 'present')
    if text != original or documents['updated']:
        stamp = timestamp(root)
        text = replace_field(text, 'Last updated', stamp)
        text = text.rstrip() + f'\n\n### {stamp} — artifact location correction\n\n'
        text += f'Caller-declared unchanged object. Reason: {reason}\n\n'
        text += '```json\n' + json.dumps({'before': old_value,
                                        'after': destination.relative_to(root).as_posix(),
                                        'operation': getattr(args, 'operation', 'manual reconcile'),
                                        'documents': documents['updated']}, indent=2, ensure_ascii=False) + '\n```\n'
    from workflow_integrity import stage_integrity
    text, integrity = stage_integrity(root, plan, entry, text)
    plan.add(entry, text)
    result = plan.report(args.apply)
    result.update(entity_id=checked['entity_id'], detail=entry.relative_to(root).as_posix(),
                  payload=destination.relative_to(root).as_posix(), documents=documents, integrity=integrity,
                  non_claim='Caller declares unchanged content/provenance. Exact path reconciliation does not rewrite scientific conclusions or prove external availability.')
    return result
