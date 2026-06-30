---
description: FT-001 login, logout, current-session, activation handoff, and auth error API contract.
status: active
owner: architecture
type: contract
feature_id: FT-001
last_updated: 2026-06-29
source_of_truth:
  - .memory-bank/features/FT-001-local-accounts-sessions-actor-context.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/local-session-security.md
  - .memory-bank/contracts/actor-context.md
  - .memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md
---
# Local Session API

## Ownership

- Owns: FT-001 login/logout/me route shapes, internal credential activation
  handoff, stable auth/session error catalog, and no-leak failure behavior.
- Does not own: password/token algorithms, cookie attribute values,
  persistence schema, Plant permission resolution, or FT-003's public invite
  endpoint and invite validation.
- Related specs:
  - [.memory-bank/contracts/api-guidelines.md](api-guidelines.md): global HTTP,
    error-envelope, authz, and origin rules.
  - [.memory-bank/contracts/local-session-security.md](local-session-security.md):
    session lifecycle and cookie/bearer transport.
  - [.memory-bank/contracts/actor-context.md](actor-context.md): protected-route
    identity and authorization context.
  - [.memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md](../tech-specs/FT-003-boss-admin-surface-admin-audit.md):
    public local invite activation route and invite validation.

## API Surface

Feature-local route group:

- `POST /api/session/login`
- `POST /api/session/logout`
- `GET /api/session/me`

Account creation and public invite activation routes belong to FT-003.
PlantAccessGrant resolution belongs to FT-002 but must be callable by
ActorContext.

## Internal Credential Activation Handoff

Purpose: provide the credential/session primitive used by FT-003's public
`POST /api/local-invites/activate` route after FT-003 validates the invite
credential.

Inputs from FT-003:

- `local_invite_id`
- `account_id`
- `farm_id`
- `membership_id`
- `password`
- optional `display_name`
- `transport`: `cookie | bearer`

Behavior:

- atomically sets the first local `password_hash` for the pending Account;
- activates the Account and FarmMembership;
- creates a LocalSession using the same server-side model as login;
- returns session identity and `session_expires_at`;
- emits the session-cookie instruction for browser/PWA transport when called
  from the FT-003 route boundary.

Failure codes surfaced by the FT-003 route:
`AUTH_ACTIVATION_INVALID`, `AUTH_ACCOUNT_DISABLED`,
`AUTH_MEMBERSHIP_DISABLED`, `VALIDATION_FAILED`.

## POST /api/session/login

Request fields:

- `login_name`
- `password`

Success:

- status `200`;
- sets the session cookie for browser/PWA transport;
- body contains `account_id`, `farm_id`, `membership_id`, `role_preset`, and
  `session_expires_at`.

Failure codes:
`AUTH_CREDENTIAL_INVALID`, `AUTH_ACCOUNT_PENDING`, `AUTH_ACCOUNT_DISABLED`,
`AUTH_MEMBERSHIP_REQUIRED`, `AUTH_MEMBERSHIP_DISABLED`, `VALIDATION_FAILED`.

`AUTH_CREDENTIAL_INVALID` is generic and must not reveal whether the login
exists.

## POST /api/session/logout

- Request fields: none.
- Success status: `204`.
- Revokes the current session when present.
- Clears the session cookie for browser/PWA transport.
- Missing or invalid session may still return `204` after clearing client auth
  state; the route must not leak session validity.

## GET /api/session/me

Success:

- status `200`;
- body contains:
  - `account_id`
  - `display_name`
  - `farm_id`
  - `membership_id`
  - `role_preset`
  - `membership_status`
  - `session_expires_at`
  - `plant_scope_summary`: safe summary only, such as role-level all-Plant
    access for Boss or granted Plant IDs for Engineer/Consultant when the
    FT-002 resolver is available.

Failure codes:
`AUTH_SESSION_REQUIRED`, `AUTH_SESSION_INVALID`, `AUTH_SESSION_EXPIRED`,
`AUTH_ACCOUNT_DISABLED`, `AUTH_MEMBERSHIP_REQUIRED`,
`AUTH_MEMBERSHIP_DISABLED`.

## Error Shape

All errors follow API Guidelines:

```json
{
  "error": {
    "code": "AUTH_SESSION_REQUIRED",
    "message": "Authentication is required.",
    "request_id": "req_..."
  }
}
```

## Stable Error Catalog

| Code | HTTP status | Use |
|---|---:|---|
| `AUTH_SESSION_REQUIRED` | 401 | No session credential on a protected route. |
| `AUTH_SESSION_INVALID` | 401 | Malformed, unknown, revoked, or unverifiable session. |
| `AUTH_SESSION_EXPIRED` | 401 | Session exists but `expires_at` is in the past. |
| `AUTH_CREDENTIAL_INVALID` | 401 | Login failed with generic no-leak message. |
| `AUTH_ACTIVATION_INVALID` | 401 | Invite activation credential missing, expired, used, revoked, or invalid; surfaced by FT-003. |
| `AUTH_ACCOUNT_PENDING` | 403 | Account is not activated for normal routes. |
| `AUTH_ACCOUNT_DISABLED` | 403 | Account disabled. |
| `AUTH_MEMBERSHIP_REQUIRED` | 403 | No FarmMembership for the single local Farm. |
| `AUTH_MEMBERSHIP_DISABLED` | 403 | FarmMembership disabled or not active. |
| `AUTH_FORBIDDEN` | 403 | Role lacks authority for a non-Plant-specific operation. |
| `AUTH_PLANT_FORBIDDEN` | 404 | Generic FT-001 Plant-scoped denial without existence leak; FT-002 Plant routes use `plant_not_found_or_forbidden`. |
| `VALIDATION_FAILED` | 422 | Invalid request fields without protected details. |

## Failure Rules

- Missing, expired, revoked, malformed, or unknown session fails closed.
- `pending_activation` Account cannot access normal routes except FT-003's
  public invite activation route.
- Disabled Account or FarmMembership fails closed.
- Missing FarmMembership fails closed.
- Missing PlantAccessGrant prevents Plant-scoped visibility for
  Engineer/Consultant.
- Authorization errors must not reveal unauthorized Plant existence.
- Consultant cannot create domain task/recommendation records, approve
  governance by default, or approve physical actions.
- Passwords, activation secrets, session tokens, token hashes, cookies,
  bearer tokens, and auth headers must not enter logs, audit/export, Bus,
  UI Feed, screenshots, or agent context.

## Verification Target

- Contract tests cover exact request/response fields, statuses, and stable
  error-code mappings.
- Login tests prove generic no-account-enumeration failure behavior.
- Login and activation tests prove browser/PWA responses use the transport
  contract without returning raw token data in JSON.
- Logout tests prove `204`, revocation when present, cookie clearing, and
  idempotence for missing/invalid sessions.
- `GET /api/session/me` tests prove a safe actor/session summary without
  secrets or unauthorized Plant details.
