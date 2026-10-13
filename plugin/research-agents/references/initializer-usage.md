# Research Project Initializer: Usage and Boundaries

## 1. Package layout

This Plugin's canonical research baseline is in `assets/baseline/`. The deterministic initializer is `scripts/research_init.py`. The Plugin repository's task, discussion, decision, and test records are not baseline payload and are never copied into an initialized research project.

## 2. Root-project commands

Run a zero-write preflight first:

```bash
python3 <plugin-root>/scripts/research_init.py root \
  --target /absolute/path/to/new-project
```

For a clean fresh target, apply only after the user has requested initialization:

```bash
python3 <plugin-root>/scripts/research_init.py root \
  --target /absolute/path/to/new-project \
  --apply
```

For a non-empty adoption target or a writing recognized-project extension, run preflight, review its exact plan identifier, obtain explicit confirmation, and re-run with `--apply --confirm-plan <Plan-ID>`.

### Optional project information for A and B

For Skill-driven fresh/adopt initialization, reuse fields already provided. If
any are missing, ask one combined question for only those fields, stating that
the user may skip them. Wait for the reply, then apply the fallback below to
fields still unspecified; do not ask repeatedly. No reply is not a skip choice.
If the user has already instructed the Agent to use defaults or summarize the
directory, follow that instruction directly without asking. Explicit defaults
also bypass directory summarization in B. This question is handled by the Skill;
the CLI remains noninteractive.

- **A — New project:** provide any known project name, background and initial
  task description. Omitted fields default independently to the directory name,
  unspecified-background guidance and unspecified-task guidance.
- **B — Existing directory without an installed baseline:** the Agent/Skill
  uses user-supplied fields, then, after the question/skip step, extracts missing fields from reliable
  existing README/project documentation or explicit task records. It preserves
  source paths/links in the prepared description text. When a field cannot be
  identified accurately, leave it omitted for the same generic fallback.

The CLI accepts explicit single-line text; it does not read a README to infer
project information or invoke a model. For example, preflight with:

```bash
python3 <plugin-root>/scripts/research_init.py root \
  --target /absolute/path/to/project \
  --project-name 'Detector response study' \
  --background 'Study detector response using the supplied reference material.' \
  --task-description 'Review the starting model assumptions.'
```

All three options are optional and reject empty/multiline values. Include the
same values when applying. They are shown in the preflight report and included
in Plan ID; changing them invalidates a prior adoption confirmation.
For extracted text, retain provenance, for example
`--background 'Study detector response. Source: [README.md](README.md).'`.
Record an extracted name's source in the background text too. The CLI treats
these descriptions as caller input, not verified scientific evidence.

Fresh writes the information into newly generated README.md/PROJECT_CONTEXT.md
and uses the display name in PROJECT_STATUS.md. Adoption preserves an existing
README byte-for-byte and places the information in newly created
PROJECT_CONTEXT.md; it generates README only when absent. The display name does
not rename a path. An initial task description does not allocate a task ID,
create a task record, establish progress or authorize research execution.

These options are rejected for recognized extend, which preserves existing
project entry text except its supported directory-inventory patches. Update
established project information through the project's record-editing rules.
Reserved-path collisions still fail closed; this input support is not a baseline
updater. Bare CLI calls receive generic defaults in both A and B; the packaged
initializer Skill supplies the grounded extraction step for B.

Every root invocation plans the complete standard catalog: the six core root
directories; context/, artifacts/, docs/, assets/, workspaces/ and relations/;
all six predefined references/ children; and docs/communication/. Empty
directories are valid scaffolding. The initializer records their paths and roles
in PROJECT_CONTEXT.md and BASELINE_MANIFEST.md without inventing actual content
or primary entry points. Root artifacts/ is ready for explicit registration;
no artifact IDs, content or relation registry are created at root initialization.
Legacy --optional-dir arguments remain validated compatibility inputs and no
longer restrict the directory set. The catalog in scripts/research_init/catalog.py
is the single runtime source of the accepted directory structure.

### Plan identity, local time and recovery

Both A and B have a Plan ID. It binds prepared/default descriptions, date,
machine timezone, baseline source bytes/revision, relevant target state and
the intended writes. Regenerate the plan after any of these change. Fresh does
not require a second confirmation; an optional supplied token must still match.
Adopt and writing extend require the exact current token. Inventory changes in
extend appear as `patch-managed`, including manifest/context updates.

New context records the executing machine's IANA timezone automatically: valid
`TZ`, then the `/etc/localtime` zoneinfo link or `/etc/timezone`. No timezone
question is needed. An invalid configured TZ or an undetectable IANA zone fails
before project writes; configure the machine's timezone and rerun. Existing
context timezone is preserved on extend.

Before project writes, the initializer stages all new contents and backs up
every existing file it will patch, with original mode/timestamps and a recovery
journal. The backup is outside the target in the machine's temporary directory;
it covers this invocation's write set, not the whole project's research data.
Ordinary apply failures trigger restoration of patched files and removal of
this invocation's new files/directories. `failed-rolled-back` returns nonzero.
If restoration is incomplete, `recovery-required` returns nonzero and reports
residual paths and the retained backup directory. Stop dependent work, inspect
`recovery.json` and compare its hashes with the current files and `previous/`
copies before manually restoring only the affected paths. Do not overwrite
intervening changes. Successful apply/recovery removes the backup; a cleanup
failure leaves its location in the report.

The per-target lock coordinates initializer invocations. Recovery does not
guarantee restoration after power loss, process termination or uncooperative
concurrent edits; retained backups/journals support manual investigation. A
stale lock after termination also requires manual investigation before removal.

## 3. Work-package commands

```bash
python3 <plugin-root>/scripts/research_init.py work-package \
  --project /absolute/path/to/project \
  --task T-123 \
  --topic bounded-analysis \
  --mode minimal \
  --purpose 'Grounded one-line purpose.'
```

Use `--apply` only after the relevant root project/task rules permit the bounded workspace operation.

## 4. Boundaries

- A preflight is read-only.
- A conflict produces zero writes and cannot be overridden by confirmation.
- Fresh/adopt create only planned absent paths and preserve existing project content. Recognized extend may also patch its confirmed manifest/context directory-inventory regions, preserving existing rows/dates and unrelated text; it never replaces existing baseline payload.
- The initializer does not start costly computation, handle user-supplied sensitive data beyond the request, or make external submissions/communications without the separate required confirmation.
- The Plugin is MERIX Research Plugin (`merix-research`), distributed under MIT. Installation and baseline application are separate operations; availability and release status are recorded by the selected distribution source.

## 5. Existing-project baseline updates

Changing the Plugin's source or updating the installed Plugin does not update
baseline files already copied into a research project. A new project receives
the baseline from the Plugin used in that initialization.

For an existing project's baseline, use the three-command interface:

```bash
python3 <plugin-root>/scripts/research_init.py baseline inspect --project <absolute-project-root> --json
python3 <plugin-root>/scripts/research_init.py baseline plan --project <absolute-project-root> --output <temporary-plan.json> --json
python3 <plugin-root>/scripts/research_init.py baseline apply --project <absolute-project-root> --plan-file <temporary-plan.json> --confirm-plan <plan-id> --json
```

`inspect` is read-only. `plan` writes only a temporary review file and may use
a temporary JSON decisions file for conflicts or unknown ancestors. `apply`
revalidates the exact plan, preserves project-local changes and records the
current/previous inventory only after successful application. Successful apply
deletes the temporary plan; failed rollback or recovery-required outcomes keep
it until the failure is resolved. A Plugin source update and a
project-baseline application remain separate operations.

The root `README.md`, `PROJECT_CONTEXT.md`, and `PROJECT_STATUS.md` entries use
explicit managed-region markers recorded in the baseline inventory. Baseline
updates replace only a selected managed region and preserve project-specific
content. An older or custom project without a trusted region inventory or
declared marker is reported as `unknown` and requires an explicit decision;
the updater does not infer a safe whole-file replacement. Symlink and type
conflicts are reported as conflicts and fail closed.

## Work-package identity

New work packages declare a stable Work package ID. Supply `--id WP-NNN` to
select a unique explicit identity; the compatible default uses the task suffix.
Multiple packages under one task require distinct IDs. Extend preserves the
established identity. Package and root-task topics may differ; links always
point to the actual authoritative task record.
