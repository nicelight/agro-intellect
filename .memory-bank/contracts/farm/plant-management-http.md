---
description: Concrete Farm, Plant lifecycle, PlantAccessGrant, authorization, response, and error HTTP contract.
status: active
type: api_contract
last_updated: 2026-07-06
source_of_truth:
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/domains/farm/farm-plant-access-storage.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
  - .memory-bank/domains/admin/admin-audit.md
---
# Plant Management HTTP

## Scope

Defines the protected JSON API for the current Farm summary, authorized active
Plant selection, Plant create/rename/archive/restore, and Boss-only
PlantAccessGrant administration.

## Out of scope

- Account/membership administration and the `/api/admin/plants` projection;
- retained-history contents, timeline/export, photos, check-ins, tasks,
  approvals, governance, agents, UI Feed, and PWA components;
- a public/bootstrap HTTP endpoint. Canonical Farm/`tomato_001` bootstrap is an
  operator command owned by the Farm storage spec.

## Common response shapes

`FarmSummary`:

- `farm_id: uuid`, `farm_key: "local_farm"`, `display_name: string`;
- `created_at`, `updated_at`: RFC 3339 timestamps.

`PlantPermissionSummary` is the safe serializable subset of the current
`PlantPermissionContext`:

- `can_read`, `can_comment`, `can_operate`, `can_create_domain_tasks`,
  `can_manage_access`, `can_approve_actions`;
- `source: boss_role|plant_access_grant`;
- nullable `grant_id`.

`PlantSummary`:

- `plant_id`, `farm_id`: UUID;
- `plant_key`, `display_name`;
- `status: active|archived`;
- `created_at`, `updated_at`;
- `permissions: PlantPermissionSummary` when returned by a normal actor route.

`PlantAccessGrantSummary`:

- `grant_id`, `membership_id`, `plant_id`: UUID;
- `status: active|revoked`;
- `plant_approve_actions: boolean`;
- `created_at`, `updated_at`.

All response models exclude Account credentials, session/token material,
password hashes, raw headers, internal SQL errors, and raw audit summaries.
Protected responses set `Cache-Control: no-store`.

## Routes

| Method and path | Request | Success | Authorization and behavior |
|---|---|---|---|
| `GET /api/farm` | none | `200 FarmSummary` | any active FarmMembership; exact ActorContext Farm only |
| `PATCH /api/farm` | `{display_name}` | `200 FarmSummary` | active Boss; actual change writes `farm_display_name_changed`; same trimmed value is a no-op |
| `GET /api/plants` | none | `200 {items: PlantSummary[]}` | active Plants only; Boss sees all, Engineer/Consultant only active grants; stable order by `plant_key`, then `plant_id` |
| `POST /api/plants` | `{plant_key, display_name}` | `201 PlantSummary` | active Boss or Engineer; Engineer creator grant/audit pair is atomic and represented in returned permissions |
| `GET /api/plants/{plant_id}` | none | `200 PlantSummary` | normal active-Plant read only; archived and unauthorized share the no-leak denial |
| `PATCH /api/plants/{plant_id}` | `{display_name}` | `200 PlantSummary` | active Boss or Engineer with active grant; Consultant/archived/denied cannot rename |
| `POST /api/plants/{plant_id}/archive` | no body | `200 PlantSummary` | active Boss only; locks and rechecks Plant; already archived is a no-op |
| `POST /api/plants/{plant_id}/restore` | no body | `200 PlantSummary` | active Boss only; locks and rechecks Plant; already active is a no-op |
| `GET /api/plants/{plant_id}/access` | none | `200 {items: PlantAccessGrantSummary[]}` | active Boss only; allowed for active or archived Plant; stable order by membership ID |
| `PUT /api/plants/{plant_id}/access/{membership_id}` | `{plant_approve_actions}` | `201` when created, otherwise `200 PlantAccessGrantSummary` | active Boss only; create/reactivate/update same stable grant; allowed while Plant archived |
| `POST /api/plants/{plant_id}/access/{membership_id}/revoke` | no body | `200 PlantAccessGrantSummary` | active Boss only; allowed while Plant archived; already revoked is a no-op |

Request models reject unknown fields. `farm_key`, `plant_key`, status, IDs,
timestamps, grant status, and audit fields have no update payload.

## Authorization and transaction rules

- Every route resolves ActorContext before repository/business work.
- Plant normal read/rename uses the current FT-001 permission resolver and
  `AUTH_PLANT_FORBIDDEN` no-existence-leak behavior.
- Plant creation is Farm-scoped and checks active membership plus
  `boss|engineer` before a Plant exists.
- Archive/restore and all nested access routes require active Boss role. Their
  Plant lookup uses lifecycle/access-management semantics so archived Plants
  remain administrable without becoming normally readable or operative.
- Create, rename, archive/restore, and grant mutations lock/recheck authority
  in the same transaction as state and AdminAuditRecord writes.
- Engineer creation returns only after the Plant, active creator grant with
  approval false, and both audit records are committed. A failed transaction
  returns no success representation and leaves no partial record.
- Consultant grant creation is allowed only with
  `plant_approve_actions=false`; Boss memberships do not receive grants.
- An inactive target membership cannot be granted/reactivated/updated. An
  existing grant may still be revoked while its membership is disabled.
- Archived Plant grant changes are persisted and visible to Boss but never
  make the Plant appear in `GET /api/plants` before restore.

## Error catalog

Every error uses the global `{error: {code, message, request_id}}` shape and
safe text.

| Code | HTTP | Meaning |
|---|---:|---|
| existing `AUTH_*` codes | existing mapping | session/account/membership/role failures from FT-001 |
| `AUTH_PLANT_FORBIDDEN` | 404 | Plant missing, unauthorized, revoked/missing grant, or archived for a normal route |
| `FARM_NOT_INITIALIZED` | 409 | ActorContext Farm has no canonical Farm row; run the documented bootstrap |
| `FARM_STATE_CONFLICT` | 409 | canonical single-Farm integrity is inconsistent; manual repair required |
| `PLANT_KEY_INVALID` | 422 | key does not match the canonical lowercase pattern |
| `PLANT_KEY_CONFLICT` | 409 | key already exists in the Farm; writes and audits roll back |
| `PLANT_GRANT_TARGET_INVALID` | 422 | target membership is wrong-Farm, inactive, Boss, or otherwise not grantable |
| `PLANT_GRANT_APPROVAL_FORBIDDEN` | 422 | approval flag true was requested for a non-Engineer target |
| `PLANT_GRANT_NOT_FOUND` | 404 | revoke target has never had a grant for this Plant |
| `PLANT_STATE_CONFLICT` | 409 | concurrent/current state no longer permits the requested mutation |
| `VALIDATION_FAILED` | 422 | malformed UUID/body, blank display name, unknown field, or other schema failure |

Unexpected DB exceptions are not returned verbatim. Uniqueness races map to
the stable conflict code after rollback; secret-bearing connection details are
redacted.

## Compatibility and verification

- Generated OpenAPI must represent every path, body, response, UUID, enum,
  timestamp, and stable error status above.
- API tests cover Boss/Engineer/Consultant/disabled roles, no-leak Plant
  denial, list filtering, Engineer immediate creator access, Boss-only
  lifecycle/access, immutable-key rejection, archived grant administration,
  no-op retries, and safe errors.
- Integration tests prove API results use the persisted snapshot provider, not
  an allow-all fixture or frontend filtering.

## Related specs

- [.memory-bank/testing/farm/plant-lifecycle-and-access.md](../../testing/farm/plant-lifecycle-and-access.md)
- [.memory-bank/contracts/admin/boss-admin-http.md](../admin/boss-admin-http.md)
