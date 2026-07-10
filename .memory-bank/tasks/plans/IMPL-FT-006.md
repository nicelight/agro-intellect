---
description: Implementation plan for FT-006 Runtime State Timeline and Plant History.
status: active
type: implementation_plan
feature_id: FT-006
last_updated: 2026-07-10
source_of_truth:
  - .memory-bank/features/FT-006-runtime-state-timeline-plant-history.md
  - .memory-bank/domains/plant-history.md
  - .memory-bank/contracts/plant-history-http.md
  - .memory-bank/testing/plant-history.md
---
# IMPL FT-006 Runtime State Timeline And Plant History

## Goal

Implement backend Plant card/history projections that preserve PostgreSQL/read
model authority, expose timeline refs as audit/export evidence only, and keep
archived Plant retained history accessible to authorized actors.

## Scope

- Add Plant history projection service over existing authoritative rows.
- Enforce active normal-read and archived retained-history authorization.
- Return safe check-in, measurement, photo, lifecycle/admin audit, and
  timeline refs.
- Expose protected Plant history card/list HTTP routes and OpenAPI coverage.
- Prove timeline replay cannot create or mutate runtime history.

## Non-goals

- Plant operations writes, photo upload, raw timeline export package, PWA UI,
  Vision processing, agent publication, Safety Gate, task/follow-up, Companion,
  dataset, or generic event-sourcing infrastructure.

## Constitution Check

- Spec Before Code: tasks derive from FT-006 and linked canonical specs.
- KISS: compute projections from source rows; no new history table or event
  sourcing.
- Safety/authority: history reads never grant state-advancing authority and
  timeline refs never become runtime authority.
- Security: T3 because retained-history reads and source refs are
  authorization-sensitive and cross multiple runtime records.
- Blockers: none.

## Direct Canonical Design Links

- `.memory-bank/domains/plant-history.md`
- `.memory-bank/contracts/plant-history-http.md`
- `.memory-bank/contracts/timeline-event.md`
- `.memory-bank/contracts/access/actor-context.md`
- `.memory-bank/states/plants/plant-and-access-lifecycle.md`
- `.memory-bank/domains/plant-operations.md`
- `.memory-bank/domains/photo-artifacts.md`
- `.memory-bank/domains/admin/admin-audit.md`
- `.memory-bank/testing/plant-history.md`

## Dependencies

- `TASK-021-T3-FT-005-W1` provides photo catalog/artifact source rows.
- `TASK-022-T3-FT-005-W2` provides integrated operations/photo HTTP evidence
  used by the final FT-006 API flow.

## Ordered Implementation Strategy

### W1 - Projection Service And Authority Checks

`TASK-023-T3-FT-006-W1` implements Plant history service/query helpers,
projection shapes, retained-history authorization, pagination core, timeline
consistency checks, and focused service tests.

### W2 - HTTP And Integrated Evidence

`TASK-024-T3-FT-006-W2` implements protected history/card HTTP routes, OpenAPI
tests, integrated active/archive retained-history flow, behavior-spec
traceability, and durable FT-006 docs sync.

## Expected Touched Areas

- `backend/app/plant_history/`
- `backend/app/api/history.py`
- `backend/app/api/__init__.py`
- `backend/app/main.py`
- `tests/backend/plant_history/`
- `tests/backend/api/`
- FT-006 protocol/evidence and Memory Bank docs during execution.

## Verification Strategy

- Focused projection/authorization/timeline-consistency tests for FT-006.
- API/OpenAPI tests for history card/list routes.
- Regression tests for auth, Plant access, operations, photo, and admin routes.
- Full test suite when practical.
- `node scripts/mb-lint.mjs` and `git diff --check`.

## UAT

1. Boss or granted Engineer creates check-in, pH/EC measurement, and accepted
   photo for `tomato_001`.
2. Authorized user opens Plant history and sees safe source refs, artifact
   refs, and timeline refs derived from PostgreSQL/read model.
3. Boss archives the Plant and can still read retained history.
4. Archived history read does not enable check-in, upload, task, approval,
   agent publication, or governance transitions.
