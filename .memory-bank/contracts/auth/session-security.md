---
description: Password, session-token, browser-cookie, bearer, and auth-material security contract.
status: active
type: security_contract
last_updated: 2026-06-30
source_of_truth:
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/evidence-redaction.md
---
# Session Security

## Scope

Defines credential hashing, opaque session-token generation and comparison,
browser cookie transport, optional bearer transport, and redaction rules.

## Out of scope

Relational shape, session transitions, HTTP payloads/errors, ActorContext, Boss
Account creation, and first-Boss bootstrap.

## Credential and token shape

- `password_hash`: Argon2id PHC string generated with `argon2-cffi`.
- `raw_session_token`: client-only opaque URL-safe token generated from at
  least 32 random bytes with Python `secrets` APIs.
- `token_hash`: lowercase SHA-256 hex digest of the exact token UTF-8 bytes.

## Rules

- Runtime Argon2id parameters are `time_cost=3`, `memory_cost=65536`,
  `parallelism=4`, `hash_len=32`, and `salt_len=16` unless a later explicit
  security spec replaces them.
- Plain SHA passwords, unsalted hashes, reversible encryption, homemade KDFs,
  and plaintext password storage are forbidden.
- Session tokens contain at least 256 bits of entropy, for example
  `secrets.token_urlsafe(32)`.
- The raw token is returned only once through the selected transport and is
  never persisted, logged, audited, exported, sent to Bus/UI Feed/agent
  context, or written to evidence.
- Lookup computes `token_hash`; comparison with a stored digest uses a
  constant-time primitive such as `hmac.compare_digest`.
- Password mismatch and missing login expose only generic auth failures.

## Browser cookie

- Name `agro_intellect_session`; value is the raw opaque token.
- `HttpOnly=true`, `SameSite=Lax`, `Path=/`.
- Default `Max-Age=604800`; `Expires` equals `LocalSession.expires_at`.
- `Secure=false` only for explicit loopback HTTP origins such as
  `localhost`/`127.0.0.1`; HTTPS and all browser cookie use outside loopback
  require `Secure=true`.
- Browser/PWA is cookie-first. Successful login does not include the raw token
  in JSON.
- Logout clears the same cookie attributes with `Max-Age=0` and an expired
  `Expires`; clearing is idempotent.
- Cookie TTL never outlives the persisted session.

## Optional bearer transport

- Disabled by default for browser/PWA.
- When explicitly enabled for a non-browser/LAN client, return the raw token
  once through a safe response field/header, require `Authorization: Bearer`,
  use no-store caching, emit no session cookie, and still persist only the
  digest.
- Plain HTTP LAN browser-cookie mode is forbidden. Optional LAN browser mode
  requires HTTPS, explicit enablement, origin controls, and `Secure=true`.

## Failures and redaction

- Empty, malformed, unknown, revoked, expired, or unverifiable tokens fail
  closed under the session HTTP error catalog.
- Multiple credentials on one request fail closed unless a later route spec
  defines precedence.
- Passwords, tokens, token hashes, cookies, bearer credentials, auth headers,
  and `.env` values are redacted from every error/log/evidence surface.
- No hosted recovery, email delivery, third-party identity, refresh token, or
  SaaS tenancy is introduced.

## Verification

- Unit tests prove Argon2id parameters and one-way verification.
- Token tests prove entropy, SHA-256 digest-only persistence, malformed-token
  rejection, and constant-time comparison.
- API tests assert cookie attributes, TTL alignment, loopback/HTTPS `Secure`
  behavior, logout clearing, and bearer isolation when enabled.
- Redaction tests cover all auth material listed above.

## Related specs

- [.memory-bank/domains/auth/session-storage.md](../../domains/auth/session-storage.md)
- [.memory-bank/states/auth/session-lifecycle.md](../../states/auth/session-lifecycle.md)
- [.memory-bank/contracts/auth/session-http.md](session-http.md)
- [.memory-bank/contracts/evidence-redaction.md](../evidence-redaction.md)
