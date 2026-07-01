---
description: Local account, membership, and password-session expiry, revocation, and fail-closed lifecycle.
status: active
type: state_spec
last_updated: 2026-06-30
source_of_truth:
  - .memory-bank/domains/identity/account-membership.md
  - .memory-bank/domains/auth/session-storage.md
  - .memory-bank/contracts/auth/session-security.md
---
# Session Lifecycle

## Scope

Defines lifecycle transitions and guards for password session issuance,
validity, expiry, revocation, and active/disabled Account/Membership status.

## Lifecycle

```text
active Account + valid password -> new LocalSession active
active session + expires_at reached -> expired
logout -> current LocalSession revoked
disabled Account or Membership -> related sessions invalid for privileged use
```

## Rules

- Default session TTL is seven days from `created_at`.
- Login creates a new session; expired/revoked sessions are never revived.
- Issuance returns the raw token once through the selected transport and stores
  only the digest defined by session security.
- Presented tokens are hashed and compared through the security contract.
- Logout revokes only the current session and may be idempotent when the
  credential is missing/invalid.
- Validity fails closed across session, Account, and FarmMembership state.
- `last_seen_at` may update at most once per request, is cheap, and is not an
  authorization source.
- Disable status invalidates privileged use immediately even if batch session
  revocation is deferred.
- MVP has no refresh-token lifecycle; users re-login after expiry.

## Failures

- Missing, malformed, expired, revoked, unknown, or disabled state
  follows the stable session HTTP errors and never leaks credential/account
  existence.

## Verification

- Tests cover login, TTL, expiry, current-session revocation, idempotent logout,
  and disabled Account/Membership denial.
- Tests prove issuance uses digest-only storage and never revives a session.
- No refresh-token schema or transition exists.

## Related specs

- [.memory-bank/contracts/auth/session-security.md](../../contracts/auth/session-security.md)
- [.memory-bank/contracts/auth/session-http.md](../../contracts/auth/session-http.md)
- [.memory-bank/contracts/access/actor-context.md](../../contracts/access/actor-context.md)
