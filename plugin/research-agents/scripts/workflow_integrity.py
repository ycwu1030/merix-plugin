"""Artifact byte inventories, retained baselines, and explicit access recovery."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from workflow_records import FilePlan, WorkflowError, fields, local_path, one_line, replace_field, timestamp

LOCATION = 'Canonical payload location or controlled access route'
CHECKSUM = 'Checksum or comparable integrity identifier'
STATUS = 'Integrity check and status'
STATES = {'recorded', 'passed', 'mismatch', 'pending', 'unavailable'}


def load_integrity(root: Path, entry: Path, plan: FilePlan) -> dict | None:
    path = local_path(root, entry.parent / 'integrity.json')
    plan.watch(path)
    raw = plan.before[path]
    if raw is None:
        return None
    try:
        def unique(pairs):
            result = {}
            for name, value in pairs:
                if name in result:
                    raise ValueError('duplicate key')
                result[name] = value
            return result
        data = json.loads(raw, object_pairs_hook=unique)
        if (data['version'] != 1 or data['algorithm'] != 'sha256'
                or data['artifact_id'] != fields(plan.before[entry].decode('utf-8'))['id']
                or data['last_check']['status'] not in STATES or not isinstance(data['history'], list)):
            raise ValueError('invalid identity or status')
        baseline = data['baseline']
        expected = data.get('expected_sha256')
        if expected is not None and not re.fullmatch('[0-9a-f]{64}', expected):
            raise ValueError('invalid expected checksum')
        if data['last_check']['status'] in {'recorded', 'passed', 'mismatch'} and baseline is None and not (data['last_check']['status'] == 'mismatch' and expected):
            raise ValueError('observed integrity status requires a baseline')
        if baseline is not None:
            if baseline['root_type'] not in {'file', 'directory'} or not isinstance(baseline['files'], list) or not baseline['files']:
                raise ValueError('invalid inventory')
            names = []
            for item in baseline['files']:
                name = item['path']
                relative = Path(name)
                if (not isinstance(name, str) or relative.is_absolute() or '..' in relative.parts
                        or name != relative.as_posix() or baseline['root_type'] == 'file' and name != '.'
                        or baseline['root_type'] == 'directory' and name == '.'
                        or type(item['size_bytes']) is not int or item['size_bytes'] < 0
                        or not re.fullmatch('[0-9a-f]{64}', item['sha256'])):
                    raise ValueError('invalid file checksum')
                names.append(name)
            if len(set(names)) != len(names) or baseline['root_type'] == 'file' and len(names) != 1:
                raise ValueError('duplicate or invalid file inventory')
        recovery = data['recovery']
        if recovery is not None and (recovery['strategy'] not in {'backup', 'replace'}
                                    or not recovery['next_action'].strip() or recovery['status'] not in {'pending', 'backed-up', 'replaced'}):
            raise ValueError('invalid recovery plan')
        if recovery and recovery['status'] == 'replaced':
            from workflow_relations import entity_kind
            if (recovery['strategy'] != 'replace' or entity_kind(recovery['replacement']) != 'artifact'
                    or recovery['replacement'] == data['artifact_id'] or not recovery['resolved_at']
                    or not recovery['completion_reason'].strip() or not data.get('recovery_history')):
                raise ValueError('invalid retained replacement completion')
        if data['last_check']['status'] == 'unavailable' and recovery is None:
            raise ValueError('unavailable access requires a recovery plan')
        cleanup = data.get('cleanup')
        if cleanup is not None:
            history = data['cleanup_history']
            if baseline is None or not isinstance(history, list) or not history:
                raise ValueError('cleanup requires retained baseline and history')
            for event in [cleanup, *history]:
                if (event['status'] not in {'cleaned', 'restored'} or not event['requested_by'].strip()
                        or not event['reason'].strip() or not event['reconstruction']['steps'].strip()
                        or not event['removed_files'] or not re.fullmatch('[0-9a-f]{64}', event['plan_id'])):
                    raise ValueError('invalid retained cleanup event')
                for item in event['removed_files']:
                    if (not item['path'].startswith('artifacts/') or '..' in Path(item['path']).parts
                            or type(item['size_bytes']) is not int or item['size_bytes'] < 0
                            or not re.fullmatch('[0-9a-f]{64}', item['sha256'])):
                        raise ValueError('invalid removed-file inventory')
        return data
    except (ValueError, KeyError, TypeError, AttributeError):
        raise WorkflowError('ARTIFACT_INTEGRITY_INVALID', 'recover the retained checksum inventory; do not overwrite or reset it', path.relative_to(root).as_posix())


def inventory(root: Path, plan: FilePlan, source: Path) -> dict | None:
    """Hash exactly the declared root, including bytes staged by archival."""
    source = local_path(root, source)
    staged = [path for path, content in plan.after.items() if content is not None and path.is_relative_to(source)]
    if source in plan.after and plan.after[source] is not None or source.is_file():
        root_type, files = 'file', [source]
    elif source.is_dir() or staged:
        root_type, files = 'directory', []
        if source.is_dir():
            for path in [source, *sorted(source.rglob('*'))]:
                local_path(root, path)
                if path.is_dir():
                    plan.watch_directory(path)
                else:
                    files.append(path)
        files = sorted(set(files + staged))
    else:
        if source.exists():
            raise WorkflowError('ARTIFACT_PAYLOAD_INVALID', 'integrity checks require a regular file or directory', source.relative_to(root).as_posix())
        plan.watch(source)
        return None
    result = []
    for path in files:
        local_path(root, path)
        if path not in plan.after and not path.is_file():
            raise WorkflowError('ARTIFACT_PAYLOAD_INVALID', 'integrity inventory requires regular files', path.relative_to(root).as_posix())
        plan.watch(path)
        content = plan.after.get(path, plan.before[path])
        if content is None:
            continue
        result.append({'path': '.' if root_type == 'file' else path.relative_to(source).as_posix(),
                       'size_bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()})
    return {'root_type': root_type, 'files': result}


def differences(baseline: dict, current: dict) -> dict:
    expected = {item['path']: item for item in baseline['files']}
    actual = {item['path']: item for item in current['files']}
    return {'added': sorted(actual.keys() - expected.keys()), 'removed': sorted(expected.keys() - actual.keys()),
            'changed': sorted(name for name in expected.keys() & actual.keys() if expected[name] != actual[name]),
            'root_type_changed': baseline['root_type'] != current['root_type']}


def stage_integrity(root: Path, plan: FilePlan, entry: Path, text: str, *, source: str | None = None,
                    unavailable: str | None = None, recovery: str | None = None,
                    follow_up: str | None = None, retain_failure: bool = False,
                    require_recovery: bool = True) -> tuple[str, dict]:
    data = fields(text)
    saved = load_integrity(root, entry, plan)
    state = saved or {'version': 1, 'artifact_id': data['id'], 'algorithm': 'sha256',
                      'baseline': None, 'expected_sha256': None, 'last_check': {}, 'recovery': None, 'history': []}
    if saved is None and data.get(CHECKSUM.lower()):
        expected = re.fullmatch(r'(?:sha256:)?([0-9a-f]{64})', data[CHECKSUM.lower()])
        if not expected:
            raise WorkflowError('ARTIFACT_CHECKSUM_INPUT_INVALID', 'supply a SHA-256 file checksum or leave the CLI-owned checksum field empty; recover missing collection inventories rather than resetting them')
        state['expected_sha256'] = expected.group(1)
    stamp = timestamp(root)
    is_local = data['payload status'] == 'present'
    check = {'status': 'pending', 'checked_at': None, 'route': data[LOCATION.lower()], 'source': None}
    current = None
    if unavailable:
        check.update(status='unavailable', checked_at=stamp, reason=one_line(unavailable))
    elif is_local or source:
        observed = local_path(root, data[LOCATION.lower()] if is_local else source)
        if is_local and source and local_path(root, source) != observed:
            raise WorkflowError('ARTIFACT_SOURCE_MISMATCH', 'local verification uses the declared payload; external --source cannot replace it')
        if data['artifact granularity'] == 'single file' and observed.is_dir():
            raise WorkflowError('ARTIFACT_PAYLOAD_INVALID', 'single-file verification cannot use a directory as its source')
        try:
            current = inventory(root, plan, observed)
            access_reason = 'Declared content is not locally accessible'
        except OSError as exc:
            current, access_reason = None, 'Content could not be read: ' + str(exc)
        check.update(source=observed.relative_to(root).as_posix(), checked_at=stamp)
        if current is None:
            check.update(status='unavailable', reason=access_reason)
        elif not current['files']:
            if state['baseline'] is None:
                raise WorkflowError('ARTIFACT_SOURCE_EMPTY', 'an empty collection cannot establish a checksum baseline')
            check.update(status='mismatch', **differences(state['baseline'], current))
        elif state['baseline'] is None:
            expected = state.get('expected_sha256')
            previous = plan.before.get(entry)
            if is_local and previous is not None and not expected:
                prior = fields(previous.decode('utf-8'))
                if prior.get('payload status') in {'present', 'cleaned'}:
                    old = local_path(root, prior[LOCATION.lower()])
                    missing = (not old.exists() or old.is_dir()
                               and not any(path.is_file() for path in old.rglob('*')))
                    prior_loss = any(item.get('status') == 'unavailable'
                                     and item.get('source') == old.relative_to(root).as_posix()
                                     for item in state['history'])
                    if missing or prior_loss or prior['payload status'] == 'cleaned':
                        route = prior.get('reproduction or reconstruction route') or 'not recorded'
                        cost = prior.get('regeneration cost / constraint') or 'not recorded'
                        raise WorkflowError('ARTIFACT_RESTORATION_PROOF_REQUIRED',
                                            'Original content is missing and no retained checksum proof exists. '
                                            'Report this condition and obtain the user decision before executing '
                                            f'reconstruction. Recorded route: {route}; cost/constraint: {cost}',
                                            entry.relative_to(root).as_posix())
            if expected and (current['root_type'] != 'file' or current['files'][0]['sha256'] != expected):
                if plan.before[entry] is None:
                    raise WorkflowError('ARTIFACT_CHECKSUM_MISMATCH', 'declared checksum does not match accessible bytes; preserve the claim and investigate')
                check.update(status='mismatch', changed=[item['path'] for item in current['files']],
                             added=[], removed=[], root_type_changed=current['root_type'] != 'file')
            else:
                state['baseline'] = dict(current, recorded_at=stamp)
                check['status'] = 'recorded'
        else:
            delta = differences(state['baseline'], current)
            check.update(status='mismatch' if any(delta.values()) else 'passed', **delta)
        if current is not None and check['status'] == 'mismatch':
            check['observed'] = current
    elif data['payload status'] == 'unavailable':
        check.update(status='unavailable', checked_at=stamp, reason='Caller declared external content unavailable')
    if bool(recovery) != bool(follow_up):
        raise WorkflowError('ARTIFACT_RECOVERY_REQUIRED', 'supply both --recovery backup|replace and --follow-up')
    if check['status'] == 'unavailable':
        if recovery:
            state['recovery'] = {'strategy': recovery, 'next_action': one_line(follow_up),
                                 'reason': check['reason'], 'status': 'pending'}
        elif not state['recovery']:
            if require_recovery:
                raise WorkflowError('ARTIFACT_RECOVERY_REQUIRED', 'unavailable content requires a local-backup or replacement next action')
        else:
            state['recovery'].update(status='pending', reason=check['reason'])
    elif recovery:
        raise WorkflowError('ARTIFACT_RECOVERY_INVALID', 'a recovery plan accompanies unavailable access')
    if check['status'] in {'recorded', 'passed'} and is_local and state['recovery'] and state['recovery']['strategy'] == 'backup':
        state['recovery']['status'] = 'backed-up'
    if check['status'] in {'mismatch', 'unavailable'} and not retain_failure:
        raise WorkflowError('ARTIFACT_INTEGRITY_' + check['status'].upper(), 'content differs from the retained baseline or is unavailable; use verify to record findings and resolve before relocation')
    state['last_check'] = check
    state['history'].append(dict(check, recovery=state['recovery'].copy() if state['recovery'] else None))
    if is_local and check['status'] in {'recorded', 'passed'} and (state.get('cleanup') or {}).get('status') == 'cleaned':
        state['cleanup'] = dict(state['cleanup'], status='restored', restored_at=stamp,
                                restored_location=data[LOCATION.lower()])
        state['cleanup_history'].append(state['cleanup'].copy())
    sidecar = entry.parent / 'integrity.json'
    plan.add(sidecar, json.dumps(state, indent=2, ensure_ascii=False) + '\n', create=saved is None)
    baseline = state['baseline']
    checksum = ('sha256:' + baseline['files'][0]['sha256'] if baseline and baseline['root_type'] == 'file'
                else 'inventory: integrity.json (SHA-256 per file)' if baseline else 'pending; no accessible bytes recorded')
    if not baseline and state.get('expected_sha256'):
        checksum = 'expected sha256:' + state['expected_sha256'] + '; no matching baseline recorded'
    text = replace_field(text, CHECKSUM, checksum, section='3. Payload, access, and integrity')
    text = replace_field(text, STATUS, check['status'] + '; registry: integrity.json', section='3. Payload, access, and integrity')
    if baseline:
        size = sum(item['size_bytes'] for item in baseline['files'])
        text = replace_field(text, 'Size', f'{size} bytes; {len(baseline["files"])} file(s)', section='3. Payload, access, and integrity')
    return text, state


def artifact_verify(root: Path, args) -> dict:
    from workflow_domain import record_check
    entry = local_path(root, args.path)
    if entry.is_dir():
        entry = entry / 'ARTIFACT.md'
    if entry.name != 'ARTIFACT.md' or not entry.is_relative_to(root / 'artifacts'):
        raise WorkflowError('ARTIFACT_PATH_INVALID', 'verify requires a root artifact entry')
    if args.unavailable and (args.source or not args.reason):
        raise WorkflowError('ARTIFACT_VERIFY_INPUT_INVALID', '--unavailable requires --reason and cannot be combined with --source')
    plan = FilePlan(root)
    plan.watch(entry)
    checked = record_check(root, str(entry), 'artifact')
    errors = [item for item in checked['diagnostics'] if item.get('severity', 'error') == 'error'
              and item['code'] not in {'ARTIFACT_PAYLOAD_MISSING', 'ARTIFACT_INTEGRITY_MISSING',
                                       'ARTIFACT_INTEGRITY_MISMATCH', 'ARTIFACT_INTEGRITY_UNAVAILABLE'}]
    if errors:
        raise WorkflowError(errors[0]['code'], errors[0]['message'], errors[0]['path'])
    original = plan.before[entry].decode('utf-8')
    if fields(original)['payload status'] == 'cleaned':
        if args.source or args.unavailable or args.recovery or args.follow_up:
            raise WorkflowError('ARTIFACT_CLEANUP_STATE_INVALID', 'restore deliberately cleaned content by explicit archival/reconciliation before verification')
        return {'outcome': 'no-op', 'changes': [], 'entity_id': checked['entity_id'],
                'detail': entry.relative_to(root).as_posix(), 'integrity': load_integrity(root, entry, plan),
                'diagnostics': [{'code': 'ARTIFACT_PAYLOAD_CLEANED', 'severity': 'warning',
                                 'path': entry.relative_to(root).as_posix(),
                                 'message': 'content was deliberately cleaned; historical checksum findings retained, no current byte verification performed'}]}
    if fields(original)['payload status'] != 'present' and not args.source and not args.unavailable:
        if args.recovery or args.follow_up:
            raise WorkflowError('ARTIFACT_RECOVERY_INVALID', 'record an access failure with --unavailable and --reason before supplying recovery flags')
        saved = load_integrity(root, entry, plan)
        return {'outcome': 'no-op', 'changes': [], 'entity_id': checked['entity_id'],
                'detail': entry.relative_to(root).as_posix(), 'integrity': saved,
                'diagnostics': [{'code': 'ARTIFACT_INTEGRITY_PENDING', 'severity': 'warning',
                                 'path': entry.relative_to(root).as_posix(),
                                 'message': 'no external bytes supplied; prior observations and recovery plan retained; no current verification performed'}],
                'non_claim': 'No remote access or current byte verification occurred.'}
    text, state = stage_integrity(root, plan, entry, original, source=args.source,
                                 unavailable=args.reason if args.unavailable else None,
                                 recovery=args.recovery, follow_up=args.follow_up, retain_failure=True,
                                 require_recovery=args.apply)
    check = state['last_check']
    text = replace_field(text, 'Last updated', timestamp(root))
    plan.add(entry, text)
    result = plan.report(args.apply)
    diagnostics = []
    if check['status'] in {'mismatch', 'unavailable'}:
        diagnostics.append({'code': 'ARTIFACT_INTEGRITY_' + check['status'].upper(), 'severity': 'error',
                            'path': entry.relative_to(root).as_posix(), 'message': 'retained checksum baseline unchanged; resolve content/access findings before use'})
    elif check['status'] == 'pending':
        diagnostics.append({'code': 'ARTIFACT_INTEGRITY_PENDING', 'severity': 'warning',
                            'path': entry.relative_to(root).as_posix(), 'message': 'no accessible external bytes supplied; verification remains pending'})
    if state['recovery'] and state['recovery']['status'] == 'pending':
        diagnostics.append({'code': 'ARTIFACT_ACCESS_RECOVERY_PENDING', 'severity': 'warning',
                            'path': entry.relative_to(root).as_posix(),
                            'message': 'complete the recorded local-backup or replacement action; restored access alone does not resolve source reliability'})
    result.update(entity_id=checked['entity_id'], detail=entry.relative_to(root).as_posix(),
                  integrity=state, diagnostics=diagnostics,
                  non_claim='Checks compare bytes and membership, not scientific validity, remote availability or source authenticity. External sources are caller-selected authorized local views; no network fetch or monitoring runs.')
    return result


def artifact_recovery_complete(root: Path, args) -> dict:
    """Record a caller-selected replacement without rewriting the original source."""
    from workflow_artifact_queries import artifact_entry
    from workflow_domain import record_check
    from workflow_records import registry
    from workflow_relations import target_errors
    entry = artifact_entry(root, None, args.path)
    successor = artifact_entry(root, args.replacement, None)
    if entry == successor:
        raise WorkflowError('ARTIFACT_REPLACEMENT_INVALID', 'replacement must have its own distinct artifact identity')
    reason, plan = one_line(args.reason), FilePlan(root)
    plan.watch(entry)
    plan.watch(successor)
    checked = record_check(root, str(entry), 'artifact')
    errors = [item for item in checked['diagnostics'] if item.get('severity', 'error') == 'error'
              and item['code'] not in {'ARTIFACT_INTEGRITY_UNAVAILABLE', 'ARTIFACT_INTEGRITY_MISMATCH', 'ARTIFACT_PAYLOAD_MISSING'}]
    if errors:
        raise WorkflowError(errors[0]['code'], errors[0]['message'], errors[0]['path'])
    state = load_integrity(root, entry, plan)
    if not state or not state['recovery'] or state['recovery']['strategy'] != 'replace':
        raise WorkflowError('ARTIFACT_RECOVERY_REQUIRED', 'the original entry must have an explicit replacement recovery action')
    candidate = record_check(root, str(successor), 'artifact')
    errors = [item for item in candidate['diagnostics'] if item.get('severity', 'error') == 'error']
    if errors:
        raise WorkflowError(errors[0]['code'], errors[0]['message'], errors[0]['path'])
    original = plan.before[successor].decode('utf-8')
    if fields(original)['payload status'] in {'unavailable', 'cleaned'}:
        raise WorkflowError('ARTIFACT_REPLACEMENT_INVALID', 'replacement must be accessible and retained at its declared route')
    if fields(original)['payload status'] != 'present' and not args.source:
        raise WorkflowError('ARTIFACT_SOURCE_REQUIRED', 'an external replacement needs an authorized project-local byte view')
    relations = local_path(root, 'relations/RELATIONS.yaml')
    plan.watch(relations)
    try:
        data = registry(root)
    except ValueError as exc:
        raise WorkflowError('RELATION_INVALID', str(exc), 'relations/RELATIONS.yaml')
    matching = [edge for edge in data['relations'] if edge['source'] == args.replacement
                and edge['target'] == checked['entity_id'] and edge['relation'] == 'supersedes']
    if not matching:
        raise WorkflowError('ARTIFACT_REPLACEMENT_RELATION_REQUIRED', 'declare the selected successor through new/register --supersedes or relation add before resolving recovery')
    errors = target_errors(root, data)
    if errors:
        raise WorkflowError(errors[0]['code'], errors[0]['message'], errors[0]['path'])
    for edge in matching:
        plan.watch(edge['basis'].split('#', 1)[0])
    text, observation = stage_integrity(root, plan, successor, original, source=args.source)
    if observation['last_check']['status'] not in {'recorded', 'passed'}:
        raise WorkflowError('ARTIFACT_REPLACEMENT_INVALID', 'observe the selected replacement bytes before completing recovery')
    if observation['recovery'] and observation['recovery']['status'] == 'pending':
        raise WorkflowError('ARTIFACT_REPLACEMENT_INVALID', 'resolve the selected successor\'s own reliability action before declaring it the completed replacement')
    stamp = timestamp(root)
    text = replace_field(text, 'Last updated', stamp)
    plan.add(successor, text)
    previous = state['recovery'].copy()
    state['recovery'] = dict(previous, status='replaced', replacement=args.replacement,
                             resolved_at=stamp, completion_reason=reason,
                             relation_registry='relations/RELATIONS.yaml')
    event = {'at': stamp, 'reason': reason, 'before': previous, 'after': state['recovery'].copy(),
             'replacement_observation': observation['last_check'].copy()}
    state.setdefault('recovery_history', []).append(event)
    plan.add(entry.parent / 'integrity.json', json.dumps(state, indent=2, ensure_ascii=False) + '\n')
    old_text = replace_field(plan.before[entry].decode('utf-8'), 'Last updated', stamp)
    old_text = old_text.rstrip() + f'\n\n### {stamp} — artifact recovery completion\n\n'
    old_text += 'Original source/access facts retained; caller-selected successor recorded in the central registry.\n\n'
    old_text += '```json\n' + json.dumps(event, indent=2, ensure_ascii=False) + '\n```\n'
    plan.add(entry, old_text)
    result = plan.report(args.apply)
    result.update(entity_id=checked['entity_id'], detail=entry.relative_to(root).as_posix(),
                  replacement=args.replacement, recovery=state['recovery'], replacement_integrity=observation,
                  diagnostics=[{'code': 'ARTIFACT_REPLACEMENT_SELECTED', 'severity': 'info',
                                'path': entry.relative_to(root).as_posix(),
                                'message': 'original observations retained; successor bytes observed and caller-declared recovery completion recorded'}],
                  non_claim='No original endpoint access, scientific equivalence, future reliability or completed downstream reference migration is certified. No files are fetched or research executed.')
    return result
