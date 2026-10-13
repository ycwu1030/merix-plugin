"""Initializer reuse and explicit Run/Artifact template records; no execution."""
from __future__ import annotations

import json
from pathlib import Path
import re

from relationctl import new_relation, validate_registry
from workflow_records import FilePlan, SLUG, WorkflowError, fields, local_path, one_line, registry, replace_field, text_file, timestamp
from workflow_relations import entity_index, entity_kind, resolve_entity, target_errors

RUN_FIELDS = ['Run ID', 'Root task', 'Execution intent', 'Configuration-freeze boundary',
              'Code revision / snapshot', 'Environment manifest', 'Input manifest',
              'Randomness / seed plan and actual seed record', 'Exact invocation / entry point',
              'Planned resources', 'Overall execution disposition', 'Execution outcome']
ARTIFACT_FIELDS = ['ID', 'Name', 'Artifact granularity', 'Logical content', 'Formats / schema / units',
                   'Version or integrity identifier', 'Origin', 'Producer task / run or source locator',
                   'Payload status', 'Canonical payload location or controlled access route',
                   'Sensitivity, license, and access conditions', 'Retention reason', 'Known limitations']
ARTIFACT_GRANULARITIES = {'single file', 'coherent collection', 'manifest-only reference'}
ARTIFACT_ORIGINS = {'generated', 'external', 'user-supplied', 'derived'}
ARTIFACT_PAYLOAD_STATES = {'present', 'controlled external reference', 'restricted no-copy', 'unavailable', 'cleaned'}
ARTIFACT_REGENERATION_COSTS = {'low', 'material', 'high-cost', 'not reproducible locally'}
ARTIFACT_UPDATE_FIELDS = {
    'metadata': {'Name', 'Logical content', 'Formats / schema / units', 'Producer task / run or source locator',
                 'Sensitivity, license, and access conditions', 'Retention reason', 'Known limitations',
                 'Do not infer / do not use for', 'Safe continuation notes',
                 'Reproduction or reconstruction route', 'Regeneration cost / constraint',
                 'Retention, deletion, or external-storage boundary'},
    'location': {'Canonical payload location or controlled access route', 'Payload status'},
}


def artifact_id_plan(root: Path, plan: FilePlan, requested: str | None) -> str:
    """Plan a durable ID history update alongside the selected entry record."""
    history = local_path(root, 'artifacts/.artifact-ids.json')
    plan.watch(history)
    saved = plan.before[history]
    allocated = []
    if saved is not None:
        try:
            data = json.loads(saved)
            allocated = data['allocated_ids']
            if (data['version'] != 1 or not isinstance(allocated, list)
                    or any(not isinstance(value, str) or entity_kind(value) != 'artifact' for value in allocated)
                    or len(set(allocated)) != len(allocated)):
                raise ValueError('invalid allocation history')
        except (ValueError, KeyError, TypeError):
            raise WorkflowError('ARTIFACT_ID_HISTORY_INVALID', 'preserve or recover the valid artifact ID history; do not reset it')
    used = set(allocated)
    for entity, entries in entity_index(root).items():
        if entity_kind(entity) != 'artifact':
            continue
        if len(entries) != 1:
            raise WorkflowError('ARTIFACT_ID_DUPLICATE', f'duplicate existing artifact ID {entity}')
        used.add(entity)
        plan.watch(entries[0][0])
    if requested is not None and entity_kind(requested) != 'artifact':
        raise WorkflowError('ARTIFACT_INPUT_INVALID', 'supply a canonical positive artifact ID with at least three digits')
    entity = requested or f'A-{max((int(value[2:]) for value in used), default=0) + 1:03d}'
    if entity in used:
        raise WorkflowError('ARTIFACT_ID_DUPLICATE', 'artifact ID was already allocated and cannot be reused')
    used.add(entity)
    plan.add(history, json.dumps({'version': 1, 'allocated_ids': sorted(used, key=lambda value: int(value[2:]))},
                                indent=2) + '\n', create=saved is None)
    return entity


def record_check(root: Path, value: str, kind: str) -> dict:
    path = local_path(root, value)
    if path.is_dir():
        path = path / ('RUN.md' if kind == 'run' else 'ARTIFACT.md')
    text = text_file(root, path)
    data = fields(text)
    required = RUN_FIELDS if kind == 'run' else ARTIFACT_FIELDS
    diagnostics = []
    for label in required:
        content = data.get(label.lower(), '')
        if not content or content.startswith('<') or ' | ' in content:
            diagnostics.append({'code': f'{kind.upper()}_FIELD_MISSING', 'path': path.relative_to(root).as_posix(), 'message': f'missing explicit {label}'})
    if kind == 'artifact' and data.get('artifact granularity') and data['artifact granularity'] not in ARTIFACT_GRANULARITIES:
        diagnostics.append({'code': 'ARTIFACT_GRANULARITY_INVALID', 'path': path.relative_to(root).as_posix(),
                            'message': 'Artifact granularity must be single file, coherent collection or manifest-only reference'})
    if kind == 'artifact':
        for field, allowed, code in [('origin', ARTIFACT_ORIGINS, 'ARTIFACT_ORIGIN_INVALID'),
                                     ('payload status', ARTIFACT_PAYLOAD_STATES, 'ARTIFACT_PAYLOAD_INVALID'),
                                     ('regeneration cost / constraint', ARTIFACT_REGENERATION_COSTS, 'ARTIFACT_REGENERATION_COST_INVALID')]:
            value = data.get(field, '')
            if value and ' | ' not in value and value not in allowed:
                diagnostics.append({'code': code, 'path': path.relative_to(root).as_posix(), 'message': 'invalid declared ' + field})
    entity = data.get('run id' if kind == 'run' else 'id', '')
    if entity_kind(entity) != kind:
        diagnostics.append({'code': f'{kind.upper()}_ID_INVALID', 'path': path.relative_to(root).as_posix(), 'message': 'invalid declared ID'})
    elif len(entity_index(root).get(entity, [])) != 1:
        diagnostics.append({'code': f'{kind.upper()}_ID_DUPLICATE', 'path': path.relative_to(root).as_posix(), 'message': 'ID must identify exactly one entry record'})
    headings = len(re.findall(r'^## \d+\.', text, re.MULTILINE))
    if headings != (7 if kind == 'run' else 6):
        diagnostics.append({'code': f'{kind.upper()}_SECTIONS_INVALID', 'path': path.relative_to(root).as_posix(), 'message': 'record does not retain the accepted template sections'})
    if kind == 'artifact' and data.get('payload status') == 'present':
        payload = data.get('canonical payload location or controlled access route', '')
        try:
            from workflow_artifacts import payload_location
            target = payload_location(root, path, payload, data.get('artifact granularity', ''))
            if not target.exists():
                raise WorkflowError('ARTIFACT_PAYLOAD_MISSING', 'declared local payload does not exist')
        except WorkflowError as exc:
            diagnostics.append({'code': exc.code, 'path': path.relative_to(root).as_posix(), 'message': str(exc)})
    if kind == 'artifact':
        from workflow_integrity import load_integrity
        plan = FilePlan(root)
        plan.watch(path)
        try:
            integrity = load_integrity(root, path, plan)
            cleaned = data.get('payload status') == 'cleaned'
            cleanup = integrity.get('cleanup') if integrity else None
            if cleaned and (not cleanup or cleanup['status'] != 'cleaned') or not cleaned and cleanup and cleanup['status'] == 'cleaned':
                diagnostics.append({'code': 'ARTIFACT_CLEANUP_STATE_INVALID', 'path': path.relative_to(root).as_posix(),
                                    'message': 'payload status must agree with the retained cleanup event; restore through explicit verified archival/reconciliation'})
            elif cleaned:
                diagnostics.append({'code': 'ARTIFACT_PAYLOAD_CLEANED', 'severity': 'warning',
                                    'path': path.relative_to(root).as_posix(),
                                    'message': 'local payload deliberately cleaned; identity, historical checksums and reconstruction steps retained; restore and verify before byte-dependent use'})
            if integrity is None:
                diagnostics.append({'code': 'ARTIFACT_INTEGRITY_MISSING', 'severity': 'warning',
                                    'path': path.relative_to(root).as_posix(), 'message': 'no checksum inventory; explicitly check accessible content to adopt a baseline'})
            elif integrity['last_check']['status'] in {'pending', 'unavailable', 'mismatch'}:
                state = integrity['last_check']['status']
                replaced = integrity['recovery'] and integrity['recovery']['status'] == 'replaced'
                diagnostics.append({'code': 'ARTIFACT_INTEGRITY_' + state.upper(), 'severity': 'warning' if state == 'pending' or state == 'unavailable' and replaced else 'error',
                                    'path': path.relative_to(root).as_posix(), 'message': 'last recorded integrity status: ' + state + '; use artifact check for a current observation'})
            if integrity and integrity['recovery'] and integrity['recovery']['status'] == 'pending':
                diagnostics.append({'code': 'ARTIFACT_ACCESS_RECOVERY_PENDING', 'severity': 'warning',
                                    'path': path.relative_to(root).as_posix(), 'message': 'recorded backup or replacement action remains pending'})
            if integrity and integrity['recovery'] and integrity['recovery']['status'] == 'replaced':
                diagnostics.append({'code': 'ARTIFACT_REPLACEMENT_SELECTED', 'severity': 'info',
                                    'path': path.relative_to(root).as_posix(),
                                    'message': 'original access history retained; caller-selected replacement: ' + integrity['recovery']['replacement']})
        except WorkflowError as exc:
            diagnostics.append({'code': exc.code, 'path': path.relative_to(root).as_posix(), 'message': str(exc)})
    return {'entity_id': entity, 'detail': path.relative_to(root).as_posix(), 'fields': data,
            'diagnostics': diagnostics, 'non_claim': 'Structural record checks do not prove execution, integrity, Contract satisfaction, or scientific validity.'}


def artifact_links(root: Path, plan: FilePlan, args, path: Path, text: str, stamp: str) -> tuple[str, list[dict]]:
    """Add only explicitly declared artifact lineage to the existing authority."""
    links = ([('supersedes', args.supersedes)] if args.supersedes else [])
    links.extend(('derived_from', entity) for entity in args.derived_from)
    if not links:
        return text, []
    if not args.reason:
        raise WorkflowError('ARTIFACT_CHANGE_REASON_REQUIRED', 'supply --reason for a version or derived artifact')
    reason = one_line(args.reason)
    if not local_path(root, 'relations/RELATIONS.yaml').is_file():
        raise WorkflowError('RELATION_NOT_CONFIGURED', 'enable the existing relation registry before registering linked artifacts')
    plan.watch('relations/RELATIONS.yaml')
    data = registry(root)
    errors = target_errors(root, data)
    if errors:
        raise WorkflowError(errors[0]['code'], errors[0]['message'], errors[0]['path'])
    edges = []
    for relation, entity in links:
        target, kind = resolve_entity(root, entity)
        if kind != 'artifact':
            raise WorkflowError('ARTIFACT_LINEAGE_INVALID', 'predecessor/upstream must identify an existing artifact')
        plan.watch(target)
        edge = new_relation(data, args.entity_id, relation, entity, path.relative_to(root).as_posix(), stamp)
        edge['note'] = reason
        data['relations'].append(edge)
        edges.append(edge)
        label = 'Supersedes / succeeded by' if relation == 'supersedes' else 'Upstream artifact(s)'
        pointer = 'registry: relations/RELATIONS.yaml'
        if fields(text).get(label.lower(), '') not in {'', pointer}:
            raise WorkflowError('ARTIFACT_LINEAGE_INPUT_CONFLICT', f'use explicit lineage flags rather than a second {label} definition')
        text = replace_field(text, label, pointer)
    errors = validate_registry(data)
    if errors:
        raise WorkflowError('RELATION_INVALID', '; '.join(errors), 'relations/RELATIONS.yaml')
    plan.add('relations/RELATIONS.yaml', json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    return text, edges


def artifact_update(root: Path, args) -> dict:
    if args.change_kind == 'metadata' and (args.recovery or args.follow_up):
        raise WorkflowError('ARTIFACT_RECOVERY_INVALID', 'use unavailable verification or a location-status update for recovery inputs')
    path = local_path(root, args.path)
    if path.is_dir():
        path = path / 'ARTIFACT.md'
    if not path.is_relative_to(local_path(root, 'artifacts')) or path.name != 'ARTIFACT.md':
        raise WorkflowError('ARTIFACT_PATH_INVALID', 'update requires a root artifact entry')
    plan = FilePlan(root)
    plan.watch(path)
    original = text_file(root, path)
    checked = record_check(root, str(path), 'artifact')
    errors = [item for item in checked['diagnostics'] if item.get('severity', 'error') == 'error'
              if not (args.change_kind == 'location' and item['code'] in {'ARTIFACT_PAYLOAD_MISSING', 'ARTIFACT_PAYLOAD_LAYOUT',
                                                                         'ARTIFACT_INTEGRITY_MISMATCH', 'ARTIFACT_INTEGRITY_UNAVAILABLE'})]
    if errors:
        raise WorkflowError(errors[0]['code'], errors[0]['message'], errors[0]['path'])
    reason = one_line(args.reason)
    text, changes = original, {}
    for item in args.sets:
        if '=' not in item:
            raise WorkflowError('ARTIFACT_UPDATE_INPUT_INVALID', 'supply field=value corrections')
        name, value = item.split('=', 1)
        if name not in ARTIFACT_UPDATE_FIELDS[args.change_kind] or name in changes:
            raise WorkflowError('ARTIFACT_UPDATE_FIELD_INVALID', f'{name} is not a unique {args.change_kind} correction; register changed content as a new artifact')
        value = one_line(value)
        before = fields(text).get(name.lower(), '')
        changes[name] = {'before': before, 'after': value}
        text = replace_field(text, name, value)
    data = fields(text)
    if any(not data.get(label.lower()) or data[label.lower()].startswith('<') or ' | ' in data[label.lower()]
           for label in ARTIFACT_FIELDS):
        raise WorkflowError('RECORD_INPUT_MISSING', 'corrections must retain explicit required artifact fields')
    if 'Regeneration cost / constraint' in changes and data['regeneration cost / constraint'] not in ARTIFACT_REGENERATION_COSTS:
        raise WorkflowError('ARTIFACT_REGENERATION_COST_INVALID', 'use the declared template cost/constraint vocabulary')
    if data['payload status'] not in ARTIFACT_PAYLOAD_STATES:
        raise WorkflowError('ARTIFACT_PAYLOAD_INVALID', 'invalid payload status')
    if data['payload status'] == 'cleaned' and fields(original)['payload status'] != 'cleaned':
        raise WorkflowError('ARTIFACT_CLEANUP_REQUIRED', 'use human-requested cleanup; a location edit cannot declare content removed')
    if fields(original)['payload status'] == 'cleaned' and args.change_kind == 'location' and data['payload status'] != 'present':
        raise WorkflowError('ARTIFACT_CLEANUP_STATE_INVALID', 'restore cleaned content through an explicit present-content location and retained-baseline verification')
    documents = {'updated': [], 'historical': []}
    if data['payload status'] == 'present':
        from workflow_artifacts import payload_location, reconcile_documents
        destination = payload_location(root, path, data['canonical payload location or controlled access route'], data['artifact granularity'])
        if not destination.exists():
            raise WorkflowError('ARTIFACT_PAYLOAD_MISSING', 'declared local payload does not exist')
        before = fields(original)
        if args.change_kind == 'location' and before['payload status'] == 'present':
            old = local_path(root, before['canonical payload location or controlled access route'])
            documents = reconcile_documents(root, plan, old, destination, excluded=(old, path.parent / 'payload'))
            # Reconciliation can also update other live references in this manifest.
            base = plan.after.get(path, original.encode('utf-8')).decode('utf-8')
            for name, values in changes.items():
                base = replace_field(base, name, values['after'])
            text = base
    changes = {name: values for name, values in changes.items() if values['before'] != values['after']}
    if changes:
        stamp = timestamp(root)
        text = replace_field(text, 'Last updated', stamp)
        text = text.rstrip() + f'\n\n### {stamp} — artifact {args.change_kind} correction\n\n'
        text += f'Caller-declared unchanged object. Reason: {reason}\n\n```json\n{json.dumps(changes, indent=2, ensure_ascii=False)}\n```\n'
    integrity = None
    if args.change_kind == 'location':
        from workflow_integrity import stage_integrity
        text, integrity = stage_integrity(root, plan, path, text, recovery=args.recovery,
                                          follow_up=args.follow_up, retain_failure=data['payload status'] != 'present')
    plan.add(path, text)
    result = plan.report(args.apply)
    result.update(entity_id=checked['entity_id'], detail=path.relative_to(root).as_posix(), change_kind=args.change_kind,
                  documents=documents, integrity=integrity,
                  non_claim='Caller declares unchanged content/provenance. Record correction does not move payloads or establish scientific equivalence.')
    return result


def create_record(root: Path, args) -> dict:
    kind = args.command
    expected = RUN_FIELDS if kind == 'run' else ARTIFACT_FIELDS
    if not SLUG.fullmatch(args.topic) or (kind == 'run' and entity_kind(args.entity_id) != kind):
        raise WorkflowError(f'{kind.upper()}_INPUT_INVALID', 'supply a valid typed ID and lowercase hyphenated topic')
    if kind == 'run' and entity_index(root).get(args.entity_id):
        raise WorkflowError(f'{kind.upper()}_ID_DUPLICATE', 'declared ID already exists')
    plan = FilePlan(root)
    plan.watch(args.record_file)
    supplied = json.loads(text_file(root, args.record_file))
    if not isinstance(supplied, dict) or not all(isinstance(value, str) for value in supplied.values()):
        raise WorkflowError('RECORD_INPUT_INVALID', '--record-file must contain a JSON object of string template fields')
    source = getattr(args, 'source', None)
    operation = getattr(args, 'operation', None)
    if bool(source) != bool(operation):
        raise WorkflowError('ARTIFACT_ARCHIVE_INPUT_INVALID', '--source and --operation must be supplied together')
    if source:
        if not args.reason:
            raise WorkflowError('ARTIFACT_CHANGE_REASON_REQUIRED', 'explicit archival requires --reason')
        one_line(args.reason)
        if supplied.get('Payload status', 'present') != 'present':
            raise WorkflowError('ARTIFACT_PAYLOAD_INVALID', 'external/restricted declarations cannot be copied by archival')
        supplied['Payload status'] = 'present'
    if kind == 'artifact':
        if not local_path(root, 'artifacts').is_dir():
            raise WorkflowError('ARTIFACT_MODULE_NOT_CONFIGURED', 'explicitly enable root artifacts/ before registering records')
        if args.entity_id is not None and supplied.get('ID', args.entity_id) != args.entity_id:
            raise WorkflowError('RECORD_ID_MISMATCH', '--id differs from declared record ID')
        args.entity_id = artifact_id_plan(root, plan, args.entity_id if args.entity_id is not None else supplied.get('ID'))
    missing = [label for label in expected if label not in supplied and label not in {'Run ID', 'ID'}
               and not (source and label == 'Canonical payload location or controlled access route')]
    if missing:
        raise WorkflowError('RECORD_INPUT_MISSING', 'supply explicit fields: ' + ', '.join(missing))
    if supplied.get('ID', supplied.get('Run ID', args.entity_id)) != args.entity_id:
        raise WorkflowError('RECORD_ID_MISMATCH', '--id differs from declared record ID')
    stamp = timestamp(root)[:10]
    template = text_file(root, 'templates/' + ('RUN.md' if kind == 'run' else 'ARTIFACT.md'))
    if kind == 'run':
        workspace = local_path(root, args.work_package)
        package = fields(text_file(root, workspace / 'WORK_PACKAGE.md'))
        if entity_kind(package.get('work package id', '')) != 'work_package':
            raise WorkflowError('RUN_WORK_PACKAGE_INVALID', 'work package must declare its own stable WP-NNN ID')
        task_id = supplied['Root task'].strip(chr(96))
        _, root_kind = resolve_entity(root, task_id)
        package_task = re.search(r'T-\d{3}', package.get('root task', ''))
        if root_kind != 'task' or not package_task or package_task.group(0) != task_id:
            raise WorkflowError('RUN_TASK_MISMATCH', 'run Root task must equal the selected work package Root task ID')
        runs = local_path(root, workspace / 'runs')
        if not runs.is_dir():
            raise WorkflowError('RUN_MODULE_NOT_CONFIGURED', 'enable runs/ in the work package before creating a run record')
        path = runs / f'{args.entity_id}-{args.topic}' / 'RUN.md'
        text = template.replace('R-NNN', args.entity_id).replace('<Run Topic>', args.topic).replace('YYYY-MM-DD', stamp)
        text = replace_field(text, 'Run ID', args.entity_id)
    else:
        artifacts = local_path(root, 'artifacts')
        if not artifacts.is_dir():
            raise WorkflowError('ARTIFACT_MODULE_NOT_CONFIGURED', 'explicitly enable root artifacts/ before registering records')
        path = local_path(root, args.path) if args.action == 'register' else artifacts / f'{args.entity_id}-{args.topic}' / 'ARTIFACT.md'
        if not path.is_relative_to(artifacts) or path.name != 'ARTIFACT.md':
            raise WorkflowError('ARTIFACT_PATH_INVALID', 'artifact entry must be artifacts/<leaf>/ARTIFACT.md')
        text = template.replace('A-NNN', args.entity_id).replace('<Artifact Name>', args.topic).replace('YYYY-MM-DD', stamp)
        text = replace_field(text, 'ID', args.entity_id)
    documents = {'updated': [], 'historical': []}
    if source:
        from workflow_artifacts import archive_payload, LOCATION
        original_location = supplied.get(LOCATION)
        original_source, destination, documents = archive_payload(root, plan, path, source, operation, supplied['Artifact granularity'])
        if original_location and local_path(root, original_location) not in {original_source, destination}:
            raise WorkflowError('ARTIFACT_SOURCE_MISMATCH', 'record location must agree with --source or the archive destination')
        supplied[LOCATION] = destination.relative_to(root).as_posix()
    allowed = {name for name, _ in re.findall(r'^- \*\*(.+?):\*\*([^\n]*)$', template, re.MULTILINE)}
    for name, value in supplied.items():
        if name not in allowed:
            raise WorkflowError('RECORD_FIELD_INVALID', f'unknown template field {name}')
        text = replace_field(text, name, one_line(value))
    for label in expected:
        content = fields(text).get(label.lower(), '')
        if not content or content.startswith('<') or ' | ' in content:
            raise WorkflowError('RECORD_INPUT_MISSING', f'supply an explicit {label}')
    if kind == 'artifact':
        if fields(text)['artifact granularity'] not in ARTIFACT_GRANULARITIES:
            raise WorkflowError('ARTIFACT_GRANULARITY_INVALID', 'Artifact granularity must be single file, coherent collection or manifest-only reference')
        if supplied['Origin'] not in ARTIFACT_ORIGINS:
            raise WorkflowError('ARTIFACT_ORIGIN_INVALID', 'invalid artifact origin')
        if supplied['Payload status'] not in ARTIFACT_PAYLOAD_STATES - {'cleaned'}:
            raise WorkflowError('ARTIFACT_PAYLOAD_INVALID', 'invalid payload status')
        if 'Regeneration cost / constraint' in supplied and supplied['Regeneration cost / constraint'] not in ARTIFACT_REGENERATION_COSTS:
            raise WorkflowError('ARTIFACT_REGENERATION_COST_INVALID', 'use the declared template cost/constraint vocabulary')
        if supplied['Payload status'] == 'present':
            from workflow_artifacts import payload_location
            target = payload_location(root, path, supplied['Canonical payload location or controlled access route'], supplied['Artifact granularity'])
            if not target.exists() and not source:
                raise WorkflowError('ARTIFACT_PAYLOAD_MISSING', 'declared local payload does not exist')
    elif supplied['Overall execution disposition'] not in {'completed', 'failed', 'cancelled', 'terminated', 'incomplete'}:
        raise WorkflowError('RUN_DISPOSITION_INVALID', 'invalid execution disposition')
    links = []
    if kind == 'artifact':
        text, links = artifact_links(root, plan, args, path, text, stamp)
    if source:
        text += f'\n### {timestamp(root)} — artifact archive\n\n'
        text += f'Reason: {one_line(args.reason)}\n\n```json\n' + json.dumps(
            {'source': original_source.relative_to(root).as_posix(), 'destination': destination.relative_to(root).as_posix(),
             'operation': operation, 'documents': documents['updated']}, indent=2, ensure_ascii=False) + '\n```\n'
    integrity = None
    if kind == 'artifact':
        from workflow_integrity import stage_integrity
        plan.watch(path)
        text, integrity = stage_integrity(root, plan, path, text, recovery=args.recovery,
                                          follow_up=args.follow_up, retain_failure=True)
        plan.add_directory(path.parent / 'payload')
    plan.add(path, text, create=True)
    result = plan.report(args.apply)
    result.update(entity_id=args.entity_id, detail=path.relative_to(root).as_posix(),
                  non_claim='Record creation does not execute research or certify scientific outcomes; payload operations require explicit source/operation inputs.')
    if kind == 'artifact':
        result['id_status'] = 'registered' if args.apply else 'tentative'
        result['relations'] = links
        result['documents'] = documents
        result['integrity'] = integrity
        if source:
            result['payload'] = destination.relative_to(root).as_posix()
    return result


def work_package(root: Path, args) -> dict:
    from research_init.work_package import build_work_package_plan, apply_work_package_plan, render_work_package_report
    if args.action == 'report':
        if not SLUG.fullmatch(args.topic) or not re.fullmatch(r'T-\d{3}', args.task):
            raise WorkflowError('WORK_PACKAGE_INPUT_INVALID', 'invalid task/topic')
        path = local_path(root, f'workspaces/{args.task}-{args.topic}/WORK_PACKAGE.md')
        text = text_file(root, path)
        return {'detail': path.relative_to(root).as_posix(), 'fields': fields(text), 'record': text}
    if not args.purpose:
        raise WorkflowError('WORK_PACKAGE_PURPOSE_MISSING', 'preflight/create needs explicit --purpose')
    text_file(root, 'templates/WORK_PACKAGE.md')
    from workflow_records import task_show
    task_show(root, args.task)
    plan = build_work_package_plan(root, task_id=args.task, topic=args.topic, mode=args.mode,
                                   modules=args.module, purpose=args.purpose, date=args.date, work_package_id=args.id)
    for item in plan.paths:
        local_path(root, item.path)
    result = apply_work_package_plan(plan, apply=args.action == 'create' and args.apply)
    return {'outcome': result.outcome, 'report': render_work_package_report(plan, result),
            'diagnostics': [{'code': 'WORK_PACKAGE_CONFLICT', 'path': 'workspaces', 'message': message} for message in plan.conflicts]}


def domain_operation(root: Path, args) -> dict:
    if args.command == 'artifact':
        from workflow_artifact_cli import artifact_operation
        return artifact_operation(root, args)
    if args.command == 'work-package':
        return work_package(root, args)
    if args.action == 'check':
        return record_check(root, args.path, args.command)
    return create_record(root, args)
