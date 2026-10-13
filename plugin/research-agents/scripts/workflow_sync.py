"""Explicit optional Taskboard adapter using its JSON CLI, never HTTP endpoints."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile

from workflow_records import FilePlan, WorkflowError, direct_dependencies, local_path, registry, task_show, text_file

BINDING_FIELDS = ['threadId', 'codexProjectId', 'codexProjectKind', 'codexHostId', 'workspacePath']
BINDING_OPTIONS = ['--binding-thread-id', '--binding-codex-project-id', '--binding-codex-project-kind',
                   '--binding-codex-host-id', '--binding-workspace-path']


def metadata_matches(name: str, actual, expected) -> bool:
    # Taskboard trims outer whitespace from descriptions on ingestion.
    if name == 'description' and isinstance(actual, str):
        return actual.strip() == expected.strip()
    return actual == expected


class Taskboard:
    def __init__(self, executable: Path):
        if not executable.is_absolute() or not executable.is_file():
            raise WorkflowError('SYNC_ADAPTER_INVALID', 'supply the exact absolute path to the selected Taskboard executable')
        self.executable = executable

    def call(self, arguments: list[str]) -> dict:
        try:
            process = subprocess.run([str(self.executable), *arguments, '--json'], capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.TimeoutExpired):
            raise WorkflowError('SYNC_SERVICE_UNAVAILABLE', 'the selected Taskboard CLI could not complete the request')
        try:
            result = json.loads(process.stdout)
        except (ValueError, TypeError):
            raise WorkflowError('SYNC_RESPONSE_INVALID', 'Taskboard did not return a JSON object')
        if not isinstance(result, dict):
            raise WorkflowError('SYNC_RESPONSE_INVALID', 'Taskboard response must be an object')
        if process.returncode or result.get('error'):
            error = result.get('error')
            code = error.get('code', '') if isinstance(error, dict) else ''
            if 'VERSION' in code or 'CONFLICT' in code:
                raise WorkflowError('SYNC_VERSION_CONFLICT', 'Taskboard rejected the stale write; reread and reconcile before retrying')
            if code in {'SERVICE_UNAVAILABLE', 'LOCAL_COMPANION_REQUIRED'}:
                raise WorkflowError('SYNC_SERVICE_UNAVAILABLE', 'the selected Taskboard service is unavailable')
            raise WorkflowError('SYNC_API_ERROR', f'Taskboard operation failed ({code or process.returncode}); no automatic retry')
        return result

    def issue(self, external_id: str) -> dict:
        response = self.call(['issue', 'get', external_id])
        task = response.get('task')
        if not isinstance(task, dict) or task.get('identifier') != external_id or not isinstance(task.get('version'), int):
            raise WorkflowError('SYNC_RESPONSE_INVALID', 'issue identity/version is missing or differs from the requested identifier')
        return task

    def context(self, external_id: str, after_comments: str | None = None, after_attachments: str | None = None) -> dict:
        issue = self.issue(external_id)
        comment_args = ['comment', 'list', external_id]
        attachment_args = ['attachment', 'list', '--task', external_id]
        if after_comments:
            comment_args += ['--after', after_comments]
        if after_attachments:
            attachment_args += ['--after', after_attachments]
        comments = self.call(comment_args)
        attachments = self.call(attachment_args)
        if not isinstance(comments.get('comments'), list) or not isinstance(attachments.get('attachments'), list):
            raise WorkflowError('SYNC_RESPONSE_INVALID', 'invalid context list response')
        return {'issue': issue, 'comments': comments['comments'], 'attachments': attachments['attachments'],
                'comment_cursor': comments.get('nextCursor'), 'attachment_cursor': attachments.get('nextCursor')}


def live_statuses(root: Path, executable: Path) -> tuple[dict, list[dict]]:
    adapter = Taskboard(executable)
    statuses = {}
    errors = []
    data = registry(root)
    prerequisites = set(target for targets in direct_dependencies(data).values() for target in targets)
    for task_id in sorted(prerequisites):
        try:
            task = task_show(root, task_id)
            values = task['fields']
            external_id = values.get('external tracker id') or values.get('taskboard id') or values.get('taskboard')
            if external_id and external_id != '—':
                statuses[external_id] = adapter.issue(external_id).get('status')
        except WorkflowError as exc:
            errors.append({'code': exc.code, 'path': task_id, 'message': str(exc)})
    return statuses, errors


def _binding(issue: dict, args) -> dict | None:
    saved = issue.get('threadBinding')
    supplied = {field: getattr(args, option[2:].replace('-', '_'), None) for field, option in zip(BINDING_FIELDS, BINDING_OPTIONS)}
    if saved:
        if not isinstance(saved, dict) or not all(saved.get(field) for field in BINDING_FIELDS):
            raise WorkflowError('SYNC_BINDING_INCOMPLETE', 'saved Codex binding is incomplete; explicit repair is required')
        if saved['threadId'] != args.thread_id:
            raise WorkflowError('SYNC_BINDING_OTHER_THREAD', 'the issue is bound to another conversation')
        if any(supplied.values()) and supplied != saved:
            raise WorkflowError('SYNC_BINDING_CONFLICT', 'supplied binding differs from the saved binding')
        return {field: saved[field] for field in BINDING_FIELDS}
    if any(supplied.values()):
        if not all(supplied.values()) or supplied['threadId'] != args.thread_id:
            raise WorkflowError('SYNC_BINDING_INCOMPLETE', 'all five binding values must describe the current native Codex conversation')
        return supplied
    if args.status in {'in_progress', 'in_review', 'blocked'}:
        raise WorkflowError('SYNC_BINDING_INCOMPLETE', 'an owned status write requires all five binding values')
    return None


def synchronize(root: Path, args) -> dict:
    if not args.taskctl:
        raise WorkflowError('SYNC_ADAPTER_NOT_CONFIGURED', 'external synchronization requires explicit --taskctl')
    local = task_show(root, args.task_id)
    values = local['fields']
    external_id = values.get('external tracker id') or values.get('taskboard id') or values.get('taskboard')
    if not external_id or external_id == '—':
        raise WorkflowError('SYNC_EXTERNAL_ID_MISSING', 'the local task has no declared external tracker ID', local['detail'])
    adapter = Taskboard(args.taskctl)
    receipt_path = local_path(root, f'tasks/.workflow-sync/{args.task_id}.json')
    saved = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    if not isinstance(saved, dict) or (saved and saved.get('external_id') != external_id):
        raise WorkflowError('SYNC_RECEIPT_INVALID', 'saved receipt does not describe this external task')
    context = adapter.context(external_id, args.after_comments or saved.get('comment_cursor'),
                              args.after_attachments or saved.get('attachment_cursor'))
    issue = context['issue']
    if issue.get('archivedAt'):
        raise WorkflowError('SYNC_ARCHIVED', 'archived issues are not changed by synchronization')
    priority = {'P0': 'urgent', 'P1': 'high', 'P2': 'medium', 'P3': 'low'}.get(values.get('priority'))
    expected = {'description': local['record'], 'priority': priority}
    desired_status = args.status or issue.get('status')
    if args.status == 'done' and (not args.accept_completion or values.get('state') != 'completed'):
        raise WorkflowError('SYNC_ACCEPTANCE_REQUIRED', 'done requires --accept-completion and local State completed')
    if args.status == 'in_progress' and (values.get('state') != 'active' or values.get('readiness') != 'ready'):
        raise WorkflowError('SYNC_STATE_DISAGREEMENT', 'in_progress requires local active/ready; the CLI does not start task work')
    if args.status == 'canceled' and values.get('state') != 'canceled':
        raise WorkflowError('SYNC_STATE_DISAGREEMENT', 'canceled requires local State canceled')
    data = registry(root)
    dependencies = direct_dependencies(data).get(args.task_id, [])
    expected_dependencies = []
    for task_id in dependencies:
        dependency = task_show(root, task_id)['fields']
        target = dependency.get('external tracker id') or dependency.get('taskboard id') or dependency.get('taskboard')
        if not target or target == '—':
            raise WorkflowError('SYNC_DEPENDENCY_ID_MISSING', f'{task_id} has no external ID')
        expected_dependencies.append(target)
    current_dependencies = sorted(item['identifier'] for item in issue.get('relations', {}).get('blockedBy', []))
    mismatches = [name for name, value in expected.items() if value is not None and not metadata_matches(name, issue.get(name), value)]
    if args.status and issue.get('status') != args.status:
        mismatches.append('status')
    if sorted(expected_dependencies) != current_dependencies:
        mismatches.append('blocked_by')
    report = {'task_id': args.task_id, 'external_id': external_id, 'outcome': 'read',
              'version': issue['version'], 'live_status': issue.get('status'),
              'mismatches': mismatches, 'comment_cursor': context['comment_cursor'],
              'attachment_cursor': context['attachment_cursor'], 'comments': context['comments'],
              'attachments': context['attachments'], 'local_hash': local['hash'], 'changes': []}
    if not args.apply:
        return report
    if not args.thread_id:
        raise WorkflowError('SYNC_ATTRIBUTION_MISSING', '--thread-id is required for external writes')
    binding = _binding(issue, args)
    comment = text_file(root, args.comment_file) if args.comment_file else None
    if args.status == 'in_review' and issue.get('status') != 'in_review' and not (comment and comment.strip()):
        raise WorkflowError('SYNC_REVIEW_COMMENT_REQUIRED', 'moving into review requires --comment-file with outcome, verification, and limitations')
    if 'blocked_by' in mismatches and not args.sync_relations:
        raise WorkflowError('SYNC_RELATION_DRIFT', 'direct dependency views disagree; supply --sync-relations for an explicit correction')
    if args.sync_relations:
        for identifier in sorted(set(current_dependencies) ^ set(expected_dependencies)):
            target = adapter.issue(identifier)
            if target.get('projectId') != issue.get('projectId'):
                raise WorkflowError('SYNC_PROJECT_MISMATCH', 'dependency issue belongs to another Taskboard project')
    receipt_plan = FilePlan(root)
    receipt_plan.add(receipt_path, json.dumps(saved))

    def local_unchanged():
        if task_show(root, args.task_id)['hash'] != local['hash'] or registry(root) != data:
            raise WorkflowError('SYNC_LOCAL_CONFLICT', 'local task or registry changed during synchronization; reconcile before retrying')

    def persist():
        receipt = {key: value for key, value in report.items() if key not in {'comments', 'attachments'}}
        receipt_plan.add(receipt_path, json.dumps(receipt, indent=2, ensure_ascii=False) + '\n')
        try:
            receipt_plan.report(True)
            report['receipt'] = receipt_path.relative_to(root).as_posix()
        except (WorkflowError, OSError) as exc:
            report.setdefault('diagnostics', []).append({'code': 'SYNC_RECEIPT_WRITE_FAILED', 'path': receipt_path.relative_to(root).as_posix(), 'message': str(exc)})
            report['outcome'] = 'partial'
        return report

    try:
        local_unchanged()
        if any(name in mismatches for name in ['description', 'priority']):
            with tempfile.TemporaryDirectory() as directory:
                body = Path(directory) / 'task-description.md'
                body.write_text(local['record'], encoding='utf-8')
                command = ['issue', 'update', external_id, '--description-file', str(body),
                           '--thread-id', args.thread_id, '--if-version', str(issue['version'])]
                if priority:
                    command += ['--priority', priority]
                adapter.call(command)
            report['changes'].append('metadata')
            issue = adapter.issue(external_id)
        if comment:
            local_unchanged()
            with tempfile.TemporaryDirectory() as directory:
                body = Path(directory) / 'outcome.md'
                body.write_text(comment, encoding='utf-8')
                response = adapter.call(['comment', 'add', external_id, '--body-file', str(body), '--thread-id', args.thread_id])
            report['changes'].append('comment')
            report['comment_id'] = (response.get('comment') or {}).get('id')
            issue = adapter.issue(external_id)
        if args.status and (issue.get('status') != args.status or issue.get('threadBinding') != binding):
            local_unchanged()
            command = ['issue', 'move', external_id, '--status', desired_status,
                       '--thread-id', args.thread_id, '--if-version', str(issue['version'])]
            if binding:
                for field, option in zip(BINDING_FIELDS, BINDING_OPTIONS):
                    command += [option, binding[field]]
            adapter.call(command)
            report['changes'].append('status')
            issue = adapter.issue(external_id)
        if args.sync_relations:
            for operation, identifiers in [('remove', set(current_dependencies) - set(expected_dependencies)),
                                           ('add', set(expected_dependencies) - set(current_dependencies))]:
                for identifier in sorted(identifiers):
                    local_unchanged()
                    adapter.call(['issue', 'relation', operation, external_id, '--type', 'blocked_by',
                                  '--issue', identifier, '--thread-id', args.thread_id, '--if-version', str(issue['version'])])
                    report['changes'].append(f'blocked_by {operation} {identifier}')
                    issue = adapter.issue(external_id)
        readback = adapter.issue(external_id)
        if comment:
            after = adapter.context(external_id, context['comment_cursor'], context['attachment_cursor'])
            if not any(item.get('id') == report['comment_id'] and item.get('body') == comment for item in after['comments']):
                raise WorkflowError('SYNC_COMMENT_READBACK_MISMATCH', 'outcome comment could not be verified in readback')
            report['comment_cursor'], report['attachment_cursor'] = after['comment_cursor'], after['attachment_cursor']
            readback = after['issue']
        local_unchanged()
        failures = [name for name, value in expected.items() if value is not None and not metadata_matches(name, readback.get(name), value)]
        if args.status and readback.get('status') != desired_status:
            failures.append('status')
        if binding and readback.get('threadBinding') != binding:
            failures.append('threadBinding')
        if sorted(item['identifier'] for item in readback.get('relations', {}).get('blockedBy', [])) != sorted(expected_dependencies):
            failures.append('blocked_by')
        report.update(outcome='synchronized' if not failures else 'readback-mismatch',
                      version=readback['version'], live_status=readback.get('status'), mismatches=failures)
        if failures:
            report['diagnostics'] = [{'code': 'SYNC_READBACK_MISMATCH', 'path': local['detail'], 'message': 'readback differs: ' + ', '.join(failures)}]
        return persist()
    except WorkflowError as exc:
        report['outcome'] = 'partial' if report['changes'] else 'failed'
        report['diagnostics'] = [{'code': exc.code, 'path': local['detail'], 'message': str(exc)}]
        if exc.code == 'SYNC_VERSION_CONFLICT':
            try:
                report['latest_version'] = adapter.issue(external_id)['version']
            except WorkflowError:
                pass
        return persist()
