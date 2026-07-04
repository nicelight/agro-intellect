---
description: FT-002 Farm Plant Lifecycle And Access Grants.
status: draft
type: feature
feature_id: FT-002
epic: EP-001
lifecycle: planned
last_updated: 2026-06-30
spec_design_links:
  - .memory-bank/domains/farm/farm-plant-access-storage.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
  - .memory-bank/contracts/access/actor-context.md
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/states/lifecycle-map.md
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

## Specification Composition

- [Farm/Plant/access storage](../domains/farm/farm-plant-access-storage.md)
  defines only the identity/status relationships required by the FT-001 seam.
- [Plant/access lifecycle](../states/plants/plant-and-access-lifecycle.md)
  defines only active/archived and active/revoked permission effects.
- [ActorContext](../contracts/access/actor-context.md) defines concrete Plant
  permission resolution and fail-closed output.

This slice exists only to stabilize FT-001. Full storage/migrations, seeds,
mutation/API/error contracts, retained-history services, audit integration,
verification plan, and task queue are outside this composition.

## Non-Goals

- Hard delete, multi-Farm tenancy, or a general ACL engine.
- Plant operation forms, daily check-ins, photo upload, or detailed Plant
  history rendering beyond access/lifecycle hooks.
- Agent output generation, MessageEnvelope/UI Feed projection, Safety Gate
  policy, or physical-action task execution.
