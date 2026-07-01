---
description: Login, logout, current-session HTTP boundary and stable auth/session errors.
status: active
type: api_contract
last_updated: 2026-06-30
source_of_truth:
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/auth/session-security.md
  - .memory-bank/states/auth/session-lifecycle.md
  - .memory-bank/contracts/access/actor-context.md
---
# Session HTTP

## Scope

Defines `POST /api/session/login`, `POST /api/session/logout`,
`GET /api/session/me` and their payloads, statuses, and errors.

## Out of scope

Password/token algorithms, cookie constants, persistence, Plant resolution,
Boss account creation, and first-Boss bootstrap.

## POST /api/session/login

- Request: `login_name`, `password`.
- Success `200`: sets browser/PWA session cookie; body has `account_id`,
  `farm_id`, `membership_id`, `role_preset`, `session_expires_at`.
- Failures: `AUTH_CREDENTIAL_INVALID`, `AUTH_ACCOUNT_DISABLED`,
  `AUTH_MEMBERSHIP_REQUIRED`,
  `AUTH_MEMBERSHIP_DISABLED`, `VALIDATION_FAILED`.
- Credential failure is generic and does not reveal whether login exists.

## POST /api/session/logout

- No request fields; success `204`.
- Revoke current session when valid and always clear browser auth state.
- Missing/invalid session may return `204`; do not leak validity.

## GET /api/session/me

- Success `200` returns `account_id`, `display_name`, `farm_id`,
  `membership_id`, `role_preset`, `membership_status`,
  `session_expires_at`, and a safe `plant_scope_summary`.
- Plant summary reflects ActorContext/Plant permission resolution when
  available and never leaks unauthorized Plant details.
- Failures: `AUTH_SESSION_REQUIRED`, `AUTH_SESSION_INVALID`,
  `AUTH_SESSION_EXPIRED`, `AUTH_ACCOUNT_DISABLED`,
  `AUTH_MEMBERSHIP_REQUIRED`, `AUTH_MEMBERSHIP_DISABLED`.

## Error envelope and catalog

Errors use API Guidelines `{error:{code,message,request_id}}`.

| Code | Status | Use |
|---|---:|---|
| `AUTH_SESSION_REQUIRED` | 401 | Missing protected-route credential. |
| `AUTH_SESSION_INVALID` | 401 | Malformed, unknown, revoked, or unverifiable session. |
| `AUTH_SESSION_EXPIRED` | 401 | Persisted session expired. |
| `AUTH_CREDENTIAL_INVALID` | 401 | Generic login failure. |
| `AUTH_ACCOUNT_DISABLED` | 403 | Account disabled. |
| `AUTH_MEMBERSHIP_REQUIRED` | 403 | No local Farm membership. |
| `AUTH_MEMBERSHIP_DISABLED` | 403 | Membership not active. |
| `AUTH_FORBIDDEN` | 403 | Role lacks non-Plant authority. |
| `AUTH_PLANT_FORBIDDEN` | 404 | Generic protected-seam Plant denial without existence leak. |
| `VALIDATION_FAILED` | 422 | Invalid safe request fields. |

## Failure and security rules

- All session/Account/Membership checks fail closed.
- Authorization failures do not reveal unauthorized Plant existence.
- Responses and logs exclude passwords, session tokens,
  digests, cookies, bearer credentials, and auth headers.

## Verification

- Contract tests cover exact fields, statuses, errors, and no-account-
  enumeration behavior.
- Transport tests prove safe cookie/bearer behavior without raw token JSON in
  browser flows.
- Logout tests cover revocation, clearing, and idempotence.
- `/api/session/me` tests prove safe scoped summaries.

## Related specs

- [.memory-bank/contracts/api-guidelines.md](../api-guidelines.md)
- [.memory-bank/contracts/auth/session-security.md](session-security.md)
- [.memory-bank/states/auth/session-lifecycle.md](../../states/auth/session-lifecycle.md)
- [.memory-bank/contracts/access/actor-context.md](../access/actor-context.md)
