# A-NNN: <Artifact Name>

> Durable identity and provenance record for one coherent file/data artifact, or a manifest-only controlled external reference. Keep this record concise: link to runs, comparisons, analysis, sources, tasks, and documents rather than copying their content.

## 1. Identity and content

<!-- Define the artifact's stable identity and logical content. An artifact may be one file, a coherent collection, or a manifest-only reference; do not create one record per incidental file. -->

<!-- Select a complete unit that can be independently referenced, used and handed off. A coherent collection shares source, version and retention rationale and is normally used together. Independent provenance, reuse or updates normally require separate registrations; directory co-location or one producer run alone does not decide grouping. -->

- **ID:** `A-NNN`
<!-- A-NNN means a stable positive project-global number with at least three digits. Normal registration allocates it; explicit imports may supply an unused ID. Names, locations and uses do not change identity. -->
- **Name:**
- **Registered:** YYYY-MM-DD
- **Last updated:** YYYY-MM-DD
- **Artifact granularity:** `single file` | `coherent collection` | `manifest-only reference`
- **Logical content:**
- **Formats / schema / units:**
- **Version or integrity identifier:**
<!-- Descriptive corrections or an authorized unchanged-content location update retain the ID and leave a correction log. Changed durable content or collection membership normally needs a new ID with explicit predecessor/upstream relations. -->

## 2. Origin and provenance

<!-- State how the artifact entered the project. Preserve source or producer identity; do not replace it with a local interpretation. -->

- **Origin:** `generated` | `external` | `user-supplied` | `derived`
- **Producer task / run or source locator:**
- **Upstream artifact(s):**
- **Creation, acquisition, or registration route:**
- **Source-type-specific provenance:**
  - **Generated:** producer `T-NNN` / `R-NNN`, code/environment/input links.
  - **External:** canonical source/version/locator, access or license boundary, and registration date.
  - **User-supplied or restricted:** explicit authorization scope and non-transmission/non-reuse boundary.
  - **Manifest-only:** reason no local payload is retained and the effect if access is unavailable.

## 3. Payload, access, and integrity

<!-- State whether the project holds a payload and how it may be accessed. Integrity is a file/reference property, not a scientific-validity claim. -->

<!-- CLI registration creates ARTIFACT.md, integrity.json and payload/ uniformly. Local present content belongs in payload/: filename for a single file, useful internal structure for a collection. External/restricted entries retain an empty scaffold without implying local content or accessibility. CLI archival may fill an empty payload/; manual reconciliation updates related project-document path references. Original execution/source facts and correction history remain traceable. -->

- **Payload status:** `present` | `controlled external reference` | `restricted no-copy` | `unavailable` | `cleaned`
<!-- cleaned is set only by the human-requested CLI cleanup flow with retained cleanup/reconstruction history; ordinary creation or a metadata edit cannot certify removal. -->
- **Canonical payload location or controlled access route:**
- **Sensitivity, license, and access conditions:**
- **Size:**
- **Checksum or comparable integrity identifier:**
- **Integrity check and status:**
<!-- CLI owns these integrity fields and integrity.json beside this manifest: SHA-256/size per file, retained baseline, timestamped observations and access-recovery plan. Local registration records bytes; artifact check rechecks them without replacing mismatched baselines. Recheck after manual moves/transfers and before consequential reuse/handoff. External bytes absent means pending, not verified. On access failure record reason plus a local-backup or replacement next action; check promptly when accessible and retain the follow-up until actually resolved. Use update --change-kind recovery for a registered distinct replacement with explicit central supersedes and checked bytes; retain original source/access facts and all recovery events. Copying still requires authorization and permits no no-copy override. -->

## 4. Retention and reproducibility

<!-- Explain why the artifact is durable and how it can be recreated or checked. Do not imply reproducibility if a source, environment, input, or authorization is unavailable. -->

<!-- The user or Agent assesses durable value and supplies a meaningful Retention reason. CLI validation requires the field; it does not judge the reason's scientific merit. -->

- **Retention reason:** `cross-task reference` | `comparison evidence` | `conclusion support` | `handoff` | `sensitive/restricted registry` | `high-cost or hard-to-regenerate output` | `other`
<!-- CLI metadata update accepts these existing reconstruction/cost/storage labels with a reason. Caller-supplied steps and constraints do not establish successful reproduction. -->
- **Reproduction or reconstruction route:**
- **Regeneration cost / constraint:** `low` | `material` | `high-cost` | `not reproducible locally`
- **Retention, deletion, or external-storage boundary:**
<!-- Default is retention, including superseded versions. A human may request bounded local payload cleanup. CLI requires a reason, reconstruction document and confirmation of its current safety plan; live payload references/unfinished consumers, shared ownership or integrity mismatch block it. Keep this manifest, all related records, baseline/history, relationships and ID allocation history after cleanup. CLI appends exact removed-file inventory, requester/reason, steps and constraints here and in integrity.json. Preserve unavailable reconstruction ingredients explicitly; steps do not prove recoverability. Restore cleaned/lost bytes only against retained original integrity evidence; without proof, report this route/constraints and await the user decision on reconstruction. A candidate's first checksum cannot certify identity with a missing original. -->

## 5. Relations and use

<!-- Register relationships without relocating or duplicating the artifact. A relation to a comparison, analysis, or document does not by itself establish a scientific conclusion. -->

<!-- CLI-created supersedes/derived_from facts are authoritative in the configured relation registry. The corresponding manifest fields point to that registry; query it by this artifact ID rather than maintaining a second full definition. -->

- **Produced by:**
- **Consumed by:**
- **Evidence for comparison(s):**
- **Used in analysis:**
- **Used in document(s):**
- **Supersedes / succeeded by:**

## 6. Limitations and handoff

<!-- State safe-use boundaries, known limitations, and what a later agent needs to know. Link to authoritative detailed records. -->

- **Known limitations:**
- **Do not infer / do not use for:**
- **Safe continuation notes:**
- **Related task(s), run(s), comparison(s), and records:**
