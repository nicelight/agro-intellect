---
description: Foundation runtime substrate contract for the verified FT-000 backend baseline.
status: active
owner: architecture
type: architecture
last_updated: 2026-06-26
source_of_truth:
  - .memory-bank/foundation.md
  - .memory-bank/architecture/system-architecture.md
  - backend/app/main.py
  - backend/app/config.py
  - backend/app/database.py
---
# Foundation Runtime Substrate

## Ownership

- Owns: executable FT-000 runtime shape, backend entrypoint, dependency direction, app factory boundary, settings/database injection, and smoke route mounting.
- Does not own: product route groups, auth/session behavior, Plant lifecycle, admin workflows, agent runtime, Safety Gate, UI Feed, or product domain schemas.
- Related specs:
  - [.memory-bank/contracts/foundation-smoke-api.md](../contracts/foundation-smoke-api.md): owns `/health` and `/ready` response contract.
  - [.memory-bank/domains/foundation-data-substrate.md](../domains/foundation-data-substrate.md): owns DB/session/Alembic/runtime-root substrate.
  - [.memory-bank/runbooks/foundation-local-runtime.md](../runbooks/foundation-local-runtime.md): owns local setup/start commands.

## Substrate Shape

- Primary backend entrypoint: `backend.app.main:create_app`.
- Default ASGI app: `backend.app.main:app`.
- `create_app` accepts optional `AppSettings`, optional `DatabaseHandle`, and `readiness_check_database`.
- The created FastAPI app stores resolved `settings`, `database`, and readiness mode in `app.state`.
- Foundation-owned routes are limited to `/health` and `/ready`.
- Product features must extend this substrate by adding owning route/module registration in their feature tasks; Foundation must not pre-implement product modules.

## Dependency Direction

- `backend.app.main` may depend on `backend.app.config` and `backend.app.database`.
- `backend.app.database` may depend on `backend.app.config`.
- Foundation redaction helpers live under `backend.app.core` and may be used by settings, scripts, or tests.
- Product feature modules may depend on the substrate helpers, but substrate modules must not import product feature modules.

## Rules

- Foundation MUST keep `/health` and `/ready` product-data-free.
- Foundation MUST support explicit settings/database injection for tests and future feature composition.
- Foundation MUST keep local-first defaults: loopback start path, PostgreSQL-ready DB handle, local runtime roots, and `local_only` sync status.
- Foundation MUST NOT create product tables, product routes, Product Agent behavior, UI Feed behavior, Safety Gate behavior, or domain records.
- Future product tasks that change the app factory or substrate helpers must preserve existing FT-000 smoke behavior or explicitly update this spec and related tests.

## Verification Target

- `.venv/bin/python -m pytest tests` proves import/start behavior, settings injection, `/health`, `/ready`, DB readiness mode, migration baseline, local runtime roots, and redaction helpers after local bootstrap.
- `.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000` remains the local backend start command after local bootstrap.

## Extension Route

- `/prd-to-tasks FT-<NNN>` may extend this owner only when a product feature needs to change app composition or shared substrate behavior.
- Product-specific route paths, schemas, migrations, state machines, and verification examples stay in feature-local specs.
