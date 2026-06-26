---
description: FT-004 Authorized Plant Operations And Daily Check-In.
status: draft
type: feature
feature_id: FT-004
epic: EP-002
lifecycle: planned
last_updated: 2026-06-26
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

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Plant Operations module and data flow.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): mutable runtime state ownership.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): operations route authorization and validation.

## SDD Design Gate

Run global `/spec-design` before this feature is task-decomposed. Then run `/prd-to-tasks FT-004`; it must define exact daily check-in state, fields, persistence sequence, freshness projections, and API/UI dependencies during its feature-level SDD design phase before writing tasks. Use standalone `/spec-improve FT-004` only for repair or advanced refresh without task generation.
