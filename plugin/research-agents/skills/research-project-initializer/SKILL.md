---
name: research-project-initializer
description: Plan and apply the MERIX baseline or a root-governed work package when a user explicitly wants a new research project or bounded computational workspace; do not use for ordinary research work in an already configured project.
metadata:
  short-description: Initialize research projects safely
---

# Research Project Initializer

Use this installed Plugin Skill when the user wants to create, adopt, extend, or inspect a research-project baseline, or to create/extend one bounded computational work package. It prepares grounded explicit inputs and calls the deterministic initializer; it does not invent scientific content.

## 1. Orient and prepare explicit inputs

1. Read this Plugin's `assets/baseline/AGENTS.md`, `assets/baseline/RESEARCH_WORKFLOW.md`, and `references/initializer-usage.md`.
2. Identify the absolute target/project path and whether the request is for a root project or a work package.
3. Gather only inputs the script cannot safely infer:
   - Root fresh/adopt: follow the one-question sequence in Section 2 for optional project name, background and brief initial task description. The complete standard directory catalog is automatic; no directory selection is required. Users may skip project information.
   - Work package: authoritative `T-NNN`, lower-case hyphenated topic slug, `minimal`/`full`/`extend` mode, selected modules for `extend`, grounded one-line purpose, and any explicitly requested one-line passive updates.
4. Do not invent a task, purpose, source, convention, execution result, artifact, or scientific claim to satisfy an initializer field.

## 2. Root-project flow

For fresh/adopt initialization, prepare project information in this order before
preflight:

1. Reuse information the user has already supplied; do not ask for it again.
2. If any fields are missing, ask one combined question naming only the missing
   project name, background and/or initial task description. Explicitly say that
   the user may skip them. Wait for the reply before preparing fallback values or
   applying initialization. If the user already requested defaults or directory
   summarization, skip this question and follow that instruction directly.
3. Use the reply's supplied values. For fields the user skips or leaves
   unspecified, apply the A/B fallback below without repeating the question.
   An explicit request for defaults uses defaults even in B; it does not trigger
   directory summarization. No reply is not a choice to skip.

Apply fallback independently to each remaining field:

- **A — New project (fresh):** use user-supplied values. For omitted fields,
  the CLI defaults to the target directory name and generic background/task
  guidance that explicitly says the project-specific information is unspecified.
- **B — Existing directory without an installed baseline (adopt):** after the
  question/reply step or a direct instruction to summarize, read relevant existing
  README/project documentation and explicit task records. Extract only what
  those sources establish. If the name, background or initial task cannot be
  determined accurately, omit that field so the CLI supplies its generic default.
  File names and code presence alone do not establish a current task or progress.
- Summarization belongs to the Agent, not the CLI. Pass prepared, non-empty
  single-line text through `--project-name`, `--background` and
  `--task-description`. Include source paths/links for extracted background and
  tasks in their text; when extracting a project name, record its source in the
  background text as well. User-provided values take precedence independently.
- A project name is a display name; it does not rename the directory. The initial
  task description is starting context, not a formal task ID, task creation,
  active state, execution authorization or verified result.
- Already initialized projects use recognized `extend`; these three inputs are
  rejected there because existing entry files are preserved. Updating their
  project information follows the project's own record-editing rules.

1. Always run a zero-write preflight first:

   ```bash
   python3 <plugin-root>/scripts/research_init.py root --target <absolute-target>
   ```

   Include each prepared optional field in both preflight and apply invocations.
   Omit unavailable fields. The report shows the effective name, background,
   initial task description and their write destinations. Changing these values
   changes the Plan ID, so an adoption confirmation must match the current inputs.

2. Read the report, especially target mode, every path disposition, conflict/manual-resolution section, and `Plan ID`. Both fresh and adopt have an ID bound to prepared information, source bytes, relevant target state and machine timezone. Regenerate after changes. The CLI records the machine's local IANA timezone automatically; do not ask the user for it. If detection fails, report the exact machine-configuration issue before applying.
3. If the report has any `conflict`, make no mutation. Explain the conflict and manual route; a confirmation cannot override it.
4. For a clean `fresh` target, run the same command with `--apply` only when the user has requested initialization.
5. For non-empty `adopt` or writing recognized-project `extend`, obtain explicit confirmation of the exact current plan from the user, then re-run with `--apply --confirm-plan <Plan-ID>`.
6. After an applied result, open `PROJECT_CONTEXT.md`, `README.md` and `AGENTS.md`. Fresh initialization writes the supplied/default project information into new README/context files and the display name into status. Adoption preserves an existing README and records the information in the new context file; it creates a README only if absent. Do not rewrite a preserved README to synchronize it as part of adoption. Add formal task records and progress only through a separately selected task operation; the initial description alone does not create either.
7. Empty standard directories are intentional. Root initialization also creates
   the empty artifacts/ home and records the complete directory inventory.
   Compatible extend completes missing paths/managed rows through the same
   exact-plan confirmation process; it never upgrades diverged baseline files.
8. Extend previews actual inventory patches as `patch-managed`. Before writes,
   the CLI stages content and backs up only affected existing files outside the
   project. On failure, read the outcome: `failed-rolled-back` means this
   invocation's writes were restored; `recovery-required` means restoration is
   incomplete. Report residual paths and the retained backup, stop dependent
   work and follow the recovery guidance in `references/initializer-usage.md`.
   Never claim success from a failed apply or delete retained recovery material.

## 2.1 Existing-project baseline updates

Use the packaged three-command interface when the user asks to update an
already initialized project's baseline:

```bash
python3 <plugin-root>/scripts/research_init.py baseline inspect --project <absolute-project-root> --json
python3 <plugin-root>/scripts/research_init.py baseline plan --project <absolute-project-root> --output <temporary-plan.json> --json
python3 <plugin-root>/scripts/research_init.py baseline apply --project <absolute-project-root> --plan-file <temporary-plan.json> --confirm-plan <plan-id> --json
```

The candidate is the current Plugin baseline available to this Skill. Inspect
does not write; plan writes only a temporary plan; apply revalidates the plan,
preserves project-local records, rotates `.baseline/inventory/current.json` to
`previous.json`, and updates `BASELINE_MANIFEST.md` after successful writes.
Conflicts and unknown ancestors require an explicit temporary decisions file.
Delete a plan after success; retain it through failed rollback or recovery
until the failure is handled. Do not use this flow to migrate instantiated
records or infer project progress.
The root `README.md`, `PROJECT_CONTEXT.md`, and `PROJECT_STATUS.md` files are
mixed files: update only their explicit managed regions recorded in inventory.
Missing markers or trusted region inventory produce `unknown` and require an
explicit decision; symlink and file/directory type conflicts fail closed.

## 3. Work-package flow

1. Confirm that the project already has root `workspaces/` enabled and exactly one matching root task record.
2. Preflight first:

   ```bash
   python3 <plugin-root>/scripts/research_init.py work-package \
     --project <absolute-project-root> \
     --task T-NNN \
     --topic <lowercase-topic-slug> \
     --mode minimal|full|extend \
     --purpose '<grounded purpose>'
   ```

3. Add `--module <name>` only for explicit work-package modules and `--passive-field 'LABEL=VALUE'` only for the accepted one-line fields.
4. Treat any conflict as zero-write and resolve it manually. For a compatible no-op extension, do not rewrite the entry point merely to refresh timestamps.
5. Run with `--apply` only when the user request and the target project's confirmation rules allow the bounded workspace operation. Read the report after apply and update the authoritative root task/status records for the meaningful structural outcome.

## 4. Non-negotiable boundaries

- Fresh/adopt never overwrite, merge, rename, move, delete, or semantically validate existing project content. Recognized extend may patch only its confirmed manifest/context directory-inventory regions, preserving unrelated text and established rows.
- The root initializer copies only this Plugin's release baseline/templates, creates preflight `create` paths and performs the supported bounded extend patches. It never copies Plugin-repository development history or independently summarizes a directory.
- A work package is not a nested project: no local `AGENTS.md`, project context/status, task/decision/discussion tree, project reference archive, or independent artifact registry.
- Do not use this workflow to start or expand high-cost computation, process non-AI user-supplied sensitive data outside the request, change core scope/assumptions/conventions, or perform external communication without the separate required confirmation.
- Do not claim public availability, submit externally, or install/publish this Plugin outside the user's explicit request.

## 5. Optional workflow CLI

For project checks, focus/handoff reports, explicit task/relation maintenance,
or evidence/formula/work-package/Run/Artifact records, use the packaged workflow CLI. Read
[Workflow CLI usage](../../references/workflow-cli-usage.md) for inputs,
projection ownership, write previews, and optional synchronization.

```bash
python3 <plugin-root>/scripts/workflowctl.py --root <project-root> project check --json
python3 <plugin-root>/scripts/workflowctl.py --root <project-root> task check --json
python3 <plugin-root>/scripts/workflowctl.py --root <project-root> focus show --task T-NNN --json
python3 <plugin-root>/scripts/workflowctl.py --root <project-root> task list T-NNN --json
python3 <plugin-root>/scripts/workflowctl.py --root <project-root> handoff check T-NNN --json
python3 <plugin-root>/scripts/workflowctl.py --root <project-root> evidence list --json
python3 <plugin-root>/scripts/workflowctl.py --root <project-root> evidence check --json
```

The workflow CLI is project-local in its inputs but installed with the Plugin
in its invocation path. It requires only the initialized project's core
baseline files. The local Board, relation registry, and external tracker are
optional modules; when absent, the CLI reports `not configured` and does not
pretend that external status has been verified.

Use the CLI for deterministic checks and declared record operations. It does
not infer scientific conclusions, task dependencies, scope, priority,
acceptance, or external completion.

Use `evidence list/check` for structural evidence-record discovery and checks.
Use `formula check` and `formula allocate` for Formula Index order, locations,
and non-reused IDs. Formula allocation previews by default and writes only with
`--apply`; neither route decides formula importance, source roles, correctness,
or scientific conclusions.

Mutation commands preview by default; inspect the result before `--apply`.
Task operations use the project's declared timezone. Work-package creation
reuses initializer gates. Run/Artifact commands create explicit template
records without research execution. For ordinary artifact registration, discovery,
archival, verification, recovery or human-requested cleanup in an initialized
project, use the [artifact manager Skill](../research-artifact-manager/SKILL.md)
and [operation map](../../references/artifact-operations.md). Its detailed
inputs and limits share workflow CLI Section 7. The primary artifact operations
are new/list/update/store/check/cleanup; list exposes saved views, check observes
accessible bytes, and store defaults to the recorded accessible local source.
Root initialization creates the
standard registry home without registering content; project updates still need
their accepted confirmed adoption path. Inspect mutation previews before apply.
A requested Taskboard
adapter uses the exact selected executable and preserves versions, full native
bindings, separate context cursors, and verified readback; it is optional.

For selected work, workflow Section 4.8 defines startup and continuation using
existing task fields. The CLI retrieves that context; this initializer Skill
does not become a mandatory entry point for ordinary project work. Follow the
project's installed rules and accepted dependency policy, with Board, relations,
and external synchronization only when enabled.

For Run submission and long-running execution monitoring, use the separate
[research-run-manager Skill](../research-run-manager/SKILL.md). Work-package
initialization creates records and directories; it does not submit programs or
create Codex heartbeat automations.
