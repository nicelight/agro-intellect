---
description: Verification specification for Plant card/history projections, retained-history access, and timeline authority boundaries.
status: active
type: testing_spec
last_updated: 2026-07-10
source_of_truth:
  - .memory-bank/domains/plant-history.md
  - .memory-bank/contracts/plant-history-http.md
  - .memory-bank/testing/strategy.md
---
# Plant History Verification

## Scope

Defines deterministic evidence for FT-006 Plant card/history projections,
timeline-ref authority separation, and retained-history reads.

## Required evidence

- Service/projection tests for `PlantHistoryCard` and `PlantHistoryEntry`
  computed from PostgreSQL/read-model source rows.
- Authorization tests for active normal read and archived retained-history
  read across Boss, granted Engineer, granted Consultant, revoked grant,
  disabled membership, unauthorized Plant, and wrong Farm.
- Retention tests that archive a Plant after check-in, manual measurement,
  accepted photo, and Plant/admin audit rows exist, then prove authorized
  retained history remains readable and no state-advancing command is implied.
- Timeline consistency tests proving orphan timeline lines cannot create
  history entries and missing timeline lines cannot override PostgreSQL source
  rows.
- Pagination tests for newest-first ordering, stable cursor behavior, limits,
  and source-type filtering.
- API/OpenAPI tests for `/api/plants/{plant_id}/history/card` and
  `/api/plants/{plant_id}/history`.
- Redaction tests for response summaries, timeline refs, artifact refs, logs,
  exports, screenshots, and evidence.

## Anti-cheat checks

- Plant card latest values, counts, and status read PostgreSQL source rows, not
  `timeline.jsonl`, photo manifests, UI Feed, raw chat, or agent text.
- Timeline replay is audit/export only and cannot mutate or populate runtime
  Plant history.
- Archived retained-history read does not grant operate, task creation, action
  approval, agent publication, or governance transition authority.
- Future source families such as tasks, approvals, agent outputs, Companion,
  and dataset records are not faked before their owning feature schemas exist.
- Responses and evidence omit secrets/auth material, absolute paths, raw SQL,
  provider payloads, hidden reasoning, raw Companion proposal text, raw chat,
  and UI Feed content.

## Suggested gates

- `.venv/bin/python -m pytest tests/backend/plant_history`
- `.venv/bin/python -m pytest tests/backend/api -k ft006`
- `.venv/bin/python -m pytest tests`
- `node scripts/mb-lint.mjs`
- `git diff --check`
