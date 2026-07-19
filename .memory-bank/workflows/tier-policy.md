---
description: Advisory tier profiles for TASK execution, evidence, verification, and synchronization.
status: active
---
# Tier Policy

Task records use one classification field:

```json
"tier": "T0"
```

Allowed values are `T0`, `T1`, `T2`, and `T3`. The field is required for
routing and risk communication. It does not by itself impose hard execution or
closure gates.

## Governing interpretation

- T2/T3 workflow requirements are advisory defaults. Protocol depth, task
  gates, `/verify`, `/red-verify`, feature semantic review, human checkpoints,
  strict doctor, and `/mb-sync` SHOULD be selected according to actual risk.
- The explicit owner or scheduler MAY combine, reorder, skip, or replace these
  checks and MAY close a T2/T3 task using the evidence it considers sufficient.
- Missing recommended T2/T3 process artifacts SHOULD produce warnings and
  follow-up recommendations, not automatic `blocked`, `failed`, or closure
  rejection.
- In T2/T3 task cards, legacy or generated `required: true`, “must”, and
  “requires” wording for process gates is interpreted as a strong default
  recommendation unless the explicit owner separately declares that exact gate
  mandatory for the current task/run.
- When practical, the owner SHOULD record which recommendations were run,
  skipped, combined, or accepted as residual risk. Absence of that note is not
  itself a closure blocker.
- This advisory policy does not weaken product invariants, authorization and
  safety rules, source-of-truth contracts, destructive-operation protections,
  or explicit user decisions. A process waiver cannot make incorrect behavior
  correct.

## Ownership and status

- Scheduler mode normally lets `/autopilot` or `/autonomous` write task status
  transitions. Manual mode normally lets the explicit standalone owner decide
  closure.
- `/execute`, `/verify`, `/red-verify`, and `/mb-sync` SHOULD report evidence
  and recommendations without silently expanding scope.
- The scheduler or explicit owner selects sufficient current evidence, records
  any accepted process gaps when practical, and writes the lifecycle decision.
- A `semantic-concern`, failed check, missing checkpoint, incomplete protocol,
  or stale verification SHOULD be considered explicitly. Tier alone does not
  turn that process gap into a hard blocker, while a demonstrated product/spec,
  safety, authorization, scope, or source-of-truth violation remains blocking.
- Task/spec contradictions and unsafe or unauthorized actions remain reasons
  to stop because they are correctness/scope problems, not optional process
  ceremony.

## Closure, attempts, and evidence

This section is the canonical closure/retry contract. Other workflows and
skills route here instead of restating tier-specific closure rules.

- Runtime reports use
  `.tasks/<TASK_ID>/<TASK_ID>-S-<STAGE>-final-report-<code|docs>-NN.md`.
- `NN` is a zero-padded two-digit execution-attempt number. The initial attempt
  is `01`; every bounded rerun of `/execute` increments it. `/execute`, `/verify`, and
  `/red-verify` reports for one attempt use the same `NN` and are never
  overwritten. New numbered reports include the exact line `ATTEMPT: NN`;
  validators use that marker to distinguish this convention from legacy report
  numbering.
- When numbered reports exist, the highest attempt is current. Closure and
  failure decisions use only reports from that attempt; an older PASS, FAIL,
  semantic verdict, or checkpoint cannot override the current attempt.
- Legacy task/protocol evidence without numbered reports remains readable as a
  compatibility fallback. Do not combine it with a newer numbered attempt to
  manufacture closure evidence.
- Functional `/verify` and adversarial `/red-verify` are separate stages. When
  both are selected for T3 confidence, run them in separate fresh sessions.
- The scheduler or explicit owner writes the final `done|failed|blocked`
  decision and concrete current-attempt evidence links to the indexed task
  record. Child skills report evidence and recommendations; they do not
  silently take scheduler ownership.

## Retry and recovery

- The default active attempt limit comes from
  `.memory-bank/workflows/autonomy-policy.md`. `max_attempts_per_task: 5` means
  one initial attempt plus four bounded retries.
- A retry is allowed only when it stays inside the same task outcome, tier,
  dependencies, accepted scope, and normative specs, and does not repeat an
  unsafe or non-idempotent side effect.
- On scheduler start/resume, an existing `in_progress` task is handled before
  promotion or ready-task selection. The highest numbered attempt determines
  the next missing stage: resume `/execute`, `/verify`, or a separately selected
  `/red-verify`. If artifacts conflict or the safe next stage is unclear, stop
  and record the ambiguity instead of guessing.
- When the attempt limit is exhausted, the scheduler writes `failed`, blocks
  direct dependents, records current evidence, and stops with
  `HALT_FAILURE_BUDGET`. `/autopilot` does not create a replacement task.
  Follow-up/replacement work returns through the normal planning, review, and
  readiness flow.
- After such a halt, an explicit owner MAY authorize a task-scoped recovery
  exception without changing the global attempt limit. The durable task or
  planning evidence MUST name the failed task, preserve every prior attempt and
  terminal report, state the exact next attempt and effective per-task limit,
  bound the accepted repair scope, and state the attempts remaining afterward.
  This creates neither an implicit retry nor a replacement task: planning must
  be reconciled and receive a fresh task-plan `APPROVE`. After those conditions
  are recorded, the scheduler MAY perform a non-attempt `failed -> planned`
  lifecycle recovery for the specifically authorized task. That transition
  preserves all prior reports, terminal evidence, and attempt accounting; it
  neither starts nor consumes the named recovery attempt.
- The applicable strict doctor MUST then pass over the recovered `planned`
  queue before `planned -> ready`, execution selection, or consumption of the
  named recovery attempt. A pre-transition doctor failure caused solely by the
  authorized task's `failed` lifecycle hold is a sequencing diagnostic, not a
  structural waiver and not a substitute for the required post-transition
  PASS. Any later retry requires another explicit owner decision.

## Feature-local wave boundary

- `wave` is local to one feature. A boundary is the pair `(feature, wave)`, not
  a global group of every task whose `wave` string happens to match.
- Boundary synchronization remains advisory and follows the owner-selected
  confidence profile; this definition adds no new task field or batch ID.

## Recommended profiles

### T0 — trivial or docs-only

- Compact or no protocol.
- Cheapest relevant check when useful.
- `/verify`, `/red-verify`, and full `/mb-sync` usually unnecessary.

### T1 — local code or local behavior

- Compact evidence is usually sufficient.
- Relevant unit/lint/type checks are recommended when available.
- Independent verification is optional.

### T2 — cross-module, API, state, data, or domain work

Recommended default:

- use task-scoped protocol/evidence proportionate to the change;
- run applicable contract, integration, migration, or domain checks;
- run `/verify` when independent functional evidence adds value;
- use feature-level `/red-verify --feature FT-<ID>` when semantic drift risk is
  material;
- synchronize Memory Bank at a useful wave/feature boundary.

Compact protocol, owner-accepted evidence, combined verification, or direct
closure are valid alternatives. None of the recommendations above is an
automatic closure prerequisite.

### T3 — critical, security, production, or irreversible work

Recommended default:

- use a full task protocol and explicit evidence;
- run focused and regression checks;
- run independent `/verify`;
- run per-task `/red-verify` for adversarial semantic review;
- obtain a human checkpoint for high-impact or irreversible decisions;
- run strict doctor and boundary `/mb-sync` when they improve confidence.

The owner or scheduler may waive, combine, or reorder any of these process
steps. In particular, `/verify PASS`, `SEMANTIC_VERDICT: semantic-pass`, the
exact `HUMAN_CHECKPOINT: done` marker, full protocol files, strict doctor, and
wave-boundary `/mb-sync` are recommended evidence, not universal T3 closure
conditions.

## Tier assignment guidance

- Docs-only and safe: usually `T0`.
- Local, contained, low blast radius: usually `T1`.
- API, contracts, state, data, migration, domain logic, or multiple modules:
  usually `T2`.
- Auth, permissions, security, deploy/runtime, irreversible/data-loss,
  payments, or compliance: usually `T3`.
- If execution reveals a different risk level, the owner MAY reclassify,
  rebuild, split, or continue under an explicitly accepted profile.
