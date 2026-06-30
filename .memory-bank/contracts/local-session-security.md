---
description: FT-001 credential, session token, lifecycle, cookie, and bearer security contract.
status: active
owner: architecture
type: contract
feature_id: FT-001
last_updated: 2026-06-29
source_of_truth:
  - .memory-bank/features/FT-001-local-accounts-sessions-actor-context.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/evidence-redaction.md
  - .memory-bank/domains/local-identity-session-data.md
  - .memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md
---
# Local Session Security

## Ownership

- Owns: FT-001 password hashing, opaque session token generation and hashing,
  session lifecycle, browser cookie transport, and optional bearer transport.
- Does not own: relational column/index shape, HTTP route payloads/error
  catalog, ActorContext authorization, or FT-003 invite-secret lifecycle.
- Related specs:
  - [.memory-bank/domains/local-identity-session-data.md](../domains/local-identity-session-data.md):
    persistent `password_hash`, `token_hash`, and LocalSession shape.
  - [.memory-bank/contracts/local-session-api.md](local-session-api.md): login,
    logout, session inspection, and activation handoff HTTP behavior.
  - [.memory-bank/contracts/evidence-redaction.md](evidence-redaction.md):
    redaction requirements for logs, tests, and handoff evidence.
  - [.memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md](../tech-specs/FT-003-boss-admin-surface-admin-audit.md):
    public invite activation and activation-secret lifecycle.

## Credential And Token Shape

- `password_hash`: Argon2id PHC string generated through `argon2-cffi`.
- `raw_session_token`: client-only opaque URL-safe token generated from at
  least 32 random bytes with Python `secrets` APIs.
- `token_hash`: lowercase hex SHA-256 digest of the exact raw session token
  bytes after UTF-8 encoding.

## Credential And Token Rules

- `TASK-006` must add `argon2-cffi` as a runtime dependency and use Argon2id
  for password hashing and verification.
- Runtime password hashing parameters are
  `time_cost=3`, `memory_cost=65536`, `parallelism=4`, `hash_len=32`, and
  `salt_len=16` unless a later explicit security spec replaces them.
- Plain SHA, unsalted hashes, reversible encryption, homemade password KDFs,
  and plaintext password storage are forbidden for `password_hash`.
- Session tokens must be generated with at least 256 bits of entropy; for
  example, `secrets.token_urlsafe(32)`.
- The raw session token may be returned only once through the selected session
  transport and must never be persisted, logged, audited, exported, inserted
  into Bus/UI Feed/agent context, or written into test evidence.
- Session lookup computes `token_hash` from the presented token and verifies
  the stored digest with constant-time comparison such as
  `hmac.compare_digest`.
- Password verification delegates secret comparison to Argon2id verification;
  failure surfaces only generic auth errors.

## Session Lifecycle

```text
FT-003 local invite/bootstrap -> Account pending_activation + FarmMembership invited
FT-003 invite activation -> Account active + FarmMembership active + LocalSession
active account + valid password -> LocalSession active until expires_at or revoked_at
logout -> current LocalSession revoked
disabled account or disabled membership -> all related sessions invalid for privileged use
```

- Default session TTL is 7 days from `created_at`.
- MVP has no refresh-token flow; users re-login after expiry.
- `last_seen_at` may be updated at most once per request and should be cheap; it
  is not an authorization source.
- Login creates a new LocalSession; it does not silently revive expired or
  revoked sessions.
- Logout revokes only the current session. FT-003 account/membership disable
  paths invalidate all privileged use by status check even before batch
  revocation exists.
- Activation/setup secrets are one-time local secrets created, validated, and
  status-tracked by FT-003. FT-001 does not expose a public activation route.
- FT-003's `POST /api/local-invites/activate` is the only public invite
  activation endpoint. After FT-003 validates `local_invite_id` plus
  `activation_secret`, it calls the FT-001 internal credential/session
  primitive to set `password_hash`, activate Account/Membership, and issue a
  LocalSession.
- Pending activation and invited membership may access only the FT-003 public
  invite activation route. They cannot access Farm/Plant data, context
  builders, admin routes, agent routes, Bus context, or UI Feed data.

## Browser Cookie Shape

- Name: `agro_intellect_session`.
- Value: raw opaque session token.
- `HttpOnly`: required.
- `SameSite`: `Lax`.
- `Path`: `/`.
- `Max-Age`: `604800` seconds by default.
- `Expires`: same instant as `LocalSession.expires_at`.
- `Secure`: `false` only for explicit loopback HTTP development origins such
  as `http://localhost` or `http://127.0.0.1`; `true` for HTTPS and any browser
  cookie use outside loopback.

## Transport Rules

- Browser/PWA uses the HTTP-only same-site cookie by default.
- Login and FT-003 invite activation success set exactly this cookie for
  browser/PWA transport and do not include the raw token in the JSON body.
- Logout clears the cookie with the same name/path/samesite/secure mode and
  `Max-Age=0`; the clearing response should also set an already-expired
  `Expires` value.
- Cookie TTL must not outlive the persisted `LocalSession.expires_at`.
- Plain HTTP LAN browser cookie mode is forbidden. Optional LAN browser mode
  must use HTTPS, explicit enablement, API Guidelines origin controls, and
  `Secure=true`.
- Bearer mode is disabled by default for browser/PWA flows. When explicitly
  enabled for non-browser/LAN clients, the raw token is returned once in a safe
  response field or header, clients send `Authorization: Bearer ...`, and the
  server still stores only `token_hash`.
- Bearer responses use no-store cache behavior and must not also set the
  session cookie.
- No hosted recovery, email delivery, third-party identity, or SaaS tenancy is
  introduced in MVP.

## Edge Cases And Errors

- Empty, malformed, unknown, revoked, expired, or unverifiable tokens fail as
  `AUTH_SESSION_INVALID` or the more specific expiry/status code owned by the
  session API contract.
- Password mismatch and missing login both surface as
  `AUTH_CREDENTIAL_INVALID` without account enumeration.
- Missing cookie and missing bearer credential on a protected route surface
  `AUTH_SESSION_REQUIRED`.
- Multiple session credentials on one request fail closed with
  `AUTH_SESSION_INVALID` unless a later route spec explicitly chooses
  precedence.
- Cookie clearing is idempotent: logout returns `204` and clears the browser
  cookie even when the presented session is missing or invalid.
- Every failure path redacts passwords, raw tokens, token hashes, cookies,
  bearer tokens, auth headers, and `.env` values before logs or evidence are
  written.

## Verification Target

- Unit tests prove Argon2id hash/verify success and failure without storing or
  returning plaintext passwords.
- Unit tests prove session token generation produces opaque high-entropy
  values, persists only SHA-256 `token_hash`, rejects bad tokens, and uses
  constant-time digest comparison.
- Session API tests assert login cookie name/attributes, TTL alignment, and
  correct `Secure` behavior for loopback versus HTTPS.
- Logout tests assert cookie clearing and idempotence.
- Bearer-mode tests, when implemented, prove no cookie is emitted and only
  `token_hash` is persisted.
- Redaction evidence proves auth material is removed from error/log-like
  strings.
