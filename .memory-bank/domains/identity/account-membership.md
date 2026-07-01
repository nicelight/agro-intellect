---
description: Account and FarmMembership relational storage, constraints, indexes, and deferred Farm relation.
status: active
type: data_spec
last_updated: 2026-06-30
source_of_truth:
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/domains/foundation-data-substrate.md
---
# Account And FarmMembership Storage

## Scope

Defines the exact PostgreSQL shape, constraints, indexes, initial migration,
and deferred Farm FK boundary for `Account` and `FarmMembership`.

## Out of scope

Session persistence, credential/token algorithms, HTTP transport, Farm/Plant
lifecycle, Boss account-creation service, and admin audit records.

## Shape

- `accounts`:
  - `account_id`: native PostgreSQL `uuid`, primary key, non-null, application
    default `uuid.uuid4`.
  - `login_name`: `text`, non-null, canonical normalized value only.
  - `display_name`: `text`, non-null.
  - `account_status`: `varchar(32)`, non-null.
  - `password_hash`: unbounded `text`, non-null.
  - `created_at`, `updated_at`: `timestamptz`, non-null, server default `now()`.
  - `disabled_at`: nullable `timestamptz`.
- `farm_memberships`:
  - `membership_id`: native PostgreSQL `uuid`, primary key, non-null,
    application default `uuid.uuid4`.
  - `account_id`, `farm_id`: native PostgreSQL `uuid`, non-null.
  - `role_preset`: `varchar(16)`, non-null.
  - `membership_status`: `varchar(16)`, non-null.
  - `created_at`, `updated_at`: `timestamptz`, non-null, server default `now()`.
  - `disabled_at`: nullable `timestamptz`.

## Rules

- SQLAlchemy maps UUID columns as Python `uuid.UUID` with `Uuid(as_uuid=True)`;
  identifiers are application-generated with `uuid.uuid4`.
- Use string columns plus named DB checks, not PostgreSQL ENUM:
  - `account_status IN ('active', 'disabled')`;
  - `membership_status IN ('active', 'disabled')`;
  - `role_preset IN ('boss', 'engineer', 'consultant')`.
- Every Account has a non-null password hash. PHC validation and Argon2id
  hashing belong to the session-security boundary, not a DB prefix check.
- Canonicalize login input with `strip().lower()` before persistence. A named
  DB check requires `login_name = lower(btrim(login_name))` and non-empty;
  exactly one unique B-tree lookup covers stored `login_name`.
- Services update `updated_at`; no DB trigger is introduced.
- `farm_memberships.account_id -> accounts.account_id` uses `ON DELETE
  RESTRICT`. Authority relations never cascade delete.
- The first identity migration creates non-null UUID `farm_id` without a Farm
  FK and must not create `farms`. Before the Farm spec closes this relation, no
  released path may create durable memberships; rollback-scoped fixtures may.
- A later full FT-002 design must define and verify the final Farm relation
  before product membership writes are enabled. FT-001 does not select its
  migration/reconciliation algorithm.
- Required indexes are exactly one unique normalized account login lookup and
  one unique `farm_memberships(account_id, farm_id)` lookup. Do not add
  duplicate indexes with the same leading columns.

## Edge cases and errors

- DB checks reject invalid statuses/roles and null credentials.
- Non-normalized/empty login is rejected; normalized duplicates conflict.
- Account deletion is rejected while memberships reference it; disable is the
  supported lifecycle path.
- FT-001 must not silently create a Farm or infer a final Farm migration.

## Verification

- Model/migration inspection covers native UUID, `timestamptz`, exact
  nullability/defaults, checks, `RESTRICT` Account FK, uniqueness, and indexes.
- PostgreSQL tests prove UUID round-trip, login conflicts, invalid values,
  required password hash, non-cascading relations, and deferred Farm FK
  absence.
- Full Farm migration and final FK verification are deferred to FT-002.

## Related specs

- [.memory-bank/domains/runtime-data-model.md](../runtime-data-model.md)
- [.memory-bank/domains/foundation-data-substrate.md](../foundation-data-substrate.md)
- [.memory-bank/domains/auth/session-storage.md](../auth/session-storage.md)
- [.memory-bank/domains/farm/farm-plant-access-storage.md](../farm/farm-plant-access-storage.md)
- [.memory-bank/contracts/auth/session-security.md](../../contracts/auth/session-security.md)
