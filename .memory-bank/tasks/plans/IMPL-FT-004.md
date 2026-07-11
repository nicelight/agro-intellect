---
description: Implementation plan for FT-004 Authorized Plant Operations and Daily Check-In.
status: active
type: implementation_plan
feature_id: FT-004
last_updated: 2026-07-11
source_of_truth:
  - .memory-bank/features/FT-004-authorized-plant-operations-daily-check-in.md
  - .memory-bank/domains/plant-operations.md
  - .memory-bank/contracts/plant-operations-http.md
  - .memory-bank/testing/plant-operations.md
---
# IMPL FT-004 Authorized Plant Operations And Daily Check-In

## Goal

Implement backend authorized daily check-ins, observations, manual pH/EC
measurements, freshness projections, and operations HTTP routes.

## Scope

- Add Plant operations persistence/service for check-ins and measurements.
- Enforce ActorContext operate authorization and archived-Plant deny.
- Compute pH/EC freshness from PostgreSQL/read model.
- Emit required audit refs through the global Timeline Event boundary.
- Expose protected operations HTTP routes and OpenAPI coverage.

## Non-goals

- Photo file upload and catalog storage; FT-005 owns it.
- Plant history/timeline presentation.
- Agent output, Safety Gate, action tasks, follow-up, and PWA UI.

## Constitution Check

- Spec Before Code: tasks derive from FT-004 and linked canonical specs.
- KISS: preserve the two completed implementation tasks and add one cohesive
  repair task for the feature-level findings; no generic workflow engine.
- Safety/authority: fresh pH/EC is evidence only; it never unlocks physical
  actions without Safety Gate and human approval.
- Security: T3 because writes are Plant-scoped, authorization-sensitive, and
  feed future Safety Gate decisions.
- Blockers: none.

## Direct Canonical Design Links

- `.memory-bank/domains/plant-operations.md`
- `.memory-bank/contracts/plant-operations-http.md`
- `.memory-bank/contracts/timeline-event.md`
- `.memory-bank/contracts/access/actor-context.md`
- `.memory-bank/states/plants/plant-and-access-lifecycle.md`
- `.memory-bank/states/plant-state-trust.md`
- `.memory-bank/testing/plant-operations.md`

## Dependencies

- Completed FT-001..FT-003 provide sessions, ActorContext, Plant access,
  canonical Farm/Plant bootstrap, Boss/Engineer setup, and admin evidence.

## Ordered Implementation Strategy

### W1 - Persistence And Service

`TASK-019-T3-FT-004-W1` implements DB models/migration, operations service,
validation, authorization, freshness projection, and timeline refs.

### W2 - HTTP And Integrated Evidence

`TASK-020-T3-FT-004-W2` implements protected API routes/OpenAPI, focused
integration flow, behavior-spec traceability, and durable FT-004 docs sync.

### W3 - Authority And Evidence Semantics Repair

`TASK-025-T3-FT-004-W3` repairs the three feature-level semantic failures in
one service/API/test slice: canonical pH/EC normalization across PostgreSQL,
responses, projections, and timeline summaries; future-dated evidence staying
stale; and rejection of observation text without explicit state. It depends
on the completed W2 feature boundary and does not rewrite historical tasks.

## Expected Touched Areas

- `backend/app/plant_operations/`
- `backend/app/api/operations.py`
- `backend/app/api/__init__.py`
- `backend/app/main.py`
- `backend/migrations/versions/`
- `tests/backend/plant_operations/`
- `tests/backend/api/`
- FT-004 protocol/evidence and Memory Bank docs during execution.

## Verification Strategy

- Focused model/service/API tests for FT-004.
- Regression tests for existing auth, Plant access, and admin routes.
- Full test suite when practical.
- `node scripts/mb-lint.mjs` and `git diff --check`.
- PostgreSQL probe comparing accepted excess-scale input across immediate
  response, timeline payload, stored row, and later read.
- Service/HTTP probes for future-dated freshness and observation text without
  state, including zero-write/zero-event evidence for the rejected check-in.

## UAT

1. Bootstrap Farm, first Boss, and one Engineer with `tomato_001` access.
2. Engineer logs in and creates a check-in with observation plus pH/EC.
3. Latest measurement projection reports fresh pH/EC.
4. Archived or unauthorized Plant check-in fails without writes.
5. Excess-scale values agree across response, PostgreSQL, timeline, and later
   reads; future-dated values remain stale; observation text without state is
   rejected and preserved nowhere as a false `no_observation_provided` event.

## Repair Evidence Basis

- `.tasks/FT-004/FT-004-S-RED-VERIFY-final-report-docs-01.md`
- Existing `TASK-019` and `TASK-020` records remain `done` historical evidence.
