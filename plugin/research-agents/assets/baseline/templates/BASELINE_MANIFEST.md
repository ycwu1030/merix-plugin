# Baseline Manifest

<!-- research-baseline-manifest:v1 -->

> Compact installation and update metadata for this project. This file is not behavioral authority: use `AGENTS.md`, `RESEARCH_WORKFLOW.md`, `PROJECT_CONTEXT.md`, and `PROJECT_STATUS.md` for project operation. Keep detailed plans, conflicts, and update evidence in the relevant task, discussion, and decision records.

## 1. Installed baseline

- **Baseline package:** `merix-research`
- **Baseline release:** unreleased
- **Source identity type:** `git-commit`
- **Source repository or distribution:**
- **Source revision:** unavailable
- **Source revision algorithm:** `sha1`
- **Source state:** unknown
- **Baseline payload digest:** unavailable
- **Payload digest scope:** `AGENTS.md`, `RESEARCH_WORKFLOW.md`, and `templates/`
- **Current baseline inventory:** [.baseline/inventory/current.json](.baseline/inventory/current.json)
- **Previous baseline inventory:** unavailable — no trusted ancestor
- **Project identity entry point:** [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md)

## 2. Installation

- **Installed on:** YYYY-MM-DD
- **Installation route:** `fresh initialization` | `confirmed adoption application` | `confirmed extend application`
- **Initializer / invocation record:**
- **Confirmation record (if required):**

## 3. Installed payload and enabled modules

- **Release payload:** `AGENTS.md`, `RESEARCH_WORKFLOW.md`, and `templates/`
- **Instantiated project files:** `README.md`, `PROJECT_CONTEXT.md`, `PROJECT_STATUS.md`, and this manifest

| Path | Classification | Enabled on | Enablement route | Role / primary entry point | Record |
| --- | --- | --- | --- | --- | --- |
| `tasks/` | required root | YYYY-MM-DD | `initial-standard` | Permanent task records | [PROJECT_STATUS.md](PROJECT_STATUS.md) |
| `discussions/` | required root | YYYY-MM-DD | `initial-standard` | Chronological substantive discussions | |
| `decisions/` | required root | YYYY-MM-DD | `initial-standard` | Accepted project decisions | |
| `references/` | required root | YYYY-MM-DD | `initial-standard` | Source/exploration entry point | |
| `analysis/` | required root | YYYY-MM-DD | `initial-standard` | Scientific reasoning and evidence chain | |
| `code/` | required root | YYYY-MM-DD | `initial-standard` | Project-local code entry point | |

<!-- BEGIN INITIALIZER-MANAGED OPTIONAL MODULES v1 -->
- **Precreated standard directories:** recorded by the initializer; empty directories do not certify content or configured capabilities.
<!-- END INITIALIZER-MANAGED OPTIONAL MODULES v1 -->

## 4. Local divergence and exceptions

- **Known local divergence from installed baseline payload:**
- **Applicable scoped ADR exception(s):**
- **Unresolved compatibility or preservation boundary:**

## 5. Update state

- **Last actual baseline-payload application:**
- **Update status:** no update recorded
- **Last applied release/source revision/payload digest:**
- **Detailed update record:**

## 6. Handoff and limitations

- **What this manifest does not establish:** file-content integrity, project scientific validity, or applicability of a future release.
- **Safe continuation note:** `baseline inspect` and `baseline plan` do not update this manifest; `baseline apply` updates it only after the payload and inventory have been applied successfully.
- **Related task, discussion, or decision records:**
