# MERIX Research Plugin

**Memory, Evidence, Research, Integrity, eXecution.**

MERIX provides Codex Skills, project templates and local tools for initializing
and governing reproducible research projects. Research records and evidence
stay in the project directory, with explicit boundaries for changes,
execution, verification and human acceptance.

- Plugin ID: `merix-research`
- Marketplace: `merix`
- Version: `0.1.0`
- License: MIT
- Copyright: Yongcheng Wu, MERIX Group

## Included Skills

| Skill | Use |
| --- | --- |
| `research-project-initializer` | Create, adopt or extend a research-project baseline; prepare work packages and confirmed baseline updates. |
| `research-artifact-manager` | Register, find, store, check and explicitly clean up research artifacts. |
| `research-run-manager` | Plan or submit local detached runs and inspect execution records. |

The Plugin includes the shared scripts, templates, references and required
Markdown formatter Hook used by these Skills. The Hook normalizes supported
generated research Markdown; ambiguous or malformed output is reported for
repair. Code and excluded project-control files are protected.

## Requirements

- Codex Desktop with GitHub Marketplace support and Plugin Hook review/trust.
- `python3` available to Codex for packaged scripts and the Hook. The tools use
  the Python standard library; validated Python/runtime versions are recorded
  with release evidence.
- Git for repository Marketplace installation.

Taskboard is optional. Local initialization and workflow tools do not require
an external tracker, API credentials or a scheduler. Detached runs execute
the explicitly selected program; scientific correctness and resource limits
remain the researcher's responsibility.

## Install from GitHub in Codex Desktop

After the release is published:

1. Open Plugin/Marketplace management in Codex Desktop.
2. Add the GitHub Marketplace `ycwu1030/merix-plugin`.
3. Select marketplace `merix` and install **MERIX Research Plugin**.
4. Review the bundled Hook command and explicitly trust it through Codex's
   supported Hook review interface. Installing/enabling alone does not grant
   Hook trust. Restart or reload if the client requests it.
5. In a disposable project, initialize the baseline and check a supported
   generated Markdown edit before using the Plugin in real work.

Interface labels may vary by Desktop version. GitHub installation requires
published repository content; a local candidate alone does not prove this route.

## Initialize a project

Ask Codex to use `research-project-initializer` for a selected directory,
supplying project information or requesting defaults. The Skill previews the
plan and preserves existing content. Existing non-empty directories and
writing extensions require confirmation of the exact plan before application.

The initializer can also be called directly. Replace `<plugin-root>` with the
installed Plugin directory, or `plugin/research-agents` in this checkout:

```bash
python3 <plugin-root>/scripts/research_init.py root --target /absolute/path/to/project
python3 <plugin-root>/scripts/research_init.py root --target /absolute/path/to/project --apply
python3 <plugin-root>/scripts/workflowctl.py --root /absolute/path/to/project project check --json
```

The second command applies a clean fresh-project plan. Adoption and writing
extensions additionally require `--confirm-plan <Plan-ID>`. A conflict cannot
be overridden by confirmation.

## Work in an initialized project

Read its `AGENTS.md`, `PROJECT_CONTEXT.md`, `PROJECT_STATUS.md` and installed
workflow before selecting work. Initialization does not start research or
allocate a formal task. Ordinary research follows the installed project rules.

The workflow CLI supports task lifecycle, relations, focus/handoff, structural
evidence checks, Formula Index allocation, work-package/Run records and artifact
operations. Mutation commands preview by default; inspect the plan before
applying. Run submission requires explicit execution authorization. Monitoring
observes recorded state; it does not infer success.

Updating the Plugin does not upgrade baseline files already copied into a
project. Use the separate inspect/plan/confirmed-apply updater to preserve
local changes. Previous `research-agents` installs retain their identity;
review any old installation and avoid enabling duplicate formatter Hooks.

## Documentation

- [Initializer and update guide](plugin/research-agents/references/initializer-usage.md)
- [Workflow CLI guide](plugin/research-agents/references/workflow-cli-usage.md)
- [Artifact operations](plugin/research-agents/references/artifact-operations.md)
- [Markdown formatter and Hook](plugin/research-agents/references/markdown-format-usage.md)
- [Changes](CHANGELOG.md)
- [MIT license](LICENSE)

## First-release limits

The interface is evolving. The scripts do not establish scientific validity,
invent evidence, infer acceptance or automatically upgrade research projects.
Hook repair covers supported normalization; diagnostics can require manual
repair. Compatibility applies only to recorded validated environments.
GitHub/Desktop installation must be checked against the published candidate
before that route is reported as verified.
