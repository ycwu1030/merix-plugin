"""Continuation reports from the existing selected-task record."""
from pathlib import Path
import re
from urllib.parse import unquote

from workflow_records import WorkflowError, local_path, task_show, text_file


def heading_anchor(title: str) -> str:
    return re.sub(r'[^\w\- ]', '', title.lower()).replace(' ', '-')


def record_link_path(root: Path, record: Path, value: str) -> Path:
    """Resolve stored record-relative links while guarding every component."""
    path = Path(unquote(value))
    if path.is_absolute():
        return local_path(root, path)
    destination = record.parent
    for part in path.parts:
        destination = destination.parent if part == '..' else destination / part
        destination = local_path(root, destination)
    return destination


def link_errors(root: Path, record: Path, link: str) -> list[dict]:
    match = re.search(r'\]\(([^)]+)\)', link)
    target = match.group(1) if match else link.strip().strip(chr(96))
    path_part, _, fragment = target.partition('#')
    try:
        destination = record_link_path(root, record, path_part) if path_part else record
        content = text_file(root, destination)
        if fragment:
            anchors = {heading_anchor(title) for title in re.findall(r'^#{1,6} ([^\n]+)', content, re.MULTILINE)}
            if unquote(fragment) not in anchors:
                raise WorkflowError('HANDOFF_ANCHOR_MISSING', f'unknown heading anchor: {fragment}', destination.relative_to(root).as_posix())
    except WorkflowError as exc:
        return [{'code': exc.code, 'path': exc.path, 'message': str(exc)}]
    return []


def handoff(root: Path, task_id: str, report: dict | None = None) -> dict:
    report = report if report is not None else task_show(root, task_id)
    data = report['fields']
    diagnostics = []
    required = ['scope', 'current result', 'current step', 'implementation plan version',
                'resume entry', 'next action', 'blocker', 'last updated']
    for name in required:
        if not data.get(name):
            diagnostics.append({'code': 'HANDOFF_FIELD_MISSING', 'path': report['detail'], 'message': f'missing {name}'})
    if data.get('resume entry') and data['resume entry'] != '—':
        diagnostics.extend(link_errors(root, root / report['detail'], data['resume entry']))
    step = data.get('current step')
    if step and step != '—' and not re.search(r'^- \[[ xX]\]\s*' + chr(96) + re.escape(step) + chr(96) + r':', report['record'], re.MULTILINE):
        diagnostics.append({'code': 'HANDOFF_PLAN_STEP_INVALID', 'path': report['detail'], 'message': f'current step {step} is not in the living plan'})
    if data.get('plan version') != data.get('implementation plan version'):
        diagnostics.append({'code': 'HANDOFF_PLAN_VERSION_DRIFT', 'path': report['detail'], 'message': 'snapshot and living plan versions disagree'})
    gate = (data.get('state') in {'blocked', 'awaiting-confirmation'}
            or data.get('readiness') in {'blocked-by-task', 'awaiting-input', 'awaiting-confirmation', 'high-cost-gated'}
            or data.get('blocker') not in {None, '', '—'})
    return {'task_id': task_id, 'detail': report['detail'], 'state': data.get('state'),
            'readiness': data.get('readiness'), 'current_result': data.get('current result'),
            'current_step': step, 'next_action': data.get('next action'), 'resume_entry': data.get('resume entry'),
            'blocker': data.get('blocker'), 'allowed_scope': data.get('scope'), 'gated': gate,
            'sections': {name: content for name, content in report['sections'].items()
                         if any(word in name.lower() for word in ['handoff', 'evidence', 'risk', 'work log'])},
            'diagnostics': diagnostics, 'non_claim': 'Navigation and record checks do not authorize execution or certify restored sessions.'}
