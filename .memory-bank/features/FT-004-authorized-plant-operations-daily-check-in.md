---
description: FT-004 Authorized Plant Operations And Daily Check-In.
status: active
type: feature
feature_id: FT-004
epic: EP-002
lifecycle: planned
last_updated: 2026-07-10
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
- Engineer sees Plant card/history, tasks, approvals, and follow-up entry points.
- Boss can run the same workflow for Farm Plants.

## Acceptance Criteria

- Authorized users can select only authorized Plants.
- Daily check-in supports observations, photo upload entry point, manual pH/EC, Plant card/history, cautious agent outputs, tasks, approvals, and follow-up outcomes.
- Check-in persistence is actor-scoped, Plant-scoped, and auditable.
- Missing data can produce safe measurement/check requests instead of invented evidence.

## Edge Cases & Failure Modes

- Unauthorized Plant selection fails closed.
- Archived Plants are excluded from normal operations.
- Stale or missing pH/EC remains explicit and cannot be silently treated as fresh.
- Check-in data cannot leak across PlantAccessGrant boundaries.

## Verification Targets

- Unit: check-in validation and pH/EC provenance/freshness projections after specs define them.
- Integration: daily workflow persists authorized Plant evidence and audit refs.
- E2E: Engineer completes observation plus pH/EC check-in on `tomato_001`.

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

## Implementation

- [Implementation plan](../tasks/plans/IMPL-FT-004.md): ordered task queue,
  dependencies, verification strategy, and UAT.
