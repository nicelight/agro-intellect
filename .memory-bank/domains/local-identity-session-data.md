---
description: FT-001 Account, FarmMembership, and LocalSession relational data contract.
status: active
owner: architecture
type: domain
feature_id: FT-001
last_updated: 2026-06-29
source_of_truth:
  - .memory-bank/features/FT-001-local-accounts-sessions-actor-context.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/domains/foundation-data-substrate.md
  - .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md
---
# Local Identity And Session Data

## Ownership

- Owns: exact FT-001 `Account`, `FarmMembership`, and `LocalSession` storage
  shape, constraints, indexes, initial migration, and deferred Farm FK handoff.
- Does not own: credential hashing/token algorithms, HTTP session transport,
  Farm/Plant/PlantAccessGrant lifecycle, or FT-003 invite/admin records.
- Related specs:
  - [.memory-bank/domains/runtime-data-model.md](runtime-data-model.md): shared
    UUID identity, runtime authority, and non-cascading relation rules.
  - [.memory-bank/domains/foundation-data-substrate.md](foundation-data-substrate.md):
    DB/session/Alembic substrate used by the migration.
  - [.memory-bank/contracts/local-session-security.md](../contracts/local-session-security.md):
    credential and token formats validated before persistence.
  - [.memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md](../tech-specs/FT-002-farm-plant-lifecycle-access-grants.md):
    Farm authority and final `farm_memberships.farm_id` FK closure.

## Shape

- Table `accounts`:
  - `account_id`: PostgreSQL `uuid`, primary key, non-null, application default
    `uuid.uuid4`.
  - `login_name`: `text`, non-null; stores only the canonical normalized value.
  - `display_name`: `text`, non-null.
  - `account_status`: `varchar(32)`, non-null.
  - `password_hash`: unbounded `text`, nullable.
  - `created_at`, `updated_at`: `timestamptz`, non-null, server default `now()`.
  - `disabled_at`: nullable `timestamptz`.
- Table `farm_memberships`:
  - `membership_id`: PostgreSQL `uuid`, primary key, non-null, application
    default `uuid.uuid4`.
  - `account_id`: PostgreSQL `uuid`, non-null.
  - `farm_id`: PostgreSQL `uuid`, non-null.
  - `role_preset`: `varchar(16)`, non-null.
  - `membership_status`: `varchar(16)`, non-null.
  - `created_at`, `updated_at`: `timestamptz`, non-null, server default `now()`.
  - `disabled_at`: nullable `timestamptz`.
- Table `local_sessions`:
  - `session_id`: PostgreSQL `uuid`, primary key, non-null, application default
    `uuid.uuid4`.
  - `account_id`: PostgreSQL `uuid`, non-null.
  - `token_hash`: `varchar(64)`, non-null; stores lowercase ASCII hexadecimal
    SHA-256 only.
  - `created_at`: `timestamptz`, non-null, server default `now()`.
  - `expires_at`: `timestamptz`, non-null.
  - `revoked_at`, `last_seen_at`: nullable `timestamptz`.
  - `auth_method`: `varchar(32)`, non-null.
  - `client_label`: nullable `text` containing only a safe local label.
- `LocalSession` has no raw-token, cookie, bearer, or auth-header column.

## Rules

- SQLAlchemy maps every UUID column above as Python `uuid.UUID` with
  `Uuid(as_uuid=True)`. UUIDs are application-generated with `uuid.uuid4`; no
  PostgreSQL extension or integer sequence is required.
- Statuses/roles use ordinary string columns plus named DB `CHECK` constraints,
  not PostgreSQL native ENUM types:
  - `accounts.account_status IN ('pending_activation', 'active', 'disabled')`;
  - `farm_memberships.membership_status IN ('invited', 'active', 'disabled')`;
  - `farm_memberships.role_preset IN ('boss', 'engineer', 'consultant')`;
  - `local_sessions.auth_method IN ('local_password', 'local_invite_activation')`.
- The Account credential check is:
  `active -> password_hash IS NOT NULL`,
  `pending_activation -> password_hash IS NULL`, and
  `disabled -> password_hash may be null or non-null`.
  Argon2id PHC validation belongs to the session security component; the DB
  must not add a brittle PHC-prefix check or arbitrary maximum length.
- The application canonicalizes login input with `strip().lower()` before
  persistence. PostgreSQL is the final guard: a named check requires
  `login_name = lower(btrim(login_name))` and `login_name <> ''`; one unique
  B-tree constraint/index on stored `login_name` provides normalized
  uniqueness. Do not add `citext` or a second functional unique index.
- `updated_at` is set to the mutation time by the owning service; no DB trigger
  is introduced. Nullable lifecycle timestamps remain null until their matching
  disable/revoke/seen transition occurs.
- `farm_memberships.account_id -> accounts.account_id` and
  `local_sessions.account_id -> accounts.account_id` are required FKs with
  `ON DELETE RESTRICT`. No authority relation uses cascading delete.
- `farm_memberships.farm_id` is intentionally non-null but has no FK in the
  FT-001 migration because FT-001 must not create the FT-002-owned `farms`
  table. Before FT-002, no released bootstrap/admin path may create durable
  FarmMembership rows; rollback-scoped migration/repository fixtures and
  internal service tests may use temporary rows.
- FT-002 must close the deferred relation before enabling Farm/membership
  product writes: create/reuse the single Farm authority, reconcile at most one
  existing distinct membership `farm_id`, then add and validate
  `farm_memberships.farm_id -> farms.farm_id ON DELETE RESTRICT`.
- Required uniqueness/indexes are exactly:
  - one unique normalized lookup for `accounts.login_name`;
  - one unique constraint/index on `farm_memberships(account_id, farm_id)`;
  - one unique lookup index on `local_sessions.token_hash`;
  - one non-unique index on `local_sessions.account_id`;
  - one non-unique index on `local_sessions.expires_at`.
  Do not add duplicate indexes for the same leading columns.
- Token generation/hashing must produce exactly 64 lowercase hex characters
  before persistence. Format validation belongs to the session security
  component; the migration owns the non-null `varchar(64)` storage shape.

## Edge Cases And Errors

- Invalid status, role, or auth-method values are rejected by DB checks.
- An `active` Account without `password_hash`, or a `pending_activation`
  Account with one, is rejected. Disabling an unactivated Account may preserve
  `password_hash=null`.
- Non-normalized or empty `login_name` is rejected; two inputs that normalize
  to the same stored value conflict on the single unique lookup.
- Account deletion is rejected while membership/session rows reference it;
  disabling/revoking is the supported lifecycle path.
- More than one distinct pre-FT-002 `farm_id` in durable membership rows blocks
  the FT-002 migration; it must not create multiple Farm authorities or rewrite
  memberships silently.
- A migration/model containing raw session material, a cascading authority FK,
  duplicate token/login indexes, or an FT-001-created `farms` table violates
  this contract.

## Verification Target

- `TASK-005` model/migration tests inspect table/column names, native UUID and
  `timestamptz` types, nullability/defaults, named checks, FKs, uniqueness, and
  the exact index set.
- PostgreSQL integration tests prove UUID round-trip, normalized login conflict,
  invalid enum-like values rejected, active/pending password checks, required
  fields/timestamps, non-cascading Account relations, and no raw-token column.
- `TASK-005` tests explicitly prove `farm_memberships.farm_id` is UUID/non-null
  but has no FK and that no `farms` table is created by the FT-001 migration.
- FT-002 migration tests prove zero/one/multiple pre-existing distinct
  membership `farm_id` handling and successful final `RESTRICT` FK validation.
- `TASK-006` security tests prove Argon2id PHC and lowercase 64-character
  SHA-256 formats before values reach persistence.
