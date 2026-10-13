---
name: research-run-manager
description: Submit and monitor an explicitly prepared research Run through a detached local backend; create a Codex heartbeat monitor for long-running submissions and report meaningful state changes in the current conversation.
metadata:
  short-description: Submit and monitor research Runs safely
---

# Research Run Manager

Use this Skill after the user has supplied the program, code, environment,
inputs and an initialized project's `R-NNN` record. The Skill owns submission
and lifecycle observation around that program. It does not modify the program,
judge scientific validity, retry automatically, or register outputs without an
explicit artifact operation.

## 1. Submit

1. Read the project's `AGENTS.md`, `RESEARCH_WORKFLOW.md`, `RUN.md`, and the
   workflow CLI reference.
2. Confirm the Run has a frozen configuration, explicit working directory,
   command, resource plan, log paths and optional heartbeat/progress file.
3. Run a preview, inspect it, then submit explicitly:

   ```bash
   python3 <plugin-root>/scripts/workflowctl.py --root <project-root> \
     run submit --path <run-path> --command '<user-supplied-command>' \
     --cwd <working-directory> --progress-file <progress-file> --apply --json
   ```

4. After a successful submission, create a Codex **heartbeat automation**
   attached to the current conversation. The automation prompt must identify
   the project and Run path, call the one-shot `run monitor`, and report only
   state changes, failure or unexpected termination, completion, concerning
   resource observations, or required user action. Keep it quiet when nothing
   meaningful changed.
5. Record the automation ID and interval in the Run controller state. If the
   Codex app automation capability is unavailable, report that monitoring was
   not scheduled; do not claim that the CLI created it.

The heartbeat automation is the session-level scheduling layer. The project
CLI only persists the requested schedule and performs one-shot observations;
it cannot create a Codex app automation by itself.

## 2. Observe and recover

- Use `run status` for a read-only observation and `run monitor --apply` when
  the current observation should be persisted.
- The automation may report progress from the explicitly declared heartbeat or
  progress file, process state, CPU and memory observations, and logs.
- Automatic retry is disabled. A retry requires an explicit user action and
  must first establish that the previous attempt is terminal and the frozen
  configuration is unchanged.
- Stop, retry and artifact registration are separate explicit actions.

## 3. Artifact boundary

Do not glob Run outputs or decide retention automatically. Register a selected
output through the existing artifact manager and record the returned `A-NNN`
in the Run record. Artifact registration remains subject to its own provenance,
integrity, access and retention rules.

## 4. Non-claims

Run submission and monitoring establish operational observations only. They do
not establish Contract satisfaction, implementation correctness, output
integrity, reproducibility, or a scientific conclusion.
