# Research Project — Agent Instructions

## 1. Purpose

This project uses a reusable research-work baseline for Codex. Its project-local records, evidence, conventions, code, and conclusions belong in this project; do not treat the baseline as a source of scientific facts or settled project knowledge.

## 2. Authority and orientation

1. Current user instructions are highest priority.
2. This root `AGENTS.md` is the default mandatory contract.
3. An accepted project ADR may override a named root default only as an explicit, applicable, narrowly scoped exception; it cannot waive truthfulness, provenance and claim boundaries, sensitive-data protection, external-action authorization, legal/safety/access controls, or the high-cost-computation confirmation gate.
4. `RESEARCH_WORKFLOW.md` supplies detailed mandatory method where it expands this contract.
5. Discussions provide context but are not binding unless promoted through an accepted decision or these operating files.

Before substantive work, read this file, `PROJECT_CONTEXT.md`, `PROJECT_STATUS.md`, the relevant task record, and applicable accepted decisions/discussions. If material authority, scope, or convention applicability is unclear, identify the boundary before taking consequential action.

## 3. Records, tasks, and project memory

Record every substantive discussion, decision, scope or convention change, assumption, conclusion, unresolved boundary, and meaningful task outcome in project Markdown. Use:

1. `discussions/` for faithful discussion and rationale;
2. `decisions/` for accepted durable decisions;
3. `PROJECT_CONTEXT.md` for concise stable project memory;
4. `PROJECT_STATUS.md` for compact current task state and next actions; and
5. permanent `tasks/T-NNN-<topic>.md` records for independent, evidence-bearing, parallel, pausable, handoffable, or explicitly tracked work.

Keep `PROJECT_CONTEXT.md` and `PROJECT_STATUS.md` concise. Update affected task records and status entries after meaningful outcomes without overwriting unrelated parallel work. Detailed lifecycle, status fields, split/merge/reopen, completion, and handoff procedures are in `RESEARCH_WORKFLOW.md`.

## 4. Directory and initialization boundary

Root initialization precreates `tasks/`, `discussions/`, `decisions/`, `references/`, `analysis/`, `code/`, `context/`, `artifacts/`, `docs/`, `assets/`, `workspaces/` and `relations/`, the six reference subdirectories, and `docs/communication/`. Empty scaffolds are valid. The workflow defines their roles; record actual work and entry points from grounded project facts. Each explicit artifact registration creates `ARTIFACT.md`, `integrity.json` and `payload/`; an empty payload directory does not establish local content or availability.

Do not move, delete, overwrite, or infer existing project content to reshape a project. `artifacts/` is the unique root registry for durable artifacts. A work package under `workspaces/` is an execution layer for one bounded task, not a nested project: root records remain authoritative, and a work-package initializer must not create or operate the root artifact registry or process sensitive/restricted material. Follow the workflow for initialization, updates, adoption, reports, and work-package structure.

For ordinary artifact work, use the packaged artifact manager Skill and operation map with workflow CLI Section 7. Use new/list/update/store/check/cleanup. List exposes saved records and known uses; check validates records and accessible bytes separately. --records-only skips hashing; --apply saves observations without changing baselines. Store defaults to the recorded accessible local source; an explicit candidate still requires original integrity proof for restoration.

Retain artifacts by default, including superseded content. Cleanup requires a human request and a reviewed CLI safety plan. Remove only the explicitly selected local payload files; retain the identity, manifest, all related records, checksum/history, relations, cleanup reason and reconstruction steps. Mark cleaned content explicitly and verify restored bytes against the retained baseline before use. If cleaned or lost content lacks matching retained integrity evidence, report the recorded reconstruction method/constraints and let the user decide whether to execute it. A newly measured candidate checksum does not prove original identity. Follow workflow Section 9.1 for the bounded cleanup/restoration procedure.

## 5. Cross-work integrity

Before substantive work, state scope, assumptions, deliverable, and proportionate verification criteria. Distinguish source facts, project/workspace definitions, locally derived results, assumptions, and unresolved boundaries. Preserve truthful provenance, exact locators where available, and traceable evidence; never present snippets, recollections, or secondary summaries as primary-source facts.

Declare applicable conventions and domain before substantive derivation or comparison. Keep claims within evidence and requested scope. Label provisional conclusions, state their evidence and limitations, and do not use them as settled premises or external conclusions without explicit user confirmation. Preserve discrepancies and original evidence; do not silently repair source, derivation, code, or result mismatches. Make surgical changes and verify proportionately before reporting completion.

For analytical formula encoded in software, record its basis and label whether evidence supports provenance/derivation, implementation correspondence, and/or physical/numerical behavior. Use the smallest sufficient non-duplicative checks for the stated risk and claim; symbolic computation is reproducible algebraic evidence, not automatic physical validation.

## 6. Explicit confirmation required

Obtain explicit user confirmation before:

- starting or materially expanding high-cost computation, including Monte Carlo or lattice simulation;
- transmitting, publishing, repurposing, or persisting non-AI-generated user-supplied sensitive data outside the requested work;
- materially changing agreed research scope, a core physical assumption, or a key convention;
- external submission, sending, publication, commitments, or sharing project code/documents/data; and
- any destructive or non-reversible action not explicitly authorized.

Use `awaiting-confirmation` only when a direct user decision/authorization is required to continue safely; use `blocked` for an external obstacle or one that remains after confirmation.

## 7. Work-type minimums

- **Literature:** record question/scope, source identity/version, relevant locator, access boundary, source role, and source-versus-interpretation distinction. Treat original PDFs as source evidence and conversions as derived copies.
- **Derivations:** declare conventions, definitions, signs, bases, normalizations, assumptions, and domain; preserve a trace from inputs/source equations to conclusions; use proportionate independent checks.
- **Reproduction and numerical work:** before main computation, create the root task's Reproduction Target and Comparison Contract. Preserve its fixed target, acceptance condition, exclusions, and bounded claim level; do not silently relax criteria after seeing results.
- **Code:** distinguish independent published-scale code projects from project-local scripts. Make the smallest change, retain traceable implementation provenance, and run the minimum sufficient direct verification before claiming success.
- **Documents and communication:** preserve source authority, provenance, notation, and audience. Use Markdown by default; maintain Formula Index identities for important project formulae; protect external material; use only real citation metadata; do not send or publish without confirmation.

`RESEARCH_WORKFLOW.md` defines the complete methods, templates, verification selection, document rules, and exception handling for these minimums.

## 8. Collaboration and portability

Default project documentation is English; user conversation may be Chinese or mixed Chinese/English. Keep the baseline tool-neutral; select tools from explicit project context or user direction. The root file governs the project. Add a subdirectory `AGENTS.md` only for a dedicated code-development directory where extra local guidance is necessary; it may supplement but not weaken this contract.

Act autonomously for routine low-risk work, but surface material ambiguity, evidence gaps, scope/convention conflicts, safety/cost gates, and consequential alternatives. Assess user proposals critically and evidence-groundedly rather than reflexively agreeing or disagreeing. A coordinating Agent may delegate independent, non-overlapping work and must integrate and verify the results.
