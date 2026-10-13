# R-NNN: <Run Topic>

> Durable execution record for one configuration-frozen, rerunnable, reportable, or handoff-relevant run. Record execution facts and links to evidence; do not duplicate environment/input manifests, decide Contract satisfaction, or state a scientific conclusion.

## 1. Identity and execution intent

<!-- Identify the one execution unit and the root task/work package it serves. -->

- **Run ID:** `R-NNN`
- **Root task:**
- **Work package (if any):**
- **Created:** YYYY-MM-DD
- **Last updated:** YYYY-MM-DD
- **Execution intent:**
- **Configuration-freeze boundary:**

## 2. Frozen configuration references

<!-- Link to the immutable or recorded configuration. Do not copy manifest contents. -->

- **Code revision / snapshot:**
- **Environment manifest:**
- **Input manifest:**
- **Randomness / seed plan and actual seed record:**
- **Consumed artifact(s) (`A-NNN`):**
- **Relevant source, derivation, analysis, or configuration records:**

## 3. Invocation and resource record

<!-- Record what actually ran. Keep credentials and secrets out of this file. -->

- **Execution target:** `local` | `remote` *(non-sensitive profile/target only, if applicable)*
- **Working location:**
- **Exact invocation / entry point:**
- **Started / ended:**
- **Planned resources:**
- **Actual resources or observed usage:**
- **Scheduler or job identifier(s), if applicable:**
- **Controller backend / detached submission identity:**
- **Heartbeat / progress file:**
- **Monitor schedule hook:** one-shot invocation may be called by an external scheduler; no schedule is installed by this CLI.

## 4. Attempts, subjobs, and execution disposition

<!-- Attempts may remain in one R-NNN only while the frozen configuration is unchanged. -->

| Attempt / subjob | Start / end | Disposition | No-change retry? | Log / note |
| --- | --- | --- | --- | --- |
|  |  | `completed` | `yes` / `no` |  |

- **Overall execution disposition:** `completed` | `failed` | `cancelled` | `terminated` | `incomplete`
- **Material change requiring a new `R-NNN`?:**

## 5. Produced and consumed artifacts

<!-- Link durable outputs and controlled references. Do not create duplicate artifact identities here. -->

- **Produced artifact(s) (`A-NNN`):**
- **Run-local outputs / logs:**
- **External, restricted, or manifest-only outputs:**
- **Artifact registration or return path:**

## 6. Warnings, failures, and anomalies

<!-- Record operational facts and their immediate reproducibility consequence. Do not turn this into a scientific comparison. -->

- **Warnings / anomalies:**
- **Failures and recovery attempts:**
- **Resource or execution deviations:**
- **Reproducibility consequence:**

## 7. Bounded execution outcome and handoff

<!-- State only what this execution established operationally. Link the next comparison record for Contract or scientific judgment. -->

- **Execution outcome:**
- **Available / unavailable outputs:**
- **Does not establish:** Contract satisfaction, physical/numerical behavior, or scientific conclusion unless a linked `C-NNN` says so.
- **Next comparison / follow-up record:**
- **Safe continuation or rerun notes:**
- **Retry policy:** `explicit-only`; automatic retry is disabled.
