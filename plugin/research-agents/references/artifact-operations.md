# Artifact operation map

Use this map to select an operation in one research project. The installed
project's AGENTS/workflow and accepted local decisions govern its use; package
updates require the existing confirmed adoption path. The canonical policy is
[workflow Section 9.1](../assets/baseline/RESEARCH_WORKFLOW.md#91-artifact-first-model),
the record is [ARTIFACT.md](../assets/baseline/templates/ARTIFACT.md), and exact
arguments are in [workflow CLI Section 7](workflow-cli-usage.md#7-work-packages-runs-and-artifacts).
This reference maps operations to those authorities rather than redefining them.

## 1. Registration and discovery

| Operation | CLI or human responsibility | Record / invariant |
| --- | --- | --- |
| Initialize the root registry home | research_init root; compatible confirmed adopt/extend for existing structure | Complete standard skeleton, context/manifest/report; no implicit artifact registration |
| Decide what to retain and select a file/collection/reference unit | User/Agent supplies explicit template inputs; new/check validate completeness | Retention reason and granularity; no automatic sweep or scientific judgment |
| Register generated, external, user-supplied or derived material | artifact new with record-file; explicit source/operation when archiving | Stable ID, six-section manifest, integrity.json and payload/ |
| Allocate or import an ID / register at an explicit established path | Automatic new allocation, optional id and destination path | Project-global identity/history, gaps/nonreuse, zero reservation on preview |
| List, filter or find registered artifacts | artifact list with query/status/origin/granularity filters | Read-only registry view; empty scaffolds are not objects |
| Inspect one entry or resolve its ID/path | artifact list ID or --path (default record view) | Read-only fields/record hash; duplicates or invalid selectors are diagnosed |
| Read file inventories, checksum observations, cleanup/restoration or reconstruction history | artifact list --view inventory or history | Saved records only; use check for current bytes |
| Find references, consumers/producers and version/derivation relations | artifact list --view references; relation show/path for the central graph | Known project text/structured references and explicit central edges, with inspection limits stated |

## 2. Contents, records and relationships

| Operation | CLI or human responsibility | Record / invariant |
| --- | --- | --- |
| Archive a selected local file/collection by copy or move | new --source --operation, or existing artifact store with recorded local source or explicit candidate | payload/ files, manifest/inventory and identifiable related document paths share FilePlan |
| Manually place, rename or relocate unchanged payload files inside their entry | User performs the authorized file operation; artifact update location records it | Retained identity/baseline, repaired live paths and preserved original locators |
| Correct names/descriptions/access/retention/limitations | artifact update --change-kind metadata | Bounded fields with reason and before/after history; no payload edit |
| Record/correct reconstruction route, cost and retention/storage conditions | artifact update metadata using existing template labels | Human-supplied steps/constraints; no invented or executed reconstruction |
| Correct an unchanged object's current location/access status | artifact update --change-kind location | Local bytes must match retained baseline; unavailable needs a concrete recovery plan |
| Produce a changed version, derivation, split or merged collection | Perform the authorized research/preparation separately, then new with explicit lineage | New IDs for changed units/content; no inferred grouping, derivation or scientific equivalence |
| Record producer/consumer/document/decision relationships | relation add with explicit basis/reason; new lineage flags | Central registry is the single relation authority; manifests point there |
| Use an artifact in a run/task/analysis/document | Resolve the ID/manifest, inspect status and check relevant bytes; record explicit references/relations | A known ID is not proof of current content or permission to run computation |
| Change a license/access restriction or add source context | Explicit metadata correction and applicable human authorization | Source/access facts and correction history remain traceable; no no-copy override |

## 3. Integrity, access, retention and recovery

| Operation | CLI or human responsibility | Record / invariant |
| --- | --- | --- |
| Check registration/record/inventory structure | artifact check --records-only | Read-only diagnostics and last saved findings; no rehash |
| Establish an accessible baseline or recheck bytes after transfer/manual changes/before reuse | artifact check; new/store also record/compare bytes | SHA-256/size per file, retained baseline and observation history |
| Record inaccessible content and its reliability action | check --unavailable --reason --recovery --follow-up, or appropriate registration/location inputs | Original source facts plus explicit backup/replacement next action |
| Inspect a regained authorized external view | check --source with a project-local acquired view | No implicit copying or claim of remote endpoint access; reliability action remains visible |
| Acquire a source or generate a backup/reconstruction candidate | Separate explicitly authorized acquisition/research task | Artifact CLI does not fetch remote resources or execute research |
| Retain a same-source local backup | Explicit store/location update of authorized acquired bytes | Existing unit/ID/provenance and baseline; a manifest-only unit needs a separate local unit |
| Select and register a different replacement source | Human selects; new and explicit central supersedes relation | Distinct ID/source facts, caller-declared role replacement, no equivalence inference |
| Record completion of the replacement action | artifact update --change-kind recovery with replacement ID and reason; authorized local view when external | Original unavailable record/history retained; replacement observation and relation pointer; no endpoint/quality certification |
| Retain or supersede an old artifact | Default retain; explicit supersedes edge for successor | Supersession does not delete content or recycle identity |
| Request and apply cleanup | Human request; artifact cleanup preview and exact current confirmation | Only selected local files removed; all records, history, relationships and steps retained |
| Restore cleaned or lost unchanged content | Explicit store or location update; candidate files compare to retained original evidence | Without proof report reconstruction method/constraints for user decision; restored history remains, changed bytes use new IDs |
| Diagnose a mismatch, missing file, corrupt record/history or interrupted manual operation | check reports; human recovers authoritative evidence, then checks/reconciles explicitly | No reset/rebase to hide differences, no inferred historical IDs or invented provenance |

## 4. Explicit boundaries for other possible actions

These actions can arise around artifacts. Their inclusion here is an operation
inventory, not a promise of a packaged command or authorization to perform them.

| Action | Current route / boundary |
| --- | --- |
| Export/share/upload/download or create project-wide backups | Separately scoped authorized transfer/publication task; preserve canonical identities/provenance, access conditions and verify bytes. No packaged artifact export/upload/remote-delete service is delivered |
| Move/rename an entire artifact entry or migrate storage/project roots | Separate explicit migration plan for all records/paths/history. Current commands handle registered payload placement and reconciliation, not arbitrary whole-entry/root migration |
| Batch-register/split/merge/purge/deduplicate | Caller selects actual units and uses existing operations; no automatic inference, sweep or bulk purge |
| Permanently remove manifests, allocation history or relationships | Outside retained-record cleanup; do not reclaim IDs or silently break historical evidence |
| Automatically expire content, monitor endpoints or retry recovery later | No automatic schedule/monitor/purge is configured; any scheduling request is separate |
| Judge scientific validity, durable value, source reliability or reproducibility | User/Agent review and authorized research; CLI records the declaration and checks structure/bytes |
| Upgrade a project's installed baseline/Skill or globally install/publish the Plugin | Existing inspect/plan/draft/confirmed-apply/update policy and separate installation/publication authorization |

## 5. Agent routing

Use the packaged [research-artifact-manager Skill](../skills/research-artifact-manager/SKILL.md)
for ordinary artifact work in an initialized project. The initializer Skill
handles root/work-package construction. Deterministic record/file checks and
coordinated mutations belong in the CLI; value/coherence/source/reconstruction
judgments and grounded inputs stay with the user/Agent. Keep task outcome,
operation application, saved integrity findings and scientific acceptance
separate when reporting the result.
