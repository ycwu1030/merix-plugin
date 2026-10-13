# T-NNN: <Task Title>

> Complete stable record for one nontrivial task. Keep its current snapshot aligned with `PROJECT_STATUS.md`; append meaningful outcomes to the work log. Source comments below each heading explain the intended boundary.

## 1. Task identity and scope

<!-- Define the task's stable identity, objective, scope, exclusions, state, priority, and related tasks. Do not place chronological history here. -->

- **ID:** `T-NNN`
- **Priority:** `P0` | `P1` | `P2` | `P3`
- **State:** `backlog` | `active` | `paused` | `in_review` | `completed` | `canceled`
- **Readiness:** `ready` | `not-ready` | `blocked-by-task` | `awaiting-input` | `awaiting-confirmation` | `high-cost-gated` | `completed`
- **Created:** YYYY-MM-DD
- **Last updated:** YYYY-MM-DD HH:mm (<project timezone>)
- **Objective:**
- **Scope:**
- **Acceptance:**
- **Out of scope:**
- **Deliverable / intended audience:**
- **Related task(s):**
- **External tracker ID:** `<project-specific ID>` | `—`

## 2. Current snapshot

<!-- Mirror the current status row: concise result, next action, and blocker. Do not duplicate the work log or full evidence. -->

- **Current result:** `verified` | `provisional` —
- **Current step:** `S1` | `—`
- **Implementation plan version:** `v1`
- **Resume entry:** `#8-handoff`
- **Next action:**
- **Blocker:** `—`
- **Status-row link:** [PROJECT_STATUS.md](../PROJECT_STATUS.md)

## 3. Reproduction Target and Comparison Contract

<!-- Retain this section in every task record. For a substantive reproduction or independent numerical task, complete the contract before the main computation; this is the unique canonical task-level contract. For another task type, write `Not applicable — <short reason>` and do not delete the heading. Detailed execution evidence belongs in linked artifacts, not duplicated here. -->

- **Applicability:** `required` | `not applicable` —
- **Target source or system / version / locator:**
- **Target object or behavior:**
- **Target modality:** `analytical / derivational` | `numerical / quantitative` | `qualitative / structural` | `behavioral / pipeline`
- **Planned acceptance condition:** `exact match / proven equivalence` | `translation-resolved match` | `bounded partial agreement`
- **Inputs, parameters, approximations, artifact references, and randomness scope:**
- **Comparison method and predeclared criterion:**
- **Exclusions, mismatch boundaries, and scientific non-claims:**
- **Actual comparison disposition:** `not started` | `condition met` | `localized, evidence-supported discrepancy` | `unresolved discrepancy`
- **Detailed evidence / execution record links:**

## 4. Work log

<!-- Append one dated entry for each meaningful outcome, including evidence, decision or status change, and the next action. -->

### YYYY-MM-DD

- **Outcome:**
- **Evidence / outputs:**
- **Decision or status change:**
- **Next action:**

### Implementation plan

<!-- Keep the current plan here. Revise it when evidence changes the route; record material revisions in the Work log. Give each step a stable ID and a checkable completion condition. -->

- **Plan version:** `v1`
- [ ] `S1`: <bounded step and completion condition>
- [ ] `S2`: <bounded step and completion condition>

## 5. Evidence and outputs

<!-- Link the artifacts supporting task claims: sources, code, data, results, checks, and generated outputs. Do not copy their full contents. -->

| Item | Role | Location | Verification status |
| --- | --- | --- | --- |
| | | | |

## 6. Links to discussions and decisions

<!-- Link discussions for reasoning context and ADRs for accepted durable choices. Do not duplicate either record here. -->

| Type | Link | Role |
| --- | --- | --- |
| Discussion | | |
| Decision | | |

## 7. Risks, limitations, and blockers

<!-- Record task-scoped risks, validity limits, and blockers with their effects and resolution conditions. Paused tasks record every cause and recovery condition here or in their handoff; waiting for authorization/input and technical obstacles are pause reasons. -->

| Item | Effect | Resolution condition or boundary | Detailed record |
| --- | --- | --- | --- |
| None identified yet | | | |

## 8. Handoff

<!-- State what the next agent should open first, the current assumptions/conventions, verification boundary, unfinished work or explicit absence of follow-up, and explicit relationships to parallel tasks. Do not duplicate detailed evidence; link it. -->

- **Recommended next entry point:**
- **What a later agent must read first:**
- **Current assumptions, conventions, and boundaries:**
- **Completed work and verification boundary:**
- **Unfinished work / `No known follow-up`:**
- **Related and parallel tasks / direction of effect:**
- **Safe continuation note:**

<!-- The task CLI maintains a bounded Lifecycle evidence JSON subsection here for pause causes and submission/review references, versions and fingerprints. State remains in Section 1; do not create a second checkpoint file or invent approval evidence. -->
