# Research Project Workflow

> Detailed operational handbook for this initialized research project. It expands the root `AGENTS.md`; current user instructions remain highest priority. Keep project-specific scientific facts, conventions, sources, task state, and conclusions in project-local records rather than in this reusable handbook.

## 1. Status and scope

This workflow is self-contained for a newly initialized project. Project-local accepted decisions, discussions, and task/evidence records may add scoped detail after initialization; they do not alter the root contract except through an explicit qualified exception.

The Plugin and its Skill manage the selected research project's own content, tasks, evidence and workflow. Cross-project task aggregation, priority management and shared-resource arbitration are outside their scope.

## 2. Authority and operating model

### 2.1 Authority order

1. Current user instructions.
2. Root `AGENTS.md`.
3. `RESEARCH_WORKFLOW.md` and applicable accepted project decisions in `decisions/`.
4. Relevant `discussions/` records.

A discussion is not binding merely because it exists. Durable rules become operative when accepted in an ADR and, where required, promoted into `AGENTS.md` or `RESEARCH_WORKFLOW.md`.

### 2.1.1 Authority conflicts and scoped ADR exceptions

Root `AGENTS.md` is the default mandatory contract, but an applicable accepted ADR may create a narrow explicit exception to a named root default. Such an ADR must state the exception, scope, rationale, conditions, remaining safeguards, downstream effects, and any separately required user authorization. It cannot waive user instructions or universal integrity, sensitive-data, external-action, legal/safety/permission, or high-cost-computation authorization safeguards. Within its stated scope, an accepted ADR prevails over conflicting workflow wording; a later ADR changes an earlier one only through an explicit relation such as `supersedes` or `refines`. Preserve a material ambiguity as an open boundary rather than silently choosing.

### 2.1.2 Rule-layer migration

Before moving, condensing, or deleting substantive root rules, create a traceable allocation map and a paired root/workflow draft. The map identifies the current root location, classification, any required root short form, workflow destination, authority basis, and verification criterion. User review and separate explicit approval are required before applying the substantive migration; paired execution must then verify that no mandatory behavior was lost. The map is an execution aid, not a new authority.

### 2.2 Documentation pipeline

Every substantive discussion, decision, scope change, assumption, conclusion, unresolved question, meaningful research outcome, and task-state change is recorded in Markdown:

```text
discussion record → accepted ADR → concise AGENTS.md rule → detailed workflow/template guidance
```

The reusable baseline is tool-neutral and must not contain project-specific scientific facts, sources, conventions, status, or conclusions.

### 2.3 Language and portability

Project documentation defaults to English. User conversations may be Chinese or mixed Chinese/English. Markdown should use portable syntax, standard relative links, blank lines between semantic blocks, and no renderer-specific features unless a target renderer is declared.

### 2.4 Default Agent autonomy and clarification

When the objective, scope, deliverable, and relevant conventions are clear and no confirmation gate applies, the Agent proceeds autonomously and reports its action and proportionate evidence. A material ambiguity affecting scientific scope, deliverable, core assumption, key convention, method, source interpretation, or cost requires a brief statement of the material alternatives and a focused question before action. Existing confirmation gates override this default. For a non-material ambiguity, the Agent makes and briefly states the smallest reasonable assumption rather than unnecessarily blocking progress.

### 2.5 Epistemic status and bounded response structure

When they materially affect interpretation or later work, distinguish `source fact`, `workspace definition`, `derived here`, `assumption`, `verified`, `provisional`, and `open boundary`; do not label routine prose mechanically. Explain alternatives only when their trade-offs matter. Ordinary responses default to direct conclusion, necessary evidence, material assumptions/limitations, and an applicable next action or confirmation need. Material uncertainty must appear beside the claim it qualifies. A `verified` claim names its verification object and boundary rather than implying unperformed checks.

### 2.6 Collaboration state and execution transparency

Keep discussion, proposal awaiting acceptance, accepted decision, executed action, and deferred/paused work distinct. A proposal is not implemented or settled before acceptance; an accepted decision is not evidence of execution. An executed action states what was done, observed result, and verification extent. If a consequential action could reasonably be inferred but was not performed, say so and explain why. Partial, failed, or confirmation-gated actions state their condition and next action. Include a compact status/next-action line only for a meaningful project-state change, execution, pending decision, blocker, deferral, failure, or handoff.

### 2.7 Proactive material-risk and evidence-boundary handling

Before proceeding, flag material scope creep, accepted-decision conflict, provenance loss, unsupported conclusion, hidden cost, or irreversible/destructive change. Briefly propose a simpler route when it can meet the objective with less complexity, cost, or risk. Missing, contradictory, inaccessible, or insufficient evidence must remain an explicit limitation and claim boundary; propose the smallest useful evidence-gathering step rather than filling the gap from recollection. Identify conflicts among user instruction, accepted rules, sources, code, and current records at the proper authority layer. Apply this escalation only when validity, scope, safety, reproducibility, cost, or later decisions can materially change.

### 2.8 User correction, disagreement, and critical review

A user correction or new idea is neither automatically accepted nor reflexively opposed. Identify the affected claim or record and assess it independently from relevant facts, sources, derivations, code, and assumptions. State promising elements as well as concrete limitations, unsupported steps, conflicts, risks, and validity conditions. For a material effect on an active result or deliverable, pause the affected claim, reassess the smallest necessary evidence and downstream records, and state whether unrelated work can continue. Respect user authority over objectives and strategy while keeping factual and scientific characterization evidence-grounded; correct durable records traceably.

### 2.9 Parallel delegation and coordinator review

The coordinating Agent may proactively delegate clearly independent subtasks when useful and permitted. Parallel subtasks must have no material dependency and disjoint write scopes; they must not edit the same document or shared mutable artifact concurrently. Each subtask needs a bounded objective, inputs, outputs, evidence/verification expectations, and integration path. The coordinating Agent critically reviews delegated results before incorporation, and chooses model level according to task difficulty and risk. Existing confirmation gates apply to delegated work.

### 2.10 Rule allocation, response defaults, and pre-automation review

`AGENTS.md` remains concise and mandatory; `RESEARCH_WORKFLOW.md` contains the detailed operating guidance; ADRs preserve material accepted-policy boundaries and rationale; and the readable baseline remains non-authoritative. Response structures are defaults unless an accepted safety, provenance, state/transparency, task-record, or handoff rule mandates a disclosure. Before implementing a consequential automation change, ensure its governing policy is accepted and its remaining ambiguity is resolved or explicitly bounded.

## 3. Project memory, directory structure, and initialization boundary

### 3.1 Stable context and current status

- `PROJECT_CONTEXT.md` is concise, stable project memory: definitions, sources, conventions, scope, and durable project facts.
- `PROJECT_STATUS.md` is the compact current control panel: active, in_review, backlog, paused, and recently completed tasks.
- Neither file is a complete discussion log or evidence archive.
- Unknown information must remain explicitly unknown until supported and promoted.

### 3.2 Standard directory skeleton

Every initialized research project contains:

```text
tasks/
discussions/
decisions/
references/
analysis/
code/
```

Initialization also precreates the formerly optional root directories:

```text
context/
artifacts/
docs/
assets/
workspaces/
relations/
```

Within `references/`, initialization precreates these standard subdirectories:

```text
exploration/
reading/
bib/
audits/
reviews/
library/
```

Initialization also creates `docs/communication/` for substantive communication drafts and records. The canonical CLI catalog contains this complete skeleton and every initializer invocation plans it without per-directory selection. Empty scaffolds are valid; they establish a location, not actual sources, scientific work, configured relation/Board/external adapters or payload availability. Create content and record real entry points only for grounded work. Preserve existing directory contents. An older project may have a smaller skeleton; complete it through its accepted project-structure/baseline-update process.

### 3.3 Initialization boundaries

The project initializer creates the complete standard directory skeleton non-destructively and records its paths/roles in PROJECT_CONTEXT.md and BASELINE_MANIFEST.md. It must preserve existing content and fail closed on unsafe conflicts. Root initialization creates the empty artifacts/ home; allocation, registration and payload operations use explicit artifact commands. Work-package initialization remains a separate execution interface. Directory presence alone does not establish a configured optional capability or authorize research execution.


### 3.4 Baseline package and root-project initialization

#### 3.4.1 Package payload and project identity

A reusable baseline copies release-form `AGENTS.md`, this workflow, and the complete `templates/` directory. It instantiates `PROJECT_CONTEXT.md`, `PROJECT_STATUS.md`, the complete standard directory skeleton, and `BASELINE_MANIFEST.md`. It does not copy baseline-development discussions, decisions, tasks, roadmap, status dashboard, or readable review aids.

`PROJECT_CONTEXT.md` is the project identity entry point. `BASELINE_MANIFEST.md` records: installed baseline identity; installation route/time; installed payload and enabled directory-module inventory; local divergence/exceptions; update state; and handoff/limitations. Before publication, use `Baseline release: unreleased` and a short source revision; after publication, use the release identifier and short source revision. Update it for actual baseline-payload changes and enabled directory-module inventory changes, not for every ordinary file or run.

#### 3.4.2 Root target modes and path dispositions

The root initializer recognizes `fresh`, recognized-project `extend`, bounded `adopt`, and `conflict` targets.

For a new project (`fresh`), the caller may supply a display name, brief background
and initial task description. The Agent reuses supplied fields and asks once for
all missing fields together, making clear they may be skipped. It waits for the
reply before fallback and does not repeat the question. An explicit instruction
to use defaults or summarize the directory bypasses the question; follow the
requested route, including defaults without summarization in an existing directory.
No reply is not a skip choice. Remaining omitted fields use the directory name and generic
guidance that marks project-specific information as unspecified. For an existing
directory without an installed baseline (`adopt`), the Agent first uses explicit
user fields, then, after the question/skip step, extracts each missing field from reliable project documentation
or explicit task records, retaining source paths; uncertain fields use the same
defaults. The CLI only renders prepared inputs and does not infer science from
the directory. New README/context files receive this starting information;
existing README content is preserved and adoption writes to the new context file.
Display names do not rename paths, and task descriptions do not create task
records, set active state or establish research progress. Recognized `extend`
does not replace established project information with these initialization inputs.

For each planned or relevant path, report one of:

- `create`: explicitly planned, absent, and safe to create;
- `patch-managed`: an actual bounded directory-inventory change in existing manifest/context;
- `retain-unvalidated`: expected-type existing directory in an adoption target whose contents are preserved without semantic validation;
- `outside-plan`: existing material not in the selected baseline plan;
- `skip-compatible`: compatible existing baseline content in a recognized-project extension; or
- `conflict`: incompatible, ambiguous, or unsafe collision.

A missing path is `create` only when included in the standard construction plan or another explicitly accepted interface. Any conflict makes the entire invocation fail closed with zero writes. Compatible extension can complete absent standard directories and missing inventory rows through the bounded managed regions; preserve prior inventory dates/rows and all unrelated text.

#### 3.4.3 Root preflight, confirmation, apply, and report

Every invocation follows: orient/classify → zero-write preflight → plan/report → mode-specific confirmation → create only permitted paths → post-apply verification and record update.

- A clean `fresh` request for the complete standard skeleton needs no second confirmation.
- A writing recognized-project `extend` needs separate explicit confirmation; read-only detection/plan/draft does not write.
- A bounded `adopt` always needs confirmation of the exact plan, even with no conflict.
- A conflict cannot be overridden by confirmation in that invocation.

Fresh and adopt both have a Plan ID bound to prepared project information,
date, executing-machine timezone, source bytes/revision, relevant target state
and planned writes. A supplied token must match even for fresh. New context
uses the machine's local IANA timezone automatically; extend preserves the
existing timezone. Undetectable/invalid machine timezone fails before writes.

Before root writes, stage all new contents and back up affected existing files
with modes/timestamps and a recovery journal outside the project. Ordinary
failure restores patched files and removes this invocation's newly created
paths. Report `failed-rolled-back` or, when restoration is incomplete,
`recovery-required`, retained backup and exact residual paths; both fail the
invocation. Do not continue dependent work until incomplete recovery is resolved.
Backups cover the write set, not all project data, and are removed after verified
success or recovery unless cleanup fails. Power loss, process termination and
uncooperative concurrent writers require manual investigation; no automatic
complete-restoration guarantee is made for them. The initializer usage reference
defines backup inspection and guarded manual restoration.

Every dry run, conflict, confirmation wait, and apply result has these report sections: Invocation summary; Target classification; Preflight result; Path plan; Confirmation state; Apply result; Record updates; Conflicts and manual resolution; Boundaries and limitations.

The initializer uses the static directory catalog without inferring scientific facts, sources, conventions, tasks, configured capabilities, conclusions or project-specific content. It does not overwrite, rename, move, merge, delete, or otherwise modify existing content outside an explicitly authorized bounded patch.

#### 3.4.4 Package-source changes and installed-project updates

The Plugin's source, the installed Plugin, and this project's copied baseline
have separate update states. A package-source change or Plugin installation
update does not change this project's `AGENTS.md`, workflow, templates,
scientific records, or installed-baseline manifest. Newly initialized projects
receive the baseline of the Plugin actually used for initialization.

An existing-project baseline update follows `inspect → plan → explicit confirmed
apply`. The packaged interface is `baseline inspect`, `baseline plan`, and
`baseline apply`. Inspect is read-only; plan writes only a temporary review file
and apply revalidates its exact plan before writing. Compare the current project
against `.baseline/inventory/current.json` and the current Plugin candidate:
unchanged project plus changed candidate is an update, local-only change is
preserved, both sides changed is a conflict, and a missing/untrusted ancestor is
unknown. Conflicts and unknown ancestors require an explicit decision. Keep only
`current.json` and the immediately previous `previous.json`; instantiated
scientific records remain project-local. Record `BASELINE_MANIFEST.md` changes
only after actual application.

The current initializer's fresh/adopt/extend modes do not automatically replace
an installed baseline. A Plugin source update and a project-baseline application
remain separate operations.
Project-local discussions and decisions remain this research project's records;
they do not amend the reusable Plugin without a separate package-development
change. The project follows its own installed rules and accepted scoped decisions.

## 4. Tasks, status, lifecycle, and parallel work

### 4.1 Permanent task records

Create a stable `T-NNN-<topic>.md` record for work with an independent objective, deliverable, evidence chain, verification boundary, pause/handoff boundary, parallel value, or explicit tracking request. Do not create task records for trivial answers or transient queries.

Task records remain at permanent paths. They are never moved or deleted merely because their state changes. A completed task is reactivated only when its original objective genuinely reopens; independent follow-up work gets a successor task.

### 4.2 Task states and priority

Allowed states:

```text
backlog
active
paused
in_review
completed
canceled
```

- `backlog`: recorded work not yet started. Creation alone does not authorize execution.
- `active`: selected work currently being advanced.
- `paused`: suspended work or review. Record all causes, recovery conditions, next action and resume entry. Technical blockers and waiting for authorization/input are reasons for pausing, not separate lifecycle states.
- `in_review`: submitted results awaiting review. Ordinary waiting for review remains in_review.
- `completed`: the declared objective reached a traceable outcome and its current submitted result passed the agreed review.
- `canceled`: the task will not continue. Retain its reason, downstream effect and any successor.

The allowed transitions are:

| Source | Allowed targets |
| --- | --- |
| backlog | active, canceled |
| active | paused, in_review, canceled |
| paused | active, canceled |
| in_review | active, paused, completed, canceled |
| completed | active, for a special reopening of the original objective |
| canceled | none |

No task returns to backlog. Paused work resumes only to active, then may be submitted to in_review. Completion always follows in_review and actual approval of the current result; no direct-completion exemption exists. Reopening preserves prior results and acceptance history; independent objectives get successor tasks. Same-state work updates the existing record.

Priority is independent of state and uses `P0`–`P3`. Pausing retains priority. Readiness keeps its existing separate vocabulary; a lifecycle change cannot erase a real dependency, authorization or computation gate.

Historical planned/blocked/awaiting-confirmation records remain readable without inferred causes or review evidence. Strict audits flag old states; lifecycle writes require an explicitly reviewed conversion first. This compatibility does not silently upgrade existing projects or create past approval evidence.

### 4.3 Readiness, focus, and cancellation

Readiness remains separate from lifecycle state and uses the v1 vocabulary in
the task template. `main_line` records the project's main work line;
`current_line` records the line currently being advanced; and
`current_milestone` records the active milestone when the project enables a
local Board or work-line registry. Without that optional module,
`PROJECT_STATUS.md` and the selected task record remain the focus entry points.
When a Board is enabled, its task row provides the current bounded task and its
next action.

Priority remains separate from state and readiness. It does not authorize
execution or replace explicit task selection. When work is no longer needed,
cancel the task explicitly and record the reason and downstream effect. Do not
introduce a stale-task state or infer cancellation from age.

### 4.4 Status synchronization

Every meaningful task outcome or state change updates:

- permanent task record;
- current snapshot;
- dated work log;
- matching `PROJECT_STATUS.md` row;
- matching local Board row when a Board is enabled;
- applicable discussion, decision, evidence, artifact, and handoff records.

`PROJECT_STATUS.md` must accurately show all concurrent tasks as separate entries. Updating one task must not overwrite, hide, or leave stale another task’s status, result, next action, blocker, or relation. A local Board is optional; if enabled, it is a derived operational view and must obey the same rule.

Each status row contains a compact current snapshot:

```text
ID | Priority | State | Current result | Next action | Related task(s) | Blocker | Detail | Last updated
```

`Next action` is mandatory. If no follow-up is known, write `No known follow-up`; do not leave it blank.

Task timestamps use the IANA timezone declared in `PROJECT_CONTEXT.md`. An
external tracker ID is optional and must use the project's own tracker or
coordination system; the baseline does not require Codex Taskboard or a fixed
identifier prefix.

### 4.4 Completion and handoff

A task can complete with a positive deliverable, bounded negative result, infeasibility finding, or insufficient-evidence result when that is a supported terminal answer to the task’s declared objective. Completion does not mean the broader scientific question is solved.

Before any task leaves `active`, its permanent record must provide a self-sufficient handoff:

- identity, objective, scope, deliverable, and intended audience;
- state, priority, date, and result status;
- completed work and performed checks;
- material checks not performed, skipped, or inapplicable and their consequences;
- evidence and output entry points;
- assumptions, conventions, limitations, and unresolved boundaries;
- blocker or exact confirmation request when applicable;
- related and parallel-task relationships;
- mandatory next action;
- safe continuation guidance.

### 4.5 Pause, resume, continuation, and handoff protocol

Use `paused` for deliberate deferral, technical obstacles, missing inputs or required user decisions. Record the specific reasons and resolution conditions. Normal waiting for submitted-result review remains `in_review`; genuinely suspended review uses `paused`. Before leaving active work, preserve the existing task snapshot and handoff fields: current step, last completed action, one next action, `resume_entry`, pause reason or exact confirmation request, evidence and artifact entry points, related task context, allowed write scope, material gates, and `last_updated`.

To resume a paused task, select it again, read the task record, open `resume_entry`, and confirm that no actual blocker, confirmation gate, or high-cost start condition prevents the next action. If none does, resume into `active`; entering review then requires `submit`. A valid unchanged prior review can be reused through this sequence, without repeating that review. A newly discovered blocker or gate is recorded explicitly. Continuation is same-task recovery after interruption; handoff allows another conversation, Agent, machine, or workspace to take over using the same task record. Extra path or environment checks are made only when they matter to the next action. Ordinary high-cost, sensitive, and confirmation gates still apply.

### 4.6 Optional local Board

A project may enable `tasks/TASK_BOARD.md` as a compact operational index. One
task record remains authoritative. The Board is a derived view and must not
invent task state, readiness, priority, dependencies, blockers, or next
actions. When enabled, its rows should expose the task ID, title, state,
readiness, priority, current result, next action, dependencies, blockers,
resume entry, last-updated timestamp, and detail link. A structured work-line
header may expose `main_line`, `current_line`, and `current_milestone`; these
are navigation fields and do not authorize execution. Mechanical checks are
consistency audits and do not silently migrate or rewrite historical records.

### 4.7 Optional packaged workflow CLI

The installed initializer Skill links the packaged workflow CLI usage contract.
Invoke `python3 <plugin-root>/scripts/workflowctl.py --root <project-root>` for
project/task/evidence checks, explicit task/relation/formula operations,
focus/handoff reports, projection refresh, and work-package/Run/Artifact record
support.
Task commands use `task new`, `task list [T-NNN]`, `task update`, eight explicit lifecycle verbs (`start`, `pause`, `resume`, `submit`, `revise`, `complete`, `cancel`, `reopen`), `task check`, `task refresh`, and optional `task sync`. `resume` has only the active target. `update` cannot edit State. Submitted targets and review approval bind to a version and content fingerprint in the existing task record; `complete` records actual approval and cannot grant it. Local mutations preview by default and require `--apply`; IDs, scope,
acceptance, priorities, relations, and execution facts come from explicit
inputs. Task timestamps use the project timezone. Missing optional modules
are not enabled implicitly. Reports and records do not execute research,
accept outcomes, or satisfy scientific comparison Contracts.

The optional external adapter reads context and versions, preserves native
ownership bindings, stops on conflicts, verifies readback, and records separate
comment/attachment cursors locally. External status changes remain explicit;
completion still requires actual user acceptance. Local records remain
authoritative. Record generation and synchronization do not bypass the gates
below or authorize sensitive payload copying, computations, or publication.

Evidence records use the read-only `evidence list` and `evidence check` routes
for structural discovery and validation of comparison, derivation, source-audit,
literature, and Formula Index records. These checks do not infer source roles,
scientific validity, Contract satisfaction, or derivation correctness. The
`formula check` route validates Formula Index order, locations, completeness,
and allocation history. `formula allocate` previews by default and requires
`--apply` to write `FORMULA_INDEX.md` and `.workflowctl/formula-ids.json`; it
records an explicit caller-provided identity and does not decide formula
importance or correctness.

### 4.8 Starting and continuing selected work

When a task is selected, recover its objective, scope, current result, next
action, resume entry, and any recorded blocker from the project context,
status, and permanent task record. Read the enabled Board or relation views
when relevant; no fixed reading order is required. Use the recorded
`next_action` and `resume_entry` to continue under Section 4.5. If no task is
selected, no task-management action is required.

The optional packaged CLI can retrieve this context with
`task list T-NNN --view context` or `task list T-NNN --view handoff`. The older `focus show --task T-NNN`, `task show T-NNN`, and `handoff report T-NNN` remain compatibility routes.
Eligible-task output is a candidate list, not task selection. Apply dependency
rules from this project's accepted policy and enabled modules; optional tools
do not establish a new mandatory external-tracker policy.

After meaningful work, update the task snapshot and Work log, then its status
and enabled Board projections under Section 4.4. Use explicit CLI record
operations and projection refresh when applicable. If external synchronization
is configured and requested, use the adapter's versioned writes and readback;
report any unresolved mismatch in the same task record. Section 4.7 and the
packaged CLI reference define those operations.

## 5. Confirmation gates and safety boundaries

Explicit user confirmation is required before:

- starting or materially expanding high-cost computation, including Monte Carlo or lattice simulation;
- transmitting, publishing, repurposing, or persisting user-supplied non-AI-generated sensitive data outside the explicitly requested work;
- materially changing research scope;
- changing a core physical assumption;
- changing a key convention;
- external submission, sending, publication, authorship, acknowledgement, conflict, or equivalent declarations;
- sharing code, documents, data, or other project materials externally where the action is not already explicitly authorized.

The proposed change, reason, downstream effect, and exact decision requested must be recorded before waiting for confirmation.

## 6. Evidence, claims, and source provenance

### 6.1 Claim boundaries

Distinguish:

- source facts;
- project/workspace definitions;
- results derived in current work;
- assumptions;
- provisional interpretations;
- unresolved boundaries.

Do not present search snippets, secondary summaries, unverified recollections, or invented citations as primary-source facts. Core claims require claim-level evidence with an exact locator where available.

### 6.2 Source roles and conflicts

Classify each source by role and preserve its version, reading copy, access state, and precise locator where relevant. Material source conflicts and version differences require an explicit audit. Unavailable full text or unresolved conflicts limit the claim to `provisional` unless the task establishes a different bounded result.

External PDFs are source evidence and are protected. Local PDF-to-Markdown or OCR output is a derived working copy, never a replacement for the original PDF. The future local physics-paper PDF conversion task remains deferred.

### 6.3 Specialist literature exploration

A project may configure a specialist source profile. For high-energy-physics work, the accepted preference is to use arXiv and INSPIRE-HEP as primary discovery sources when configured by the project. Exploration records preserve useful leads and searched scope; detailed reading records are created for substantively used sources.

BibTeX for project papers uses citation information supplied by INSPIRE-HEP. Bibliographic metadata must never be invented.

## 7. Derivations and symbolic computation

### 7.1 Derivation requirements

Before substantive derivation or formula comparison, declare:

- conventions and scope;
- definitions and symbols;
- signs, bases, axes, ordering, and normalization;
- units and dimensional conventions;
- assumptions, approximations, boundaries, and applicability domain;
- source-to-workspace translations.

Preserve a trace from source or local input to each substantive transformation, correction, approximation, and final formula. Preserve source text when auditing it; annotate rather than silently rewrite.

### 7.2 Source basis and provenance

Every important derived expression needs a truthful basis locator. The basis may be:

- an external source;
- first principles or a stated theoretical framework;
- a project-local derivation or source audit;
- an explicit implementation/design choice with rationale and limitation;
- a project discovery or experience, truthfully labelled as project-local evidence.

Never fabricate a literature basis.

### 7.3 Mathematica and verification layers

Configured Mathematica/Wolfram tooling may provide reproducible symbolic or algebraic evidence. It does not automatically establish physical validity. Preserve executable code, assumptions, environment, inputs, outputs, and limitations when the result supports a core claim or handoff.

Separate three verification objects:

1. provenance/derivation;
2. implementation correspondence;
3. physical/numerical behavior.

A meaningful check must state which object(s) it supports. The detailed route for analytical-formula encoding checks remains subject to the accepted proportionate rules and must not be replaced by a generic “formula verified” statement.

## 8. Reproduction, numerical work, and computation

### 8.1 Contract before main computation

Every substantive reproduction or independent numerical task has a Reproduction Target and Comparison Contract before the main computation. The contract specifies source/system and version, target object or behavior, inputs and parameter range, comparison method, acceptance condition, tolerance or qualitative rule, exclusions, and scientific non-claims.

Use:

- `R-NNN` for one configuration-frozen execution unit;
- `C-NNN` for one fixed-basis comparison conclusion.

Material changes to code, input, environment, randomness, resources, algorithm, execution target, comparison basis, or acceptance condition require a new relevant run/comparison record.

### 8.2 Claim-strength ladder

Report no higher than the evidence supports:

1. `execution completed`;
2. `implementation verified`;
3. `contract target satisfied`;
4. `scientific conclusion supported`.

Visual resemblance alone is not quantitative validation unless the predeclared Contract explicitly defines a qualitative target.

### 8.3 Work packages and remote execution

The first execution controller is a portable local detached backend. The user
supplies the program, code, environment and inputs; the CLI supplies explicit
submission metadata, process identity, one-shot observations and bounded
handoff. `run submit` is preview-only unless `--apply` is supplied. The
controller does not install a resident monitor: `run monitor` takes one
observation and may be called by an external scheduler. CPU and memory are
observed when available. Progress is read only from an explicitly declared
heartbeat/progress file. Retry is explicit-only and disabled by default.
Artifact registration remains an explicit user/Agent action through the artifact
CLI; Run submission never sweeps or copies outputs.

A lightweight work package under `workspaces/T-NNN-<topic>/` is an execution layer, not a nested project. Project governance, task records, discussions, decisions, source records, and durable artifacts remain at the root.

The remote execution framework is reserved for future work. The current project leaves space for remote profiles, scheduler job IDs, environment and artifact links, and return paths, but does not assume a configured remote environment or authorize credential handling.

High-cost computation requires confirmation, pre-run configuration/resource review, and post-run evidence.



### 8.4 Work-package construction, maintenance, and verification

Create a lightweight work package only for an explicitly enabled bounded reproduction or numerical execution task that already has a root `T-NNN` record. It is never a nested project. Root `PROJECT_CONTEXT.md`, `PROJECT_STATUS.md`, tasks, decisions, discussions, project-level references, and the root artifact registry remain authoritative.

The work package conventionally lives at `workspaces/T-NNN-<topic>/` and has one `WORK_PACKAGE.md` entry point. The root task retains the canonical Reproduction Target and Comparison Contract; the work-package entry point links to the root task file and names the Contract section in text without relying on an automatic heading anchor.

Construction modes are:

- `minimal`: create only the package directory and `WORK_PACKAGE.md`;
- `full`: create `WORK_PACKAGE.md` plus `analysis/`, `code/`, `environment/`, `inputs/`, `runs/`, `comparisons/`, and `logs/`; and
- `extend`: create only explicitly requested missing accepted directories/templates in an existing compatible package.

The Agent or global Skill prepares explicit inputs: root task, path/topic, mode, selected modules, a grounded concise Purpose summary, and any explicitly requested grounded task-information updates. The deterministic initializer does not perform language-model reasoning or infer science; it preflights, creates permitted paths, applies allowed bounded patches, and reports.

A compatible `WORK_PACKAGE.md` has exactly one initializer-managed Section 1 date field:

```markdown
- **Last updated:** YYYY-MM-DD <!-- initializer-managed:last-updated -->
```

and exactly one ordered Section 4 structural region:

```markdown
<!-- BEGIN INITIALIZER-MANAGED STRUCTURE v1 -->
...
<!-- END INITIALIZER-MANAGED STRUCTURE v1 -->
```

A structural extension updates only the date value and the content strictly between these markers. The region records enabled local directories, their standard roles, and neutral placeholders. It never invents concrete code entry points, environment facts, inputs, runs, comparisons, artifacts, evidence, or scientific claims.

Purpose, scope-specific deliverables/non-claims, included execution material, labelled evidence links, and labelled limitation/handoff fields may be changed only when an explicit grounded input identifies a unique supported one-line field. The initializer may not rewrite arbitrary prose, headings, comments, marker lines, or tables outside the managed region. Missing, duplicate, malformed, unsupported, or inconsistent patch targets are conflicts with zero writes.

Reports retain path dispositions for ordinary paths and separately state the document-patch action: `none`, `required bounded structural patch`, or `explicitly requested grounded patch`. For every document patch, name affected regions/labels, cause/basis, preservation statement, and outcome. A no-op extension with no missing selected module and no explicit passive update leaves `WORK_PACKAGE.md` unchanged.

Acceptance tests cover minimal/full creation, selected/complete extension, dry run, missing identity, incompatible entry point, unsafe paths, compatible retention, and artifact-registry non-interference. Every conflict test asserts zero created paths. Work-package initialization never creates the root `artifacts/` directory, allocates `A-NNN`, copies/registers/relocates payloads, or processes sensitive/restricted material.

## 9. Artifacts, data, results, and databases

### 9.1 Artifact-first model

The packaged artifact operation map and workflow CLI reference Section 7 route
registration, discovery, files, relations, integrity and cleanup. The artifact
manager Skill handles ordinary artifact work. The six CLI operations are new/list/update/store/check/cleanup. List
exposes registered records, retained inventories/history and known uses. Check
validates records and observes accessible bytes separately; --records-only
checks saved structure/status. Missing, external or cleaned bytes are not
certified by a valid manifest.

`artifacts/` is precreated at root initialization and is the unique project registry for durable artifacts. Registering an artifact remains explicit. A durable artifact receives a stable `A-NNN` identity and one canonical location or controlled external manifest. Runs, inputs, comparisons, analyses, and documents reference artifacts rather than copying or moving them when their role changes.

Every explicit registration creates the same complete entry structure: ARTIFACT.md, integrity.json and payload/. The default entry is `artifacts/A-ID-topic/`. Local registered contents live inside payload/: filename for a single file, useful internal structure for a coherent collection. Existing explicit entry paths retain their identity. External/restricted entries also receive an empty payload/ scaffold; their explicit status/access route and pending verification remain authoritative. An empty directory does not satisfy a present-content declaration: local registration still requires actual files or explicit archival inputs. No additional artifact child layout is inferred.

The CLI handles explicitly selected local file operations and also reconciles manual operations. Use `new --source --operation copy|move --reason` to archive while registering, `artifact store` for an existing unchanged local object, and `artifact update --change-kind location` after manually placing the same unchanged object inside its `payload/`. Store defaults to the recorded definite accessible local source; --source selects an authorized candidate when needed. Already held, state-consistent bytes are a checked no-op. Missing or external content requires explicit source preparation rather than inferred historical locations. Copy retains source files; move removes the selected source files after payload and document writes succeed, and may retain empty original directories. Archival may fill an empty payload/ scaffold; existing content is never merged/overwritten. Symlinks/overlaps are rejected, and another artifact's registered content/references cannot be silently reassigned. Preview is read only; `--apply` commits files, directories and records with ordinary-error rollback.

Archival and reconciliation update all identifiable project-document path references, including task/run/analysis/document records and structured relation/input records. The CLI scans project UTF-8 Markdown/text, TeX/HTML and JSON/YAML/TOML, handles root-relative, document-relative and absolute local paths, and reports the updated documents. Ambiguous interpretations block application. Original execution commands, source facts and prior correction history retain their locators; current pointers are updated and history/source relocation notes or retained-reference reports preserve the distinction. Registered payload contents and protected external material are not edited. Binary document bodies require their editable source/rendering workflow; path reconciliation does not establish that exported documents were regenerated. Payload, manifest, ID/lineage and document changes share the coordinated file plan; manual reconciliation declares unchanged content rather than proving equivalence.

The CLI owns checksum recording and rechecking. Registration of accessible local content records a SHA-256 baseline in the entry's integrity.json, linked from ARTIFACT.md Section 3. A file/collection inventory records each regular file's payload-relative path, byte size and checksum; collections are not represented by only a directory checksum. For a file root, path . denotes that file, whose actual location is in the manifest. Registration/archival and manually corrected local locations share inventory/manifest updates with the file plan. Relocation compares existing baselines and refuses mismatched bytes or membership; old observation routes remain historical facts. Explicit artifact check recomputes the current inventory and reports added, missing and changed files. Applying its findings records observations/history and manifest status, even when verification fails, without replacing the baseline or modifying content. Different content follows the new-ID policy below. A first accessible inventory is recorded, not retrospectively verified; corrupt inventories must be recovered rather than reset.

Recheck before consequential reuse or handoff, after transfers/manual file operations, and promptly when previously unavailable content becomes accessible. Artifact check validates records and compares accessible bytes by default; --records-only skips hashing and cannot persist observations. --apply records actual findings; mismatches remain failures. External views absent and deliberate cleanup remain explicit no-observation states. --all is read only. Byte checks do not establish source authenticity, scientific correctness or continued remote availability.

External content without accessible bytes remains pending. On an access failure, record the reason and a concrete backup or replacement next action; applying unavailable status requires that recovery plan. Treat the external resource as unreliable for durable reliance until that action is resolved. Restored access permits immediate byte verification but does not by itself complete recovery. Obtain an authorized local backup under payload/ or select and register a reliable replacement, preserving the original provenance and existing ID/version/relationship rules. Restricted no-copy conditions still apply; use an authorized alternative when copying is unavailable. Check can read a caller-selected authorized project-local view without copying it or claiming remote endpoint access. Store/location update can retain such acquired bytes for an existing file/collection unit, preserving its source route and comparing any established baseline; a manifest-only unit needs a separately registered local unit rather than an implicit granularity change. Use artifact update --change-kind recovery for a registered distinct replacement with an explicit central supersedes relation and passing current bytes. Retain the original unavailable state, source facts and every recovery event; completion records the selected action rather than certifying equivalence or updating consumers automatically. The CLI does not automatically download, monitor, select or certify replacements.

The user or Agent decides whether material has durable project value and should be registered: cross-task/run reuse, comparison or conclusion support, handoff, controlled sensitive/restricted access, costly regeneration, or another explicit retention need. The caller supplies a meaningful `Retention reason` in the artifact record. The artifact CLI requires that reason and checks record completeness; it does not assess the scientific merit of the reason or automatically register all run outputs. Temporary run-local material remains eligible to stay local under Section 9.2.

Select an artifact unit that can be independently referenced, used and handed off. Related files may form one coherent collection when they share source, version and retention rationale and are normally used together. Objects with independent provenance, reuse or updates normally receive separate registrations and explicit relationships. Directory co-location or production by one run alone does not determine grouping. The user or Agent selects the unit and declares `Artifact granularity` as `single file`, `coherent collection` or `manifest-only reference`. The CLI validates this declaration and record completeness; it does not infer scientific coherence or automatically group or split files.

Artifact IDs are positive project-global numbers written with at least three digits: `A-001` through `A-999`, then `A-1000` and onward. Normal CLI registration allocates the next number after the largest recorded allocation or existing declared artifact ID. Explicit IDs remain available for imports or controlled cases, including unused historical numbers; they do not lower the automatic sequence. Names, locations and uses do not change the established ID. Gaps are allowed and allocated IDs are never reused.

The CLI retains allocation history in `artifacts/.artifact-ids.json` and commits history and entry creation through the existing coordinated file-plan write path. Keep this history with the project even when an entry is removed; do not delete/reset it to reclaim numbers. First adoption includes existing declared IDs but cannot reconstruct unavailable older deletion history. Corrupt history must be recovered before allocating. Preview is read only and its candidate ID is not reserved. A competing or stale registration fails on conflict and may be planned again from current state; ordinary write failures use the existing rollback behavior. This coordination covers cooperating CLI writers, not new crash-recovery or noncooperating-writer guarantees.

For an already registered object, descriptive corrections or an authorized location change retain its ID when content and provenance are unchanged. Record the reason, prior values, changed fields and update time. Changed durable content, changed collection membership or a derived object normally receives a new ID with explicit predecessor/upstream relationships. Keep old referenced content traceable and do not silently substitute changed content under an old ID. The user or Agent classifies the change; structural checks do not establish scientific or content equivalence.

Use `artifact update` for caller-declared metadata or location-record corrections. Existing reproduction/reconstruction route, regeneration cost and storage-boundary fields may be corrected with grounded inputs and a reason; the CLI does not execute the steps. Its bounded fields preserve identity, granularity, origin and version/integrity identifiers and retain a correction log. This command edits records, not payload files; local location corrections also reconcile project-document references. Use `artifact new --supersedes` for a new retained version and `--derived-from` for a derived artifact, with an explicit reason and an existing relation registry. These flags declare artifact-to-artifact `supersedes` or `derived_from` edges in the existing central authority; manifest lineage fields point there. New ID history, entry and lineage writes share FilePlan. No source or scientific relationship is inferred from filenames or matching content.

Retain artifacts by default, including superseded versions. Cleanup starts with a human request; neither age, a task state nor a successor authorizes automatic deletion. Use `artifact cleanup` with the selected entry, named human requester, reason and project-local UTF-8 reconstruction document. Preserve actual steps, code/input/environment/source references, validation method and cost/access constraints; state any unavailable ingredients. Supplied instructions are retained evidence, not a successful reconstruction or scientific-value assessment.

The CLI previews removal of only the registered local payload files after comparing current bytes/membership with the retained checksum baseline. Shared registered content, live payload-path references, and explicit consuming tasks that are unfinished or cannot be resolved block cleanup. Run/work-package consumers are checked through their owning root task. Historical commands/source locators, completed/canceled consumer records and stable-ID/manifest references remain recorded. Reference checking covers the known project text/structured formats; binary documents, payload-internal and external dependencies require human review. Resolve current use explicitly before replanning; do not erase history to make a check pass. The plan binds the request, consulted files and directory membership. Applying requires the exact current preview plan_id via --confirm-plan; changed inputs require renewed review. Files and records share the existing FilePlan conflict checks and ordinary-error rollback.

After cleanup, Payload status is cleaned. Keep ARTIFACT.md, integrity.json with the original baseline/observations, allocation history, all task/run/source/document records and central relationships. Append the requester, reason, confirmed plan, removed-file paths/sizes/checksums, reference findings, reconstruction steps and constraints to the manifest and integrity cleanup history. Preserve the former payload location as a historical locator and retain the empty directory scaffolds. Cleaning a retained backup reopens its existing recovery action instead of leaving it marked backed-up. Check reports deliberate cleanup without claiming current byte verification or silently rebasing integrity. No registry records, external/restricted resources or unrelated local files are deleted by this command. Reacquired identical content can be explicitly archived/reconciled, must match the original checksum inventory and leaves cleanup/restoration history intact; different content needs the established new-ID/version route. Existing projects require their confirmed baseline update before using newly delivered rules.

The work-package initializer must not create or operate the root artifact registry, allocate `A-NNN`, or process sensitive/restricted payloads without a separately authorized root workflow.

For cleaned or lost content, restore a selected candidate under the existing ID
only when retained original integrity evidence establishes the same content. A
file requires the retained checksum; a collection requires the complete per-file
inventory and membership. A first checksum measured on a candidate is not proof
against the missing original. If evidence is absent, invalid or mismatched,
report the condition and the recorded reconstruction route/constraints, preserve
all records, and let the user decide whether to execute reconstruction. Do not
execute reconstruction or silently substitute the candidate. Matching evidence
permits the requested restoration without a separate reconstruction decision;
normal operation previews/access boundaries remain. Retain restoration/history
and verify actual reconstruction results without claiming identity from steps
or approval alone. First acquisition of never-held external content remains a
first observation, with its explicit source/reliability boundaries.

### 9.2 Data and results distinction

A durable input or output is classified by identity and provenance, not merely by whether it was used as input or output in a particular run. A result from one run that becomes an input to another remains the same durable artifact when its identity and provenance are unchanged; the later run records it as a consumed artifact.

Short-lived, reproducible, run-local material may remain local to the run. Expensive, handoff-relevant, sensitive, externally sourced, or conclusion-bearing data needs durable artifact/provenance treatment.

### 9.3 Optional local SQL/analytical database

A project may enable a local SQL or analytical database for large, relational, query-intensive, or repeated-run data. It is not part of the default structure and the baseline remains tool-neutral.

A database record preserves schema/version, engine/package version, import or generation code and command, source artifact IDs/hashes, database version/hash where feasible, query entry points, limitations, and sensitivity/access boundaries. Parallel reads are a supported design target; concurrent writes require an explicit transaction, locking, serialization, or writer-ownership strategy.

## 10. Documents, figures, tables, and communication

### 10.1 Markdown

- The baseline does not prescribe fixed inline-math or display-math delimiters; the Agent selects suitable syntax for the task and target environment.
- When an explicit task requests it, the opt-in post-generation Markdown formatter/auditor may normalize supported generated mathematics to `$...$` and blank-line-separated `$$...$$` output. A task may explicitly invoke its single-file postprocess command after writing a Markdown work file; neither the initializer nor the baseline automatically installs or triggers it. It audits project work Markdown rather than baseline/control/template files by default and does not change the Agent-facing delimiter-neutral rule.
- Important or later-referenced display formulae use explicit project-global `\tag{F-NNN}` identifiers.
- The root Formula Index retains stable project-global `F-NNN` identities independently of the selected delimiter syntax.
- The root `FORMULA_INDEX.md` is created when the first formula ID is allocated; IDs increase monotonically, gaps are allowed, and IDs are never reused.
- Cross-file references use descriptive standard relative links.
- Semantic blocks are separated by blank lines.
- Ordinary prose is not reflowed merely for normalization.
- Each complete standalone document has one unnumbered `#` title and hierarchically numbered lower headings.
- Automatic TOC and front matter are not default requirements.

### 10.2 LaTeX and PDF

Editable `.tex`, `.bib`, figure source, and other project-maintained source files are authoritative; compiled PDF is derived. Compile every PDF-affecting change and perform visual checks when reader-facing acceptance requires them.

Protect external PDFs. Do not alter submission-template formatting unless explicitly requested. Formal paper PDFs must not display internal `F-NNN` tags; use ordinary LaTeX numbering and internal labels if needed. BibTeX metadata must come from INSPIRE-HEP and must not be fabricated.

For a complete local physics-paper PDF-to-Markdown workflow, every
pre-registered mathematical anchor must be represented in explicit,
human-auditable LaTeX for both inline and displayed mathematics. Unicode or
special-character approximations do not satisfy that gate. The original PDF
remains the evidence source; the Markdown or OCR result is a derived working
representation with usable source-page traceability. A generic formatter or
undocumented cleanup must not convert failed mathematical output into a
passing workflow. Any multi-stage mathematics-recovery route must be named,
frozen, manifested, and evaluated as its own workflow. A candidate that does
not meet this gate remains a bounded text or navigation aid rather than a
complete conversion workflow.

### 10.3 Figures and tables

For project-generated figures, plotting scripts or editable vector/source representations are authoritative; exported images are derived. Paper figures require visual checks after generation and embedding. Do not silently smooth, remove outliers, crop meaningful content, normalize, rescale, or otherwise alter data for appearance.

Project-generated tables retain source-data and generation provenance. Exported CSV/XLSX/LaTeX/Markdown tables are derived unless explicitly declared otherwise. Reader-facing tables need captions, column names, units, precision/error information, abbreviation/footnote explanations, and evidence links. Formatting must not hide numerical differences.

### 10.4 Code-facing documentation

Independent large code projects have their own Git repository and must be self-contained with:

```text
README.md
docs/physics/
docs/implementation/
src/
tests/
examples/
```

`examples/` is required. The consuming research project records exact version/release/commit, purpose, relevant interface/conventions, results, limitations, and handoff, but does not copy the independent project’s full documentation. Small project-local scripts use lightweight code rules and do not require this structure.

### 10.5 Short external communication

Persist only substantive messages with scientific/technical claims, commitments, decisions, feedback, version confirmations, important handoff information, or later project impact. `docs/communication/` is optional. Agents may draft and revise but may not send, publish, make commitments in the user’s name, or share sensitive/project material externally without confirmation.

### 10.6 Word/DOCX and presentations

Markdown remains the default authoring basis. Word/DOCX and presentations may be read or reviewed, but no default agent-generation workflow is accepted. Handle future writing or material editing case by case after defining source, renderer/application, preservation requirements, visual acceptance, and confirmation boundaries.

## 11. Optional and future capabilities

The following are not enabled merely because this handbook describes their boundaries:

- root artifact-registry allocation/registration workflows;
- Markdown syntax/format auditing beyond the explicit opt-in formatter/auditor described in Section 10.1;
- local physics-paper PDF-to-Markdown conversion tooling;
- reusable plotting-style or figure-QA tooling;
- database-engine/schema tooling;
- remote/HPC execution profiles;
- a `policy/` directory split; and
- work-type-specific verification methods beyond the accepted proportionate rules.

Enable or implement an optional capability only through an explicit project task and applicable user authorization.

## 12. Canonical navigation

- Mandatory operating contract: [`AGENTS.md`](AGENTS.md)
- Detailed methods: [`RESEARCH_WORKFLOW.md`](RESEARCH_WORKFLOW.md)
- Stable project memory: [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md)
- Current task dashboard: [`PROJECT_STATUS.md`](PROJECT_STATUS.md)
- Permanent task records: [`tasks/`](tasks/)
- Discussion records: [`discussions/`](discussions/)
- Accepted project decisions: [`decisions/`](decisions/)
- Reusable templates: [`templates/`](templates/)
