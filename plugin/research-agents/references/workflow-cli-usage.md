# Workflow CLI usage

Invoke the installed Plugin and select the initialized research project:

```bash
python3 <plugin-root>/scripts/workflowctl.py --root <project-root> project check --json
```

Python 3.10 or later and its standard library are sufficient. Discover
`<plugin-root>` through the installed initializer Skill. The Plugin's scripts
are separate from the research project. `--root` and `--json` also work after
the group or leaf subcommand. Each leaf has `--help` for exact inputs.

## 1. Commands and touched records

| Command | Function and explicit inputs | Authority / records touched |
| --- | --- | --- |
| `project check` | Required baseline paths and file/directory kinds | Read only: baseline files and required directories |
| `task check [T-NNN] [--area AREA] [--strict]` | Record/handoff/lifecycle/review/relation/dependency/view diagnostics; strict mode audits legacy records | Read only: local records and references |
| `task list [T-NNN]` | Collection filters or selected task views; records array with record_hash | Read only: task records |
| `task show T-NNN` | Compatibility response with fields/sections/record/hash | Read only: selected task |
| `task new` | Explicit ID/topic/title/objective/scope/acceptance/deliverable/next action/priority/Contract applicability | New task, matching status/optional Board rows; registry only for explicit prerequisites |
| `task update T-NNN` | Bounded --set/--input patches, --reason, optional --if-hash; State rejected | Selected task/history, projections; registry only for explicit prerequisite edits |
| `task start/pause/resume/submit/revise/complete/cancel/reopen T-NNN` | Explicit lifecycle action and evidence, --reason, optional --input/--if-hash | Selected task/history and projections; never starts a process or grants approval |
| `task refresh T-NNN` / `task refresh --all` | Preview/rebuild derived displays | Dependency display, status and existing Board |
| `task sync T-NNN --taskctl PATH` | Explicit optional external adapter | Same version/binding/cursor/readback contract as sync external-readback |
| `relation check` / `validate` / `target-check` | Syntax, declared IDs, entity kinds, documentary basis, cycles | Read only: optional registry and entry records |
| `relation show ID` / `path SOURCE TARGET` | Established adjacent edges or one directed path | Read only: registry and identities |
| `relation add SOURCE TYPE TARGET --basis PATH --reason TEXT` | Explicit established edge; date optional | Registry; for depends_on, source task history and source/target projections |
| `dependency check [--taskctl PATH]` | Prerequisite state/readiness, cycles, drift, optional live external status | Read only: registry/tasks/optional Board/external issues |
| `focus show [--task T-NNN] [--taskctl PATH]` | Selected checkpoint, work lines, all eligible tasks and bounded explanations | Read only: records and optional external issues |
| `view refresh [--task T-NNN]` | Refresh projections from local authority | Task dependency fields, PROJECT_STATUS.md, existing optional Board |
| `handoff check T-NNN` / `report T-NNN` | Checkpoint, resume path/anchor, current plan step/version | Read only: selected task and resume record |
| `sync external-readback --task T-NNN --taskctl PATH` | Context/mismatches; explicit metadata/status/relation writes and readback | Optional external issue/comment and local sync receipt |
| `work-package preflight` / `create` / `report` | Explicit task/topic/purpose; optional ID/mode/modules/date | Selected workspaces/T-NNN-topic entry and execution directories only |
| `run check --path PATH` / `new` | Explicit ID/topic/work package and JSON template fields | Read or create one runs/R-NNN[-M]-topic/RUN.md in a configured work package |
| `evidence list [--kind KIND]` | Discover comparison, derivation, source-audit, literature, and Formula Index records | Read only: known project evidence locations |
| `evidence check [--kind KIND] [--path PATH]` | Check record sections, explicit fields, stable IDs, duplicate IDs, local links, and Formula Index consistency | Read only: selected evidence records and declared links |
| `formula check` | Check root Formula Index order, duplicate/non-indexed IDs, row completeness, and declared locations | Read only: `FORMULA_INDEX.md` and `.workflowctl/formula-ids.json` |
| `formula allocate` | Preview or apply one explicit Formula Index row and update non-reuse history | `FORMULA_INDEX.md` and `.workflowctl/formula-ids.json`; no scientific judgment |
| `artifact new` | Explicit template JSON/topic; optional ID/destination/source/copy or move/lineage | Register a stable unit and full scaffold; coordinated payload/record/reference writes when requested |
| `artifact list [ID]` | Collection filters or selected record/inventory/history/references view | Read-only saved evidence and known references |
| `artifact update ID` | Metadata/location field corrections, or specialized recovery completion; reason required | Preserve identity, history and baseline; reconcile manual placement or record checked replacement completion |
| `artifact store ID` | Recorded accessible local source by default; optional explicit candidate; copy/move and reason | Place unchanged bytes under payload/ with coordinated records/references; proof-gated restoration |
| `artifact check ID` / `check --all` | Record consistency and fresh accessible-byte check; records-only or authorized external view | Read only by default; single-entry --apply records actual findings without modifying bytes/baseline |
| `artifact cleanup ID` | Human request, reconstruction file and exact current plan confirmation | Remove selected local bytes; retain all records, identity, checksum/history and steps |

Reports, queries and checks without --apply never write. Artifact check --apply
saves observations; --records-only and --all stay read only. Local mutations preview by default;
`--apply` writes. Previews contain changed paths, hashes, and diffs. Work-package
commands report the initializer's path plan; preflight always makes zero writes.
No command executes research, chooses work automatically, or accepts results.

Evidence record checks are structural only. `evidence list` discovers records in
the standard comparison, analysis, and reference directories. `evidence check`
checks explicit template sections, unresolved fields, stable IDs, local Markdown
links, and duplicate IDs. It does not infer source roles, scientific validity,
Contract satisfaction, or derivation correctness. Formula allocation previews by
default, creates the root `FORMULA_INDEX.md` only on `--apply`, and retains
allocated IDs in `.workflowctl/formula-ids.json`; gaps are allowed and IDs are
never reused. The allocation command records the caller's description, location,
basis, and status without deciding formula importance or correctness.

## 2. Output and failures

All JSON responses have `schema_version: 1`, `ok`, and `diagnostics`. Diagnostics
carry `code`, project-relative `path`, `message`, `severity`, `failure_class`,
and optional `entity`. Invalid outside paths use `<input>`. Failure classes
separate invalid local data, required input, conflicts, and unavailable external
evidence. Exit codes remain portable across command families:

- `0`: no error diagnostics; informational not-configured messages and read-only sync mismatches may be present;
- `1`: error diagnostics; inspect the stable code and failure class;
- `2`: command-line usage error.

Record checks prove structural consistency only; artifact check also observes
accessible bytes, with separate results for records and content. Neither result
proves scientific validity. A preview does not freeze later
shared-file changes. Use a task's displayed hash with `task update --if-hash`
when applying an update reviewed against that exact snapshot.

## 3. Optional modules

Run `project check` after applied root initialization/adoption/extension, on
first takeover of an unfamiliar project or after migration/restoration, after
structural edits, or when a path failure suggests structural damage. It checks
README.md, AGENTS.md, RESEARCH_WORKFLOW.md, PROJECT_CONTEXT.md,
PROJECT_STATUS.md and BASELINE_MANIFEST.md as files, the required runtime
the `templates/` directory and runtime templates `templates/TASK.md`,
`templates/RUN.md`, `templates/ARTIFACT.md` and `templates/WORK_PACKAGE.md`,
and all nineteen standard directories by kind. All checked files must be
non-empty UTF-8 text. Other templates remain available for explicit record
types but are not required by the current project-check command. It does not
validate semantic content or installed version. It reports
`PROJECT_MISSING_PATH`, `PROJECT_WRONG_KIND`, and `PROJECT_EMPTY_FILE`
separately; symlink paths retain `PATH_SYMLINK`.
First confirm the selected root when a check fails. Preserve existing content
and inspect missing paths, wrong kinds or symlinks before repair. Pause operations
that depend on the failed foundation. Initializer extend can complete missing
standard-extra directories; missing core paths remain conflicts. Baseline
replacement follows the staged, explicitly confirmed update process. Recheck
the structure and affected operation after repair; this check never repairs files.

Core checks need initialized-project baseline paths. Task mutations require a
valid IANA `Project timezone` in PROJECT_CONTEXT.md. Missing optional modules
are not enabled implicitly:

- Existing tasks/TASK_BOARD.md enables Board checks/projections.
- Explicit relations/RELATIONS.yaml uses JSON-compatible YAML; bootstrap with
  `{"version": 1, "relations": []}`. Declared dependency views without a registry fail closed.
- Root initialization precreates workspaces/ and artifacts/ with the complete standard directory catalog. Record commands still require their homes; old project structure is completed through the accepted initializer/update workflow. Work-package runs/ follows its own selected execution profile.
- External operations require the caller-selected exact `--taskctl` executable. No fixed tracker, issue prefix, token, or endpoint is a baseline dependency.

## 4. Task and projection operations

```bash
python3 <plugin-root>/scripts/workflowctl.py --root <project-root> task new \
  --task-id T-001 --topic method-check --title 'Check the method' \
  --objective 'Validate the bounded implementation' --scope 'Declared method only' \
  --acceptance 'Predeclared checks pass' --deliverable 'A validation record' \
  --next-action 'Read the method specification' --priority P1 --readiness ready \
  --contract-applicability 'not applicable' --contract-reason 'Tooling task only' --json
```

Use `--contract-applicability required` for scientific comparison work and
complete the task-level Contract before computation. New tasks are backlog;
record creation does not start them. Repeat `--depends-on T-NNN` for explicit
existing prerequisites. No relation is inferred.

```text
task update T-001 --set 'Next action=Inspect result' --reason 'Checks finished' --if-hash HASH
task update T-002 --depends-on T-001 --reason 'Declared direct prerequisite'
task update T-002 --clear-dependencies --reason 'Explicit prerequisite correction'
```

Editable fields: Priority, Readiness, Objective, Scope, Out of scope,
Acceptance, Deliverable / intended audience, Current result, Current step,
Implementation plan version, Resume entry, Next action, Blocker, External tracker
ID. Plan-version edits also update the living plan's version. Current step must
exist in the living plan or be `—`. Changes append a dated Work log entry.
State writes through update return USE_LIFECYCLE_COMMAND. Cancellation uses task cancel and is refused while dependent tasks still name the prerequisite. Terminal objective/acceptance/outcome changes require reopening or a successor.

### 4.1 Query and lifecycle

```text
task list [--state STATE] [--readiness VALUE] [--priority VALUE] [--query TEXT] [--eligible]
task list T-NNN [--view full|snapshot|plan|history|evidence|context|handoff|review]
task start T-NNN --reason TEXT
task pause T-NNN --reason TEXT --resume-when TEXT
task resume T-NNN --reason TEXT
task submit T-NNN [--input FILE] --reason TEXT
task revise T-NNN --feedback-ref PATH[#ANCHOR] --reason TEXT
task complete T-NNN --review-ref PATH[#ANCHOR] --review-version VERSION --reason TEXT
task cancel T-NNN --reason TEXT
task reopen T-NNN --reason TEXT
```

Every lifecycle mutation also accepts --input FILE, --if-hash HASH and --apply.
Active-entry commands accept explicit --taskctl PATH when prerequisite tasks
have external trackers. They require ready/no recorded blocker, valid next
step/handoff, and completed prerequisites; unavailable live evidence refuses
the transition. Real authorization, scientific validity and applicable
execution gates remain Agent/user judgments, not implications of flags.

List without an ID returns summaries; with an ID it defaults to the full
record. Selected IDs cannot mix with collection filters. An unknown ID is an
error. Plan and history views separate the current living plan from outcomes.
Context/handoff views expose continuation information; review exposes the
lifecycle evidence stored in the same task record.

| Action | Sources | Target |
| --- | --- | --- |
| start | backlog | active |
| pause | active, in_review | paused |
| resume | paused | active |
| submit | active | in_review |
| revise | in_review | active |
| complete | in_review | completed |
| cancel | backlog, active, paused, in_review | canceled |
| reopen | completed | active |

Resume has no --to. Even suspended review follows paused → active → in_review.
Its reason records the basis for resolving all applicable pause conditions;
readiness/blocker changes use an explicit snapshot patch. Reopen preserves the
original objective and approval history; its reason supplies the special
reopening basis. Update causes while remaining paused using input.pause.

### 4.2 Bounded operation input

--input is a project-relative UTF-8 JSON file for this invocation, not a
persistent checkpoint database. Unknown keys and State injection are rejected.
The supported patches are:

```json
{
  "snapshot": {"next_action": "Review current result", "resume_entry": "#8-handoff"},
  "plan": {
    "version": "v2",
    "steps": [{"id": "S1", "text": "Inspect result", "completed": false}]
  },
  "sections": {"evidence": "- Evidence: see result.md"}
}
```

Snapshot keys are lowercase editable-field names with spaces replaced by
underscores (deliverable_intended_audience for the deliverable field).
Sections append prose to work_log/evidence/risks/handoff; they cannot replace
identity, lifecycle or plan headings. Plan steps require stable unique S-number
IDs, text and optional boolean completed; changed steps need a new version and
the prior plan remains quoted in the Work log. The current step must remain in
the resulting plan. --set and input cannot assign the same field twice.

Pause or same-state paused update also accepts:

```json
{"pause": {"reasons": [{"reason": "Input unavailable", "resume_when": "Input supplied"}]}}
```

Pause adds the command's required reason/condition to these additional causes.
Update replaces the current cause list, retaining prior context in history.
Reasons stay visible even after resume records their resolution basis.

### 4.3 Submission and actual approval

First submission requires input.submission:

```json
{
  "submission": {
    "version": "v1",
    "targets": ["docs/result.md#result"],
    "verification_refs": ["docs/checks.md"],
    "limitations": "Only the declared bounded result was checked"
  }
}
```

Targets and verification refs resolve from project root and must be UTF-8
files or uniquely identified Markdown headings. Verification refs may be empty
only with explicit limitations. The mutable whole task/control sections are
not review targets. The CLI binds target contents and objective/scope/acceptance
to a submission fingerprint; task timestamps/log/state do not create a new
result version. Changed contents/context require a new submission version.
An unchanged recorded submission can be reused with submit without --input.

The submit response and task list T-NNN --view review expose the fingerprint.
The actual review source referenced by complete must record:

```text
- **Task ID:** T-NNN
- **Review result:** approved
- **Submission version:** v1
- **Submission fingerprint:** <fingerprint from the reviewed submission>
```

Passed is also accepted as the review result. Complete checks the actual
source, current version and content binding, then records its reference and
sets readiness completed. A flag or an invented approved statement cannot
create reviewer authority. Review must have actually occurred under the task's
acceptance contract. Valid unchanged approval can be reused after pause/resume;
changed targets cannot use the old approval. All evidence stays in the existing
Handoff Lifecycle evidence subsection, with transitions and prior plans in
Work log. No second task state is stored there.

### 4.4 Checks, compatibility and projections

Task check areas: record, handoff, lifecycle, review, relations, dependencies,
views and all (default). Checks are read only; refresh previews or repairs
projections, not task state. Refresh requires one ID or --all. Task sync keeps
external status explicit: there is no automatic paused → blocked mapping.

Legacy planned/blocked/awaiting-confirmation records remain readable in list
and non-strict schema audits. Lifecycle mutations return TASK_LEGACY_STATE;
convert them only through an explicitly reviewed project update preserving
pause causes, local divergence and historical evidence. Strict checks flag old
states and unverified historical completions. Compatibility task show and
older focus/handoff/view/sync routes remain available; no removal deadline is
implied. Updating Plugin source does not upgrade existing projects.

Task and dependency checks report snapshot drift in existing status/Board rows.
View refresh reports drift before and after the proposed change.
Projection ownership covers matching task-ID rows and declared columns.
Manual prose, unknown columns, and the broader manual Related task(s) status
column remain intact. State changes move rows among the baseline Current work,
Planned and paused, and Completed recently sections; the completed section stays
a curated subset. Custom files receive new tables within explicit BEGIN/END
WORKFLOWCTL TASK VIEW v1 markers. Prerequisite edits refresh the source and
changed prerequisites; they do not migrate unrelated history.

Local plans reject duplicate IDs, existing creation targets, symlinks, outside
paths, stale snapshots, and competing CLI locks. Writes stage files, recheck
original bytes, replace each file, and roll back caught failures. This is
optimistic coordination, not a crash-proof multi-file database transaction;
noncooperating editors still require review.

## 5. Relations, focus, and handoff

Declared IDs: T-NNN, WP-NNN, R-NNN[-M], A-NNN, DISC-NNN, ADR-NNNN. Artifact NNN
is a positive number with at least three digits, continuing as A-1000 after A-999.
Work-package and run identities resolve through leaf WORK_PACKAGE.md and RUN.md entry
records. Targets and basis files must exist inside the project. Duplicate IDs/
edges, self-relations, invalid entity kinds, and dependency cycles are rejected.
Vocabulary: depends_on, has_work_package, executes, consumes, produces,
documents, governs, successor_of, supersedes, derived_from. The last two connect
artifact versions or derived artifacts to their explicit predecessors/upstreams.
Generic task/relationship retirement has no v1 lifecycle
contract; explicit artifact payload cleanup is described in Section 7. Explicit prerequisite replacement/clearing records the owning task's
reason. Standalone relationctl retains syntax validation/queries; its add writes
immediately using unified target/cycle/projection checks. Use workflowctl for
previewed writes.

Dependency checks validate the declared IDs, kinds and basis files of direct
`depends_on` edges as well as cycles and derived dependency displays. Invalid
graph structure suppresses the eligible-task list and prevents active entry.
Active entry checks dependency display drift before changing state; it does
not silently repair it. An explicit refresh can rebuild drifted displays from
a valid registry. Refresh rejects unresolved registry targets, invalid basis
files and cycles before proposing writes. Without a registry, dependency
declarations in either task records or Board rows are preserved and reported
as `DEPENDENCY_AUTHORITY_MISSING`; they are never cleared or promoted to edges.

With no declared dependencies, a missing registry is informational and local
checks and task operations remain usable. Enabling the registry is explicit.
Only caller-declared direct edges are stored; path output does not create
transitive edges. Basis checks establish file existence and confinement, not
the truth of its contents or the validity of a heading anchor. Correcting
general relation history and selecting a project dependency policy require
their own scoped decisions.

Focus selects only `--task T-NNN` or an explicit Board Current task field. It
returns line/milestone context, result/step/next action/resume/blocker/detail,
state/readiness/gated, allowed scope, and all eligible tasks. A Board selection
must identify one task; an ambiguous declaration or a nonempty declaration
without a task ID returns `FOCUS_SELECTION_INVALID`. An unknown task ID returns
`TASK_MISSING`. An explicit
`--task` overrides Board selection. With no selection, the current task stays
unset; neither priority nor the candidate list selects it.
One witness path per reachable prerequisite bounds
explanations. Registry eligibility requires local completed/completed and live
done when a prerequisite declares an external ID. Missing evidence and view
drift remain explicit. Optional checks do not adopt unaccepted project policy.

Candidates exclude tasks with an explicit recorded blocker even when readiness
is ready. Handoff and selected focus reports expose that blocker through
`gated`; readiness gates remain visible too. Selected focus and `task list
T-NNN --view context|handoff` reuse handoff checkpoint, resume-link and plan
checks. Failures are top-level diagnostics with exit 1; the invalid selected
task is omitted from focus candidates. Other valid candidates remain visible
unless graph/projection errors invalidate the candidate set. Unselected tasks
are not subjected to a new universal handoff-validation ceremony.

Handoff checks validate checkpoint presence, resume links/heading anchors,
and current plan step/version agreement. Reports expose scope, gates, evidence,
risks, and continuation context. A valid report neither proves restored runtime
state nor authorizes high-cost, sensitive, or confirmation-gated execution.

## 6. Explicit external synchronization

```text
sync external-readback --task T-001 --taskctl /absolute/path/to/taskctl
sync external-readback --task T-001 --taskctl /absolute/path/to/taskctl --thread-id ACTUAL_ID --apply
```

Read issue context, comments, and attachments before deciding on writes; honor
instructions to wait. Synchronization uses the local record as the description
and maps explicit P0/P1/P2/P3 priorities to urgent/high/medium/low. Status needs
`--status`; direct external prerequisites need `--sync-relations`. Neither is
inferred. Parent/related edges are outside this operation.

Each write uses the latest version, preserves the saved five-field native Codex
binding, rejects foreign ownership, prechecks prerequisite project identity,
and verifies live metadata/status/binding/relations. Description comparison
accounts for the service trimming outer whitespace; internal content differences
remain mismatches. Unbound owned status needs
all five --binding-* fields listed by --help. Attribution alone is insufficient.
In_progress requires local active/ready. Moving into in_review requires an
explicit `--comment-file` containing outcome, verification, and limitations; the
comment is read back. Done requires local completed and --accept-completion.
These flags carry caller authorization and never replace actual user acceptance
or authorize backlog execution.

Conflicts stop and reread without replaying writes. Unavailable services,
partial writes, and mismatches are distinct reports. External calls are not one
atomic transaction; reconcile partial results explicitly. Apply results save
hashes, versions, outcome, and separate comment/attachment cursors in
`tasks/.workflow-sync/T-NNN.json`; raw comments/attachments are not copied.
Later reads reuse saved cursors unless --after-comments/--after-attachments
override them. Read-only calls create no receipt.

## 7. Work packages, runs, and artifacts

### Artifact command selection

The primary set is new, list, update, store, check, cleanup. Existing-entry
operations select exactly one positional ID or --path ENTRY. New's --path is a
destination, not a selector. Collection list accepts filters; selected list
accepts --view record|inventory|history|references and rejects collection filters.
These views expose saved evidence and do not rehash payloads.

```text
artifact list --origin generated --query scan
artifact list A-001 --view record
artifact list A-001 --view inventory
artifact list A-001 --view history
artifact list A-001 --view references
artifact check A-001
artifact check A-001 --records-only
artifact check --all
artifact store A-001 --operation copy --reason 'Retain the recorded object'
```

Check requires one selector or --all. --all checks each registered entry read
only and rejects --apply and per-entry observation inputs; apply individual
findings explicitly. --records-only rejects --apply and byte/access/recovery
inputs. Default check exposes record_check (saved structure/status) and
content_check (this call's observation). content_check.status is recorded for
first accessible evidence, passed/mismatch for baseline comparison, unavailable
for failed access, cleaned for deliberate removal, not-observed when no external
view is supplied, or blocked when record corruption prevents checking. observed
marks an actual byte/access observation; verified is true only for a passing
retained-baseline comparison. persisted marks a saved observation. Exit success
alone does not mean bytes were verified. A prior saved mismatch remains in
record_check while a fresh matching observation can pass; the retained baseline
never changes. --apply saves actual findings, even failures, which still return
error diagnostics. External/cleaned no-observation calls do not rewrite history.

Compatibility routes remain callable: register → new with --path;
show/references → list with the corresponding view; archive → store with explicit
source; reconcile → update location; verify → check's byte-observation backend;
recovery-complete → update recovery. Check's old structural-only behavior is now
explicit --records-only. Compatibility verify retains its original response
shape. These names do not add further core operations.


The [artifact operation map](artifact-operations.md) covers supported operations,
human responsibilities and surrounding actions that require separate work.

### Read-only artifact discovery

```text
artifact list --query scan --status present --origin generated
artifact list --granularity "coherent collection"
artifact list A-001 --view record
artifact list --path artifacts/A-001-scan --view inventory
artifact list A-001 --view history
artifact list A-001 --view references
```

Select exactly one ID or path for a saved view. Missing/duplicate IDs and
invalid selectors are diagnosed. List includes registered manifests, excluding
payload-internal notes and empty scaffolds; filters use declared record fields.
Selected list returns the record or saved inventory/history. The references view reports explicit
central edges and identifiable project text/structured references, including
manifest links. It cannot discover undocumented, binary, external or
payload-internal uses. These queries never modify records or hash current bytes;
use check for a fresh observation. An absent registry remains not configured.

### Creation inputs

```text
work-package preflight --task T-001 --topic method-check --id WP-001 --purpose 'Bounded check' --mode full
work-package create --task T-001 --topic method-check --id WP-001 --purpose 'Bounded check' --mode full --apply
work-package report --task T-001 --topic method-check
run new --id R-001-001 --topic validation --work-package workspaces/T-001-method-check --record-file run-input.json
artifact new --id A-001 --topic result --record-file artifact-input.json
artifact new --id A-002 --topic source --path artifacts/A-002-source/ARTIFACT.md --record-file source-input.json
artifact new --topic result --record-file artifact-input.json
artifact new --topic source --path artifacts/controlled-source/ARTIFACT.md --record-file source-input.json
```

### Run submission and one-shot monitoring

`run new` and `run check` create and validate records only. They never launch a
program. The lightweight local controller accepts an explicit user-supplied
command and starts it with detached standard streams and a controller-owned
attempt record. Preview is the default; `--apply` is required to submit.

```text
run submit --path workspaces/T-001-method-check/runs/R-001-001-validation \
  --command 'python code/run.py --config inputs/config.json' \
  --cwd workspaces/T-001-method-check --progress-file workspaces/T-001-method-check/logs/progress.json --apply
run status --path workspaces/T-001-method-check/runs/R-001-001-validation
run monitor --path workspaces/T-001-method-check/runs/R-001-001-validation --apply
run schedule --path workspaces/T-001-method-check/runs/R-001-001-validation --interval 30 --apply
run stop --path workspaces/T-001-method-check/runs/R-001-001-validation --apply
run retry --path workspaces/T-001-method-check/runs/R-001-001-validation --apply
```

The first backend is `local-detached-v1`; its process identity and observations
are stored beside `RUN.md` in `.run-controller.json`. The implementation uses
platform-native detached process creation and does not require a resident
service. `run monitor` is one-shot and can be invoked by cron, launchd,
systemd, Task Scheduler or another external scheduler. The CLI does not install
or own that schedule. CPU and memory are observations when the local platform
exposes them; unavailable measurements remain unavailable.

`run schedule --apply` records the requested Codex-thread monitoring schedule
in `.run-controller.json` with `automation_status=pending-codex-automation`.
The current Codex session then creates the thread heartbeat automation and
records its automation ID in the Run state. The project-local CLI cannot create
a Codex app automation without that session-level operation.

Progress comes only from an explicitly selected heartbeat/progress file. The
controller does not parse arbitrary stdout and does not infer health from file
existence. Retry is explicit only and disabled by default; material changes to
the frozen configuration require a new `R-NNN`. Output registration remains a
separate explicit `artifact new/store/check` operation. The Run controller does
not glob outputs, choose retention, copy payloads, or certify scientific
results.

Work packages reuse minimal/full/extend initializer gates. The compatible
default ID is WP- plus the task suffix; another package for the same task needs
a distinct explicit --id. Extend cannot change established IDs. No provenance
relation is created automatically.

--record-file is a project-local JSON object of exact template field labels to
explicit single-line strings. Unknown, missing, or placeholder values are
rejected. Read the project templates to supply meaningful values:

- Run required fields: Root task, Execution intent, Configuration-freeze boundary,
  Code revision / snapshot, Environment manifest, Input manifest, Randomness /
  seed plan and actual seed record, Exact invocation / entry point, Planned
  resources, Overall execution disposition, Execution outcome. Root task must
  match the work package. Disposition: completed, failed, cancelled, terminated,
  incomplete. A pre-execution record states incomplete; the caller supplies facts.
- Artifact required fields: Name, Artifact granularity, Logical content,
  Formats / schema / units, Version or integrity identifier, Origin, Producer
  task / run or source locator, Payload status, Canonical payload location or
  controlled access route, Sensitivity, license, and access conditions, Retention
  reason, Known limitations. Origin: generated, external, user-supplied, derived.
  Payload status: present, controlled external reference, restricted no-copy,
  unavailable. Local present paths are inventoried with per-file SHA-256/size;
  external/no-copy routes without accessible bytes remain pending. Local present content must be inside this entry's
  payload/. With explicit --source and --operation, the CLI derives Payload
  status and the destination location; the other required fields remain explicit.

--id supplies the required Run ID or an optional explicit Artifact ID; a JSON ID must agree. Checks retain seven
Run or six Artifact sections. Artifact check validates records and observes current accessible bytes by
default; --records-only checks saved record/inventory structure without hashing.
The record_check and content_check results remain separate. Neither command accesses remote endpoints, executes runs, freezes
environments, or judges scientific Contract results.

The user or Agent decides whether an artifact has durable value and selects it
for registration. The caller must provide a meaningful Retention reason.
Artifact new reject an omitted, blank or unresolved-placeholder reason;
artifact check diagnoses an incomplete reason in an existing record. The CLI
validates required fields without assessing the scientific merit of the reason.
Registration operates on the explicitly selected artifact; it does not sweep
run outputs into the registry. See workflow Section 9.1 for retention criteria.

Artifact granularity must be single file, coherent collection or manifest-only
reference. The user or Agent selects the complete object to register using
workflow Section 9.1. Artifact new reject an unsupported declaration;
artifact check diagnoses it in an existing record. The CLI validates the
explicit declaration without judging scientific coherence or automatically
grouping/splitting files by directory or producer run.

For artifacts, omit both --id and JSON ID for automatic allocation. Supplying
JSON ID without --id is an explicit-ID request. IDs use canonical positive
numbers with at least three digits: A-001, A-999, A-1000. Automatic allocation
continues above the largest ID in retained history/current declarations. An
explicit import may fill an unused historical gap; any already allocated ID
is rejected even if its entry was removed. Display topics do not affect identity.

New defaults to artifacts/ID-topic/ARTIFACT.md. An explicit --path selects
an entry directory or ARTIFACT.md, which need not embed the allocated ID. Without --apply,
id_status is tentative, no paths/history change and the candidate is not
reserved. With --apply, successful registration returns id_status registered.
History and entry writes share FilePlan's lock/snapshot/rollback path. Competing
plans can return WRITE_CONFLICT; re-plan from current state rather than treating
a preview candidate as reserved. Failed validation or ordinary write rollback
does not allocate an ID.

Keep artifacts/.artifact-ids.json with the project and do not reset it when
retiring an entry. The first successful adoption includes existing declared IDs;
older deleted identities require recovered history and cannot be inferred.
Malformed history stops allocation. This adds no crash-recovery guarantee or
coordination with writers that bypass the CLI.

### Artifact record corrections and new versions

The user or Agent declares the change type. Descriptive corrections or a changed
access/location record retain the ID when content and provenance are unchanged.
Changed durable content, collection members or derived objects use a new ID.
Preserve old referenced content and record explicit lineage; do not silently
replace the old payload. CLI structure checks do not prove unchanged content
or scientific equivalence.

```text
artifact update A-001 --change-kind metadata --set 'Name=Corrected label' --reason 'Correct description; object unchanged'
artifact update A-001 --change-kind location --set 'Canonical payload location or controlled access route=artifacts/A-001-result/payload/result.dat' --reason 'Record an authorized unchanged-content location'
artifact new --topic corrected --record-file corrected-input.json --supersedes A-001 --reason 'Corrected retained data version'
artifact new --topic derived --record-file derived-input.json --derived-from A-001 --derived-from A-002 --reason 'Declared derivation inputs'
```

All default to preview; add --apply to write. Update requires --change-kind and --reason. Metadata/location kinds require
at least one --set. Recovery requires --replacement and rejects --set,
--recovery and --follow-up; it uses the specialized completion checks below.
--source is available only for an authorized external replacement byte view. Metadata fields are Name, Logical content,
Formats / schema / units, Producer task / run or source locator, Sensitivity,
license, and access conditions, Retention reason, Known limitations, Do not infer
/ do not use for, Safe continuation notes, Reproduction or reconstruction route,
Regeneration cost / constraint, and Retention, deletion, or external-storage
boundary. An explicit regeneration cost is low, material, high-cost or not
reproducible locally; steps and constraints are supplied by the caller. Location fields are Canonical
payload location or controlled access route and Payload status. Identity,
granularity, origin, version/integrity fields and lineage cannot be changed by
this correction command. Required fields remain complete and declared local
present paths must exist. A location correction can repair a missing old path.

Updates retain the six template sections, last-updated time and an appended
reason/before/after log. They preserve allocation history and actual files;
same-value corrections are no-ops. New versions/derivations retain the complete
explicit creation inputs. --supersedes selects one existing artifact;
--derived-from may repeat for distinct existing artifacts. A reason is required
when either is used. relations/RELATIONS.yaml must already be configured.
The explicit edges are authoritative there; corresponding manifest fields use
registry pointers. Supply lineage through the flags rather than another JSON
field definition. Old records are unchanged; relation show OLD_ID finds reverse
links. Creation, allocation and relation writes share FilePlan conflict/rollback
behavior. Update alone does not move files; new stores bytes only when
explicit source/operation inputs are supplied.

### Store payloads and reconcile manual placement

```text
artifact new --topic scan --record-file scan-input.json --source workspaces/T-001-study/runs/R-001-study/scratch/scan.csv --operation copy --reason 'Retain comparison data'
artifact new --topic scan --path artifacts/retained-scan/ARTIFACT.md --record-file scan-input.json --source workspaces/T-001-study/runs/R-001-study/scratch/scan.csv --operation move --reason 'Archive selected local data'
artifact store A-001 --source legacy/scan.csv --operation move --reason 'Archive the same registered object'
artifact update A-001 --change-kind location --set 'Canonical payload location or controlled access route=artifacts/A-001-scan/payload/scan.csv' --reason 'Manual unchanged-object relocation'
```

Preview is default; add --apply after inspecting the file/document plan. During new, source and operation must be supplied together; store requires
operation and reason and defaults to the record's definite accessible local
location. Supply --source only when selecting an authorized candidate explicitly. The
JSON location, when supplied, must agree with the source or selected destination;
external/restricted declarations cannot be overridden by a local archival flag.
Copy preserves source files; move removes the selected source files after the
other writes succeed. Empty source directories may remain. A file is placed at
payload/filename, a collection at payload/ with its internal structure retained.
Every registration creates ARTIFACT.md, integrity.json and payload/. Local
registration supports manually placed actual contents; manifest-only entries
retain an empty payload scaffold with their external status. Empty scaffolding
does not establish content availability or byte verification. Check diagnoses legacy
local locations outside the entry's payload/; use store or explicit location
reconciliation rather than resetting the identity or overwriting existing files.

Store uses the registered unchanged local object when it is accessible.
Already stored, state-consistent content is a no-op after comparing current bytes;
it does not append redundant history. Missing local bytes, external routes and
historical source locators are not guessed or fetched. Without a usable source,
the CLI reports ARTIFACT_SOURCE_REQUIRED with recorded reconstruction guidance.
An explicit candidate cannot substitute a different object for existing content. If the recorded local location is missing, an explicitly selected
recovery candidate may be archived only when retained integrity evidence matches;
its placement also repairs identifiable references to the missing old location. Update location checks the caller-declared actual location under payload/
without copying/deleting files and reconciles references.
Changed content, collections or provenance retain the existing new-ID boundary.
An archival source owned by another artifact is refused, preserving predecessor
content/references; produce or explicitly prepare distinct derived content first.

Document reconciliation scans the project for UTF-8 .md/.markdown/.rst/.txt,
.tex/.html/.htm, .json/.yaml/.yml/.toml path references, including structured
relation records. Root-relative, document-relative and absolute local references,
percent-encoded paths and link fragments are supported. JSON updates retain the
data structure but may reformat whitespace. External URLs, registered payload
contents, binary document bodies and dependency/tool-state directories are not
rewritten. Original execution/source fields and earlier correction/archival logs
retain their facts; textual records receive location notes when appropriate,
and JSON historical fields are preserved alongside updated live references.
The result documents.updated lists changed documents and documents.historical
lists retained historical references. The scope is exact identifiable path
references, not inference of undocumented scientific relations or regeneration
of PDF/Office exports; use their editable-source workflow for those bodies.
Ambiguous root/document-relative paths or unreadable relevant documents block
the operation instead of claiming all references were repaired.

File changes report create/update/delete, hashes and diffs; binary diffs are null.
FilePlan snapshots source bytes, existing documents and directory membership,
stages writes under its lock, and rolls back ordinary failures, including partial
source-file removals. Allocation, lineage, payloads and document changes are one
plan. This is cooperating-writer coordination and ordinary-error rollback, not
crash recovery or streaming of unbounded-size datasets. Explicit directory
creates are also reported, committed and rolled back in the same artifact plan.
Store can fill an existing empty payload/ scaffold, including empty nested
directories retained after cleanup; files, symlinks and special paths at the
destination are refused. Directory membership is watched until application. Root initialization precreates the registry home,
without allocating IDs or registering artifacts.

### Byte integrity and external access recovery

Registration inventories accessible local content automatically. Each entry
retains integrity.json beside ARTIFACT.md with algorithm sha256, artifact ID,
baseline files, last observation, observation history and any access-recovery
plan. Each file has a relative path, size_bytes and sha256. For a single root
file, path . denotes the file at the manifest's canonical location; a directory
root records every regular file relative to that directory. Empty directories
and filesystem permissions are not content checksums. The six manifest sections
stay intact; Section 3 contains the checksum/size summary and registry pointer.
An optional caller-supplied file checksum must be SHA-256 (raw lowercase hexadecimal or
sha256:hexadecimal). It is retained as an expected checksum even before external
bytes are accessible and is compared before establishing a measured baseline.
Other source-provided identifiers belong in version/provenance fields; the CLI
does not silently discard an unsupported declared checksum.

```bash
artifact check A-001
artifact check A-001 --apply
artifact check A-002 --unavailable --reason 'Canonical endpoint is inaccessible' --recovery backup --follow-up 'Acquire and archive an authorized exact-content copy' --apply
artifact check A-002 --source staging/acquired-source.dat --apply
artifact store A-002 --source staging/acquired-source.dat --operation copy --reason 'Retain the authorized same-source local backup' --apply
```

Check is read only by default. --apply updates integrity.json and manifest
summaries/history through the same FilePlan, including mismatch/unavailable
findings. Such findings still return ok false and a nonzero exit status even
when the recording operation applied successfully. No payload bytes are edited.
Recorded baselines are never refreshed to conceal changed bytes or collection
membership. Findings identify added, removed and changed files and observed
checksums for mismatches. Use the accepted new-ID/version policy for changed
durable objects. Store/location updates compare any retained
baseline and refuse mismatched content before writing files or references.
Without a prior baseline, the first accessible inventory is recorded; it does
not prove past identity. Invalid checksum records must be recovered, not reset.

Recheck after transfers/manual operations, before consequential reuse/handoff,
and promptly after regaining authorized access. Check reports record consistency and fresh accessible-byte findings separately.
For external entries, check --source reads a caller-selected project-contained regular file/collection
representing authorized external content; it does not copy it or prove the
remote endpoint currently works. Without --source or --unavailable, no external
verification occurs and prior observations/recovery plans remain untouched.

Persisting unavailable status requires --recovery backup|replace and a concrete
--follow-up. --unavailable also requires --reason and cannot be combined with
--source. New of an unavailable entry and location updates to that
status use the same recovery flags. Record failures promptly; an unavailable
resource is unreliable for durable reliance until backed up or replaced.
Restored access may verify bytes, but an unresolved recovery action remains
visible. A backup is marked backed-up only after matching accessible bytes are
actually retained at the declared local payload/ location. Acquiring/archiving
a local backup retains source provenance and any established checksum baseline.
No-copy entries cannot be archived. A manifest-only unit is not silently
converted to a file/collection; register the explicitly selected local unit
separately. A different replacement resource also receives its own ID and the
appropriate caller-declared central relation. The CLI neither selects nor
certifies scientific equivalence of alternatives, schedules monitoring nor
downloads external resources or bypasses copying/access authorization.

### Update recovery after a declared replacement

```text
artifact update A-002 --change-kind recovery --replacement A-003 --reason 'Registered and checked the selected replacement'
artifact update A-002 --change-kind recovery --replacement A-003 --source staging/replacement.dat --reason 'Checked the authorized external view' --apply
```

Preview is default. The original entry must have a recorded replacement action.
The distinct replacement must already be registered, with an explicit central
supersedes edge from replacement to original. Its structure and current bytes
must pass, and it must not have an unresolved recovery action. External
replacement content requires a caller-selected authorized project-local source.
The CLI records completion, successor ID, central-registry pointer, reason and
current byte evidence while preserving the original source/access facts,
baseline, observations and unavailable state. Completion does not certify
scientific equivalence, remote endpoint availability or downstream adoption;
review and update actual consumer references explicitly. Renewed failures reopen
the recovery action while retaining every prior completion event.

### Human-requested artifact cleanup

Retain artifacts by default, including superseded versions. Cleanup is explicit
and attributed to the human who requested it. No timer, task completion or
version relation triggers cleanup. Prepare a project-local UTF-8 reconstruction
document with actual commands/steps, code/input/environment/source references,
validation method, cost/access constraints and any unavailable ingredients.

```bash
python3 plugin/research-agents/scripts/workflowctl.py --root PROJECT artifact cleanup \
  A-001 --requested-by 'Human requester' \
  --reason 'Human-selected retention change' --reproduction-file docs/reconstruction.md --json

# Review the returned files, retained records, dependencies, constraints and plan_id.
# Repeat the same request with its exact current plan_id to execute:
python3 plugin/research-agents/scripts/workflowctl.py --root PROJECT artifact cleanup \
  A-001 --requested-by 'Human requester' \
  --reason 'Human-selected retention change' --reproduction-file docs/reconstruction.md \
  --confirm-plan PLAN_ID_FROM_CURRENT_PREVIEW --apply --json
```

Safety checks compare current bytes/membership to the retained inventory, refuse
shared registered ownership and live payload-path references, and check explicit
consumes relations against the consumer's root task. Unfinished or unresolved
consumers block cleanup; completed/canceled task relations and stable-ID/manifest
references remain traceable. Known project text/structured formats are inspected;
binary documents, payload-internal/external dependencies and scientific value
remain human review responsibilities. Caller attribution is recorded rather than
an authenticated approval service. Changed request, reconstruction document,
consulted records or directory membership invalidates confirmation. Source
commands and prior artifact history retain their original locators. Resolve live
use explicitly and preserve the earlier record before replanning.

Only the selected registered local payload files are removed. The CLI retains
ARTIFACT.md, integrity.json, its original baseline/observations, allocation
history, all related project records and relationships. Manifest and integrity
history record the human/request/reason/plan, removed paths/sizes/checksums,
reference findings and a full retained copy of the reconstruction steps. Empty
directory scaffolds remain. Payload status becomes cleaned; check reports
this intentional state without claiming new byte verification. Removing a
previously retained backup reopens its recorded recovery action. External or
restricted references and registry metadata are outside this command.

Explicit store or location update may restore unchanged content only after comparing
the original checksum baseline; retain every cleanup/restoration event. Changed
content follows the new-ID/version rule. Supplied steps do not prove successful
reconstruction, continued source access or scientific acceptability. The existing
ordinary-error rollback/cooperating-writer/resource boundaries apply; no crash
recovery, network deletion, automatic purge or research execution is added.


### Missing-content restoration and reconstruction decision

For cleaned or lost local content, store/location correction must
compare candidate bytes to retained original evidence. A recorded SHA-256 can
prove a single file; a collection needs its full retained inventory/membership.
Matching evidence permits the requested restoration under the same ID with
normal preview/apply and history. Actual mismatches retain the old baseline and
follow the existing changed-content/new-ID rule.

Absent proof refuses direct restoration with ARTIFACT_RESTORATION_PROOF_REQUIRED,
reports the recorded reconstruction route and cost/constraint and preserves files,
records and IDs. Report the method and available inputs to the user for a
reconstruction decision; do not execute it automatically. A later candidate at
the same recorded path cannot establish a fresh baseline to hide recorded loss.
Missing/corrupt inventories are recovered rather than reset. First acquisition
of previously unobserved external content remains a first observation, not a
certificate of historical identity. Reconstruction approval/instructions do not
by themselves certify the result; retain unresolved facts and check actual output.
