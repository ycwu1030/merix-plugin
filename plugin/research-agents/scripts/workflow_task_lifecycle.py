"""Task queries, bounded record patches, and the six-state lifecycle."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re

from task_board_check import LEGACY_STATES, PRIORITIES, READINESS, STATES
from workflow_handoff import handoff, heading_anchor, record_link_path
from workflow_records import (EDITABLE, FilePlan, WorkflowError, append_log, digest,
                              direct_dependencies, fields, local_path, one_line,
                              plan_views, registry, replace_field, sections,
                              task_path, task_records, task_show, text_file, timestamp)

ACTION_EDGES = {
    'start': {('backlog', 'active')},
    'pause': {('active', 'paused'), ('in_review', 'paused')},
    'resume': {('paused', 'active')},
    'submit': {('active', 'in_review')},
    'revise': {('in_review', 'active')},
    'complete': {('in_review', 'completed')},
    'cancel': {('backlog', 'canceled'), ('active', 'canceled'),
               ('paused', 'canceled'), ('in_review', 'canceled')},
    'reopen': {('completed', 'active')},
}
SNAPSHOT = {name.lower().replace(' / ', '_').replace(' ', '_'): name for name in EDITABLE}
SECTION_NAMES = {'work_log': 'Work log', 'evidence': 'Evidence and outputs',
                 'risks': 'Risks, limitations, and blockers', 'handoff': 'Handoff'}
META = re.compile(r'^### Lifecycle evidence\n\n```json\n(.*?)\n```\n?', re.MULTILINE | re.DOTALL)


def object_keys(value, allowed: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) - allowed:
        if isinstance(value, dict) and any(key.lower() == 'state' for key in value):
            raise WorkflowError('USE_LIFECYCLE_COMMAND', 'State changes require a lifecycle command')
        raise WorkflowError('TASK_INPUT_INVALID', f'{label} must be an object with only: {sorted(allowed)}')
    return value


def input_data(root: Path, args, plan: FilePlan) -> dict:
    value = getattr(args, 'input', None)
    if not value:
        return {}
    plan.watch(value)
    data = json.loads(text_file(root, value))
    allowed = {'snapshot', 'plan', 'sections'}
    if getattr(args, 'action', '') == 'submit':
        allowed.add('submission')
    if getattr(args, 'action', '') in {'pause', 'update'}:
        allowed.add('pause')
    return object_keys(data, allowed, 'operation input')


def section_span(text: str, title: str) -> tuple[int, int]:
    match = re.search(r'^## (?:\d+\. )?' + re.escape(title) + r'\n', text, re.MULTILINE)
    if not match:
        raise WorkflowError('TASK_SECTION_MISSING', f'missing section {title}')
    following = re.search(r'^## ', text[match.end():], re.MULTILINE)
    return match.end(), match.end() + following.start() if following else len(text)


def lifecycle_data(text: str) -> dict:
    start, end = section_span(text, 'Handoff')
    matches = list(META.finditer(text[start:end]))
    if len(matches) > 1:
        raise WorkflowError('TASK_LIFECYCLE_INVALID', 'duplicate lifecycle evidence blocks')
    if not matches:
        return {}
    data = json.loads(matches[0].group(1))
    data = object_keys(data, {'pause', 'submission', 'review'}, 'lifecycle evidence')
    if 'pause' in data:
        pause = object_keys(data['pause'], {'reasons', 'paused_at', 'next_action', 'resolved_at', 'resolution_basis'}, 'pause evidence')
        pause_reasons(pause)
    if 'review' in data:
        review = object_keys(data['review'], {'ref', 'version', 'fingerprint'}, 'review evidence')
        for key in ['ref', 'version', 'fingerprint']:
            one_line(review.get(key))
    return data


def pause_reasons(value: dict) -> list[dict]:
    reasons = value.get('reasons')
    if not isinstance(reasons, list) or not reasons:
        raise WorkflowError('TASK_INPUT_INVALID', 'pause.reasons must be a nonempty list')
    output = []
    for item in reasons:
        item = object_keys(item, {'reason', 'resume_when'}, 'pause reason')
        output.append({key: one_line(item.get(key)) for key in ['reason', 'resume_when']})
    return output


def write_lifecycle(text: str, data: dict) -> str:
    start, end = section_span(text, 'Handoff')
    body = text[start:end]
    block = '### Lifecycle evidence\n\n```json\n' + json.dumps(data, indent=2, ensure_ascii=False) + '\n```\n'
    match = META.search(body)
    body = body[:match.start()] + block + body[match.end():] if match else body.rstrip() + '\n\n' + block + '\n'
    return text[:start] + body + text[end:]


def patch_record(root: Path, original: str, args, plan: FilePlan) -> tuple[str, dict]:
    data = input_data(root, args, plan)
    changes = {}
    for assignment in getattr(args, 'set', []):
        name, separator, value = assignment.partition('=')
        if name.lower() == 'state':
            raise WorkflowError('USE_LIFECYCLE_COMMAND', 'State changes require start/pause/resume/submit/revise/complete/cancel/reopen')
        if not separator or name not in EDITABLE or name in changes:
            raise WorkflowError('TASK_FIELD_INVALID', f'unsupported or duplicate task field: {name}')
        changes[name] = one_line(value)
    for key, value in object_keys(data.get('snapshot', {}), set(SNAPSHOT), 'snapshot').items():
        name = SNAPSHOT[key]
        if name in changes:
            raise WorkflowError('TASK_INPUT_INVALID', f'duplicate field from --set and input: {name}')
        changes[name] = one_line(value)
    before = fields(original)
    if 'pause' in data and getattr(args, 'action', '') == 'update':
        if before.get('state') != 'paused':
            raise WorkflowError('TASK_INPUT_INVALID', 'same-state pause updates require State paused')
        pause = object_keys(data['pause'], {'reasons'}, 'pause')
        evidence = lifecycle_data(original)
        evidence['pause'] = {'reasons': pause_reasons(pause), 'paused_at': timestamp(root),
                             'next_action': before.get('next action')}
        original_pause = json.dumps(lifecycle_data(original).get('pause', {}), ensure_ascii=False)
        original = append_log(original, timestamp(root), 'Updated pause causes; prior context: ' + original_pause)
        original = write_lifecycle(original, evidence)
    protected = {'Objective', 'Scope', 'Acceptance', 'Deliverable / intended audience', 'Current result'}
    if before.get('state') in {'completed', 'canceled'} and getattr(args, 'action', '') != 'reopen':
        if any(name in protected and before.get(name.lower()) != value.strip('`') for name, value in changes.items()) or 'plan' in data:
            raise WorkflowError('TASK_TERMINAL_EDIT', 'substantive terminal changes require reopening the original goal or a successor')
    if getattr(args, 'action', '') == 'reopen':
        if any(name in protected - {'Current result'} for name in changes):
            raise WorkflowError('TASK_REOPEN_OBJECTIVE', 'reopen retains the original goal and acceptance; independent work needs a successor')
    text = original
    for name, value in changes.items():
        if name == 'Resume entry' and value != before.get('resume entry'):
            match = re.search(r'\]\(([^)]+)\)', value)
            target = match.group(1) if match else value.strip('`')
            path_part, separator, anchor = target.partition('#')
            if path_part and target != '—':
                canonical, _ = reference(root, target, plan)
                destination, _, fragment = canonical.partition('#')
                record = task_path(root, before['id'])
                link = Path(os.path.relpath(root / destination, record.parent)).as_posix()
                value = '[resume entry](' + link + ('#' + fragment if separator else '') + ')'
        section = '1. Task identity and scope' if name in {'Objective', 'Scope', 'Out of scope', 'Acceptance', 'Deliverable / intended audience', 'External tracker ID', 'Priority', 'Readiness'} else '2. Current snapshot'
        text = replace_field(text, name, value, section=section)
    if 'plan' in data:
        living = object_keys(data['plan'], {'version', 'steps'}, 'plan')
        version = one_line(living.get('version'))
        if 'Implementation plan version' in changes and changes['Implementation plan version'].strip('`') != version:
            raise WorkflowError('TASK_PLAN_VERSION_DRIFT', 'input plan and snapshot versions disagree')
        steps = living.get('steps')
        if not isinstance(steps, list) or not steps:
            raise WorkflowError('TASK_INPUT_INVALID', 'plan.steps must be a nonempty list')
        lines, ids = [], set()
        for item in steps:
            item = object_keys(item, {'id', 'text', 'completed'}, 'plan step')
            step = one_line(item.get('id'))
            if not re.fullmatch(r'S\d+', step) or step in ids or type(item.get('completed', False)) is not bool:
                raise WorkflowError('TASK_INPUT_INVALID', 'plan steps need unique S-number IDs and boolean completed values')
            ids.add(step)
            lines.append(f"- [{'x' if item.get('completed', False) else ' '}] `{step}`: {one_line(item.get('text'))}")
        start, end = section_span(text, 'Work log')
        body = text[start:end]
        match = re.search(r'^### Implementation plan\n.*?(?=^### |\Z)', body, re.MULTILINE | re.DOTALL)
        if not match:
            raise WorkflowError('TASK_PLAN_MISSING', 'missing living Implementation plan')
        if before.get('plan version') == version and lines != re.findall(r'^- \[[ xX]\] `S\d+`:.*$', match.group(0), re.MULTILINE):
            raise WorkflowError('TASK_PLAN_VERSION_REQUIRED', 'changed steps require a new plan version')
        block = '### Implementation plan\n\n- **Plan version:** `' + version + '`\n' + '\n'.join(lines) + '\n\n'
        previous = '\n'.join('> ' + line for line in match.group(0).strip().splitlines())
        text = text[:start] + body[:match.start()] + block + body[match.end():] + text[end:]
        text = replace_field(text, 'Implementation plan version', version)
        text = append_log(text, timestamp(root), 'Living plan revised; previous plan retained below.')
        start, end = section_span(text, 'Work log')
        text = text[:end].rstrip() + '\n\n' + previous + '\n\n' + text[end:]
    elif 'Implementation plan version' in changes:
        text = replace_field(text, 'Plan version', changes['Implementation plan version'])
    for key, value in object_keys(data.get('sections', {}), set(SECTION_NAMES), 'sections').items():
        if not isinstance(value, str) or not value.strip() or re.search(r'^## |^### (?:Lifecycle evidence|Implementation plan)|^- \*\*(?:State|ID|Plan version|Implementation plan version):', value, re.MULTILINE):
            raise WorkflowError('TASK_INPUT_INVALID', 'section patches append prose, not headings or lifecycle/identity/plan replacements')
        start, end = section_span(text, SECTION_NAMES[key])
        text = text[:end].rstrip() + '\n\n' + value.strip() + '\n\n' + text[end:]
    return text, data


def validate_patch(root: Path, path: Path, text: str) -> None:
    data = fields(text)
    for key, allowed in [('priority', PRIORITIES), ('readiness', READINESS)]:
        if data.get(key) not in allowed:
            raise WorkflowError('TASK_FIELD_INVALID', f'invalid {key}: {data.get(key)}', str(path))
    step = data.get('current step')
    if step != '—' and not re.search(r'^- \[[ xX]\]\s*`' + re.escape(step or '') + r'`:', text, re.MULTILINE):
        raise WorkflowError('TASK_PLAN_STEP_INVALID', 'current step must exist in the living plan')
    if data.get('implementation plan version') != data.get('plan version'):
        raise WorkflowError('TASK_PLAN_VERSION_DRIFT', 'snapshot and living plan versions disagree')


def reference(root: Path, value: str, plan: FilePlan | None = None) -> tuple[str, str]:
    value = one_line(value)
    path_part, _, anchor = value.partition('#')
    path = local_path(root, path_part)
    if plan:
        plan.watch(path)
    text = text_file(root, path)
    if anchor:
        headings = list(re.finditer(r'^(#{1,6}) ([^\n]+)\n?', text, re.MULTILINE))
        matches = [m for m in headings if heading_anchor(m.group(2)) == anchor]
        if len(matches) != 1:
            raise WorkflowError('REVIEW_ANCHOR_INVALID', 'reference must identify one existing heading', value)
        match = matches[0]
        end = next((m.start() for m in headings if m.start() > match.start() and len(m.group(1)) <= len(match.group(1))), len(text))
        text = text[match.start():end]
    return path.relative_to(root).as_posix() + ('#' + anchor if anchor else ''), text


def submission_record(root: Path, path: Path, text: str, value: dict, plan: FilePlan | None = None) -> dict:
    value = object_keys(value, {'version', 'targets', 'verification_refs', 'limitations', 'fingerprint'}, 'submission')
    version = one_line(value.get('version'))
    targets = value.get('targets')
    refs = value.get('verification_refs')
    if not isinstance(targets, list) or not targets or not isinstance(refs, list):
        raise WorkflowError('REVIEW_INPUT_REQUIRED', 'submission needs targets and explicit verification_refs lists')
    if not refs and not value.get('limitations'):
        raise WorkflowError('REVIEW_INPUT_REQUIRED', 'provide verification references or explicit verification limitations')
    fingerprints = {}
    for target in targets:
        name, content = reference(root, target, plan)
        target_path, _, anchor = name.partition('#')
        if root / target_path == path and (not anchor or anchor in {'1-task-identity-and-scope', '2-current-snapshot', '4-work-log', '8-handoff'}):
            raise WorkflowError('REVIEW_TARGET_DYNAMIC_RECORD', 'select stable result evidence, not the mutable task record or control sections', name)
        if name in fingerprints:
            raise WorkflowError('REVIEW_INPUT_INVALID', 'duplicate submission target', name)
        fingerprints[name] = digest(content)
    canonical_refs = [reference(root, ref, plan)[0] for ref in refs]
    task_fields = fields(text)
    context = {key: task_fields.get(key) for key in ['objective', 'scope', 'acceptance']}
    if any(not value for value in context.values()):
        raise WorkflowError('REVIEW_INPUT_REQUIRED', 'objective/scope/acceptance must be recorded')
    fingerprint = digest(json.dumps({'targets': fingerprints, 'context': context}, sort_keys=True))
    limitations = one_line(value['limitations']) if value.get('limitations') else ''
    return {'version': version, 'targets': list(fingerprints), 'verification_refs': canonical_refs,
            'limitations': limitations, 'fingerprint': fingerprint}


def approval_record(root: Path, task_id: str, text: str, ref: str, version: str, plan: FilePlan | None = None) -> dict:
    submission = lifecycle_data(text).get('submission')
    if not isinstance(submission, dict):
        raise WorkflowError('REVIEW_INPUT_REQUIRED', 'no recorded submission')
    current = submission_record(root, task_path(root, task_id), text, submission, plan)
    if current['fingerprint'] != submission.get('fingerprint'):
        raise WorkflowError('REVIEW_STALE_SUBMISSION', 'submitted targets or objective/scope/acceptance changed')
    if version != submission.get('version'):
        raise WorkflowError('REVIEW_VERSION_MISMATCH', 'review version differs from current submission')
    name, content = reference(root, ref, plan)
    review = fields(content)
    expected = {'task id': task_id, 'submission version': version, 'submission fingerprint': current['fingerprint']}
    if review.get('review result') not in {'approved', 'passed'} or any(review.get(key) != val for key, val in expected.items()):
        raise WorkflowError('REVIEW_APPROVAL_REQUIRED', 'review source must record approved/passed, Task ID, Submission version and Submission fingerprint', name)
    return {'ref': name, 'version': version, 'fingerprint': current['fingerprint']}


def active_conditions(root: Path, task_id: str, text: str, plan: FilePlan, executable: Path | None) -> None:
    values = fields(text)
    if values.get('readiness') != 'ready' or values.get('blocker') not in {'—', '`—`'}:
        raise WorkflowError('TASK_NOT_READY', 'active entry requires ready and no recorded blocker; explicitly update resolved conditions')
    for key in ['objective', 'scope', 'acceptance', 'next action']:
        if not values.get(key) or values[key] == '—':
            raise WorkflowError('TASK_CONTEXT_REQUIRED', f'active entry needs {key}')
    data = registry(root)
    from workflowctl import DEPENDENCY_GRAPH_ERRORS, dependency_diagnostics
    diagnostics, _ = dependency_diagnostics(root)
    for item in diagnostics:
        if item.is_error and item.code in DEPENDENCY_GRAPH_ERRORS and not item.code.startswith('VIEW_'):
            raise WorkflowError(item.code, item.message, item.path)
    for prerequisite in direct_dependencies(data).get(task_id, []):
        report = task_show(root, prerequisite)
        plan.watch(report['detail'])
        if text_file(root, report['detail']) != report['record']:
            raise WorkflowError('WRITE_CONFLICT', 'prerequisite changed while loading', report['detail'])
        if report['fields'].get('state') != 'completed' or report['fields'].get('readiness') != 'completed':
            raise WorkflowError('DEPENDENCY_NOT_ELIGIBLE', f'{prerequisite} must be completed/completed')
        external = (report['fields'].get('external tracker id') or report['fields'].get('taskboard id') or report['fields'].get('taskboard'))
        if external and external != '—':
            if not executable:
                raise WorkflowError('DEPENDENCY_LIVE_STATUS_UNVERIFIED', f'{prerequisite} has an external tracker; supply --taskctl to verify live completion')
            from workflow_sync import Taskboard
            if Taskboard(executable).issue(external).get('status') != 'done':
                raise WorkflowError('DEPENDENCY_EXTERNAL_NOT_DONE', f'{prerequisite} is not done in the external tracker')


def lifecycle(root: Path, args) -> dict:
    report = task_show(root, args.task_id)
    path = root / report['detail']
    original = report['record']
    state = report['fields'].get('state')
    if state in LEGACY_STATES:
        raise WorkflowError('TASK_LEGACY_STATE', 'explicitly review/migrate this legacy record before lifecycle writes', report['detail'])
    edges = ACTION_EDGES[args.action]
    targets = [target for source, target in edges if source == state]
    if not targets:
        raise WorkflowError('TASK_TRANSITION_FORBIDDEN', f'{args.action} is not allowed from {state}', report['detail'])
    if args.if_hash and args.if_hash != report['hash']:
        raise WorkflowError('WRITE_CONFLICT', 'task hash differs from --if-hash', report['detail'])
    reason = one_line(args.reason)
    plan = FilePlan(root)
    plan.watch(path)
    if text_file(root, path) != original:
        raise WorkflowError('WRITE_CONFLICT', 'task changed while loading', report['detail'])
    plan.watch('relations/RELATIONS.yaml')
    plan.watch('PROJECT_CONTEXT.md')
    text, inputs = patch_record(root, original, args, plan)
    data = lifecycle_data(text)
    target = targets[0]
    stamp = timestamp(root)
    if target == 'active':
        active_conditions(root, args.task_id, text, plan, args.taskctl)
        if args.action == 'resume' and not data.get('pause'):
            raise WorkflowError('TASK_PAUSE_CONTEXT_REQUIRED', 'record pause causes and recovery conditions before resuming')
        if args.action == 'revise':
            ref, _ = reference(root, args.feedback_ref, plan)
            reason += f'; feedback: {ref}'
        if args.action == 'reopen':
            reason += '; original objective reopened; prior completion/approval retained in history'
    elif args.action == 'pause':
        causes = [{'reason': reason, 'resume_when': one_line(args.resume_when)}]
        if 'pause' in inputs:
            pause = object_keys(inputs['pause'], {'reasons'}, 'pause')
            causes.extend(pause_reasons(pause))
        data['pause'] = {'reasons': causes, 'paused_at': stamp, 'next_action': fields(text).get('next action')}
    elif args.action == 'submit':
        submission = inputs.get('submission', data.get('submission'))
        if not isinstance(submission, dict):
            raise WorkflowError('REVIEW_INPUT_REQUIRED', 'submit needs input.submission or an unchanged recorded submission')
        current = submission_record(root, path, text, submission, plan)
        old = data.get('submission')
        if old and old.get('fingerprint') != current['fingerprint'] and old.get('version') == current['version']:
            raise WorkflowError('REVIEW_VERSION_REQUIRED', 'changed submission needs a new version')
        data['submission'] = current
        if old != current:
            data.pop('review', None)
    elif args.action == 'complete':
        data['review'] = approval_record(root, args.task_id, text, args.review_ref, args.review_version, plan)
        text = replace_field(text, 'Readiness', 'completed')
    elif args.action == 'cancel':
        dependents = [source for source, deps in direct_dependencies(registry(root)).items() if args.task_id in deps]
        if dependents:
            raise WorkflowError('DEPENDENCY_CANCELLATION_REVIEW', f'explicitly adjust dependent tasks first: {dependents}')
    text = replace_field(text, 'State', target)
    text = replace_field(text, 'Last updated', stamp)
    if target == 'active' and args.action == 'resume':
        data['pause']['resolved_at'] = stamp
        data['pause']['resolution_basis'] = reason
    if data:
        text = write_lifecycle(text, data)
    text = append_log(text, stamp, f'{args.action}: {state} → {target}; {reason}')
    validate_patch(root, path, text)
    candidate = dict(report, record=text, fields=fields(text), sections=sections(text))
    diagnostics = handoff(root, args.task_id, candidate)['diagnostics']
    if diagnostics:
        raise WorkflowError(diagnostics[0]['code'], diagnostics[0]['message'], diagnostics[0]['path'])
    resume_link = fields(text).get('resume entry', '')
    match = re.search(r'\]\(([^)]+)\)', resume_link)
    target_link = match.group(1) if match else resume_link.strip('`')
    path_part = target_link.partition('#')[0]
    if path_part and target_link != '—':
        plan.watch(record_link_path(root, path, path_part))
    plan.add(path, text)
    plan_views(root, plan, {args.task_id: (path, text)}, registry(root))
    result = plan.report(args.apply)
    result.update(task_id=args.task_id, action=args.action, source=state, target=target)
    if args.action == 'submit':
        result['submission'] = data['submission']
    return result


def task_list(root: Path, args) -> dict:
    task_id = args.task_id
    filters = [args.state, args.readiness, args.priority, args.query, args.eligible]
    if task_id and any(filters):
        raise WorkflowError('TASK_QUERY_INVALID', 'collection filters cannot be combined with a selected task ID')
    if not task_id and args.view:
        raise WorkflowError('TASK_QUERY_INVALID', '--view requires a task ID')
    records = [task_show(root, task_id)] if task_id else [task_show(root, key) for key in task_records(root)]
    eligible = None
    if args.eligible:
        from workflowctl import focus
        result = focus(root)
        eligible = {item['task_id'] for item in result['eligible_tasks']}
    output, diagnostics = [], []
    if args.eligible:
        diagnostics.extend(result['diagnostics'])
    for report in records:
        values = report['fields']
        if any(value and values.get(key) != value for key, value in [('state', args.state), ('readiness', args.readiness), ('priority', args.priority)]):
            continue
        if args.query and args.query.casefold() not in report['record'].casefold():
            continue
        if eligible is not None and report['task_id'] not in eligible:
            continue
        item = {'task_id': report['task_id'], 'detail': report['detail'], 'record_hash': report['hash'],
                'state': values.get('state'), 'readiness': values.get('readiness'), 'priority': values.get('priority'),
                'current_result': values.get('current result'), 'next_action': values.get('next action')}
        if values.get('state') in LEGACY_STATES:
            diagnostics.append({'code': 'TASK_LEGACY_STATE', 'path': report['detail'], 'severity': 'info',
                                'message': 'legacy state read without migration; lifecycle writes require explicit conversion'})
        if task_id:
            view = args.view or 'full'
            if view == 'full':
                item.update(fields=values, sections=report['sections'], record=report['record'])
            elif view == 'snapshot':
                item['fields'] = values
            elif view in {'context', 'handoff'}:
                item['context'] = handoff(root, task_id, report)
                diagnostics.extend(item['context']['diagnostics'])
            elif view == 'review':
                item['review'] = lifecycle_data(report['record'])
            else:
                word = {'plan': 'work log', 'history': 'work log', 'evidence': 'evidence'}[view]
                selected = {key: val for key, val in report['sections'].items() if word in key.lower()}
                if view in {'plan', 'history'}:
                    pattern = re.compile(r'^### Implementation plan\n.*?(?=^### |\Z)', re.MULTILINE | re.DOTALL)
                    selected = {key: (pattern.search(val).group(0) if pattern.search(val) else '') if view == 'plan' else pattern.sub('', val) for key, val in selected.items()}
                item['sections'] = selected
        output.append(item)
    return {'records': output, 'diagnostics': diagnostics}


def task_check(root: Path, args) -> dict:
    from task_board_check import _project_timezone, _record_diagnostics, check_project
    from workflow_records import projection_diagnostics
    ids = [args.task_id] if args.task_id else list(task_records(root))
    diagnostics = []
    areas = {'record', 'handoff', 'lifecycle', 'review', 'relations', 'dependencies', 'views'} if args.area == 'all' else {args.area}
    if 'record' in areas:
        if args.task_id:
            entries = _record_diagnostics(task_path(root, args.task_id), args.strict, _project_timezone(root))
        else:
            entries = check_project(root, strict=args.strict, require_board=False)
        diagnostics += [{'code': 'TASK_RECORD_INVALID', 'path': item.path, 'message': item.message} for item in entries]
    if 'views' in areas:
        diagnostics += projection_diagnostics(root, task_id=args.task_id)
    for task_id in ids:
        report = task_show(root, task_id)
        if 'handoff' in areas:
            diagnostics += handoff(root, task_id)['diagnostics']
        if areas & {'lifecycle', 'review'}:
            try:
                values = report['fields']
                if values.get('state') in LEGACY_STATES:
                    diagnostics.append({'code': 'TASK_LEGACY_STATE', 'path': report['detail'], 'severity': 'info', 'message': 'legacy record retained; no inferred pause/review history'})
                    continue
                if values.get('state') not in STATES:
                    raise WorkflowError('TASK_LIFECYCLE_INVALID', 'unknown task state')
                data = lifecycle_data(report['record'])
                if values.get('state') == 'paused' and not data.get('pause'):
                    raise WorkflowError('TASK_PAUSE_CONTEXT_REQUIRED', 'paused record needs explicit reasons and recovery conditions')
                if values.get('state') == 'in_review':
                    submission = data.get('submission')
                    if not isinstance(submission, dict):
                        raise WorkflowError('REVIEW_INPUT_REQUIRED', 'in_review needs recorded submission')
                    current = submission_record(root, root / report['detail'], report['record'], submission)
                    if current['fingerprint'] != submission.get('fingerprint'):
                        raise WorkflowError('REVIEW_STALE_SUBMISSION', 'submitted target/context has changed')
                if values.get('state') == 'completed' and data.get('review'):
                    review = data['review']
                    approval_record(root, task_id, report['record'], review['ref'], review['version'])
                elif values.get('state') == 'completed':
                    diagnostics.append({'code': 'REVIEW_HISTORY_UNVERIFIED', 'path': report['detail'], 'severity': 'error' if args.strict else 'info', 'message': 'historical completion retained without invented review evidence'})
            except (WorkflowError, ValueError, KeyError) as exc:
                diagnostics.append({'code': getattr(exc, 'code', 'TASK_LIFECYCLE_INVALID'), 'path': report['detail'], 'message': str(exc)})
    if 'relations' in areas:
        from types import SimpleNamespace
        from workflow_relations import relation_operation
        diagnostics += relation_operation(root, SimpleNamespace(action='check'))['diagnostics']
    if 'dependencies' in areas:
        from workflowctl import dependency_diagnostics
        entries, _ = dependency_diagnostics(root)
        relevant = set(ids)
        if args.task_id:
            dependencies = direct_dependencies(registry(root))
            pending = [args.task_id]
            while pending:
                for prerequisite in dependencies.get(pending.pop(), []):
                    if prerequisite not in relevant:
                        relevant.add(prerequisite)
                        pending.append(prerequisite)
        diagnostics += [item.as_dict() for item in entries if item.code.startswith(('DEPENDENCY', 'RELATION_')) and (not args.task_id or item.entity is None or item.entity in relevant)]
    return {'diagnostics': diagnostics}
