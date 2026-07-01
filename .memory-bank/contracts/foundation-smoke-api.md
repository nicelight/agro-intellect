---
description: Foundation smoke API contract for /health and /ready.
status: active
type: contract
last_updated: 2026-06-30
source_of_truth:
  - .memory-bank/foundation.md
  - .memory-bank/contracts/api-guidelines.md
  - backend/app/main.py
  - tests/backend/test_baseline.py
  - tests/backend/test_foundation_database_contract.py
---
# Foundation Smoke API

## Contract Scope

- Defines: substrate-level `/health` and `/ready` route shape, status behavior, and redaction requirements.
- Out of scope: product endpoint paths, product auth/session routes, OpenAPI completeness, or feature-specific error catalogs.
- Related specs:
  - [.memory-bank/contracts/api-guidelines.md](api-guidelines.md): defines cross-cutting HTTP/API guardrails.
  - [.memory-bank/architecture/foundation-runtime-substrate.md](../architecture/foundation-runtime-substrate.md): defines app factory and route mounting.
  - [.memory-bank/domains/foundation-data-substrate.md](../domains/foundation-data-substrate.md): defines DB ping/session readiness substrate.

## Shape

`GET /health`

- Success status: `200`
- Response body:

```json
{"status": "ok"}
```

`GET /ready` with database readiness disabled

- Success status: `200`
- Response body:

```json
{"status": "ready"}
```

`GET /ready` with database readiness enabled and DB ping successful

- Success status: `200`
- Response body:

```json
{"status": "ready", "checks": {"database": "ok"}}
```

`GET /ready` with database readiness enabled and DB ping failed

- Failure status: `503`
- Response body:

```json
{"status": "not_ready", "checks": {"database": "failed"}}
```

## Rules

- `/health` and `/ready` are service endpoints and MUST NOT expose Farm/Plant data.
- `/ready` MAY check database connectivity only when the app is created with `readiness_check_database=true`.
- Readiness failure responses MUST NOT include exception text, database URLs, credentials, tokens, `.env` values, or auth material.
- Foundation smoke routes MUST stay stable enough for bootstrap, test harness, and local operator checks.
- Product feature routes MUST NOT redefine these routes or change their response contract without updating this spec and Foundation tests.

## Edge Cases / Errors

- Database ping failures return generic `database=failed`.
- Missing product schema/migrations MUST NOT make `/health` fail.
- Generated OpenAPI may expose these routes after implementation exists, but this file is the normative substrate contract.

## Verification Target

- `tests/backend/test_baseline.py` verifies `/health` and default `/ready`.
- `tests/backend/test_foundation_database_contract.py` verifies DB-readiness success, redacted failure response, and no secret leakage.
