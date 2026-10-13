"""Declared entity identity, leaf paths, and bounded relation operations."""
from __future__ import annotations

import json
from pathlib import Path
import re

from relationctl import connected, find_path, new_relation, validate_registry
from workflow_records import FilePlan, WorkflowError, fields, local_path, registry, text_file

KINDS = {'task': r'T-\d{3}', 'work_package': r'WP-\d{3}', 'run': r'R-\d{3}(?:-\d+)?',
         'artifact': r'A-(?:00[1-9]|0[1-9][0-9]|[1-9][0-9]{2,})', 'discussion': r'DISC-\d{3}', 'decision': r'ADR-\d{4}'}
RELATION_KINDS = {
    'depends_on': ({'task'}, {'task'}),
    'has_work_package': ({'task'}, {'work_package'}),
    'executes': ({'work_package'}, {'run'}),
    'consumes': ({'task', 'work_package', 'run'}, {'artifact'}),
    'produces': ({'task', 'work_package', 'run'}, {'artifact'}),
    'documents': ({'discussion', 'decision'}, set(KINDS)),
    'governs': ({'decision'}, set(KINDS)),
    'successor_of': ({'task'}, {'task'}),
    'supersedes': ({'artifact'}, {'artifact'}),
    'derived_from': ({'artifact'}, {'artifact'}),
}
ID_LABELS = ['id', 'task id', 'work package id', 'work-package id', 'run id', 'artifact id', 'discussion id', 'decision id']


def entity_kind(entity: str) -> str | None:
    return next((kind for kind, pattern in KINDS.items() if re.fullmatch(pattern, entity)), None)


def entity_index(root: Path) -> dict[str, list[tuple[Path, str]]]:
    index = {}
    for directory, allowed in [('tasks', {'task'}), ('decisions', {'decision'}), ('discussions', {'discussion'}),
                               ('artifacts', {'artifact'}), ('workspaces', {'work_package', 'run'}),
                               ('analysis', {'run'}), ('runs', {'run'})]:
        base = local_path(root, directory)
        if not base.exists():
            continue
        for path in base.rglob('*.md'):
            if directory == 'artifacts' and (path.name != 'ARTIFACT.md' or any(
                    parent.name == 'payload' and (parent.parent / 'ARTIFACT.md').is_file()
                    for parent in path.parents)):
                continue  # Registered contents/notes are not registry identity declarations.
            value = fields(text_file(root, path))
            declared = next((value[label] for label in ID_LABELS if label in value), None)
            kind = entity_kind(declared or '')
            if kind not in allowed:
                continue
            # Work packages and runs resolve through an entry file in a leaf directory.
            if kind == 'work_package' and path.name != 'WORK_PACKAGE.md':
                continue
            if kind == 'run' and path.name != 'RUN.md':
                continue
            index.setdefault(declared, []).append((path, kind))
    return index


def resolve_entity(root: Path, entity: str) -> tuple[Path, str]:
    if not entity_kind(entity):
        raise WorkflowError('RELATION_ID_INVALID', f'unsupported declared entity ID {entity}')
    matches = entity_index(root).get(entity, [])
    if len(matches) != 1:
        raise WorkflowError('RELATION_TARGET_DUPLICATE' if matches else 'RELATION_TARGET_MISSING',
                            f'{entity} resolves to {len(matches)} declared records', entity)
    return matches[0]


def target_errors(root: Path, data: dict) -> list[dict]:
    errors = []
    index = entity_index(root)
    for edge in data['relations']:
        kinds = {}
        for side in ['source', 'target']:
            value = edge[side]
            kind = entity_kind(value)
            kinds[side] = kind
            matches = index.get(value, [])
            if not kind:
                errors.append({'code': 'RELATION_ID_INVALID', 'path': 'relations/RELATIONS.yaml', 'message': f'{edge["id"]}: unsupported ID {value}'})
            elif len(matches) != 1:
                errors.append({'code': 'RELATION_TARGET_DUPLICATE' if matches else 'RELATION_TARGET_MISSING',
                               'path': 'relations/RELATIONS.yaml', 'message': f'{edge["id"]}: {value} resolves to {len(matches)} declared records'})
        allowed = RELATION_KINDS[edge['relation']]
        if kinds['source'] not in allowed[0] or kinds['target'] not in allowed[1]:
            errors.append({'code': 'RELATION_KIND_INVALID', 'path': 'relations/RELATIONS.yaml',
                           'message': f'{edge["id"]}: invalid entity kinds for {edge["relation"]}'})
        try:
            text_file(root, edge['basis'].split('#', 1)[0])
        except WorkflowError as exc:
            errors.append({'code': 'RELATION_BASIS_INVALID', 'path': edge['basis'], 'message': str(exc)})
    return errors


def dependency_cycle(data: dict) -> bool:
    graph = {}
    for edge in data['relations']:
        if edge['relation'] == 'depends_on':
            graph.setdefault(edge['source'], []).append(edge['target'])
    state = {}
    def visit(node):
        state[node] = 1
        for target in graph.get(node, []):
            if state.get(target) == 1 or (state.get(target, 0) == 0 and visit(target)):
                return True
        state[node] = 2
        return False
    return any(visit(node) for node in list(graph) if not state.get(node))


def relation_operation(root: Path, args) -> dict:
    data = registry(root)
    if args.action in {'validate', 'target-check', 'check'}:
        errors = target_errors(root, data)
        if dependency_cycle(data):
            errors.append({'code': 'DEPENDENCY_CYCLE', 'path': 'relations/RELATIONS.yaml', 'message': 'direct dependencies contain a cycle'})
        return {'diagnostics': errors, 'relation_count': len(data['relations'])}
    if args.action == 'show':
        resolve_entity(root, args.entity)
        return {'relations': connected(data, args.entity)}
    if args.action == 'path':
        resolve_entity(root, args.source)
        resolve_entity(root, args.target)
        path = find_path(data, args.source, args.target)
        if path is None:
            raise WorkflowError('RELATION_PATH_MISSING', f'no established path {args.source} -> {args.target}')
        return {'relations': path}
    if not local_path(root, 'relations/RELATIONS.yaml').exists():
        raise WorkflowError('RELATION_NOT_CONFIGURED', 'enable a version 1 registry before adding edges')
    edge = new_relation(data, args.source, args.relation, args.target, args.basis, args.date)
    edge['note'] = args.reason
    data['relations'].append(edge)
    errors = validate_registry(data)
    if errors:
        raise WorkflowError('RELATION_INVALID', '; '.join(errors), 'relations/RELATIONS.yaml')
    references = target_errors(root, data)
    if references:
        raise WorkflowError(references[0]['code'], references[0]['message'], references[0]['path'])
    if dependency_cycle(data):
        raise WorkflowError('DEPENDENCY_CYCLE', 'proposed dependency creates a cycle')
    plan = FilePlan(root)
    plan.add('relations/RELATIONS.yaml', json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    if args.relation == 'depends_on':
        from workflow_records import append_log, direct_dependencies, plan_views, replace_field, task_records, timestamp
        stamp = timestamp(root)
        records = task_records(root)
        path = records[args.source]
        text = replace_field(text_file(root, path), 'Depends on', ', '.join(direct_dependencies(data)[args.source]), section='1. Task identity and scope')
        text = append_log(text, stamp, f'Added explicit prerequisite {args.target}: {args.reason}')
        text = replace_field(text, 'Last updated', stamp)
        plan.add(path, text)
        affected = {args.source: (path, text), args.target: (records[args.target], text_file(root, records[args.target]))}
        plan_views(root, plan, affected, data)
    result = plan.report(args.apply)
    result['relation'] = edge
    return result
