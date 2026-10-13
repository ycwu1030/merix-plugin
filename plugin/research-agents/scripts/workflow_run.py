"""Portable local Run submission and one-shot observation helpers."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import time

from workflow_records import FilePlan, WorkflowError, fields, local_path, replace_field, text_file, timestamp


STATE_NAME = ".run-controller.json"


def _run_file(root: Path, value: str) -> Path:
    path = local_path(root, value)
    if path.is_dir():
        path = path / "RUN.md"
    if path.name != "RUN.md" or not path.is_file():
        raise WorkflowError("RUN_MISSING", "run selector must identify a RUN.md or its directory", value)
    return path


def _state_path(path: Path) -> Path:
    return path.parent / STATE_NAME


def _load_state(path: Path) -> dict:
    state = _state_path(path)
    if not state.exists():
        return {"version": 1, "attempts": []}
    try:
        data = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise WorkflowError("RUN_CONTROLLER_STATE_INVALID", str(exc), str(state))
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("attempts"), list):
        raise WorkflowError("RUN_CONTROLLER_STATE_INVALID", "controller state must use version 1", str(state))
    return data


def _save(root: Path, path: Path, state: dict, apply: bool) -> dict:
    plan = FilePlan(root)
    plan.watch(path)
    state_path = _state_path(path)
    plan.add(state_path, json.dumps(state, indent=2, ensure_ascii=False) + "\n", create=not state_path.exists())
    return plan.report(apply)


def _command(value: str) -> list[str]:
    if not value or "\n" in value or "\r" in value:
        raise WorkflowError("RUN_COMMAND_INVALID", "command must be a nonempty single-line command")
    try:
        result = shlex.split(value, posix=os.name != "nt")
    except ValueError as exc:
        raise WorkflowError("RUN_COMMAND_INVALID", str(exc))
    if not result:
        raise WorkflowError("RUN_COMMAND_INVALID", "command must contain an executable")
    return result


def _observe_attempt(attempt: dict) -> dict:
    pid = attempt.get("pid")
    alive = False
    if isinstance(pid, int) and pid > 0:
        try:
            os.kill(pid, 0)
            alive = True
        except OSError:
            alive = False
    observation = {"observed_at": time.time(), "alive": alive}
    if alive and os.name != "nt":
        try:
            result = subprocess.run(["ps", "-o", "%cpu=,rss=", "-p", str(pid)], capture_output=True, text=True, check=False)
            values = result.stdout.split()
            if len(values) >= 2:
                observation["cpu_percent"] = float(values[0])
                observation["memory_kb"] = int(values[1])
        except (OSError, ValueError):
            observation["resource_observation"] = "unavailable"
    if attempt.get("progress_file"):
        progress = Path(attempt["progress_file"])
        if progress.is_file():
            observation["progress_file"] = str(progress)
            observation["progress_mtime"] = progress.stat().st_mtime
            observation["progress"] = progress.read_text(encoding="utf-8", errors="replace")[-4096:]
    attempt["last_observation"] = observation
    if alive:
        attempt["status"] = "running"
    elif attempt.get("status") == "running":
        attempt["status"] = "terminated"
    return observation


def _update_record(root: Path, path: Path, *, invocation: str | None = None, disposition: str | None = None,
                   actual: str | None = None, outcome: str | None = None, scheduler: str | None = None,
                   apply: bool) -> dict:
    original = text_file(root, path)
    text = original
    stamp = timestamp(root)
    updates = {
        "Exact invocation / entry point": invocation,
        "Overall execution disposition": disposition,
        "Actual resources or observed usage": actual,
        "Execution outcome": outcome,
        "Scheduler or job identifier(s), if applicable": scheduler,
        "Last updated": stamp,
    }
    for label, value in updates.items():
        if value is not None:
            text = replace_field(text, label, value)
    plan = FilePlan(root)
    plan.watch(path)
    plan.add(path, text)
    return plan.report(apply)


def submit(root: Path, args, *, retry: bool = False) -> dict:
    path = _run_file(root, args.path)
    run = fields(text_file(root, path))
    state = _load_state(path)
    attempts = state["attempts"]
    if retry and attempts:
        _observe_attempt(attempts[-1])
    if attempts and attempts[-1].get("status") == "running":
        raise WorkflowError("RUN_ALREADY_ACTIVE", "an active submission already exists", str(path))
    if retry and not attempts:
        raise WorkflowError("RUN_RETRY_UNAVAILABLE", "there is no previous submission to retry", str(path))
    command_text = args.executable_command if not retry else attempts[-1]["command"]
    command = _command(command_text)
    cwd = local_path(root, args.cwd if getattr(args, "cwd", None) else run.get("working location", "."))
    if not cwd.is_dir():
        raise WorkflowError("RUN_CWD_MISSING", "working directory does not exist", str(cwd))
    attempt_number = len(attempts) + 1
    log_dir = path.parent / "logs"
    stdout_path = local_path(root, getattr(args, "stdout", None) or (log_dir / f"attempt-{attempt_number:03d}.out"))
    stderr_path = local_path(root, getattr(args, "stderr", None) or (log_dir / f"attempt-{attempt_number:03d}.err"))
    progress = getattr(args, "progress_file", None) or (attempts[-1].get("progress_file") if retry else None)
    if not args.apply:
        return {"outcome": "planned", "attempt": {"number": attempt_number, "command": command_text,
                "argv": command, "cwd": str(cwd), "status": "not-submitted",
                "stdout": str(stdout_path), "stderr": str(stderr_path), "progress_file": progress,
                "retry": retry, "retry_policy": "explicit-only"},
                "non_claim": "Preview does not launch a process or create controller state."}
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    with stdout_path.open("ab") as stdout, stderr_path.open("ab") as stderr:
        kwargs = {"stdin": subprocess.DEVNULL, "stdout": stdout, "stderr": stderr,
                  "cwd": str(cwd), "start_new_session": True, "close_fds": True}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            kwargs.pop("start_new_session", None)
        process = subprocess.Popen(command, **kwargs)
    attempt = {"number": attempt_number, "command": command_text, "argv": command,
               "cwd": str(cwd), "pid": process.pid, "status": "running",
               "submitted_at": time.time(), "stdout": str(stdout_path), "stderr": str(stderr_path),
               "progress_file": str(local_path(root, progress)) if progress else None,
               "retry": retry, "retry_policy": "explicit-only"}
    state.update({"run_id": run.get("run id"), "backend": "local-detached-v1", "attempts": attempts + [attempt]})
    try:
        record = _update_record(root, path, invocation=command_text, disposition="incomplete",
                                scheduler=f"local-detached-v1 pid={process.pid}", apply=args.apply)
        saved = _save(root, path, state, args.apply)
    except Exception:
        try:
            os.kill(process.pid, signal.SIGTERM)
        except OSError:
            pass
        raise
    return {"outcome": "applied" if args.apply else "planned", "attempt": attempt,
            "record": record, "state": saved,
            "non_claim": "Submission records process lifecycle only; it does not establish Contract satisfaction or scientific validity."}


def run_operation(root: Path, args) -> dict:
    path = _run_file(root, args.path)
    state = _load_state(path)
    if args.action == "submit":
        return submit(root, args)
    if args.action == "retry":
        return submit(root, args, retry=True)
    if args.action == "schedule":
        if args.interval < 1:
            raise WorkflowError("RUN_SCHEDULE_INVALID", "monitor interval must be at least one minute")
        schedule = {"interval_minutes": args.interval,
                    "notify_on": ["state-change", "failure", "completion", "action-required"],
                    "owner": "codex-thread", "automation_status": "pending-codex-automation"}
        if not args.apply:
            return {"outcome": "planned", "schedule": schedule,
                    "non_claim": "Preview does not create a Codex automation or modify the Run record."}
        state["monitor_schedule"] = schedule
        saved = _save(root, path, state, True)
        return {"outcome": "prepared", "schedule": schedule, "state": saved,
                "next_action": "The current Codex session must create the thread heartbeat automation and record its automation id.",
                "non_claim": "The project CLI cannot create Codex app automations by itself."}
    if not state["attempts"]:
        raise WorkflowError("RUN_NOT_SUBMITTED", "run has no local submission", str(path))
    attempt = state["attempts"][-1]
    if args.action in {"status", "monitor"}:
        observation = _observe_attempt(attempt)
        if args.action == "monitor" and args.apply:
            _save(root, path, state, True)
            _update_record(root, path, actual=json.dumps(observation, sort_keys=True),
                           disposition="incomplete" if observation.get("alive") else "terminated",
                           outcome="one-shot monitor observation recorded", apply=True)
        return {"run": path.relative_to(root).as_posix(), "attempt": attempt, "observation": observation,
                "outcome": "observed", "non_claim": "Resource and heartbeat observations do not certify output correctness or scientific validity."}
    if args.action == "stop":
        if attempt.get("status") != "running":
            raise WorkflowError("RUN_NOT_ACTIVE", "latest submission is not active", str(path))
        try:
            os.kill(attempt["pid"], signal.SIGTERM)
        except OSError as exc:
            raise WorkflowError("RUN_STOP_FAILED", str(exc), str(path))
        attempt["status"] = "stop-requested"
        if args.apply:
            _save(root, path, state, True)
        return {"outcome": "stop-requested", "attempt": attempt}
    raise WorkflowError("RUN_ACTION_INVALID", f"unsupported run action: {args.action}")
