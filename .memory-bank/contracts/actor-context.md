---
description: ActorContext, role preset, PlantPermissionContext interface, and context-builder authorization contract.
status: active
owner: architecture
type: contract
feature_id: FT-001
last_updated: 2026-06-29
source_of_truth:
  - .memory-bank/features/FT-001-local-accounts-sessions-actor-context.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md
---
# ActorContext

## Ownership

- Owns: ActorContext field shape, fixed MVP role policy,
  PlantPermissionContext interface envelope, protected-entrypoint rules, and
  context-builder authorization hygiene.
- Does not own: Account/session persistence, credential transport, concrete
  PlantAccessGrant lookup, archived Plant behavior, or Plant route denial-code
  mapping.
- Related specs:
  - [.memory-bank/contracts/api-guidelines.md](api-guidelines.md): global
    protected-route and authorization rules.
  - [.memory-bank/contracts/agent-chat-bus.md](agent-chat-bus.md): authorized
    agent-consumable context boundary.
  - [.memory-bank/contracts/message-envelope.md](message-envelope.md): safe
    `actor_ref` and `authorization_scope` publication boundary.
  - [.memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md](../tech-specs/FT-002-farm-plant-lifecycle-access-grants.md):
    concrete PlantPermissionContext resolver semantics and Plant HTTP denials.

## Role Presets

| Role | Base authority |
|---|---|
| `boss` | Farm admin, account/member management, Plant lifecycle/access management, admin audit read, all Farm Plant visibility and operations, and physical-action approval authority only through Safety Gate. |
| `engineer` | Granted Plant read/operate, check-ins, photos, measurements, allowed tasks/follow-up; physical-action approval authority only when the active PlantAccessGrant has `plant_approve_actions=true`. |
| `consultant` | Granted Plant read/comment/advice context only; no domain task/recommendation record creation, governance approval by default, or physical-action approval. |

Do not add a general permission override matrix in MVP. The only per-Plant
override is `plant_approve_actions`.

## ActorContext Shape

Every protected product API route, protected domain service entrypoint, audit
writer, and agent/context builder resolves:

- `request_id`
- `session_id`
- `account_id`
- `farm_id`
- `membership_id`
- `role_preset`
- `membership_status`
- `auth_provenance`:
  - `auth_method`
  - `session_created_at`
  - `session_expires_at`
  - `transport`: `cookie | bearer`
- `plant_permission_resolver`

## PlantPermissionContext Shape

For Plant-scoped operations, the resolver returns:

- `plant_id`
- `plant_status`: `active | archived | null`; `null` is allowed only for
  denied/not-found/internal fail-closed paths and must not expose Plant
  existence.
- `can_read`
- `can_comment`
- `can_operate`
- `can_create_domain_tasks`
- `can_manage_access`
- `can_approve_actions`
- `source`: `boss_role | plant_access_grant | denied`
- `grant_id`: present only when `source=plant_access_grant`

## Permission Derivation

| Role/grant state | can_read | can_comment | can_operate | can_create_domain_tasks | can_manage_access | can_approve_actions |
|---|---:|---:|---:|---:|---:|---:|
| Boss active membership | yes | yes | yes | yes | yes | yes, subject to Safety Gate |
| Engineer active PlantAccessGrant | yes | yes | yes | yes | no | grant `plant_approve_actions`, subject to Safety Gate |
| Consultant active PlantAccessGrant | yes | yes | no | no | no | no |
| Engineer/Consultant missing or revoked grant | no | no | no | no | no | no |
| Disabled account or membership | no | no | no | no | no | no |

## Rules

- ActorContext is created before business logic and appears in audit records as
  safe account/membership/role references, never session tokens or auth
  material.
- `/health`, `/ready`, and explicitly public auth endpoints are exceptions;
  exceptions must not expose Farm/Plant data or auth material.
- Context builders use the same ActorContext and PlantPermissionContext as
  user-facing reads.
- Agent Chat Bus context includes `authorization_scope` derived from
  ActorContext but excludes session IDs, tokens, token hashes, password hashes,
  invite/setup secrets, auth headers, and cookies.
- Plant-scoped agent context requires `can_read=true`.
- Consultant context may include read/comment/advisory facts but must not expose
  operational task creation or approval authority.
- MessageEnvelope or Bus events may reference `actor_ref` and
  `authorization_scope`; they must not carry auth provenance beyond safe
  account/membership/role refs.
- FT-001 owns this interface shape. FT-002 owns concrete resolver values for
  `plant_status`, `grant_id`, retained-history behavior, PlantAccessGrant
  lookup, and Plant route denial codes.
- Before FT-002 persistence exists, FT-001 may implement interface types and
  fail-closed adapters/test fixtures but must not implement PlantAccessGrant
  mutation, archived-Plant lifecycle, or retained-history authorization.
- `can_approve_actions` is actor authority only and never means Safety Gate
  pass.

## Edge Cases And Errors

- Missing/invalid session, missing membership, and disabled account/membership
  fail closed through the session API error contract.
- Missing or revoked PlantAccessGrant denies Engineer/Consultant Plant scope.
- FT-001 generic protected seams may surface `AUTH_PLANT_FORBIDDEN` as `404`.
  FT-002 Plant HTTP routes use `plant_not_found_or_forbidden` for the same
  no-existence-leak class.
- `source=denied` never exposes whether a Plant exists.
- Consultant never receives `can_create_domain_tasks`,
  `can_manage_access`, or `can_approve_actions`.

## Verification Target

- Unit tests cover role preset and permission derivation.
- Compatibility tests cover all PlantPermissionContext fields expected from
  the FT-002 resolver, including `plant_status`, `grant_id`, `source=denied`,
  `can_comment`, and `can_create_domain_tasks`.
- Integration tests prove every protected route resolves ActorContext before
  business logic.
- Integration tests prove context builders enforce the same Plant
  authorization as user-facing reads.
- Agent Chat Bus context tests exclude auth material and unauthorized Plants.
- E2E tests prove Engineer sees only granted Plants and Consultant remains
  read/comment/advice only.
