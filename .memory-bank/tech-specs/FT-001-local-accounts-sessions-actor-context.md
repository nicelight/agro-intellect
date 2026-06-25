---
description: Feature SDD design for FT-001 Local Accounts Sessions And ActorContext.
status: active
owner: architecture
type: feature_design
feature_id: FT-001
last_updated: 2026-06-25
source_of_truth:
  - .memory-bank/features/FT-001-local-accounts-sessions-actor-context.md
  - .memory-bank/foundation.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md
  - .memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md
---
# FT-001 Local Accounts Sessions And ActorContext

## Purpose

Define the local identity, session, role, and ActorContext boundary that every Farm/Plant route, domain service, audit writer, and agent/context builder must use.

## Normative Inputs

- [.memory-bank/spec-backbone.md](../spec-backbone.md): global backbone is complete.
- [.memory-bank/foundation.md](../foundation.md): verified Foundation baseline for migrations, DB/session helpers, local runtime roots, and redaction.
- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Access & Admin module and source-of-truth hierarchy.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): Account, FarmMembership, ActorContext authority.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): API authz and error guardrails.
- [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md): context builders must resolve ActorContext and PlantAccessGrant before returning Bus context.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): MessageEnvelope authorization scope must not include unauthorized Farm/Plant context or auth material.
- [.memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md](FT-002-farm-plant-lifecycle-access-grants.md): Farm, Plant, and PlantAccessGrant ownership used by the ActorContext permission resolver.
- [.memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md](FT-003-boss-admin-surface-admin-audit.md): local invite/admin mutation and AdminAuditRecord ownership.
- [.memory-bank/requirements.md](../requirements.md): REQ-002, REQ-003, REQ-004, REQ-022.

## Design Depth

Feature hub only. No new global spec is needed; shared access/admin backbone is already covered by system architecture, runtime data model, API guidelines, Agent Chat Bus, MessageEnvelope, and adjacent FT-002/FT-003 feature specs.

## Ownership Boundaries

FT-001 owns:

- `Account`, `FarmMembership`, and `LocalSession` table contracts.
- local credential setup primitives, login, logout, session inspection, session invalidation, and auth error codes.
- `ActorContext` and `PlantPermissionContext` shape.
- role-preset policy as consumed by backend authorization.
- the interface used by routes, audit writers, and context builders to require ActorContext.

FT-001 does not own:

- `Farm`, `Plant`, `PlantAccessGrant`, Plant lifecycle, or `tomato_001` seeding; these belong to FT-002.
- Boss admin invite creation, public local invite activation route, account/personnel management UI, role mutation routes, Plant access mutation routes, or durable admin audit write policy; these belong to FT-003.
- Safety Gate clearance; `can_approve_actions` means actor authority only and never means Safety Gate pass.
- agent output publication, Bus event payloads, MessageEnvelope validation, or UI Feed projection.

The implementation may build a small interface stub for FT-002/FT-003 dependencies only when needed for task sequencing, but must not duplicate their domain rules.

## Data Model

Feature-owned mutable records:

- `Account`
  - `account_id`: stable local identifier.
  - `login_name`: normalized lowercase login, unique locally.
  - `display_name`
  - `account_status`: `pending_activation | active | disabled`
  - `password_hash`: nullable only while `pending_activation`.
  - `created_at`, `updated_at`, `disabled_at`
- `FarmMembership`
  - `membership_id`: stable local identifier.
  - `account_id`
  - `farm_id`
  - `role_preset`: `boss | engineer | consultant`
  - `membership_status`: `invited | active | disabled`
  - `created_at`, `updated_at`, `disabled_at`
- `LocalSession`
  - `session_id`: stable local identifier.
  - `account_id`
  - `token_hash`: unique server-side hash of the opaque token.
  - `created_at`
  - `expires_at`
  - `revoked_at`
  - `last_seen_at`
  - `auth_method`: `local_password | local_invite_activation`
  - `client_label`: optional safe label such as `local_pwa`; never user-agent secrets.

Minimum constraints:

- `Account.login_name` is unique after normalization.
- `FarmMembership` has one row per `account_id + farm_id` in MVP; multi-Farm membership is out of scope.
- `LocalSession.token_hash` is unique and indexed for lookup.
- `LocalSession` validity is computed from `expires_at`, `revoked_at`, `Account.account_status`, and `FarmMembership.membership_status`.
- Foreign keys must preserve account/session/membership referential integrity; disabling is preferred over hard delete in MVP.

The client receives only an opaque session token. Store only a token hash server-side.

## Session Lifecycle

```text
FT-003 local invite/bootstrap -> Account pending_activation + FarmMembership invited
FT-003 public invite activation calls FT-001 credential/session primitive -> Account active + FarmMembership active
active account + valid password -> LocalSession active until expires_at or revoked_at
logout -> current LocalSession revoked
disabled account or disabled membership -> all related sessions invalid for privileged use
```

Session token transport:

- Browser/PWA default: HTTP-only same-site cookie on loopback.
- Bearer token may be used only for explicit non-browser/LAN mode and must follow the same server-side session model.
- No hosted recovery, email delivery, third-party identity, or SaaS tenancy in MVP.

Concrete lifecycle decisions:

- Default session TTL is 7 days from `created_at`.
- MVP has no refresh-token flow; users re-login after expiry.
- `last_seen_at` may be updated at most once per request and should be cheap; it is not an authorization source.
- Login creates a new `LocalSession`; it does not silently revive expired or revoked sessions.
- Logout revokes only the current session. Admin disable paths from FT-003 invalidate all privileged use by status check even before batch revocation exists.
- Activation/setup secrets are one-time local secrets created, validated, and status-tracked by FT-003. FT-001 does not expose a public activation route.
- FT-003's `POST /api/local-invites/activate` is the only public invite activation endpoint. After FT-003 validates `local_invite_id` plus `activation_secret`, it calls the FT-001 internal credential/session primitive to set `password_hash`, activate Account/Membership, and issue a `LocalSession`.
- Pending activation and invited membership may access only the FT-003 public invite activation route. They cannot access Farm/Plant data, context builders, admin routes, agent routes, Bus context, or UI Feed data.

## Role Presets

KISS role presets are fixed in MVP:

| Role | Base authority |
|---|---|
| `boss` | Farm admin, account/member management, Plant lifecycle management, Plant access management, admin audit read, all Farm Plant visibility and operations, physical-action approval authority only through Safety Gate. |
| `engineer` | Granted Plant read/operate, check-ins, photos, measurements, allowed tasks/follow-up; physical-action approval authority only when the active PlantAccessGrant has `plant_approve_actions=true`. |
| `consultant` | Granted Plant read/comment/advice context only; no domain task/recommendation record creation, no governance approval by default, no physical-action approval authority. |

Do not add a general permission override matrix in MVP. The only per-Plant override is `plant_approve_actions`.

## ActorContext

Every non-health API route, protected domain service entrypoint, audit writer, and agent/context builder must resolve:

- `request_id`
- `session_id`
- `account_id`
- `farm_id`
- `membership_id`
- `role_preset`
- `membership_status`
- `auth_provenance`
  - `auth_method`
  - `session_created_at`
  - `session_expires_at`
  - `transport`: `cookie | bearer`
- `plant_permission_resolver`

For Plant-scoped operations, the resolver must return a `PlantPermissionContext`:

- `plant_id`
- `can_read`
- `can_comment`
- `can_operate`
- `can_create_domain_tasks`
- `can_manage_access`
- `can_approve_actions`
- `source`: `boss_role | plant_access_grant`

Permission derivation:

| Role/grant state | can_read | can_comment | can_operate | can_create_domain_tasks | can_manage_access | can_approve_actions |
|---|---:|---:|---:|---:|---:|---:|
| Boss active membership | yes | yes | yes | yes | yes | yes, subject to Safety Gate |
| Engineer active PlantAccessGrant | yes | yes | yes | yes | no | grant `plant_approve_actions`, subject to Safety Gate |
| Consultant active PlantAccessGrant | yes | yes | no | no | no | no |
| Engineer/Consultant missing or revoked grant | no | no | no | no | no | no |
| Disabled account or membership | no | no | no | no | no | no |

ActorContext must be created before business logic and must be present in audit records as account/membership/role references, not as session tokens or auth material.

## Context Builder Rules

- Context builders must use the same ActorContext and PlantPermissionContext as user-facing reads.
- Agent Chat Bus context must include `authorization_scope` derived from ActorContext, but must not include session IDs, tokens, token hashes, password hashes, invite/setup secrets, auth headers, or cookies.
- For Plant-scoped agent context, `can_read=true` is required. Consultant context may include read/comment/advisory facts but must not expose operational task creation or approval authority.
- A valid MessageEnvelope or Bus event may reference `actor_ref` and `authorization_scope`; it must never carry auth provenance fields beyond safe account/membership/role refs.

## API Surface

Feature-local route groups:

- `POST /api/session/login`
- `POST /api/session/logout`
- `GET /api/session/me`

Account creation and invite activation routes belong to FT-003. PlantAccessGrant resolution belongs to FT-002 but must be callable by ActorContext.

Route contracts:

Canonical public activation request belongs to FT-003's `POST /api/local-invites/activate`: `local_invite_id`, `activation_secret`, `password`, and optional `display_name`. FT-001 receives only the validated activation handoff plus credential/session inputs through the internal primitive below.

### Internal `activate local credential and issue session`

Purpose: provide the credential/session primitive used by FT-003's public `POST /api/local-invites/activate` route after FT-003 validates the invite credential.

Inputs from FT-003:

- `local_invite_id`
- `account_id`
- `farm_id`
- `membership_id`
- `password`
- `display_name` optional
- `transport`: `cookie | bearer`

Behavior:

- atomically sets the first local `password_hash` for the pending Account;
- activates the Account and FarmMembership;
- creates a `LocalSession` using the same server-side session model as login;
- returns session identity and `session_expires_at`;
- emits the HTTP-only same-site `Set-Cookie` session instruction for browser/PWA transport when called from the FT-003 route boundary.

Failure codes surfaced by the FT-003 route: `AUTH_ACTIVATION_INVALID`, `AUTH_ACCOUNT_DISABLED`, `AUTH_MEMBERSHIP_DISABLED`, `VALIDATION_FAILED`.

### `POST /api/session/login`

Request fields:

- `login_name`
- `password`

Success response:

- status `200`
- sets the session cookie for browser/PWA transport
- body:
  - `account_id`
  - `farm_id`
  - `membership_id`
  - `role_preset`
  - `session_expires_at`

Failure codes: `AUTH_CREDENTIAL_INVALID`, `AUTH_ACCOUNT_PENDING`, `AUTH_ACCOUNT_DISABLED`, `AUTH_MEMBERSHIP_REQUIRED`, `AUTH_MEMBERSHIP_DISABLED`, `VALIDATION_FAILED`.

`AUTH_CREDENTIAL_INVALID` must be generic and must not reveal whether the login exists.

### `POST /api/session/logout`

Request fields: none.

Success response:

- status `204`
- revokes the current session when present
- clears the session cookie for browser/PWA transport

Failure behavior:

- Missing or invalid session may still return `204` after clearing local client auth state. This route must not leak session validity.

### `GET /api/session/me`

Success response:

- status `200`
- body:
  - `account_id`
  - `display_name`
  - `farm_id`
  - `membership_id`
  - `role_preset`
  - `membership_status`
  - `session_expires_at`
  - `plant_scope_summary`: safe summary only, such as role-level all-Plant access for Boss or granted Plant IDs for Engineer/Consultant when FT-002 resolver is available

Failure codes: `AUTH_SESSION_REQUIRED`, `AUTH_SESSION_INVALID`, `AUTH_SESSION_EXPIRED`, `AUTH_ACCOUNT_DISABLED`, `AUTH_MEMBERSHIP_REQUIRED`, `AUTH_MEMBERSHIP_DISABLED`.

## Error Contract

All auth/session errors follow API Guidelines:

```json
{
  "error": {
    "code": "AUTH_SESSION_REQUIRED",
    "message": "Authentication is required.",
    "request_id": "req_..."
  }
}
```

Stable FT-001 error codes:

| Code | HTTP status | Use |
|---|---:|---|
| `AUTH_SESSION_REQUIRED` | 401 | No session credential on a protected route. |
| `AUTH_SESSION_INVALID` | 401 | Malformed, unknown, revoked, or unverifiable session. |
| `AUTH_SESSION_EXPIRED` | 401 | Session exists but `expires_at` is in the past. |
| `AUTH_CREDENTIAL_INVALID` | 401 | Login failed with generic no-leak message. |
| `AUTH_ACTIVATION_INVALID` | 401 | Invite activation credential missing, expired, used, revoked, or invalid; surfaced by FT-003's public activation route. |
| `AUTH_ACCOUNT_PENDING` | 403 | Account is not activated for normal routes. |
| `AUTH_ACCOUNT_DISABLED` | 403 | Account disabled. |
| `AUTH_MEMBERSHIP_REQUIRED` | 403 | No FarmMembership for the single local Farm. |
| `AUTH_MEMBERSHIP_DISABLED` | 403 | FarmMembership disabled or not active. |
| `AUTH_FORBIDDEN` | 403 | Role lacks authority for a non-Plant-specific operation. |
| `AUTH_PLANT_FORBIDDEN` | 404 | Plant-scoped access denied; response must not reveal whether the Plant exists. |
| `VALIDATION_FAILED` | 422 | Invalid request fields without protected details. |

## Failure Rules

- Missing, expired, revoked, malformed, or unknown session fails closed.
- `pending_activation` Account cannot access normal routes except FT-003's public invite activation route.
- `disabled` Account or disabled membership fails closed.
- Missing FarmMembership fails closed.
- Missing PlantAccessGrant prevents Plant-scoped visibility for Engineer/Consultant.
- Authorization errors must not reveal unauthorized Plant existence.
- Consultant cannot create domain task/recommendation records, approve governance by default, or approve physical actions.
- Passwords, activation secrets, session tokens, token hashes, cookies, bearer tokens, and auth headers must not enter logs, audit/export, Bus, UI Feed, screenshots, or agent context.

## Migration And Indexing Targets

Implementation tasks should create migrations for the feature-owned records and enforce the constraints above. Concrete table names may follow backend conventions, but generated schemas must preserve the contract names in code comments or docs pointers.

Required indexes:

- `Account.login_name` unique normalized lookup.
- `FarmMembership.account_id + farm_id` lookup and uniqueness.
- `LocalSession.token_hash` unique lookup.
- `LocalSession.account_id` lookup for revocation/status checks.
- `LocalSession.expires_at` lookup for cleanup.

No migration may create a second Farm authority or duplicate FT-002 PlantAccessGrant rules.

## Verification

- Unit: role preset derivation and `PlantPermissionContext` rules.
- Unit: account/session lifecycle and disabled-account behavior.
- Unit: secret redaction in auth/session errors.
- Unit: exact FT-001 error code mapping and no-leak login/Plant authorization behavior.
- Unit: session TTL, expiry, revocation, and logout idempotence.
- Integration: every protected route has ActorContext before business logic.
- Integration: context builders enforce the same Plant authorization as user-facing reads.
- Integration: Agent Chat Bus context excludes session/auth material and unauthorized Plants.
- Integration: `GET /api/session/me` returns safe actor/session summary without secrets.
- E2E: Engineer sees only granted Plants; Consultant remains read/comment/advice only.
- E2E: pending activation cannot access Farm/Plant data until FT-003 invite activation succeeds and FT-001 issues a session.

## Non-Goals

- Enterprise identity, OAuth, password recovery, email invite delivery, SaaS tenancy, and multi-Farm membership.
- Full ACL/permission override engine beyond `plant_approve_actions`.
- Remember-me refresh tokens, device management, hosted account recovery, audit export UI, and broad personnel management.

## Handoff To /prd-to-tasks

Tasks may implement local session storage, login/logout/me routes, the internal credential activation/session issuing primitive used by FT-003, ActorContext builder, role preset policy, PlantPermissionContext resolver interface, auth error mapping, migrations for FT-001-owned records, and tests.

Tasks must not implement FT-002 Plant lifecycle, FT-002 PlantAccessGrant mutation rules, FT-003's public local invite activation route, or FT-003 admin mutation surfaces except minimal interfaces needed by ActorContext and local activation sequencing.

## Resolved Design Decisions

- Session transport defaults to HTTP-only same-site cookie; bearer token is optional only for explicit non-browser/LAN mode.
- Public invite activation is owned only by FT-003 as `POST /api/local-invites/activate`; FT-001 exposes only the internal credential/session primitive it calls.
- Default session TTL is 7 days; no refresh-token mechanism in MVP.
- `Account` status is `pending_activation | active | disabled`.
- `FarmMembership` status is `invited | active | disabled`.
- `LocalSession` validity is computed fail-closed from session, account, and membership state.
- `PlantPermissionContext` has explicit read/comment/operate/task/manage/approve booleans.
- Boss can approve actions only as actor authority and still needs Safety Gate; Engineer needs `plant_approve_actions`; Consultant never approves physical actions.
- Unauthorized Plant access returns `AUTH_PLANT_FORBIDDEN` as 404 to avoid Plant existence leaks.
- Auth/session material is forbidden from audit/export, Bus, UI Feed, screenshots, and agent context.

## Open Questions

None for FT-001 task decomposition. Any future need for hosted identity, recovery, multi-Farm membership, refresh tokens, or a general permission matrix must route to a later global spec, not FT-001 tasks.
