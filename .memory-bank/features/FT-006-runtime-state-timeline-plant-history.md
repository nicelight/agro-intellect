---
description: FT-006 Runtime State Timeline And Plant History.
status: active
type: feature
feature_id: FT-006
epic: EP-002
lifecycle: planned
last_updated: 2026-07-10
spec_design_status: complete
spec_design_links:
  - .memory-bank/domains/plant-history.md
  - .memory-bank/contracts/plant-history-http.md
  - .memory-bank/contracts/timeline-event.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
  - .memory-bank/domains/plant-operations.md
  - .memory-bank/domains/photo-artifacts.md
  - .memory-bank/domains/admin/admin-audit.md
  - .memory-bank/testing/plant-history.md
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
---
# FT-006 Runtime State Timeline And Plant History

## Use Cases

- Backend persists mutable Plant operational state in PostgreSQL/read model.
- Backend appends audit/export events to `timeline.jsonl`.
- Authorized users view Plant card/history.
- Archived Plants retain authorized history/audit/export access.

## Acceptance Criteria

- PostgreSQL/read model is mutable runtime authority unless later active architecture spec changes it.
- `timeline.jsonl` is append-only audit/export, not primary mutable state.
- Photo files and manifests are local artifacts, not mutable runtime authority.
- Plant history can reference photos, measurements, tasks, approvals, outcomes, agent outputs, and governance records without turning UI presentation into state authority.

## Edge Cases & Failure Modes

- Timeline replay cannot override runtime state.
- Unauthorized actors cannot access Plant history/audit/export.
- Archived Plant history remains retained but not part of normal operations.
- Export/audit refs cannot include secrets/auth material.

## Verification Targets

- Unit: authority boundary rules for runtime state vs timeline/export.
- Integration: timeline refs resolve back to authoritative runtime records where required.
- E2E: archived Plant retained history remains accessible to authorized Boss.

## Behavior specs

- `.memory-bank/behavior-specs/FT-006-BHV-001-active-history-from-authority.behavior.json`
- `.memory-bank/behavior-specs/FT-006-BHV-002-archived-retained-history.behavior.json`
- `.memory-bank/behavior-specs/FT-006-BHV-003-timeline-replay-not-authority.behavior.json`

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): runtime state, timeline, and storage separation.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): authority layers and runtime invariants.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): append-only audit/export event contract.
- [.memory-bank/states/plant-state-trust.md](../states/plant-state-trust.md): Plant trust and promotion boundary for history views.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): authorized history access and redacted errors.

## Feature-Local Design Pressure

- Exact runtime-state ownership, timeline event taxonomy, history projections,
  export refs, retained-history authorization, and retention behavior.

## Specification Composition

Status: complete.

- [Plant History Data](../domains/plant-history.md) defines Plant card/history
  projections, retained-history authorization, source rows, timeline
  consistency, and redaction rules.
- [Plant History HTTP](../contracts/plant-history-http.md) defines protected
  history card/list routes, pagination, response shapes, and errors.
- [Timeline Event](../contracts/timeline-event.md) defines append-only audit/
  export refs and replay limits consumed by FT-006.
- [ActorContext](../contracts/access/actor-context.md) and [Plant And Access Lifecycle](../states/plants/plant-and-access-lifecycle.md)
  define normal-read and retained-history permissions plus archived-Plant
  operational denial.
- [Plant Operations Data](../domains/plant-operations.md), [Photo Artifacts](../domains/photo-artifacts.md),
  and [Admin Audit](../domains/admin/admin-audit.md) define the current source
  rows that FT-006 may project into Plant history.
- [Plant History Verification](../testing/plant-history.md) defines the
  focused evidence matrix.

Raw timeline export packages, PWA history UI, Vision, agents, Safety Gate,
tasks/follow-up, Companion governance, and dataset history entries remain
outside FT-006 until their owning features/specs exist.

## Implementation

- [Implementation plan](../tasks/plans/IMPL-FT-006.md): ordered task queue,
  dependencies, verification strategy, and UAT.
