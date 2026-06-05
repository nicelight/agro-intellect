---
description: Implementation plan for FT-002 Farm, Plant Lifecycle, And PlantAccessGrant.
status: active
---
# IMPL-FT-002 Farm, Plant Lifecycle, And PlantAccessGrant

## Goals

- Implement exactly one local Farm workspace with `tomato_001` as the initial Plant.
- Support multiple Plants with create/archive/restore and no hard delete.
- Implement PlantAccessGrant as the per-Plant visibility/work authorization boundary.
- Retain authorized history, photos, tasks, outcomes, timeline refs, and admin audit
  across archive/restore and grant revocation.

## Constitution Check

- Aligns with bounded MVP scope, low maintenance, Spec Before Code, and tiered DoD.
- No conflict found with the Constitution.
- Tier policy: Farm/Plant lifecycle/data work is T2; PlantAccessGrant authorization
  and access filters are T3.
- KISS boundary: one Farm only; no tenancy abstraction beyond stable local Farm scope.

## Source Artifacts

- .memory-bank/features/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
- .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
- .memory-bank/epics/EP-001-local-farm-access-and-admin.md
- .memory-bank/requirements.md

## Normative Inputs

- .memory-bank/architecture/system-architecture.md
- .memory-bank/domains/runtime-data-model.md
- .memory-bank/states/core-lifecycles.md
- .memory-bank/contracts/api-guidelines.md
- .memory-bank/testing/index.md
- .memory-bank/invariants.md

## Constraints

- PostgreSQL/read model owns Farm, Plant, PlantAccessGrant, and lifecycle state.
- Timeline JSONL, manifests, export snapshots, and UI selectors are not mutable
  authority.
- Archived Plants are excluded from normal operations and normal agent context.
- Hard delete is absent in MVP.
- Grant revocation removes future normal visibility/context retrieval without deleting
  audit/evidence.

## Invariants

- MVP has exactly one active local Farm.
- `tomato_001` is present as the initial Plant seed/migration target.
- `plant_approve_actions` is the only MVP per-permission override and never bypasses
  Safety Gate.
- Backend authorization filters Plant reads/mutations/context retrieval.

## Steps

1. Add single Farm and `tomato_001` seed/read model after FT-001 ActorContext exists.
2. Implement Plant create/archive/restore service and API routes.
3. Implement PlantAccessGrant persistence and policy.
4. Implement archive retention/history access filters and no-hard-delete guard.
5. Add lifecycle/access integration tests and generated OpenAPI validation.

## Expected Touched Files

- backend/app/farm/*
- backend/app/plants/*
- backend/app/access/*
- backend/app/db/migrations/*
- backend/app/api/*
- backend/tests/plants/*
- backend/tests/integration/*
- .memory-bank/changelog.md

## Tests

- Unit: Plant lifecycle transitions and grant policy.
- Integration: single Farm, seed Plant, authorized Plant list, grant revocation,
  archived normal-flow exclusion, retained history access.
- Contract: generated OpenAPI after schemas exist.
- Negative: no hard delete route/command, no multi-Farm route/workspace selector.

## Quality Gates

- pytest backend/tests/plants backend/tests/integration
- generated OpenAPI validation after implementation schemas exist
- node scripts/mb-lint.mjs
- node scripts/mb-doctor.mjs
- /verify and /red-verify for T2/T3 closure
- T3 human checkpoint and rollback/recovery note for PlantAccessGrant/access tasks

## UAT Steps

- Boss sees one local Farm and `tomato_001`.
- Boss creates, archives, and restores a Plant.
- Engineer sees only granted active Plants.
- Revoked grant removes normal visibility without deleting retained evidence.
- Archived Plant history remains available only through authorized history/admin views.

## Task Slice

- TASK-006: Single Farm and `tomato_001` seed/read model.
- TASK-007: Plant create/archive/restore service and routes.
- TASK-008: PlantAccessGrant persistence and authorized selector.
- TASK-009: Archive retention/history access filters.
- TASK-010: Plant lifecycle/access integration and OpenAPI tests.
