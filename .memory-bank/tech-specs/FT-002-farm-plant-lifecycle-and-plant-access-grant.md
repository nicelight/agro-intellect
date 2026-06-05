---
description: Feature-local SDD tech spec for FT-002 single Farm workspace, Plant lifecycle, and PlantAccessGrant.
status: active
feature_id: FT-002
owner: spec-improve
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/features/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
  - .memory-bank/requirements.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/states/core-lifecycles.md
  - .memory-bank/contracts/api-guidelines.md
---
# FT-002 Farm, Plant Lifecycle, And PlantAccessGrant Tech Spec

## Purpose

Define the minimum feature-local design needed before task decomposition for the single
local Farm workspace, initial `tomato_001` Plant, Plant create/archive/restore, retained
history semantics, and PlantAccessGrant authorization.

This spec refines the global backbone and must not weaken
[.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md),
[.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md), or
[.memory-bank/states/core-lifecycles.md](../states/core-lifecycles.md).

## Scope

In scope:

- exactly one active local Farm workspace;
- multiple Plants within that Farm;
- `tomato_001` initial Plant seed or migration target;
- Plant lifecycle: `active` and `archived`;
- archive/restore semantics without hard delete;
- PlantAccessGrant lifecycle: `granted` and `revoked`;
- `plant_approve_actions` as the only MVP per-permission override;
- retained authorized history, photos, tasks, outcomes, timeline refs, and admin audit.

Out of scope:

- multi-Farm tenancy or multi-Farm membership;
- broad farm-management modules;
- hard delete of Plants;
- custom per-action permission matrix beyond `plant_approve_actions`;
- server sync or hosted workspace behavior.

## Data Ownership

PostgreSQL/read model is mutable authority for:

- `Farm`;
- `Plant`;
- `PlantAccessGrant`;
- current Plant lifecycle state;
- current grant state and `plant_approve_actions`;
- retained references to authorized history, tasks, outcomes, photos, and admin audit.

Timeline JSONL, photo manifests, export snapshots, and UI Plant selector visibility are
not mutable authority.

## Farm Rules

- MVP has exactly one local Farm.
- A Farm has state `active`.
- Farm identity must be stable enough for ActorContext, Plant, audit, context-builder,
  and future export refs.
- Feature tasks must avoid adding tenancy abstractions that imply multiple Farms,
  hosted organizations, billing, or server workspace selection.

## Plant Lifecycle

Minimum Plant fields/semantics:

```yaml
plant_id: string
farm_id: string
canonical_label: string
display_name: string
state: active | archived
created_by_actor_ref: string
created_at: datetime
archived_at: datetime | null
archived_by_actor_ref: string | null
archive_reason: string | null
restored_at: datetime | null
restored_by_actor_ref: string | null
```

Rules:

- seed or migrate `tomato_001` as the initial Plant;
- new Plants are created inside the single Farm;
- archive removes the Plant from normal operational flows;
- restore returns the Plant to normal operational eligibility when authorized;
- hard delete is absent;
- archive/restore creates admin audit and may create timeline refs, but timeline replay
  never overwrites Plant state.

## Archive Visibility And Retention

Archived Plants:

- are excluded from normal Plant selector, check-in start, photo upload, measurement
  entry, agent context building for normal operation, task mutation, and physical-action
  approval paths;
- retain authorized history views, photo/catalog refs, tasks, outcomes, timeline audit,
  admin audit, and export refs;
- remain visible in admin/history views only to authorized actors.

Archive must not invalidate old evidence refs. Revoked PlantAccessGrant can remove
normal visibility/context retrieval without deleting retained audit/evidence.

## PlantAccessGrant

Minimum grant semantics:

```yaml
grant_id: string
farm_id: string
plant_id: string
account_id: string
membership_id: string
state: granted | revoked
can_view: boolean
can_work: boolean
plant_approve_actions: boolean
created_by_actor_ref: string
updated_by_actor_ref: string
revoked_at: datetime | null
```

Rules:

- grants are Farm/Plant scoped;
- active Boss authority can manage grants through Boss/Admin features;
- Engineer and Consultant need a granted PlantAccessGrant for normal Plant visibility;
- Consultant grants are advisory/read/comment only and never include physical-action
  approval authority;
- `plant_approve_actions=true` may be set only for Engineer/Boss-compatible approval
  paths and remains subject to Safety Gate rules;
- revocation removes future normal visibility, work authorization, context retrieval,
  and approval ability without deleting retained audit/evidence.

## Authorization Filter

Every Plant-scoped route and context-builder path must check:

1. resolved ActorContext;
2. single active Farm scope;
3. Account and FarmMembership state;
4. Plant state, including normal-flow exclusion when archived;
5. PlantAccessGrant state and role preset;
6. `plant_approve_actions` only for physical-action approval eligibility, never as a
   Safety Gate bypass.

Unauthorized access should return safe `permission_denied`, `not_found`, or
`archived_resource` style responses without leaking private record existence.

## API Surface To Refine In Tasks

Task decomposition may define exact endpoint and schema details for:

- read current Farm;
- list authorized active Plants;
- list archived Plants for authorized admin/history views;
- create Plant;
- archive Plant;
- restore Plant;
- grant/revoke/update PlantAccessGrant;
- read retained Plant history for authorized users.

Generated OpenAPI comes from implementation schemas later.

## Verification Targets

Required tests before FT-002 can be considered implemented:

- only one active local Farm exists and multi-Farm routes are absent;
- `tomato_001` is present as initial Plant seed/migration target;
- Plant create/archive/restore transitions obey `active`/`archived` rules;
- hard delete route or command is absent;
- archived Plants are excluded from normal operations and agent context retrieval;
- archived Plant history, photos, tasks, outcomes, timeline refs, and admin audit remain
  retained and accessible only to authorized actors;
- missing/revoked PlantAccessGrant blocks visibility, mutation, context retrieval, and
  approval eligibility;
- `plant_approve_actions` is the only per-permission override and does not bypass Safety
  Gate;
- timeline/photo/manifest/export artifacts cannot overwrite Plant lifecycle authority.

## Open Questions

No blocker for `/prd-to-tasks FT-002`. Exact labels, route names, admin view grouping,
and seed/migration mechanics can be chosen during task decomposition as long as the
single-Farm, no-hard-delete, retention, and authorization constraints hold.
