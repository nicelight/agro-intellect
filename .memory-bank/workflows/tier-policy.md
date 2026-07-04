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
- A `semantic-concern`, failed check, missing checkpoint, incomplete protocol,
  or stale verification SHOULD be considered by the owner, but does not
  automatically prevent T2/T3 closure or dependent promotion.
- Task/spec contradictions and unsafe or unauthorized actions remain reasons
  to stop because they are correctness/scope problems, not optional process
  ceremony.

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
