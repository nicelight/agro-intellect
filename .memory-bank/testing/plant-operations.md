---
description: Verification specification for authorized check-ins, manual measurements, and freshness projections.
status: active
type: testing_spec
last_updated: 2026-07-12
source_of_truth:
  - .memory-bank/domains/plant-operations.md
  - .memory-bank/contracts/plant-operations-http.md
  - .memory-bank/testing/strategy.md
---
# Plant Operations Verification

## Scope

Defines deterministic evidence for FT-004 check-in and measurement behavior.

## Required evidence

- Migration/model tests for `daily_checkins` and `manual_measurements`.
- Service tests for authorized Boss/Engineer writes and Consultant,
  unauthorized, revoked-grant, disabled, and archived denial.
- Validation tests for observation states, non-blank observation text, pH range,
  EC non-negative, at-least-one measurement value, and timezone-aware timestamps.
- Freshness tests for 24h analysis and 2h approval-input windows, computed
  independently for pH and EC, with future-dated values explicitly stale.
- PostgreSQL-backed precision tests using excess-scale pH/EC input prove the
  immediate result, persisted row, later read/freshness projection, and
  timeline payload all use the same scale-2/scale-3 `ROUND_HALF_UP` values.
- Service and HTTP validation tests prove non-blank `observation_text` without
  `observation_state` returns `VALIDATION_FAILED` and creates no check-in,
  measurement, or timeline success event.
- Service, HTTP, and OpenAPI boundary tests prove normalized observation text
  lengths 1 and 2000 are accepted, 2001 returns
  `OBSERVATION_TEXT_TOO_LONG`, no write or timeline event occurs, and the
  backend never truncates or implicitly summarizes the value.
- Operator UI component/E2E coverage proves Unicode code-point counting, a
  visible used/remaining counter, prevention of entry/paste beyond 2000, and
  display of the authoritative backend rejection for a stale or bypassing
  client; this remains Operator UI ownership.
- Timeline-ref tests proving `daily_checkin_recorded` and
  `manual_measurement_recorded` refs are created through the timeline
  foundation and are not used as mutable authority.
- API/OpenAPI tests for every FT-004 route, response, no-store behavior, and
  stable error code.
- Integrated flow proving an Engineer with `tomato_001` access records an
  observation plus pH/EC check-in.

## Anti-cheat checks

- Latest/freshness projections read PostgreSQL measurement rows, not timeline,
  UI Feed, raw chat, photo manifests, or agent text.
- Missing data is represented explicitly and does not become invented
  evidence.
- Future-dated measurements are never fresh before `computed_at`.
- Timeline numeric summaries cannot preserve pre-normalized values that differ
  from the PostgreSQL row.
- Fresh pH/EC does not bypass Safety Gate or create a physical-action task.
- Archived Plant normal-operation writes leave no check-in, measurement, or
  timeline success event.

## Suggested gates

- `.venv/bin/python -m pytest tests/backend/plant_operations`
- `.venv/bin/python -m pytest tests/backend/api -k ft004`
- `.venv/bin/python -m pytest tests`
- `node scripts/mb-lint.mjs`
- `git diff --check`
