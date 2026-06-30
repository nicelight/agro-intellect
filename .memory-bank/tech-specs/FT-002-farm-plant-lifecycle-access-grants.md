---
description: Feature SDD design for FT-002 Farm Plant Lifecycle And Access Grants.
status: active
owner: architecture
type: feature_design
feature_id: FT-002
last_updated: 2026-06-29
source_of_truth:
  - .memory-bank/features/FT-002-farm-plant-lifecycle-access-grants.md
  - .memory-bank/foundation.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/domains/local-identity-session-data.md
  - .memory-bank/contracts/actor-context.md
---
# FT-002 Farm Plant Lifecycle And Access Grants

## Purpose

Define the single local Farm, Plant lifecycle, `tomato_001` seed, and PlantAccessGrant rules that gate per-Plant visibility and work authorization.

## Ownership

- Owns: single local Farm seed, Plant lifecycle, PlantAccessGrant lifecycle,
  concrete PlantPermissionContext resolver output semantics, retained-history
  authorization, Plant/access route contracts, and Plant route denial codes.
- Does not own: Account, FarmMembership, LocalSession, credential/session
  primitives, ActorContext envelope, public invite activation route,
  AdminAuditRecord durability policy, Safety Gate clearance, agent output
  publication, MessageEnvelope validation, or UI Feed projection.
- Related specs:
  - [.memory-bank/domains/local-identity-session-data.md](../domains/local-identity-session-data.md):
    owns Account, FarmMembership, and LocalSession storage, including the
    deferred Farm FK handoff closed by FT-002.
  - [.memory-bank/contracts/actor-context.md](../contracts/actor-context.md):
    owns role presets, ActorContext, and the PlantPermissionContext interface
    envelope consumed by protected routes and context builders.
  - [.memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md](FT-003-boss-admin-surface-admin-audit.md):
    owns public invite/admin workflows and durable AdminAuditRecord write
    policy used by successful FT-002 admin mutations.
  - [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md):
    owns global no-existence-leak and stable API error guardrails.

## Normative Inputs

- [.memory-bank/spec-backbone.md](../spec-backbone.md): global backbone is complete.
- [.memory-bank/foundation.md](../foundation.md): verified Foundation baseline for local Farm/Plant migrations, DB session conventions, bootstrap, and redaction.
- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Access & Admin and Runtime State boundaries.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): Plant and PlantAccessGrant authority.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): API authz and route grouping.
- [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md): context builders must enforce ActorContext and PlantAccessGrant before agent context.
- [.memory-bank/domains/local-identity-session-data.md](../domains/local-identity-session-data.md): Account/FarmMembership storage and deferred Farm FK handoff.
- [.memory-bank/contracts/actor-context.md](../contracts/actor-context.md): role presets, ActorContext, and PlantPermissionContext interface envelope.
- [.memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md](FT-003-boss-admin-surface-admin-audit.md): AdminAuditRecord owner and audited admin mutations.
- [.memory-bank/requirements.md](../requirements.md): REQ-001, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008.

## Design Depth

Feature hub only. The global backbone already defines the Access & Admin, Runtime State, API, Bus, and ActorContext boundaries. FT-002 owns the concrete Farm/Plant/access-grant data details, route contracts, state transitions, retained-history filter, and permission resolver behavior needed before task decomposition.

## Data Model

PostgreSQL/read model is the mutable authority for all FT-002 records.

Feature-owned mutable records and required fields:

- `Farm`
  - `farm_id`: PostgreSQL native UUID/Python `uuid.UUID` identity.
  - `farm_key`: fixed MVP value `local_farm`
  - `name`
  - `farm_status`: `active`
  - `created_at`
  - `updated_at`
- `Plant`
  - `plant_id`: PostgreSQL native UUID/Python `uuid.UUID` identity.
  - `farm_id`: required UUID Farm FK.
  - `plant_key`: stable human-readable key, unique per Farm; initial value `tomato_001`
  - `display_name`
  - `crop_kind`
  - `plant_status`: `active | archived`
  - `created_by`
  - `created_at`
  - `updated_by`, `updated_at`
  - `archived_by`, `archived_at`, `archive_reason`
  - `restored_by`, `restored_at`
- `PlantAccessGrant`
  - `grant_id`: PostgreSQL native UUID/Python `uuid.UUID` identity.
  - `farm_id`: required UUID Farm FK.
  - `plant_id`: required UUID Plant FK.
  - `membership_id`: required UUID FarmMembership FK.
  - `grant_status`: `active | revoked`
  - `plant_approve_actions`: boolean
  - `granted_by`, `granted_at`
  - `revoked_by`, `revoked_at`
  - `updated_by`, `updated_at`

Required constraints:

- There is exactly one `Farm` row with `farm_key=local_farm`.
- `Plant.plant_key` is unique inside the single Farm.
- `PlantAccessGrant` references `FarmMembership` from FT-001 by `membership_id`.
- There can be at most one active `PlantAccessGrant` for the same `plant_id` and `membership_id`.
- `PlantAccessGrant.farm_id` must match both the Plant Farm and the membership Farm.
- Revoked grants are retained for audit/history and are not deleted.

Grant presence plus role preset controls visibility/work. The only MVP per-Plant override is `plant_approve_actions`; do not add a generic ACL matrix in MVP.

## Farm Authority And Deferred Membership FK Closure

This block owns the FT-002 side of the temporary
`farm_memberships.farm_id` relation defined by FT-001. FT-001 owns the initial
column and intentional FK absence; FT-002 owns Farm creation/reuse and final FK
validation.

Shape:

- `farms.farm_id` is PostgreSQL native `uuid`, mapped as Python `uuid.UUID`,
  and uses application-generated `uuid.uuid4` when no prior membership UUID
  exists.
- The final relation is
  `farm_memberships.farm_id -> farms.farm_id ON DELETE RESTRICT`.
- FT-002 follows the shared identifier contract in
  [Runtime Data Model](../domains/runtime-data-model.md).

Rules:

1. Before seeding `farms`, the FT-002 migration reads distinct non-null
   `farm_memberships.farm_id` values.
2. With zero values, it generates one UUIDv4 and creates the single
   `farm_key=local_farm` row with that ID.
3. With exactly one value, it creates/reuses `farm_key=local_farm` with that
   exact UUID; it does not rewrite existing memberships.
4. With more than one distinct value, migration stops. It must not create
   multiple Farm rows, choose one silently, or rewrite membership data.
5. After the single Farm row exists, the migration adds and validates the
   non-cascading FK before FT-002/FT-003 Farm or membership product-write paths
   are enabled.

Edge cases/errors:

- An existing `local_farm` row with a different UUID from the sole membership
  UUID is a migration conflict and must stop for explicit repair.
- Null membership `farm_id` is invalid under FT-001 and must not be backfilled
  here.
- Deleting the Farm while memberships reference it is rejected; archive/disable
  semantics are used instead of cascade deletion.
- This migration must not create a second local Farm or infer multi-Farm
  tenancy from inconsistent pre-release data.

Verification target:

- Migration tests cover zero, one matching, one conflicting, and multiple
  distinct pre-existing membership Farm IDs.
- Schema inspection proves the final native-UUID `RESTRICT` FK is present and
  validated.
- Integration tests prove an unknown `farm_id` cannot be inserted after FT-002
  migration and referenced Farm deletion is rejected without cascading.

## Farm Seed

MVP must have exactly one local Farm. First run creates or reuses the single local Farm with:

- `farm_key=local_farm`
- `farm_status=active`

Multi-Farm creation, Farm switching, hosted tenant IDs, and multi-Farm membership are forbidden in MVP. Any API or bootstrap path that would create a second Farm fails closed with `single_farm_only`.

## Plant Seed

`tomato_001` is the initial Plant and seed key. First setup must create it if no active or archived Plant with `plant_key=tomato_001` exists in the local Farm.

Seed defaults:

- `plant_key=tomato_001`
- `display_name=tomato_001`
- `crop_kind=tomato`
- `plant_status=active`

`tomato_001` is not a product limit; Boss may create additional Plants.

## Plant Lifecycle

```text
create -> active
active -> archive -> archived
archived -> restore -> active
```

Rules:

- No hard delete in MVP.
- Archive removes the Plant from normal operations and normal Plant selector.
- Archive retains history, photos, tasks, outcomes, timeline audit, and admin audit for authorized access.
- Restore returns the Plant to normal operations.
- Create, archive, and restore must write one durable AdminAuditRecord through FT-003 audit rules after a successful mutation.
- Re-archiving an archived Plant and restoring an active Plant are no-op conflicts, not successful mutations.
- Archive does not revoke PlantAccessGrant by itself; active grants remain as retained-history authorization and become operational again after restore.

Normal operations means Plant selector, daily check-in, observations, measurement entry, photo upload, action approval, agent context builder input, and default Plant history. Explicit retained-history/admin/audit/export routes may include archived Plants when ActorContext authorization passes.

## PlantAccessGrant Lifecycle

```text
grant -> active
active -> update plant_approve_actions
active -> revoke -> revoked
revoked -> grant creates a new active grant
```

Rules:

- Boss can manage PlantAccessGrant for Farm Plants.
- Engineer and Consultant cannot manage PlantAccessGrant.
- Engineer/Consultant need an active grant to see Plant data.
- Boss role can see and operate Farm Plants without per-Plant grant, but all actions still resolve through ActorContext.
- Engineer can approve physical actions only when the active grant has `plant_approve_actions=true` and Safety Gate rules pass.
- Consultant never approves physical actions even if a grant exists.
- Granting access to an archived Plant is allowed only for retained-history/admin purposes; it does not make the archived Plant selectable for normal operations.
- Updating a revoked grant is forbidden; create a new active grant instead.
- Grant, update, and revoke must write one durable AdminAuditRecord through FT-003 audit rules after a successful mutation.

## Authorization Matrix

| Actor role | Active Plant normal read | Active Plant operate | Archived Plant retained history | Manage Plant lifecycle | Manage PlantAccessGrant | Approve physical action |
|---|---|---|---|---|---|---|
| `boss` | all Farm Plants | all Farm Plants | all Farm Plants | yes | yes | only through Safety Gate |
| `engineer` | active grant required | active grant required | active grant required | no | no | active grant with `plant_approve_actions=true` and Safety Gate |
| `consultant` | active grant required | no, read/comment/advice only | active grant required | no | no | never |

Authorization failures must fail closed and must not reveal whether an unauthorized Plant exists.

For PlantPermissionContext output, `can_comment=true` follows authorized
Plant read access for Boss, granted Engineer, and granted Consultant.
`can_create_domain_tasks=true` only for Boss and granted Engineer during active
normal-operation access; it is false for Consultant, archived retained-history
access, denied access, and missing/revoked grants.

## PlantPermissionContext Resolver

FT-002 provides the concrete resolver used by the FT-001 ActorContext interface
for Plant-scoped paths. FT-001 owns the interface envelope and generic
protected-seam denial code; FT-002 owns the resolver values, PlantAccessGrant
lookup semantics, archived/retained-history behavior, and Plant route denial
code mapping.

Input:

- `farm_id`
- `membership_id`
- `role_preset`
- optional `plant_id`
- `operation_kind`: `normal_read | operate | retained_history_read | manage_lifecycle | manage_access | approve_action`

Output for a Plant-scoped result:

- `plant_id`
- `plant_status`: `active | archived | null`; `null` is allowed only when the
  internal result is denied/not-found/fail-closed and must not be exposed as a
  Plant existence leak.
- `can_read`
- `can_comment`
- `can_operate`
- `can_create_domain_tasks`
- `can_manage_access`
- `can_approve_actions`
- `source`: `boss_role | plant_access_grant | denied`
- `grant_id` when permission came from a PlantAccessGrant; otherwise `null`

Resolver rules:

- Boss uses `source=boss_role` and does not require a grant.
- Engineer/Consultant require an active grant for `normal_read` and `retained_history_read`.
- Archived Plant returns `can_read=false` for `normal_read` and may return `can_read=true` only for `retained_history_read`.
- Archived Plant always returns `can_operate=false` and `can_approve_actions=false`.
- Archived Plant retained-history access always returns
  `can_create_domain_tasks=false`.
- `can_comment=true` for authorized read/retained-history access; denied access
  returns `can_comment=false`.
- Boss and granted Engineer may return `can_create_domain_tasks=true` only for
  active normal-operation Plant access.
- Consultant always returns `can_operate=false` and `can_approve_actions=false`.
- Revoked or missing grants return `source=denied`.
- Missing or forbidden Plant route access surfaces `plant_not_found_or_forbidden`
  and must not be translated to FT-001 `AUTH_PLANT_FORBIDDEN` on FT-002 HTTP
  routes.
- Context builders and agent input builders must call this resolver and exclude denied or archived-normal-operation records before any Bus or model context is prepared.

## API Surface

Feature-local route groups use FastAPI/Pydantic-style JSON. All routes require ActorContext and backend authorization.

- `GET /api/plants`
- `POST /api/plants`
- `GET /api/plants/{plant_id}`
- `POST /api/plants/{plant_id}/archive`
- `POST /api/plants/{plant_id}/restore`
- `GET /api/plants/{plant_id}/retained-history`
- `GET /api/plants/{plant_id}/access`
- `POST /api/plants/{plant_id}/access`
- `PATCH /api/plants/{plant_id}/access/{grant_id}`
- `POST /api/plants/{plant_id}/access/{grant_id}/revoke`

Schema decisions:

- `GET /api/plants`
  - Query: `include_archived=false` by default.
  - Response item: `plant_id`, `plant_key`, `display_name`, `crop_kind`, `plant_status`, `permission_context`, `created_at`, `archived_at`.
  - Engineer/Consultant see only granted Plants; archived Plants appear only when `include_archived=true` and retained-history authorization passes.
- `POST /api/plants`
  - Boss only.
  - Request: `plant_key` optional, `display_name`, `crop_kind`.
  - Response: created Plant response item.
  - Validation: `plant_key` must be unique in Farm when provided; generated keys must not collide.
- `GET /api/plants/{plant_id}`
  - Response: Plant response item plus `updated_at`, `archive_reason` when archived.
  - Archived Plant requires retained-history authorization.
- `POST /api/plants/{plant_id}/archive`
  - Boss only.
  - Request: `archive_reason` optional safe text.
  - Response: updated Plant response item.
- `POST /api/plants/{plant_id}/restore`
  - Boss only.
  - Request: empty object.
  - Response: updated Plant response item.
- `GET /api/plants/{plant_id}/retained-history`
  - Explicit retained-history entry point only; FT-006 owns detailed history payloads.
  - Response: `plant_id`, `plant_status`, `history_available=true`, `history_scope=retained`, `refs` placeholder list for runtime/timeline refs.
- `GET /api/plants/{plant_id}/access`
  - Boss only.
  - Response item: `grant_id`, `plant_id`, `membership_id`, `grant_status`, `plant_approve_actions`, `granted_at`, `revoked_at`, `updated_at`.
- `POST /api/plants/{plant_id}/access`
  - Boss only.
  - Request: `membership_id`, `plant_approve_actions=false`.
  - Response: PlantAccessGrant response item.
- `PATCH /api/plants/{plant_id}/access/{grant_id}`
  - Boss only.
  - Request: `plant_approve_actions`.
  - Response: PlantAccessGrant response item.
- `POST /api/plants/{plant_id}/access/{grant_id}/revoke`
  - Boss only.
  - Request: empty object or optional safe `revoke_reason`.
  - Response: revoked PlantAccessGrant response item.

Stable error codes:

- `unauthorized`
- `forbidden`
- `plant_not_found_or_forbidden`
- `plant_archived`
- `plant_not_archived`
- `single_farm_only`
- `duplicate_plant_key`
- `duplicate_active_grant`
- `grant_not_found_or_forbidden`
- `grant_revoked`
- `invalid_membership_for_farm`

Use `plant_not_found_or_forbidden` and `grant_not_found_or_forbidden` where revealing existence would leak unauthorized data. FT-001 generic auth/session seams may use `AUTH_PLANT_FORBIDDEN` for non-route protected-seam denial, but concrete FT-002 Plant HTTP routes use the FT-002 lowercase route codes above.

## Audit And Event Decisions

Successful Plant and PlantAccessGrant mutations must create AdminAuditRecord entries owned by FT-003:

- `plant_created`
- `plant_archived`
- `plant_restored`
- `plant_access_granted`
- `plant_access_updated`
- `plant_access_revoked`

Audit summaries must include safe identifiers and status/permission deltas, but never session tokens, auth headers, credentials, invite codes, secrets, raw provider payloads, or hidden reasoning.

FT-002 does not publish agent-consumable Bus events for access-management text. Context builders consume PostgreSQL/read-model state through ActorContext and PlantPermissionContext. Later Plant operations/history features may publish Plant-scoped Bus events only after applying the same authorization and archived-Plant filtering.

## Failure Rules

- Unauthorized actors cannot list, read, mutate, archive, restore, or access retained history for unauthorized Plants.
- Archived Plants are excluded from normal operations unless a route explicitly asks for retained history/admin view.
- Revoked grants immediately remove Engineer/Consultant operational visibility and context-builder access.
- Duplicate active grants for the same membership/Plant are forbidden.
- Multi-Farm creation fails closed.
- Failed mutations must not create success audit records.
- PlantAccessGrant changes take effect for new ActorContext resolution immediately; existing clients must refresh permission-sensitive views after mutation.
- API responses, audit summaries, Bus/context output, screenshots, and exports must not include auth material or secret values.

## Verification

- Unit: Plant lifecycle transition policy.
- Unit: grant/revoke/update rules and `plant_approve_actions` derivation.
- Unit: PlantPermissionContext resolver for Boss, Engineer, Consultant,
  archived Plant, revoked grant, missing grant, `plant_status`, `grant_id`,
  `source=denied`, `can_comment`, and `can_create_domain_tasks`.
- Unit: compatibility between the FT-001 PlantPermissionContext interface
  envelope and the FT-002 concrete resolver output.
- Unit: FT-002 Plant route denial uses `plant_not_found_or_forbidden` while
  preserving the same no-existence-leak semantics as FT-001 generic
  `AUTH_PLANT_FORBIDDEN`.
- Unit: uniqueness/constraint policy for single Farm, `plant_key`, and duplicate active grants.
- Integration: Plant list filters Boss, Engineer, Consultant correctly.
- Integration: context builder excludes unauthorized and revoked-grant Plants.
- Integration: archived Plant is excluded from normal operations and agent context but allowed through explicit retained-history route for authorized actors.
- Integration: archive/restore retains authorized history refs.
- Integration: successful create/archive/restore/grant/update/revoke writes exactly one safe AdminAuditRecord.
- E2E: Boss grants Engineer access to `tomato_001`; Engineer sees it; archive removes it from normal operations; restore returns it.
- E2E: revoked Engineer grant removes `tomato_001` from Engineer selector and context-builder access.

## Non-Goals

- Hard delete.
- Multi-Farm tenancy.
- General ACL engine.
- Plant operation forms, check-ins, photo upload, and Plant history rendering beyond access/lifecycle hooks.
- Agent output generation, MessageEnvelope creation, UI Feed projection, Safety Gate policy, and physical-action task execution.

## Handoff To /prd-to-tasks

Tasks may implement single Farm bootstrap, `tomato_001` seed, Plant CRUD limited to create/archive/restore, PlantAccessGrant management, ActorContext permission resolver integration, retained-history authorization stub, AdminAuditRecord write integration, and tests. They must not implement daily check-in/photo/runtime history workflows, agent publication, UI Feed projection, Safety Gate behavior, or physical-action task execution except minimal references needed by archive/restore and authorization checks.
