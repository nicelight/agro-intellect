---
description: FT-000 Foundation Dev Path pseudo-feature.
status: active
type: feature
feature_id: FT-000
epic: Foundation
lifecycle: verified
owner: architecture
last_updated: 2026-06-25
source_of_truth:
  - .memory-bank/foundation.md
  - .memory-bank/requirements.md
  - .memory-bank/spec-backbone.md
  - .memory-bank/architecture/foundation-runtime-substrate.md
  - .memory-bank/domains/foundation-data-substrate.md
  - .memory-bank/contracts/foundation-smoke-api.md
  - .memory-bank/contracts/evidence-redaction.md
  - .memory-bank/testing/foundation-test-harness.md
  - .memory-bank/runbooks/foundation-local-runtime.md
  - .memory-bank/workflows/tier-policy.md
---
# FT-000 Foundation Dev Path

## Purpose

FT-000 is a reserved pseudo-feature for the executable foundation gate. It is
not a product feature and does not participate in product feature-completion
semantics.

## Use Cases

- Developer can bootstrap the local backend environment on Linux Mint.
- Developer can initialize or verify the local PostgreSQL database.
- Developer can run migrations, start the FastAPI app, and verify `/health` and
  `/ready`.
- Developer can run tests and Memory Bank gates before product feature tasking.
- Future product tasks can rely on one task-record format, backend package
  anchors, DB/session conventions, local runtime roots, and redaction baseline.

## Acceptance Criteria

- Task schema/protocol tooling accepts `TASK-<NNN>-T<N>-FT-<NNN>-W<N>` records,
  `tier`, optional `runtime_context`, and `FT-000/W0` semantics.
- Backend scaffold anchors exist for app factory, settings, database/session
  helpers, app factory extension point for future route registration, and tests
  proving import/start behavior; concrete product modules/packages belong to
  owning feature tasks.
- Linux Mint local bootstrap and PostgreSQL init paths are documented,
  idempotent, and redact secrets.
- Alembic migration baseline and DB readiness checks are executable.
- Local data/artifact roots exist with `local_only` defaults.
- Redaction helper/tests cover `.env`, tokens, passwords, DB URLs with
  credentials, and auth material.
- Final foundation gate task is indexed and `done` before product tasking.

## Edge Cases & Failure Modes

- Missing PostgreSQL tooling on Linux Mint must fail with actionable safe output.
- Bootstrap scripts must not print passwords, tokens, `.env` contents, or DB URLs
  with credentials.
- Foundation must not implement product auth/session, Plant lifecycle, admin
  workflow, agent runtime, Safety Gate, photo catalog, timeline taxonomy,
  dataset governance, or PWA UI behavior.
- Product tasks must not use `W0`.

## Verification Targets

- `bash scripts/bootstrap-local.sh`
- `.venv/bin/python -m pip install -e ".[test]"`
- `bash scripts/db-init-local.sh`
- `bash scripts/db-migrate-local.sh`
- `.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- `/health`, `/ready`, DB ping, migration status, rollback-safe test session,
  local data root availability.
- `.venv/bin/python -m pytest tests`
- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- `git diff --check`

## Normative Links

- [.memory-bank/foundation.md](../foundation.md): Foundation decision, work
  packages, pressure map, and exit criteria.
- [.memory-bank/workflows/tier-policy.md](../workflows/tier-policy.md): tier,
  protocol, single-card handoff, and FT-000 rules.
- [.memory-bank/schemas/task.schema.json](../schemas/task.schema.json): current
  task record schema.
- [.memory-bank/architecture/foundation-runtime-substrate.md](../architecture/foundation-runtime-substrate.md):
  Foundation runtime shape and app factory boundary.
- [.memory-bank/domains/foundation-data-substrate.md](../domains/foundation-data-substrate.md):
  DB/session/Alembic/runtime-root substrate.
- [.memory-bank/contracts/foundation-smoke-api.md](../contracts/foundation-smoke-api.md):
  `/health` and `/ready` contract.
- [.memory-bank/contracts/evidence-redaction.md](../contracts/evidence-redaction.md):
  Foundation evidence/log redaction contract.
- [.memory-bank/testing/strategy.md](../testing/strategy.md): global quality
  gates and risk-based verification policy.
- [.memory-bank/testing/foundation-test-harness.md](../testing/foundation-test-harness.md):
  Foundation harness, smoke targets, fixtures, and evidence requirements.
- [.memory-bank/runbooks/foundation-local-runtime.md](../runbooks/foundation-local-runtime.md):
  local setup/start/smoke runbook.
