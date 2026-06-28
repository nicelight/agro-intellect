---
description: FT-006 Runtime State Timeline And Plant History.
status: draft
type: feature
feature_id: FT-006
epic: EP-002
lifecycle: planned
last_updated: 2026-06-26
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

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): runtime state, timeline, and storage separation.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): authority layers and runtime invariants.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): append-only audit/export event contract.
- [.memory-bank/states/plant-state-trust.md](../states/plant-state-trust.md): Plant trust and promotion boundary for history views.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): authorized history access and redacted errors.

## SDD Design Gate

Global `/spec-design` is complete for shared backbone/spec routing. Then run `/prd-to-tasks FT-006`; it must define exact runtime state ownership, timeline event taxonomy, history projections, export refs, retained-history authorization, and retention behavior during its feature-level SDD design phase before writing tasks. Use standalone `/spec-improve FT-006` only for repair or advanced refresh without task generation.
