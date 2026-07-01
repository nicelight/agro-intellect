---
description: Foundation test harness and evidence contract for the verified FT-000 baseline.
status: active
type: testing
last_updated: 2026-06-30
source_of_truth:
  - .memory-bank/foundation.md
  - .memory-bank/testing/index.md
  - .memory-bank/contracts/evidence-redaction.md
  - tests/backend/
---
# Foundation Test Harness

## Scope

- Defines: FT-000 test command, smoke targets, fixture expectations, and evidence requirements.
- Out of scope: product feature test matrices, UI e2e flows, real model-provider evals, or feature-specific contract tests.
- Related specs:
  - [.memory-bank/contracts/foundation-smoke-api.md](../contracts/foundation-smoke-api.md): defines `/health` and `/ready`.
  - [.memory-bank/domains/foundation-data-substrate.md](../domains/foundation-data-substrate.md): defines DB/session/Alembic substrate.
  - [.memory-bank/contracts/evidence-redaction.md](../contracts/evidence-redaction.md): defines evidence redaction.

## Harness Shape

- Test command after local bootstrap: `.venv/bin/python -m pytest tests`.
- Memory Bank gates: `node scripts/mb-lint.mjs`, `node scripts/mb-doctor.mjs`.
- Diff hygiene: `git diff --check`.
- Smoke path: import app package, create app, call `/health`, call `/ready`, exercise DB readiness mode, verify Alembic baseline, verify local runtime roots, verify redaction.
- Test fixtures may use SQLite for Foundation DB harness behavior when they do not claim PostgreSQL product semantics.

## Rules

- Foundation tests MUST prove the executable substrate only.
- Foundation tests MUST NOT assert product Account/Farm/Plant/task/photo/agent/safety/governance table or route behavior.
- Foundation tests MUST check redaction for command output, unsupported arguments, DB URLs, auth material, and `.env` handling.
- Product feature tests may depend on this harness but must add their own feature-local unit/integration/e2e coverage.

## Evidence Required

- pytest command and result;
- local bootstrap dry-run or command transcript with redaction;
- DB init/migration dry-run or command transcript with redaction;
- `/health` and `/ready` smoke result;
- Memory Bank gate outputs;
- final Foundation gate report path when closing FT-000 work.

## Verification Target

- Existing `tests/backend/test_*` Foundation tests cover app import/start, settings, DB harness, Alembic baseline, bootstrap scripts, DB scripts, and redaction helpers.
- Any future change to FT-000 substrate must update tests before claiming Foundation remains verified.
