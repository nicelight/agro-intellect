---
description: Local Foundation runtime runbook for bootstrap, database init, migrations, start, and troubleshooting.
status: active
type: runbook
last_updated: 2026-06-30
source_of_truth:
  - .memory-bank/foundation.md
  - .memory-bank/architecture/foundation-runtime-substrate.md
  - .memory-bank/domains/foundation-data-substrate.md
  - .memory-bank/contracts/evidence-redaction.md
  - scripts/bootstrap-local.sh
  - scripts/db-init-local.sh
  - scripts/db-migrate-local.sh
---
# Foundation Local Runtime Runbook

## Scope

- Defines: local FT-000 setup/start/smoke command sequence and troubleshooting notes.
- Out of scope: production deployment, CI/CD, Docker path, hosted sync, product feature setup, or frontend/PWA runtime.
- Related specs:
  - [.memory-bank/architecture/foundation-runtime-substrate.md](../architecture/foundation-runtime-substrate.md): defines runtime shape.
  - [.memory-bank/domains/foundation-data-substrate.md](../domains/foundation-data-substrate.md): defines DB/session/migration substrate.
  - [.memory-bank/testing/foundation-test-harness.md](../testing/foundation-test-harness.md): defines test/evidence surface.

## Command Path

From the project root:

```bash
bash scripts/bootstrap-local.sh
bash scripts/db-init-local.sh
bash scripts/db-migrate-local.sh
.venv/bin/python -m pytest tests
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Smoke endpoints:

- `GET /health`
- `GET /ready`

Dry-run checks:

```bash
bash scripts/bootstrap-local.sh --dry-run
bash scripts/db-init-local.sh --dry-run
bash scripts/db-migrate-local.sh --dry-run
```

## Environment

- `.env.example` is the template.
- `.env` may be created locally by bootstrap and must not be printed.
- Required local dependency for DB setup: PostgreSQL client tools (`psql`, `pg_isready`).
- Default local runtime roots:
  - `data`
  - `data/artifacts`
  - `data/timeline`
  - `data/tmp`
  - `data/smoke`
- Default sync status: `local_only`.

## Rules

- Runbook output MUST preserve the redaction rules in [.memory-bank/contracts/evidence-redaction.md](../contracts/evidence-redaction.md).
- Foundation setup is local Linux Mint oriented and does not require Docker or hosted services.
- DB init supports only local PostgreSQL hosts for the Foundation path.
- Migration baseline proves Alembic command path and must not create product tables.
- Product features must extend this local path through their own tasks/specs rather than changing Foundation commands opportunistically.

## Troubleshooting

- Missing `python3`: install Python 3.11+ and rerun bootstrap.
- Missing PostgreSQL client tools: install `postgresql-client` before DB init.
- PostgreSQL not ready: start the local PostgreSQL service and rerun DB init.
- DB authentication failure: update local `.env` or local PostgreSQL role setup; do not paste credentials into reports.
- Migration failure: check local PostgreSQL service and `.env` values locally; reports must remain redacted.

## Verification Target

- Foundation is healthy when bootstrap, DB init, migration, tests, Memory Bank gates, and `/health`/`/ready` all pass with redacted evidence.
