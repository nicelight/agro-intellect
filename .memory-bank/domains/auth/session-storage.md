---
description: LocalSession relational storage, token-hash boundary, constraints, and indexes.
status: active
type: data_spec
last_updated: 2026-06-30
source_of_truth:
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/domains/foundation-data-substrate.md
  - .memory-bank/domains/identity/account-membership.md
  - .memory-bank/contracts/auth/session-security.md
---
# Session Storage

## Scope

Defines the exact PostgreSQL `LocalSession` shape and the persistence boundary
that stores only a server-side digest of the client credential.

## Out of scope

Password/token algorithms, cookie/bearer transport, session state transitions,
HTTP route schemas, and ActorContext authorization.

## Shape

- Table `local_sessions`:
  - `session_id`: native PostgreSQL `uuid`, primary key, non-null, application
    default `uuid.uuid4`.
  - `account_id`: native PostgreSQL `uuid`, non-null.
  - `token_hash`: `varchar(64)`, non-null, lowercase ASCII SHA-256 hex only.
  - `created_at`: `timestamptz`, non-null, server default `now()`.
  - `expires_at`: `timestamptz`, non-null.
  - `revoked_at`, `last_seen_at`: nullable `timestamptz`.
  - `auth_method`: `varchar(32)`, non-null.
  - `client_label`: nullable safe local `text` label.
- No raw-token, cookie, bearer, password, or auth-header column exists.

## Rules

- UUID mapping uses Python `uuid.UUID`, `Uuid(as_uuid=True)`, and application
  `uuid.uuid4` generation.
- A named DB check limits `auth_method` to `local_password`.
- `local_sessions.account_id -> accounts.account_id ON DELETE RESTRICT`.
- Lifecycle timestamps remain null until their matching transition.
- Token generation/hashing must produce exactly 64 lowercase hex characters
  before persistence; algorithm validation belongs to session security.
- Required indexes are exactly one unique `token_hash` lookup, one non-unique
  `account_id` index, and one non-unique `expires_at` index, without duplicates.

## Edge cases and errors

- Invalid auth methods and malformed stored digests are rejected before or at
  persistence as defined by the security boundary.
- Deleting a referenced Account is rejected; revocation/disable is the
  supported lifecycle.
- Any raw session credential storage violates this contract.

## Verification

- Schema inspection covers native UUID, timestamps, nullability/defaults,
  auth-method check, `RESTRICT` FK, exact indexes, and absence of raw material.
- PostgreSQL tests prove UUID round-trip, invalid auth-method rejection,
  Account delete rejection, unique digest lookup, and revocation timestamps.
- Security tests prove only a valid lowercase SHA-256 digest reaches storage.

## Related specs

- [.memory-bank/domains/identity/account-membership.md](../identity/account-membership.md)
- [.memory-bank/contracts/auth/session-security.md](../../contracts/auth/session-security.md)
- [.memory-bank/states/auth/session-lifecycle.md](../../states/auth/session-lifecycle.md)
