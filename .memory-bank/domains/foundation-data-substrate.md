---
description: Foundation data substrate for DB handle, session lifetime, Alembic baseline, and local runtime roots.
status: active
owner: architecture
type: domain
last_updated: 2026-06-26
source_of_truth:
  - .memory-bank/foundation.md
  - .memory-bank/domains/runtime-data-model.md
  - backend/app/config.py
  - backend/app/database.py
  - backend/migrations/env.py
  - tests/backend/test_database_harness.py
  - tests/backend/test_foundation_database_contract.py
---
# Foundation Data Substrate

## Ownership

- Owns: FT-000 DB/session/Alembic/runtime-root substrate that product features build on.
- Does not own: product table schemas, product migrations, Account/Farm/Plant records, photo catalog rows, timeline taxonomy, or dataset fields.
- Related specs:
  - [.memory-bank/domains/runtime-data-model.md](runtime-data-model.md): owns global runtime authority and product data routing.
  - [.memory-bank/architecture/foundation-runtime-substrate.md](../architecture/foundation-runtime-substrate.md): owns app factory and runtime shape.
  - [.memory-bank/runbooks/foundation-local-runtime.md](../runbooks/foundation-local-runtime.md): owns local DB init/migration commands.

## Shape

Settings substrate:

- `DATABASE_URL`
- `DATABASE_ECHO`
- `DATABASE_POOL_PRE_PING`
- `LOCAL_DATA_ROOT`
- `LOCAL_ARTIFACT_ROOT`
- `LOCAL_TIMELINE_ROOT`
- `LOCAL_TEMP_ROOT`
- `LOCAL_SMOKE_ROOT`
- `SYNC_STATUS=local_only`

Database substrate:

- `DatabaseHandle.engine()` lazily builds a SQLAlchemy engine.
- `DatabaseHandle.session_factory()` creates non-autoflush, non-expiring sessions.
- `DatabaseHandle.session()` opens and closes an application session boundary.
- `DatabaseHandle.test_session()` wraps a connection transaction and rolls it back after the test.
- `DatabaseHandle.ping()` runs `SELECT 1`.
- `DatabaseHandle.dispose()` clears engine/session factory state.

Migration substrate:

- `backend.migrations.build_alembic_config()` builds an Alembic config from `AppSettings`.
- The Foundation migration baseline has no product metadata and does not create product tables.
- Product migrations belong to owning feature tasks.

## Rules

- PostgreSQL/read model remains the mutable runtime authority selected for product features, but FT-000 only proves the DB/session/migration substrate.
- Foundation MUST NOT create Account, Farm, Plant, task, photo, agent, Safety Gate, governance, dataset, or UI projection tables.
- Runtime roots are local filesystem paths and MUST keep `local_only` semantics.
- Test sessions MUST roll back state and must not leak product data assumptions into Foundation.
- Future product migrations must use this substrate instead of inventing a parallel DB/session/Alembic path.

## Edge Cases / Errors

- SQLite may be used in tests only when the tested boundary does not claim PostgreSQL product behavior.
- Local PostgreSQL setup failures must be redacted and actionable.
- Missing local runtime directories are created by bootstrap/runbook flow, not by product features guessing paths.

## Verification Target

- `tests/backend/test_database_harness.py` verifies DB handle/session and Alembic config builders.
- `tests/backend/test_foundation_database_contract.py` verifies DB readiness, redacted DB failures, Alembic baseline, and no product table creation.
- `tests/backend/test_foundation_bootstrap_contract.py` verifies local runtime root settings and `local_only`.
