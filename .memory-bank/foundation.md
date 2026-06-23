---
description: Foundation Dev Path evidence and feature pressure map.
status: active
owner: architecture
last_updated: 2026-06-23
source_of_truth:
  - .memory-bank/spec-backbone.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/testing/index.md
  - .memory-bank/workflows/tier-policy.md
  - .memory-bank/schemas/task.schema.json
---
# Foundation Dev Path

## Gate Anchors
- Foundation Required: true
- Foundation Requirement: REQ-000
- Foundation Pseudo-Feature: FT-000
- Foundation Gate Task: TASK-004-FT-000-W-0

## Decision

Foundation is required before product feature tasking.

Reason: the current backend scaffold proves basic FastAPI app creation, settings,
SQLAlchemy handle, Alembic config construction, and pytest fixtures. Product
feature work still needs a shared executable baseline for task record shape,
backend package layout, Windows-local bootstrap, PostgreSQL database creation,
migration execution, DB readiness, transaction boundaries, local artifact roots,
and redaction defaults. Without those anchors, FT-001..FT-003 can still interpret
session tables, migrations, bootstrap steps, and local runtime paths differently.

This Foundation intentionally does not restore the old broad critical path
through Bus -> Agent -> Message/UI -> Safety -> timeline/photo export. Those
contracts remain global or feature-local specs. Foundation implements only the
minimum shared platform primitives that product features may build on.

`REQ-000`, `FT-000`, task records, packets, protocols, and implementation plans
were created by `/foundation-to-tasks`. The final foundation gate is
`TASK-004-FT-000-W-0`.

## Minimal Work Path
- Build command: `python -m pip install -e ".[test]"`
- Windows bootstrap command: `powershell -ExecutionPolicy Bypass -File scripts/bootstrap-local.ps1`
- Database init command: `powershell -ExecutionPolicy Bypass -File scripts/db-init-local.ps1`
- Migration command: `powershell -ExecutionPolicy Bypass -File scripts/db-migrate-local.ps1`
- Start command: `python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Primary entrypoint: `backend.app.main:create_app`
- Smoke path: `/health`, `/ready`, DB ping, migration status, rollback-safe test session, local data root availability.
- Test command: `python -m pytest tests`
- Memory Bank gates: `node scripts/mb-lint.mjs`, `node scripts/mb-doctor.mjs`
- Evidence: command output, pytest output, DB init/migration transcript with secrets redacted, and final foundation gate task report under `.tasks/`.

## Foundation Work Packages

`/foundation-to-tasks` should create the smallest FT-000 queue that implements
or verifies these packages.

| Package | Required outcome | Product boundary |
|---|---|---|
| Task schema/protocol alignment | `task.schema.json`, `mb-lint`, and `mb-doctor` agree on `TASK-<NNN>-FT-<NNN>-W-<N>`, `tier`, optional `runtime_context`, and `FT-000/W0` semantics. | Does not create product tasks. |
| Backend scaffold anchors | Backend has stable app factory, settings, route include pattern, bounded-context package anchors, and tests proving import/start behavior. | Does not implement auth/session, Plant lifecycle, admin UI, agents, or safety behavior. |
| Windows local bootstrap | PowerShell bootstrap sets up `.venv`, installs project/test deps, prepares `.env` from `.env.example` without printing secrets, and verifies Python/PostgreSQL tooling. | Does not require Docker or hosted services. |
| Local PostgreSQL init | PowerShell DB init creates or verifies local database/user for `DATABASE_URL` on Windows 10, with idempotent behavior and redacted output. | Does not create product domain rows. |
| Migration baseline | Alembic command path can run against local PostgreSQL and test SQLite where appropriate; migration status is inspectable. | Product tables belong to feature tasks. |
| DB session/UoW baseline | Shared engine/session/test-session dependency is available and documented; `/ready` proves DB connectivity when configured. | Does not define product repositories beyond interfaces/helpers. |
| Local runtime roots | Settings define local data/artifact root, timeline root placeholder, and temp/smoke paths with `local_only` defaults. | Does not implement photo catalog, timeline event taxonomy, or dataset export. |
| Redaction baseline | Shared redaction helper/test prevents `.env`, tokens, passwords, DB URLs with credentials, and auth material from leaking in logs/errors/bootstrap evidence. | Does not replace feature-specific redaction tests. |
| Final foundation gate | One final FT-000 gate verifies build/start/bootstrap/db/migrate/test/mb-gates on the local-first path. | Product tasking remains blocked until this gate is `done`. |

## Feature Pressure Map

| Feature | Pressure | Foundation Response | Probe | Status |
|---|---|---|---|---|
| FT-001 | Accounts/sessions need stable table/migration/session conventions before implementation. | Provide DB session/UoW, migration baseline, settings, redaction helper, and access-admin package anchor. | FT-001 task can add tables without inventing bootstrap or session infrastructure. | planned |
| FT-002 | Farm/Plant lifecycle needs the same PostgreSQL/Alembic path and package layout. | Provide migration command path and runtime-state/access package anchors. | FT-002 task can add Plant tables and seeds through the common migration path. | planned |
| FT-003 | Boss admin/audit needs safe bootstrap, redaction, and route/module conventions. | Provide admin package anchor, route include pattern, redacted error/bootstrap evidence. | Admin task uses the shared app factory and audit persistence path. | planned |
| FT-004 | Daily check-in needs local runtime DB/session path. | Provide DB readiness and transaction-test baseline only. | Feature owns check-in schema and API. | planned |
| FT-005 | Photo intake needs local artifact root conventions. | Provide settings for local data/artifact roots only. | Feature owns photo storage layout, catalog, manifests, and checksums. | planned |
| FT-006 | Runtime state/timeline needs clear authority boundaries. | Provide PostgreSQL as runtime authority and timeline root placeholder. | Feature owns timeline event taxonomy and history projections. | planned |
| FT-007 | Agent runtime needs package and settings boundaries. | Provide agent-runtime package anchor and redaction baseline. | Feature owns real model adapter/runtime decisions. | planned |
| FT-008 | Bus/UI split needs package boundaries, not implementation here. | Provide package anchors only; global contracts remain authoritative. | Feature owns Bus/UI schema and context filtering. | planned |
| FT-009 | Vision path needs artifact root and agent-runtime anchor. | Provide storage/settings anchor only. | Feature owns real vision integration. | planned |
| FT-010 | Advisor needs agent-runtime package and redaction defaults. | Provide package/settings anchor only. | Feature owns missing-data policy and Safety Gate handoff. | planned |
| FT-011 | Safety Gate needs package boundary and fail-closed defaults. | Provide safety package anchor only. | Feature owns action taxonomy and approval routing. | planned |
| FT-012 | Tasks/outcomes need DB/migration/session path. | Provide DB/UoW baseline only. | Feature owns task/approval/outcome states. | planned |
| FT-013 | Companion governance needs DB/migration and package anchor. | Provide governance package anchor only if task slicing needs it. | Feature owns proposal/decision state machine. | planned |
| FT-014 | Dataset governance needs local roots and redaction defaults. | Provide local data root and `local_only` settings. | Feature owns dataset lifecycle and trainability. | planned |
| FT-015 | Local security/storage depends on bootstrap and redaction. | Provide Windows bootstrap, local-only settings, and redaction baseline. | Feature owns LAN/storage prompt policy. | planned |
| FT-016 | PWA first demo depends on backend being startable. | Provide backend start/readiness path only. | Feature owns UI route/view implementation. | planned |

## Deferred Decisions

| Decision | Why deferred | Trigger to revisit |
|---|---|---|
| Product auth/session schema | FT-001 already owns exact local account/session lifecycle and route contracts. | `/prd-to-tasks FT-001`. |
| Single Farm and `tomato_001` seed implementation | FT-002 owns product seed semantics. Foundation only proves DB/migration capability. | `/prd-to-tasks FT-002`. |
| Admin invite/audit tables | FT-003 owns admin domain records and audit semantics. | `/prd-to-tasks FT-003`. |
| Photo catalog/timeline/export schemas | These are product features, not bootstrap primitives. | `/spec-improve` or `/prd-to-tasks FT-005/FT-006`. |
| Agent/provider configuration | MVP runtime requires real model-backed flows, but provider secrets/config must not be invented in Foundation. | `/prd-to-tasks FT-007` or explicit provider decision. |
| Frontend scaffold | Backend/local DB foundation is the immediate blocker; UI belongs to FT-016. | `/prd-to-tasks FT-016`. |
| Docker-based database path | User target is local Windows 10. Docker may be optional later, not required by Foundation. | Explicit operator request or deployment spec update. |

## Foundation Exit Criteria

- Task schema/protocol tooling accepts current `TASK-<NNN>-FT-<NNN>-W-<N>` records and `FT-000/W0` semantics.
- Windows bootstrap command is documented, idempotent, and redacts secrets.
- Local PostgreSQL database init and migration commands run or fail with actionable safe errors.
- App starts locally on loopback and `/health` plus `/ready` pass with configured DB readiness.
- DB session and rollback-safe test session are proven by tests.
- Local data/artifact root settings exist with `local_only` default semantics.
- Redaction helper/tests cover `.env`, tokens, passwords, DB URLs with credentials, and auth material.
- `python -m pytest tests` passes.
- `node scripts/mb-lint.mjs`, `node scripts/mb-doctor.mjs`, and `git diff --check` pass after `/foundation-to-tasks`.
- Final foundation gate task `TASK-004-FT-000-W-0` is `done`.
- No product feature task is generated or executed until the final FT-000 gate is done.
