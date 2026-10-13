"""Read-only scientific evidence record checks and Formula Index allocation."""
from __future__ import annotations

import json
from pathlib import Path
import re

from workflow_records import FilePlan, WorkflowError, local_path, text_file

KIND_NAMES = {
    'comparison': 'comparison',
    'derivation': 'derivation',
    'source-audit': 'source-audit',
    'literature': 'literature',
    'formula-index': 'formula-index',
}
REQUIRED = {
    'comparison': ('Identity and Contract target', 'Evidence basis', 'Comparability conditions and scope',
                   'Comparison method and predeclared acceptance condition', 'Results and observations',
                   'Assessment and disposition', 'Claim strength, limitations, and non-claims', 'Handoff and follow-up'),
    'derivation': ('Objective and claimed output', 'Convention and Scope Block', 'Inputs and source map',
                   'Derivation trace', 'Source discrepancies, corrections, or translations',
                   'Executable symbolic computation', 'Verification', 'Result, limitations, and handoff'),
    'source-audit': ('Audit question and project impact', 'Sources and versions examined', 'Direct source facts',
                     'Comparability and convention map', 'Workspace definition and project interpretation',
                     'Derived here and verification', 'Current conclusion and limitations'),
    'literature': ('Source identity and role', 'Reading copy and access', 'Version relation and transformations',
                   'Use in this project'),
}
FIELD_RE = re.compile(r'^- \*\*(.+?):\*\*[ \t]*([^\n]*)$', re.MULTILINE)
ID_RE = {
    'comparison': re.compile(r'^C-\d{3}$'),
}
FORMULA_ID = re.compile(r'F-(\d{3})')
LOCAL_LINK = re.compile(r'!?\[[^\]]*\]\(([^)]+)\)')
FORMULA_ROW = re.compile(r'^\|\s*(F-\d{3})\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|\s*$', re.MULTILINE)


def _fields(text: str) -> dict[str, str]:
    return {name.lower(): value.strip().strip('`') for name, value in FIELD_RE.findall(text)}


def _sections(text: str) -> set[str]:
    return {match.group(1).strip() for match in re.finditer(r'^## (?:\d+\.\s*)?([^\n]+)$', text, re.MULTILINE)}


def _candidate_roots(root: Path, kind: str) -> tuple[str, ...]:
    return {
        'comparison': ('comparisons', 'workspaces'),
        'derivation': ('analysis', 'workspaces'),
        'source-audit': ('references/audits',),
        'literature': ('references/reading', 'references/reviews', 'references/exploration'),
        'formula-index': ('.',),
    }[kind]


def _classify(path: Path, text: str) -> str | None:
    name = path.name.upper()
    if name == 'FORMULA_INDEX.MD' or path.name == 'FORMULA_INDEX.md':
        return 'formula-index'
    if name == 'COMPARISON.MD' or re.search(r'^# C-\d{3}:', text, re.MULTILINE):
        return 'comparison'
    if name == 'DERIVATION.MD' or re.search(r'^# Derivation:', text, re.MULTILINE):
        return 'derivation'
    if name == 'SOURCE_AUDIT.MD' or re.search(r'^# Source Audit:', text, re.MULTILINE):
        return 'source-audit'
    if name == 'REFERENCE_SOURCE.MD' or re.search(r'^# Source:', text, re.MULTILINE):
        return 'literature'
    return None


def _files(root: Path, kind: str) -> list[Path]:
    if kind == 'formula-index':
        path = local_path(root, 'FORMULA_INDEX.md')
        return [path] if path.is_file() else []
    found: set[Path] = set()
    for value in _candidate_roots(root, kind):
        base = local_path(root, value)
        if base.is_file() and base.suffix.lower() == '.md':
            found.add(base)
        elif base.is_dir():
            for path in base.rglob('*.md'):
                if path.is_file() and not path.is_symlink():
                    found.add(path)
    result = []
    for path in sorted(found):
        try:
            if _classify(path, path.read_text(encoding='utf-8')) == kind:
                result.append(path)
        except UnicodeDecodeError:
            continue
    return result


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _diagnostic(code: str, path: str, message: str, severity: str = 'error') -> dict:
    return {'code': code, 'path': path, 'message': message, 'severity': severity}


def _links(root: Path, path: Path, text: str) -> list[dict]:
    diagnostics = []
    for target in LOCAL_LINK.findall(text):
        target = target.split('#', 1)[0].strip()
        if not target or re.match(r'^(?:https?|mailto):', target):
            continue
        try:
            resolved = local_path(root, path.parent / target)
        except WorkflowError as exc:
            diagnostics.append(_diagnostic(exc.code, _relative(root, path), f'link {target}: {exc}'))
            continue
        if not resolved.exists():
            diagnostics.append(_diagnostic('EVIDENCE_LINK_MISSING', _relative(root, path), f'linked path does not exist: {target}'))
    return diagnostics


def _check_record(root: Path, kind: str, path: Path, all_ids: dict[str, dict[str, list[str]]]) -> list[dict]:
    relative = _relative(root, path)
    text = text_file(root, path)
    diagnostics = _links(root, path, text)
    sections = _sections(text)
    for section in REQUIRED.get(kind, ()):
        if section not in sections:
            diagnostics.append(_diagnostic('EVIDENCE_SECTION_MISSING', relative, f'missing section: {section}'))
    values = _fields(text)
    for label, value in values.items():
        if not value or value.startswith('<') or value == '—' or ' | ' in value:
            diagnostics.append(_diagnostic('EVIDENCE_FIELD_UNRESOLVED', relative, f'field remains unresolved: {label}', 'warning'))
    if kind == 'comparison':
        identifier = values.get('comparison id', '')
        if not ID_RE['comparison'].fullmatch(identifier):
            diagnostics.append(_diagnostic('COMPARISON_ID_INVALID', relative, 'Comparison ID must use C-NNN'))
        else:
            all_ids['comparison'].setdefault(identifier, []).append(relative)
    if kind == 'derivation':
        for label, pattern in [('D', re.compile(r'\bD-(\d{2})\b')), ('V', re.compile(r'\bV-(\d{2})\b'))]:
            for value in pattern.findall(text):
                all_ids[label].setdefault(f'{label}-{value}', []).append(relative)
    if kind == 'literature' and not values.get('citation key'):
        diagnostics.append(_diagnostic('LITERATURE_CITATION_KEY_MISSING', relative, 'literature record needs an explicit Citation key'))
    return diagnostics


def evidence_list(root: Path, kind: str | None = None) -> dict:
    kinds = [kind] if kind else list(KIND_NAMES)
    records = []
    for selected in kinds:
        for path in _files(root, selected):
            records.append({'kind': selected, 'path': _relative(root, path)})
    return {'records': records, 'non_claim': 'Listing identifies local records only; it does not establish source validity or scientific conclusions.'}


def evidence_check(root: Path, kind: str | None = None, selected_path: str | None = None) -> dict:
    kinds = [kind] if kind else list(KIND_NAMES)
    all_ids = {'comparison': {}, 'D': {}, 'V': {}}
    diagnostics = []
    records = []
    for selected in kinds:
        paths = _files(root, selected)
        if selected_path:
            requested = local_path(root, selected_path)
            paths = [path for path in paths if path == requested]
            if not paths:
                diagnostics.append(_diagnostic('EVIDENCE_RECORD_NOT_FOUND', selected_path, f'no {selected} record at selected path'))
        for path in paths:
            records.append({'kind': selected, 'path': _relative(root, path)})
            diagnostics.extend(_check_record(root, selected, path, all_ids))
    for kind, mapping in all_ids.items():
        for identifier, paths in mapping.items():
            if len(paths) > 1:
                diagnostics.append(_diagnostic('EVIDENCE_ID_DUPLICATE', paths[0], f'{identifier} occurs in multiple records: {", ".join(paths)}'))
    formula = formula_check(root)
    if kind in (None, 'formula-index'):
        diagnostics.extend(formula['diagnostics'])
    return {'records': records, 'diagnostics': diagnostics,
            'non_claim': 'Structural checks do not prove execution, integrity, Contract satisfaction, source authenticity, or scientific validity.'}


def _formula_rows(text: str) -> list[dict[str, str]]:
    return [{'id': match.group(1), 'description': match.group(2).strip(), 'location': match.group(3).strip(),
             'basis': match.group(4).strip(), 'status': match.group(5).strip()} for match in FORMULA_ROW.finditer(text)]


def _formula_history(root: Path) -> tuple[Path, list[str]]:
    path = local_path(root, '.workflowctl/formula-ids.json')
    if not path.exists():
        return path, []
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        values = data['allocated_ids']
        if not isinstance(values, list) or any(not isinstance(value, str) or not FORMULA_ID.fullmatch(value) for value in values):
            raise ValueError
        return path, values
    except (OSError, ValueError, KeyError, TypeError):
        raise WorkflowError('FORMULA_ID_HISTORY_INVALID', 'formula ID history is invalid; recover it before allocating IDs', str(path))


def formula_check(root: Path) -> dict:
    path = local_path(root, 'FORMULA_INDEX.md')
    history_path, history = _formula_history(root)
    diagnostics = []
    if not path.exists():
        if history:
            diagnostics.append(_diagnostic('FORMULA_INDEX_MISSING', 'FORMULA_INDEX.md', 'allocated formula IDs exist without the root Formula Index'))
        return {'records': [], 'diagnostics': diagnostics, 'allocated_ids': history}
    text = text_file(root, path)
    rows = _formula_rows(text)
    ids = [row['id'] for row in rows]
    if not history_path.exists() and ids:
        diagnostics.append(_diagnostic('FORMULA_ID_HISTORY_UNAVAILABLE', '.workflowctl/formula-ids.json',
                                       'existing Formula Index IDs are visible, but prior allocation history is unavailable; non-reuse cannot be fully established', 'warning'))
    if ids != sorted(ids, key=lambda value: int(value[2:])):
        diagnostics.append(_diagnostic('FORMULA_INDEX_ORDER_INVALID', 'FORMULA_INDEX.md', 'Formula Index IDs must be numerically ascending'))
    if len(ids) != len(set(ids)):
        diagnostics.append(_diagnostic('FORMULA_ID_DUPLICATE', 'FORMULA_INDEX.md', 'Formula Index IDs must be unique'))
    for identifier in ids:
        if identifier in history:
            continue
        history.append(identifier)
    for identifier in history:
        if identifier not in ids:
            diagnostics.append(_diagnostic('FORMULA_ID_NOT_INDEXED', 'FORMULA_INDEX.md', f'allocated formula ID is absent from the index: {identifier}'))
    for row in rows:
        if not row['description'] or not row['location'] or not row['basis'] or not row['status']:
            diagnostics.append(_diagnostic('FORMULA_INDEX_FIELD_MISSING', 'FORMULA_INDEX.md', f'incomplete row: {row["id"]}'))
        target = row['location'].strip('<>`')
        if target.startswith('[') and '](' in target:
            target = target.split('](', 1)[1].rstrip(')')
        if target and not target.startswith(('http://', 'https://')):
            try:
                if not local_path(root, target.split('#', 1)[0]).exists():
                    diagnostics.append(_diagnostic('FORMULA_LOCATION_MISSING', 'FORMULA_INDEX.md', f'{row["id"]} location does not exist: {target}'))
            except WorkflowError as exc:
                diagnostics.append(_diagnostic(exc.code, 'FORMULA_INDEX.md', f'{row["id"]} location: {exc}'))
    return {'records': [{'kind': 'formula-index', 'path': 'FORMULA_INDEX.md', 'count': len(rows)}],
            'diagnostics': diagnostics, 'allocated_ids': sorted(set(history), key=lambda value: int(value[2:]))}


def formula_allocate(root: Path, args) -> dict:
    if not args.description or not args.location or not args.basis:
        raise WorkflowError('FORMULA_INPUT_MISSING', 'description, location, and basis are required')
    index = local_path(root, 'FORMULA_INDEX.md')
    history_path, history = _formula_history(root)
    existing_text = index.read_text(encoding='utf-8') if index.exists() else '# Formula Index\n\n## 1. Formula registry\n\n| Formula ID | Short description | Current authoritative location | Basis / source locator | Status / relation |\n| --- | --- | --- | --- | --- |\n'
    rows = _formula_rows(existing_text)
    current = {row['id'] for row in rows} | set(history)
    requested = args.formula_id
    if requested and not FORMULA_ID.fullmatch(requested):
        raise WorkflowError('FORMULA_ID_INVALID', 'Formula ID must use F-NNN')
    identifier = requested or f'F-{max((int(value[2:]) for value in current), default=0) + 1:03d}'
    if identifier in current:
        raise WorkflowError('FORMULA_ID_REUSE', f'Formula ID is already allocated and cannot be reused: {identifier}')
    line = f'| {identifier} | {args.description.strip()} | {args.location.strip()} | {args.basis.strip()} | {args.status.strip()} |\n'
    updated = existing_text.rstrip() + '\n' + line
    plan = FilePlan(root)
    plan.add_directory('.workflowctl')
    plan.add(index, updated, create=not index.exists())
    plan.add(history_path, json.dumps({'version': 1, 'allocated_ids': sorted(current | {identifier}, key=lambda value: int(value[2:]))}, indent=2) + '\n', create=not history_path.exists())
    result = plan.report(args.apply)
    result.update(formula_id=identifier, detail='FORMULA_INDEX.md', non_claim='Allocation records identity only; it does not judge formula importance, correctness, provenance, or scientific validity.')
    return result


def evidence_operation(root: Path, args) -> dict:
    if args.command == 'evidence':
        if args.action == 'list':
            return evidence_list(root, args.kind)
        return evidence_check(root, args.kind, args.path)
    if args.action == 'check':
        return formula_check(root)
    return formula_allocate(root, args)
