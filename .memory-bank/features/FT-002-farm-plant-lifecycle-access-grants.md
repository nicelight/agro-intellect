---
description: FT-002 Farm Plant Lifecycle And Access Grants.
status: draft
type: feature
feature_id: FT-002
epic: EP-001
lifecycle: planned
last_updated: 2026-06-16
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/states/lifecycle-map.md
  - .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md
---
# FT-002 Farm Plant Lifecycle And Access Grants

## Use Cases

- Boss uses the single local Farm workspace.
- Boss creates or confirms `tomato_001` as the initial Plant.
- Boss creates additional Plants inside the local Farm.
- Boss archives or restores a Plant.
- Boss grants or revokes per-Plant access and optionally grants `plant_approve_actions`.

## Acceptance Criteria

- MVP supports exactly one local Farm workspace.
- Multiple Plants are supported; `tomato_001` is the initial Plant.
- Plant removal is archive/restore only; no hard delete in MVP.
- Archived Plants disappear from normal operations but remain retained for authorized history/audit/export access.
- PlantAccessGrant controls Plant visibility and work authorization.

## Edge Cases & Failure Modes

- Unauthorized actors cannot see, mutate, archive, restore, or access retained history for unauthorized Plants.
- Archived Plant cannot be selected for normal daily operations.
- Revoked PlantAccessGrant removes operational visibility and context-builder access.
- `plant_approve_actions` is the only MVP per-Plant permission override.

## Verification Targets

- Unit: Plant lifecycle transitions and access grant policy.
- Integration: authorized vs unauthorized Plant list and context builder.
- E2E: Boss grants Engineer access to `tomato_001`, Engineer sees it, then archived Plant leaves normal operations.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): module boundaries and runtime authority.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): Plant and PlantAccessGrant ownership.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): route authorization and fail-closed behavior.

## SDD Design Gate

Status: complete.

Feature-local `/spec-improve FT-002` produced the authoritative feature hub:

- [.memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md](../tech-specs/FT-002-farm-plant-lifecycle-access-grants.md): Farm seed, `tomato_001` seed, Plant lifecycle, PlantAccessGrant lifecycle, PlantPermissionContext resolver, route schemas, retained-history authorization, audit/event decisions, failure rules, and verification targets.

Generated task-decomposition artifacts for this feature have been intentionally removed. No FT-002 implementation plan or `TASK-*` record is active.
