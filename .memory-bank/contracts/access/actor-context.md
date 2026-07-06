---
description: ActorContext, role policy, bounded PlantPermissionContext seam, and context-builder authorization contract.
status: active
type: interface_contract
last_updated: 2026-07-06
source_of_truth:
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/domains/farm/farm-plant-access-storage.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
---
# ActorContext

## Scope

Defines the protected-request actor envelope, fixed role policy,
PlantPermissionContext shape, the minimum resolver semantics needed by FT-001,
no-leak denials, and authorization hygiene for routes/services/context builders.

## Out of scope

Account/session persistence and transport, Plant/PlantAccessGrant persistence or
mutation, retained-history workflows, Safety Gate clearance, and Plant HTTP.

## Role presets

| Role | Base authority |
|---|---|
| `boss` | Farm admin; may create Plants; all Farm Plant visibility/operations; action approval authority only through Safety Gate. |
| `engineer` | May create a Plant in the single Farm; granted Plant read/operate/tasks; action approval only when active grant has `plant_approve_actions=true` and Safety Gate passes. |
| `consultant` | Granted Plant read/comment/advice only; no domain-task creation, governance approval by default, or physical-action approval. |

The only per-Plant override is `plant_approve_actions`; no general ACL engine.

## ActorContext shape

Every protected API route, domain service entrypoint, audit writer, and
agent/context builder resolves before business logic:

- `request_id`, `session_id`, `account_id`, `farm_id`, `membership_id`;
- `role_preset`, `membership_status`;
- `auth_provenance`: `auth_method`, `session_created_at`,
  `session_expires_at`, `transport: cookie|bearer`;
- `plant_permission_resolver`.

## PlantPermissionContext shape

- `plant_id`;
- `plant_status: active|archived|null` (`null` only for internal denied/not-
  found/fail-closed paths and never as an existence leak);
- `can_read`, `can_comment`, `can_operate`, `can_create_domain_tasks`,
  `can_manage_access`, `can_approve_actions`;
- `source: boss_role|plant_access_grant|denied`;
- nullable `grant_id`, populated only for `plant_access_grant`.

## Resolver input

- `farm_id`, `membership_id`, `role_preset`, optional `plant_id`;
- `operation_kind: normal_read|operate|retained_history_read|manage_lifecycle|manage_access|approve_action`.

## Authorization matrix

| Role/state | Active read | Active operate/tasks | Archived retained history | Manage lifecycle/access | Approve action |
|---|---|---|---|---|---|
| Active Boss | all Farm Plants | yes | authorized retained history | yes | Safety Gate required |
| Engineer + active grant | yes | yes | authorized retained history | no | grant flag + Safety Gate |
| Consultant + active grant | read/comment | no | authorized read/comment only | no | never |
| Missing/revoked grant or disabled identity | no | no | no | no | no |

## Resolver rules

- Plant creation is a Farm-scoped authorization decision made from active
  ActorContext membership and `boss|engineer` role before a `plant_id` exists;
  it does not use or manufacture a `PlantPermissionContext` for the candidate
  Plant. Consultant and disabled membership are denied before persistence.
- Successful Engineer creation must atomically produce an active creator grant
  before subsequent Plant resolution. This grant resolves through the normal
  `source=plant_access_grant` path and starts with
  `plant_approve_actions=false`.
- Boss resolves with `source=boss_role` and no grant.
- Engineer/Consultant require an active grant for normal and retained-history
  reads; missing/revoked grant resolves `source=denied`.
- Archived Plant denies normal read/operate/action approval. Explicit retained
  history may allow read/comment but always denies operate, task creation, and
  action approval.
- `can_comment=true` follows authorized read for all roles.
- `can_create_domain_tasks=true` only for Boss or granted Engineer during
  active normal-operation access.
- Consultant never receives operate/task/manage/action authority.
- Engineer Plant creation does not set `can_manage_access` and does not grant
  lifecycle-management authority; archive/restore and grant management remain
  Boss-only.
- Generic FT-001 protected seams may use `AUTH_PLANT_FORBIDDEN`; it must hide
  whether the Plant exists. The concrete FT-002 HTTP error catalog is deferred.
- Context builders exclude denied and archived-normal-operation records before
  any Bus/model context is prepared.
- Before Plant persistence exists, fail-closed adapters/test fixtures may
  implement this interface but not lifecycle or grant mutation semantics.
- `can_approve_actions` is actor authority, never Safety Gate pass.

## Context hygiene

- ActorContext audit attribution uses safe account/membership/role refs, never
  raw auth material.
- `/health`, `/ready`, and explicitly public auth routes are exceptions that
  expose no Farm/Plant data.
- Agent context requires `can_read=true` and uses the same resolver as UI/API.
- Bus/MessageEnvelope may carry safe `actor_ref`/`authorization_scope`, but no
  session IDs, tokens/digests, password hashes, headers, cookies, UI Feed, raw
  chat, or unapproved proposals.

## Verification

- Unit tests cover roles, all output fields, archived access, revoked/missing
  grants, denied source, comment/task flags, and action approval derivation.
- Policy tests cover Farm-scoped Plant creation for active Boss/Engineer and
  denial for Consultant/disabled membership without requiring a pre-existing
  Plant grant.
- Compatibility tests prove one resolver shape across FT-001 protected seams
  and future FT-002 adapters.
- Integration tests prove ActorContext-before-business-logic and authorization
  parity between reads and context builders.
- Bus/model context tests exclude auth material and unauthorized Plants.
- Deferred cross-feature E2E after FT-002 tasking proves Engineer sees only
  granted Plants, immediately sees an atomically granted self-created Plant,
  and Consultant remains read/comment/advice only.

## Related specs

- [.memory-bank/contracts/api-guidelines.md](../api-guidelines.md)
- [.memory-bank/contracts/auth/session-http.md](../auth/session-http.md)
- [.memory-bank/domains/farm/farm-plant-access-storage.md](../../domains/farm/farm-plant-access-storage.md)
- [.memory-bank/states/plants/plant-and-access-lifecycle.md](../../states/plants/plant-and-access-lifecycle.md)
- [.memory-bank/contracts/agent-chat-bus.md](../agent-chat-bus.md)
- [.memory-bank/contracts/message-envelope.md](../message-envelope.md)
