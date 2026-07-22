---
description: FT-004 Authorized Plant Operations And Daily Check-In.
status: active
type: feature
feature_id: FT-004
epic: EP-002
lifecycle: verified
last_updated: 2026-07-12
spec_design_status: complete
spec_design_links:
  - .memory-bank/domains/plant-operations.md
  - .memory-bank/contracts/plant-operations-http.md
  - .memory-bank/contracts/timeline-event.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
  - .memory-bank/states/plant-state-trust.md
  - .memory-bank/testing/plant-operations.md
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/user-scenarios.md
---
# FT-004 Authorized Plant Operations And Daily Check-In

## Use Cases

- Engineer selects an authorized Plant, initially `tomato_001`.
- Engineer records daily observations.
- Engineer enters manual pH/EC measurements.
- Engineer can follow Plant-scoped refs into the FT-005 photo-intake and
  FT-006 Plant card/history boundaries.
- Boss can run the same workflow for Farm Plants.

## Acceptance Criteria

- Authorized users can select only authorized Plants.
- Daily check-in supports observations and manual pH/EC with auditable
  Plant-scoped evidence refs.
- Check-in persistence is actor-scoped, Plant-scoped, and auditable.
- Missing/stale measurement state remains explicit for downstream FT-010 and
  FT-012 consumers; FT-004 does not create agent output, tasks, approvals, or
  follow-up outcomes.

## Edge Cases & Failure Modes

- Unauthorized Plant selection fails closed.
- Archived Plants are excluded from normal operations.
- Stale or missing pH/EC remains explicit and cannot be silently treated as fresh.
- Check-in data cannot leak across PlantAccessGrant boundaries.

## Verification Targets

- Unit: check-in validation and pH/EC provenance/freshness projections after specs define them.
- Integration: daily workflow persists authorized Plant evidence and audit refs.
- API integration: Engineer completes an authorized observation plus pH/EC
  check-in on `tomato_001`.

## Behavior specs

- `.memory-bank/behavior-specs/FT-004-BHV-001-authorized-check-in-measurement.behavior.json`
- `.memory-bank/behavior-specs/FT-004-BHV-002-missing-stale-measurement-projection.behavior.json`
- `.memory-bank/behavior-specs/FT-004-BHV-003-archived-or-unauthorized-check-in-denied.behavior.json`

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Plant Operations module and data flow.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): mutable runtime state ownership.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): operations route authorization and validation.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): append-only audit/export refs for check-in evidence.
- [.memory-bank/states/plant-state-trust.md](../states/plant-state-trust.md): observation, measurement, and trust/promotion guardrails.

## Feature-Local Design Pressure

- Exact daily check-in state, fields, persistence sequence, freshness
  projections, timeline refs, and API/UI dependencies.

## Specification Composition

Status: complete.

- [Plant Operations Data](../domains/plant-operations.md) defines the exact
  check-in, observation, manual pH/EC, freshness, and runtime data rules.
- [Plant Operations HTTP](../contracts/plant-operations-http.md) defines the
  check-in and manual measurement route contract.
- [Timeline Event](../contracts/timeline-event.md) defines event ids, JSONL
  append behavior, and audit/export replay limits consumed by FT-004.
- [ActorContext](../contracts/access/actor-context.md) and [Plant And Access Lifecycle](../states/plants/plant-and-access-lifecycle.md)
  define operate permission and archived-Plant fail-closed behavior.
- [Plant State Trust](../states/plant-state-trust.md) keeps observations,
  measurements, hypotheses, and confirmed Plant state separate.
- [Plant Operations Verification](../testing/plant-operations.md) defines the
  focused evidence matrix.

Photo upload remains with FT-005. Plant history/timeline presentation, agent
outputs, tasks, approvals, follow-up, Safety Gate, and PWA components remain
outside FT-004.

## Post-verification Contract Delta

Current contracts add a 2000-code-point UI cap/counter and authoritative backend
`OBSERVATION_TEXT_TOO_LONG` zero-write rejection without truncation or summary.
Existing FT-004 evidence predates this delta. `/feature-to-tasks FT-007` must route
the missing implementation/tests through Plant Operations and Operator UI
owners rather than treating current code as compliant.

FT-004 exposes authorized evidence and freshness projections consumed by
FT-010/FT-012. Request/task creation and every approval/follow-up transition
remain with those owning features.

## Semantic Verification

SEMANTIC_VERDICT: semantic-pass

Repeated feature-level adversarial verification after
`TASK-025-T3-FT-004-W3` confirmed that the prior PostgreSQL/response/timeline
numeric divergence, future-freshness error, and silent observation loss are
resolved without authorization, archive, atomicity, or authority regressions.
Evidence: [repair recheck](../../.tasks/FT-004/FT-004-S-RED-VERIFY-final-report-docs-02.md).
The historical [semantic-fail report](../../.tasks/FT-004/FT-004-S-RED-VERIFY-final-report-docs-01.md)
is retained. Generated OpenAPI numeric typing remains a non-blocking residual
concern for separate owner triage. This boundary sync records the owner's
`implemented -> verified` lifecycle decision; the Reviewer report itself made
no lifecycle decision.

## Implementation

- [Implementation plan](../tasks/plans/IMPL-FT-004.md): ordered task queue,
  dependencies, verification strategy, and UAT.

## Implementation Evidence

- `TASK-019-T3-FT-004-W1` is recorded `done` by the scheduler after Plant
  operations persistence/service implementation, independent `VERDICT: PASS`,
  per-task `SEMANTIC_VERDICT: semantic-pass`, focused FT-004 service tests
  `9/9`, full regression `178/178`, `mb-lint` PASS, and `git diff --check`
  PASS.
- Evidence:
  [implementation](../../.tasks/TASK-019-T3-FT-004-W1/TASK-019-T3-FT-004-W1-S-IMPL-final-report-code-01.md),
  [verify](../../.tasks/TASK-019-T3-FT-004-W1/TASK-019-T3-FT-004-W1-S-VERIFY-final-report-code-01.md),
  [red-verify](../../.tasks/TASK-019-T3-FT-004-W1/TASK-019-T3-FT-004-W1-S-RED-VERIFY-final-report-docs-01.md).
- `TASK-020-T3-FT-004-W2` is recorded `done` by the scheduler after protected
  operations HTTP/API implementation, independent `VERDICT: PASS`, per-task
  `SEMANTIC_VERDICT: semantic-pass`, focused API tests `11/11`, combined
  service/API tests `20/20`, full regression `189/189`, OpenAPI inspection
  PASS, `mb-lint` PASS, and `git diff --check` PASS.
- Evidence:
  [implementation](../../.tasks/TASK-020-T3-FT-004-W2/TASK-020-T3-FT-004-W2-S-IMPL-final-report-code-01.md),
  [verify](../../.tasks/TASK-020-T3-FT-004-W2/TASK-020-T3-FT-004-W2-S-VERIFY-final-report-code-01.md),
  [red-verify](../../.tasks/TASK-020-T3-FT-004-W2/TASK-020-T3-FT-004-W2-S-RED-VERIFY-final-report-docs-01.md).
- `TASK-025-T3-FT-004-W3` is recorded `done` after repairing canonical
  measurement values, future-dated freshness, and observation validation;
  independent `VERDICT: PASS`, task-level `SEMANTIC_VERDICT: semantic-pass`,
  focused FT-004 `26/26`, and full regression `238/238` are recorded.
- Repair evidence:
  [implementation](../../.tasks/TASK-025-T3-FT-004-W3/TASK-025-T3-FT-004-W3-S-IMPL-final-report-code-01.md),
  [verify](../../.tasks/TASK-025-T3-FT-004-W3/TASK-025-T3-FT-004-W3-S-VERIFY-final-report-docs-01.md),
  [red-verify](../../.tasks/TASK-025-T3-FT-004-W3/TASK-025-T3-FT-004-W3-S-RED-VERIFY-final-report-docs-01.md).
- Scheduler waived the missing exact `HUMAN_CHECKPOINT: done` markers for
  TASK-019, TASK-020, and TASK-025 under the advisory T2/T3 process override.
  TASK-025 records that owner decision without fabricating the marker.
- FT-004 is synchronized as `verified` from the current feature-level
  `semantic-pass` report while the historical failure report remains intact.

Photo upload remains with FT-005. Plant history/timeline presentation, agent
outputs, tasks, approvals, follow-up, Safety Gate, and PWA components remain
outside FT-004.
