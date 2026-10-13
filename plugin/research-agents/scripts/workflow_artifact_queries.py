"""Read-only artifact discovery, retained evidence and known reference queries."""
from __future__ import annotations

import os
from pathlib import Path

from workflow_records import FilePlan, WorkflowError, digest, fields, local_path, registry, sections, text_file


def artifact_entry(root: Path, entity: str | None, value: str | None) -> Path:
    if bool(entity) == bool(value):
        raise WorkflowError('ARTIFACT_SELECTOR_REQUIRED', 'select one artifact ID or --path')
    if entity:
        from workflow_relations import resolve_entity
        entry, kind = resolve_entity(root, entity)
        if kind != 'artifact':
            raise WorkflowError('ARTIFACT_INPUT_INVALID', 'select an artifact ID')
    else:
        entry = local_path(root, value)
        if entry.is_dir():
            entry = entry / 'ARTIFACT.md'
    if entry.name != 'ARTIFACT.md' or not entry.is_relative_to(root / 'artifacts'):
        raise WorkflowError('ARTIFACT_PATH_INVALID', 'select a root artifact manifest')
    return entry


def artifact_query(root: Path, args) -> dict:
    from workflow_domain import record_check
    from workflow_integrity import load_integrity
    if args.action == 'list':
        home = local_path(root, 'artifacts')
        if not home.is_dir():
            return {'records': [], 'count': 0, 'diagnostics': [{'code': 'ARTIFACT_MODULE_NOT_CONFIGURED',
                    'severity': 'info', 'path': 'artifacts', 'message': 'registry home is absent; no registered artifacts inferred'}]}
        entries = []
        for directory, dirs, files in os.walk(home, followlinks=False):
            current = local_path(root, directory)
            if 'ARTIFACT.md' in files:
                entries.append(local_path(root, current / 'ARTIFACT.md'))
                dirs[:] = [name for name in dirs if name != 'payload']
            for name in dirs:
                local_path(root, current / name)
        records, diagnostics = [], []
        for entry in sorted(entries):
            text = text_file(root, entry)
            data = fields(text)
            if any(selected and data.get(label) != selected for label, selected in
                   [('payload status', args.status), ('origin', args.origin), ('artifact granularity', args.granularity)]):
                continue
            if args.query and args.query.casefold() not in ' '.join(data.values()).casefold():
                continue
            checked = record_check(root, str(entry), 'artifact')
            records.append({'entity_id': checked['entity_id'], 'path': checked['detail'], 'record_hash': digest(text),
                            'name': data.get('name', ''), 'payload_status': data.get('payload status', ''),
                            'origin': data.get('origin', ''), 'granularity': data.get('artifact granularity', ''),
                            'diagnostics': checked['diagnostics']})
            diagnostics.extend(checked['diagnostics'])
        return {'records': records, 'count': len(records), 'diagnostics': diagnostics,
                'non_claim': 'Read-only manifest discovery; saved status is not current byte verification.'}
    entry = artifact_entry(root, args.artifact_id, args.path)
    checked = record_check(root, str(entry), 'artifact')
    text = text_file(root, entry)
    plan = FilePlan(root)
    plan.watch(entry)
    integrity = None
    try:
        integrity = load_integrity(root, entry, plan)
    except WorkflowError:
        pass  # record_check already exposes the exact corrupt-inventory diagnostic.
    result = dict(checked, record_hash=digest(text))
    if args.action == 'show':
        result['view'] = args.view
        if args.view == 'record':
            result.update(content=text, sections=sections(text))
        elif args.view == 'inventory':
            result.update(integrity=integrity)
        else:
            result.update(record_history=text.split('\n### ', 1)[1] if '\n### ' in text else '',
                          observations=integrity['history'] if integrity else [],
                          cleanup_history=integrity.get('cleanup_history', []) if integrity else [],
                          recovery_history=integrity.get('recovery_history', []) if integrity else [],
                          recovery=integrity['recovery'] if integrity else None)
    else:
        from workflow_cleanup import cleanup_references
        from workflow_artifacts import LOCATION
        data = fields(text)
        target = local_path(root, data[LOCATION.lower()]) if data.get('payload status') in {'present', 'cleaned'} else None
        result['references'] = cleanup_references(root, plan, entry, target, data.get('id', ''))
        relation_path = local_path(root, 'relations/RELATIONS.yaml')
        try:
            result['relations'] = [edge for edge in registry(root)['relations']
                                   if data.get('id') in {edge['source'], edge['target']}]
        except ValueError as exc:
            raise WorkflowError('RELATION_INVALID', str(exc), 'relations/RELATIONS.yaml')
        result['relations_configured'] = relation_path.is_file()
        result['non_claim'] = 'Known text/structured references and declared central edges; binary/payload/external bodies and undeclared scientific use are not inferred.'
    return result
