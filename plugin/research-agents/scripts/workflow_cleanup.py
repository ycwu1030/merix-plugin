"""Human-requested local payload cleanup with retained identity and reconstruction."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from workflow_artifacts import LOCATION, HISTORY_FIELDS, _documents, _inside, _rewrite, payload_location
from workflow_integrity import differences, inventory, load_integrity
from workflow_records import FilePlan, WorkflowError, fields, local_path, one_line, registry, replace_field, timestamp


def cleanup_references(root: Path, plan: FilePlan, entry: Path, target: Path | None, entity: str, reproduction: Path | None = None) -> dict:
    """Retain locators; fail closed on live references to the selected bytes."""
    findings, blockers = [], []
    identity = re.compile(r'(?<![A-Za-z0-9-])' + re.escape(entity) + r'(?![A-Za-z0-9-])')
    for document in _documents(root, plan, (entry, entry.parent / 'payload')):
        try:
            text = plan.before[document].decode('utf-8')
        except UnicodeError:
            raise WorkflowError('ARTIFACT_DOCUMENT_UNREADABLE', 'reference safety requires readable UTF-8 project documents', document.relative_to(root).as_posix())
        path = document.relative_to(root).as_posix()
        matched, live, manifest, named = False, False, False, False
        def scan(value, historical=False):
            nonlocal matched, live, manifest, named
            if isinstance(value, dict):
                for key, item in value.items():
                    scan(item, historical or key in HISTORY_FIELDS or key in {'history', 'cleanup'})
            elif isinstance(value, list):
                for item in value:
                    scan(item, historical)
            elif isinstance(value, str):
                refers = target is not None and _rewrite(root, document, value, target, entry) != value
                manifest = manifest or _rewrite(root, document, value, entry.parent, entry) != value
                named = named or bool(identity.search(value))
                matched = matched or refers or manifest or named
                live = live or refers and not historical
        if document == reproduction:
            scan(text, historical=True)  # Explicit reconstruction output paths are retained instructions.
        elif document.suffix.lower() == '.json' or document.suffix.lower() in {'.yaml', '.yml'} and text.lstrip().startswith(('{', '[')):
            def unique(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError('duplicate key')
                    result[key] = value
                return result
            try:
                scan(json.loads(text, object_pairs_hook=unique))
            except ValueError:
                raise WorkflowError('ARTIFACT_DOCUMENT_INVALID', 'cleanup requires valid unambiguous JSON reference records', path)
        else:
            history = False
            for line in text.splitlines():
                if re.match(r'^### .* — artifact (?:.* correction|archive|cleanup|recovery completion)', line):
                    history = True
                scan(line, history or any(f'**{name}:**' in line or f'"{name}"' in line for name in HISTORY_FIELDS))
        if matched:
            findings.append({'path': path, 'live_payload_reference': live,
                             'manifest_reference': manifest, 'identity_reference': named})
        if live:
            blockers.append(path)
    return {'retained': findings, 'blocking': blockers,
            'scope': 'Known project UTF-8 text/structured references; payload/binary/external bodies are not inspected or rewritten.'}


def artifact_cleanup(root: Path, args) -> dict:
    from workflow_domain import record_check
    from workflow_relations import entity_index
    entry = local_path(root, args.path)
    if entry.is_dir():
        entry = entry / 'ARTIFACT.md'
    if entry.name != 'ARTIFACT.md' or not entry.is_relative_to(root / 'artifacts'):
        raise WorkflowError('ARTIFACT_PATH_INVALID', 'cleanup requires an existing root artifact entry')
    requester, reason = one_line(args.requested_by), one_line(args.reason)
    plan = FilePlan(root)
    plan.watch(entry)
    checked = record_check(root, str(entry), 'artifact')
    errors = [item for item in checked['diagnostics'] if item.get('severity', 'error') == 'error']
    if errors:
        raise WorkflowError(errors[0]['code'], errors[0]['message'], errors[0]['path'])
    original = plan.before[entry].decode('utf-8')
    data = fields(original)
    if data['payload status'] != 'present':
        raise WorkflowError('ARTIFACT_CLEANUP_NOT_LOCAL', 'cleanup removes only existing registered local content; retain external/cleaned records')
    target = payload_location(root, entry, data[LOCATION.lower()], data['artifact granularity'])
    reproduction = local_path(root, args.reproduction_file)
    if _inside(reproduction, entry.parent / 'payload') or not reproduction.is_file():
        raise WorkflowError('ARTIFACT_RECONSTRUCTION_REQUIRED', 'supply an existing project-local reconstruction document outside this payload')
    plan.watch(reproduction)
    try:
        steps = plan.before[reproduction].decode('utf-8').strip()
    except UnicodeError:
        raise WorkflowError('ARTIFACT_RECONSTRUCTION_REQUIRED', 'reconstruction steps must be readable UTF-8')
    if not steps or steps.startswith('<'):
        raise WorkflowError('ARTIFACT_RECONSTRUCTION_REQUIRED', 'provide actual reconstruction steps and known input/environment/access constraints')
    state = load_integrity(root, entry, plan)
    if state is None or state['baseline'] is None:
        raise WorkflowError('ARTIFACT_INTEGRITY_REQUIRED', 'record and verify a retained baseline before cleanup')
    current = inventory(root, plan, target)
    if current is None or any(differences(state['baseline'], current).values()):
        raise WorkflowError('ARTIFACT_INTEGRITY_MISMATCH', 'cleanup requires current bytes and membership to match the retained baseline')
    index = entity_index(root)
    for entity, records in index.items():
        if not entity.startswith('A-'):
            continue
        for record, _ in records:
            if record == entry:
                continue
            plan.watch(record)
            owner_data = fields(plan.before[record].decode('utf-8'))
            if owner_data.get('payload status') == 'present':
                owner = local_path(root, owner_data.get(LOCATION.lower(), ''))
                if _inside(target, owner) or _inside(owner, target):
                    raise WorkflowError('ARTIFACT_SOURCE_REGISTERED', 'cleanup content overlaps another registered artifact', record.relative_to(root).as_posix())
    references = cleanup_references(root, plan, entry, target, data['id'], reproduction)
    relation_path = local_path(root, 'relations/RELATIONS.yaml')
    plan.watch(relation_path)
    try:
        relations = registry(root)['relations']
    except ValueError as exc:
        raise WorkflowError('RELATION_INVALID', str(exc), 'relations/RELATIONS.yaml')
    references['relations'] = [edge for edge in relations if data['id'] in {edge['source'], edge['target']}]
    for edge in references['relations']:
        if edge['relation'] != 'consumes' or edge['target'] != data['id']:
            continue
        matches = index.get(edge['source'], [])
        consumer_state = None
        if len(matches) == 1:
            consumer, kind = matches[0]
            plan.watch(consumer)
            consumer_data = fields(plan.before[consumer].decode('utf-8'))
            if kind == 'task':
                consumer_state = consumer_data.get('state')
            else:
                task_ids = sorted(set(re.findall(r'T-\d{3}', consumer_data.get('root task', ''))))
                owners = index.get(task_ids[0], []) if len(task_ids) == 1 else []
                if len(owners) == 1:
                    plan.watch(owners[0][0])
                    consumer_state = fields(plan.before[owners[0][0]].decode('utf-8')).get('state')
        if consumer_state not in {'completed', 'canceled'}:
            references['blocking'].append(matches[0][0].relative_to(root).as_posix() if len(matches) == 1 else 'relations/RELATIONS.yaml')
    files = []
    for item in current['files']:
        path = target if current['root_type'] == 'file' else target / item['path']
        if path.name in {'ARTIFACT.md', 'RUN.md', 'WORK_PACKAGE.md'}:
            raise WorkflowError('ARTIFACT_SOURCE_RECORD', 'cleanup must retain authoritative workflow records', path.relative_to(root).as_posix())
        files.append(dict(item, path=path.relative_to(root).as_posix()))
    if references['blocking']:
        return {'outcome': 'blocked', 'changes': [], 'entity_id': data['id'], 'references': references,
                'diagnostics': [{'code': 'ARTIFACT_CLEANUP_REFERENCED', 'path': path,
                                 'message': 'live payload reference or unfinished/unresolved consuming task blocks cleanup; resolve current use while preserving history'}
                                for path in sorted(set(references['blocking']))]}
    # Confirmation binds every consulted file and directory, including request steps.
    snapshot = {'requester': requester, 'reason': reason, 'entry': entry.relative_to(root).as_posix(),
                'reproduction_file': reproduction.relative_to(root).as_posix(),
                'target': target.relative_to(root).as_posix(), 'files': files,
                'before': {path.relative_to(root).as_posix(): hashlib.sha256(value).hexdigest() if value is not None else None
                           for path, value in sorted(plan.before.items())},
                'directories': {path.relative_to(root).as_posix(): names for path, names in sorted(plan.directories.items())}}
    plan_id = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode('utf-8')).hexdigest()
    stamp = timestamp(root)
    event = {'status': 'cleaned', 'at': stamp, 'requested_by': requester, 'reason': reason, 'plan_id': plan_id,
             'previous_location': data[LOCATION.lower()], 'removed_files': files,
             'reconstruction': {'source': reproduction.relative_to(root).as_posix(),
                                'sha256': hashlib.sha256(plan.before[reproduction]).hexdigest(), 'steps': steps},
             'constraints': data.get('regeneration cost / constraint', ''), 'references': references}
    if state['recovery'] and state['recovery']['status'] == 'backed-up':
        event['previous_recovery'] = state['recovery'].copy()
        state['recovery'] = dict(state['recovery'], status='pending',
                                 reason='Human-requested cleanup removed the retained local backup')
    state['cleanup'] = event
    state.setdefault('cleanup_history', []).append(event.copy())
    text = replace_field(original, 'Payload status', 'cleaned')
    text = replace_field(text, 'Last updated', stamp)
    if not data.get('reproduction or reconstruction route'):
        text = replace_field(text, 'Reproduction or reconstruction route', 'Retained cleanup event in this manifest and integrity.json')
    text = text.rstrip() + f'\n\n### {stamp} — artifact cleanup\n\n'
    text += 'Historical payload location/checksums retained; local bytes deliberately removed.\n\n'
    text += '```json\n' + json.dumps(event, indent=2, ensure_ascii=False) + '\n```\n'
    plan.add(entry, text)
    plan.add(entry.parent / 'integrity.json', json.dumps(state, indent=2, ensure_ascii=False) + '\n')
    for item in files:
        plan.remove(item['path'])
    if args.apply and args.confirm_plan != plan_id:
        raise WorkflowError('ARTIFACT_CLEANUP_CONFIRMATION_REQUIRED', 'review a current preview and supply its exact --confirm-plan; changed inputs require a new review')
    result = plan.report(args.apply)
    result.update(entity_id=data['id'], detail=entry.relative_to(root).as_posix(), plan_id=plan_id,
                  cleanup=event, references=references,
                  non_claim='Human requests cleanup; retained steps do not prove successful reconstruction or scientific acceptability. Only selected local payload files are removed; all registry/related records and empty directories remain.')
    return result
