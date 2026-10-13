---
name: research-artifact-manager
description: Manage durable artifacts in an initialized MERIX research project when the user asks to register, inspect, check, store, reconcile, replace, restore or clean research files and their records.
metadata:
  short-description: Manage research artifacts and retained provenance
---

# Research Artifact Manager

Use the packaged workflow CLI for artifact work in one initialized research
project. Start from that project's installed AGENTS.md, workflow Section 9.1,
ARTIFACT template and applicable accepted decisions. Existing project baselines
are not automatically upgraded by a Plugin-source change; use their confirmed
update path when the requested feature requires a newer or differing contract.
Root/work-package construction belongs to the initializer Skill.

## Choose the actual operation

Read the [operation map](../../references/artifact-operations.md) to route the
request. Read the relevant part of [CLI Section 7](../../references/workflow-cli-usage.md#7-work-packages-runs-and-artifacts)
for exact arguments; use the installed Plugin's scripts/workflowctl.py with an
explicit absolute project --root. Use list with optional ID and record/inventory/history/references view to locate
saved evidence and known uses. The six operations are new/list/update/store/
check/cleanup. Check observes accessible bytes and checks records separately;
--records-only skips byte observations, --apply saves actual findings, and --all
is read only. Missing, external or cleaned bytes are not certified by records.

## Prepare grounded inputs and perform the bounded operation

- The user/Agent judges retention value, scientific coherence, change type,
  source suitability and reconstruction meaning. Supply explicit template
  fields/reasons; the CLI must not invent provenance or sweep run outputs.
- Register a stable unit with new (optional explicit entry path). Store only selected
  authorized bytes by copy/move, defaulting to the recorded accessible local
  source; use --source for an explicit candidate. Already stored consistent
  bytes are a checked no-op. Use update location after manual unchanged-content
  operations. Changed content/collection membership needs new identity and
  explicit version/derivation relations. Keep the central relation registry
  authoritative; task/run/document references point to it or the manifest.
- Correct metadata/reconstruction/constraints using the supported update fields
  with a reason. Inspect file/document diffs before apply; preserve original
  source commands, checksum baselines and history. A successful operation is
  separate from scientific validity or acceptance.
- Record unavailable sources plus a concrete backup/replacement action. Check
  returned authorized local views promptly. Store an actual same-source
  backup, or register a caller-selected successor and use update recovery
  after reviewing its explicit relation and byte observation. Source restoration
  alone does not complete recovery; no-copy/access conditions remain binding.
- Retain content by default, including superseded versions. Cleanup requires a
  human request, reason and reconstruction document, a clear safety preview,
  and confirmation of that exact current plan before apply. Resolve live
  references/unfinished consumers rather than erase their history. Preserve all
  records, original checksum/observation history and reconstruction steps.
  Explicit store or update location may restore cleaned or lost content only against
  retained original integrity evidence. Without proof, report the recorded
  reconstruction method/constraints and let the user decide whether to execute
  reconstruction. A first candidate checksum or reconstruction approval is not
  original-identity proof; different bytes need a new ID.

On conflicts or invalid evidence, retain the records and report the exact
condition and safe next action. A changed cleanup plan requires renewed review.
Report application, saved/current integrity, unresolved recovery/consumer work
and actual reconstruction verification separately. Never claim that readable
instructions prove reproduction, or that a chosen successor proves source
reliability/scientific equivalence. Acquisition, computation, export/publication,
whole-entry migration and existing-project upgrade remain separately scoped;
this Skill does not add automatic purge, endpoint monitoring or remote deletion.
