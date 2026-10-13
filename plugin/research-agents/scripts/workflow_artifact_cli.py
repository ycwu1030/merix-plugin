"""Six artifact operations, routed to the shared record and file transactions."""
from __future__ import annotations

import argparse
from pathlib import Path

from workflow_artifact_queries import artifact_entry, artifact_query
from workflow_records import WorkflowError, local_path

CORE = ('new', 'list', 'update', 'store', 'check', 'cleanup')


def configure_parser(command, action: str) -> None:
    from workflow_domain import ARTIFACT_GRANULARITIES, ARTIFACT_ORIGINS, ARTIFACT_PAYLOAD_STATES
    if action in {'new', 'register'}:
        command.add_argument('--record-file', type=Path, required=True)
        command.add_argument('--id', dest='entity_id')
        command.add_argument('--topic', required=True)
        command.add_argument('--path', required=action == 'register', help='Destination entry directory or ARTIFACT.md.')
        command.add_argument('--supersedes')
        command.add_argument('--derived-from', action='append', default=[])
        command.add_argument('--source')
        command.add_argument('--operation', choices=['copy', 'move'])
        command.add_argument('--reason')
    else:
        command.add_argument('artifact_id', nargs='?')
        command.add_argument('--path', help='Select an entry directory or ARTIFACT.md instead of an ID.')
    if action in {'list', 'show'}:
        command.add_argument('--view', choices=['record', 'inventory', 'history', 'references'],
                             default='record' if action == 'show' else None)
    if action == 'list':
        command.add_argument('--query')
        command.add_argument('--status', choices=sorted(ARTIFACT_PAYLOAD_STATES))
        command.add_argument('--origin', choices=sorted(ARTIFACT_ORIGINS))
        command.add_argument('--granularity', choices=sorted(ARTIFACT_GRANULARITIES))
    if action == 'update':
        command.add_argument('--change-kind', choices=['metadata', 'location', 'recovery'], required=True)
        command.add_argument('--set', dest='sets', action='append', default=[])
        command.add_argument('--replacement')
        command.add_argument('--source', help='Authorized local byte view for replacement completion only.')
    if action in {'store', 'archive'}:
        command.add_argument('--source', required=action == 'archive', help='Defaults to the recorded accessible local source.')
        command.add_argument('--operation', choices=['copy', 'move'], required=True)
    if action == 'reconcile':
        command.add_argument('--location', required=True)
    if action in {'check', 'verify'}:
        command.add_argument('--source', help='Authorized project-local view of external bytes; read only.')
        command.add_argument('--unavailable', action='store_true')
        command.add_argument('--reason')
    if action == 'check':
        command.add_argument('--records-only', action='store_true')
        command.add_argument('--all', action='store_true', help='Read-only check of every registered artifact.')
    if action in {'new', 'register', 'update', 'check', 'verify'}:
        command.add_argument('--recovery', choices=['backup', 'replace'])
        command.add_argument('--follow-up')
    if action == 'cleanup':
        command.add_argument('--requested-by', required=True)
        command.add_argument('--reproduction-file', required=True)
        command.add_argument('--confirm-plan')
    if action == 'recovery-complete':
        command.add_argument('--replacement', required=True)
        command.add_argument('--source')
    if action in {'update', 'store', 'archive', 'reconcile', 'cleanup', 'recovery-complete'}:
        command.add_argument('--reason', required=True)
    if action not in {'list', 'show', 'references'}:
        command.add_argument('--apply', action='store_true')


def routed(args, **changes):
    return argparse.Namespace(**(vars(args) | changes))


def invalid(message: str) -> None:
    raise WorkflowError('ARTIFACT_INPUT_INVALID', message)


def selected_query(root: Path, args) -> dict:
    selected = bool(args.artifact_id or args.path)
    if args.action == 'list':
        filtered = any(getattr(args, name) for name in ('query', 'status', 'origin', 'granularity'))
        if selected and filtered or not selected and args.view:
            invalid('collection filters require no selector; --view requires one ID or --path')
        if not selected:
            return artifact_query(root, args)
    action = 'references' if args.action == 'references' or args.view == 'references' else 'show'
    return artifact_query(root, routed(args, action=action, view=getattr(args, 'view', None) or 'record'))


def artifact_check(root: Path, args) -> dict:
    from workflow_domain import record_check
    from workflow_integrity import artifact_verify
    byte_options = any((args.source, args.unavailable, args.reason, args.recovery, args.follow_up))
    if args.records_only and (args.apply or byte_options):
        invalid('--records-only cannot save observations or accept byte/access/recovery inputs')
    if args.all:
        if args.artifact_id or args.path or args.apply or byte_options:
            invalid('--all is read only and cannot be combined with a selector or per-artifact observation inputs')
        listing = artifact_query(root, routed(args, action='list', query=None, status=None, origin=None, granularity=None))
        results = [artifact_check(root, routed(args, all=False, artifact_id=None, path=item['path']))
                   for item in listing['records']]
        return {'records': results, 'count': len(results),
                'diagnostics': [finding for item in results for finding in item['diagnostics']] +
                               [item for item in listing['diagnostics'] if item['code'] == 'ARTIFACT_MODULE_NOT_CONFIGURED']}
    entry = artifact_entry(root, args.artifact_id, args.path)
    checked = record_check(root, str(entry), 'artifact')
    result = dict(checked, record_check=checked)
    if args.records_only:
        result['content_check'] = {'status': 'not-observed', 'observed': False, 'verified': False}
        return result
    # Saved byte failures belong to historical evidence, not a fresh observation.
    physical = {'ARTIFACT_PAYLOAD_MISSING', 'ARTIFACT_INTEGRITY_MISMATCH', 'ARTIFACT_INTEGRITY_UNAVAILABLE'}
    structure = [item for item in checked['diagnostics'] if item['code'] not in physical]
    if any(item.get('severity', 'error') == 'error' for item in structure):
        result.update(diagnostics=structure, content_check={'status': 'blocked', 'observed': False, 'verified': False})
        return result
    observation = artifact_verify(root, routed(args, path=str(entry)))
    payload_status = checked['fields'].get('payload status')
    observed = payload_status != 'cleaned' and (payload_status == 'present' or bool(args.source) or args.unavailable)
    state = observation.get('integrity')
    status = state['last_check']['status'] if observed and state else 'cleaned' if payload_status == 'cleaned' else 'not-observed'
    result.update(observation)
    # Fresh access findings replace saved access warnings at the top level.
    stale = {'ARTIFACT_INTEGRITY_PENDING', 'ARTIFACT_INTEGRITY_MISSING', 'ARTIFACT_ACCESS_RECOVERY_PENDING', 'ARTIFACT_PAYLOAD_CLEANED'}
    result['diagnostics'] = [item for item in structure if item['code'] not in stale] + observation.get('diagnostics', [])
    result['content_check'] = {'status': status, 'observed': observed, 'verified': observed and status == 'passed',
                               'persisted': bool(args.apply and observed)}
    return result


def artifact_store(root: Path, args) -> dict:
    from workflow_artifacts import artifact_archive, LOCATION
    from workflow_domain import record_check
    from workflow_integrity import artifact_verify
    entry = artifact_entry(root, args.artifact_id, args.path)
    checked = record_check(root, str(entry), 'artifact')
    repairable = {'ARTIFACT_PAYLOAD_LAYOUT', 'ARTIFACT_PAYLOAD_MISSING',
                  'ARTIFACT_INTEGRITY_MISMATCH', 'ARTIFACT_INTEGRITY_UNAVAILABLE'}
    errors = [item for item in checked['diagnostics']
              if item.get('severity', 'error') == 'error' and item['code'] not in repairable]
    if errors:
        raise WorkflowError(errors[0]['code'], errors[0]['message'], errors[0]['path'])
    data = checked['fields']
    source = args.source
    if not source and data.get('payload status') in {'present', 'cleaned'}:
        candidate = local_path(root, data[LOCATION.lower()])
        if candidate.is_file() or candidate.is_dir() and any(path.is_file() for path in candidate.rglob('*')):
            source = candidate.relative_to(root).as_posix()
    if not source:
        raise WorkflowError('ARTIFACT_SOURCE_REQUIRED',
                            'no accessible recorded local source; supply an authorized candidate with --source. '
                            'Lost/cleaned originals require retained checksum proof; otherwise ask the user whether to reconstruct. '
                            'Recorded route: ' + data.get('reproduction or reconstruction route', 'not recorded') +
                            '; cost/constraint: ' + data.get('regeneration cost / constraint', 'not recorded'))
    source_path = local_path(root, source)
    held = (data.get('payload status') in {'present', 'cleaned'}
            and source_path.is_relative_to(entry.parent / 'payload')
            and source_path == local_path(root, data[LOCATION.lower()]))
    if held:
        if data['payload status'] == 'present':
            observation = artifact_verify(root, routed(args, path=str(entry), apply=False, source=None,
                                                       unavailable=False, recovery=None, follow_up=None))
            if any(item.get('severity', 'error') == 'error' for item in observation['diagnostics']):
                return observation
            from workflow_records import FilePlan
            from workflow_integrity import load_integrity
            plan = FilePlan(root)
            plan.watch(entry)
            saved = load_integrity(root, entry, plan)
            if (saved and saved['last_check']['status'] in {'recorded', 'passed'}
                    and not (saved['recovery'] and saved['recovery']['status'] == 'pending')):
                return {'outcome': 'no-op', 'entity_id': data['id'], 'detail': entry.relative_to(root).as_posix(),
                        'payload': source_path.relative_to(root).as_posix(), 'changes': [], 'diagnostics': [],
                        'integrity': saved, 'content_check': {'status': 'passed', 'observed': True, 'verified': True, 'persisted': False},
                        'source_origin': 'explicit' if args.source else 'record'}
        result = artifact_archive(root, routed(args, action='reconcile', path=str(entry), location=source))
    else:
        result = artifact_archive(root, routed(args, action='archive', path=str(entry), source=source))
    result['source_origin'] = 'explicit' if args.source else 'record'
    return result


def artifact_operation(root: Path, args) -> dict:
    from workflow_domain import artifact_update, create_record
    from workflow_artifacts import artifact_archive
    from workflow_integrity import artifact_recovery_complete, artifact_verify
    if args.action in {'list', 'show', 'references'}:
        return selected_query(root, args)
    if args.action in {'new', 'register'}:
        if args.path:
            entry = local_path(root, args.path)
            if entry.name != 'ARTIFACT.md':
                entry = entry / 'ARTIFACT.md'
            args = routed(args, action='register', path=str(entry))
        return create_record(root, args)
    if args.action == 'check':
        return artifact_check(root, args)
    if args.action == 'store':
        return artifact_store(root, args)
    entry = artifact_entry(root, args.artifact_id, args.path)
    args = routed(args, path=str(entry))
    if args.action == 'update':
        if args.change_kind == 'recovery':
            if not args.replacement or args.sets or args.recovery or args.follow_up:
                invalid('recovery completion requires --replacement; --set/--recovery/--follow-up are not completion inputs')
            return artifact_recovery_complete(root, args)
        if not args.sets or args.source or args.replacement:
            invalid('metadata/location updates require --set and cannot accept replacement completion inputs')
        return artifact_update(root, args)
    if args.action == 'verify':
        return artifact_verify(root, args)
    if args.action == 'recovery-complete':
        return artifact_recovery_complete(root, args)
    if args.action in {'archive', 'reconcile'}:
        return artifact_archive(root, args)
    from workflow_cleanup import artifact_cleanup
    return artifact_cleanup(root, args)
