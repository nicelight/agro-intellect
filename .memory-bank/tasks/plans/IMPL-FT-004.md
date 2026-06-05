---
description: Implementation plan for FT-004 Authorized Plant Selector And Daily Check-In.
status: active
---
# IMPL-FT-004 Authorized Plant Selector And Daily Check-In

## Goals

- Implement authorized active Plant selector and actor/Farm/Plant-scoped CheckIn
  lifecycle.
- Capture observations, manual pH/EC measurements, no-data states, accepted photo refs,
  and workflow navigation refs for Plant card/history, tasks, approvals, and follow-up.
- Publish agent-consumable check-in evidence only through backend Bus boundaries after
  persistence and redaction.

## Constitution Check

- Aligns with Spec Before Code, backend authorization authority, risk-based DoD,
  bounded autonomy, and local-first scope.
- No conflict found with the Constitution.
- Tier policy: CheckIn domain foundation is T2; authorization, redaction-sensitive
  evidence, Bus publication, and UI flow slices are T3.
- KISS boundary: simple daily CheckIn lifecycle; no sensor runtime dependency, no
  automated actuation, no photo internals outside FT-005.

## Source Artifacts

- .memory-bank/features/FT-004-authorized-plant-selector-and-daily-check-in.md
- .memory-bank/tech-specs/FT-004-authorized-plant-selector-and-daily-check-in.md
- .memory-bank/epics/EP-002-plant-evidence-and-runtime-authority.md
- .memory-bank/requirements.md
- .tasks/SPEC-IMPROVE-REVIEW/final-report.md

## Normative Inputs

- .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
- .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
- .memory-bank/tech-specs/FT-005-photo-intake-catalog-and-capture-manifests.md
- .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
- .memory-bank/architecture/system-architecture.md
- .memory-bank/domains/runtime-data-model.md
- .memory-bank/states/core-lifecycles.md
- .memory-bank/contracts/api-guidelines.md
- .memory-bank/contracts/agent-chat-bus.md
- .memory-bank/testing/index.md
- agents-best-practices: user-entered observations are untrusted data; model/context
  access is backend-owned; Bus publication uses bounded refs, trust/freshness labels,
  permission filtering, and redacted trace/evidence refs.

## Constraints

- PostgreSQL/read model owns authorized Plant lists, CheckIn, observations, manual
  measurements, and current operational refs.
- Selector includes only authorized active Plants; archived Plants are excluded from
  normal operations.
- Consultant access is read/comment/advisory only and cannot start operational
  mutations in MVP.
- Bus publication happens after persistence and redaction, never from UI Feed text,
  admin notices, raw chat, hidden reasoning, secrets, or unauthorized Plant data.

## Invariants

- Every CheckIn, observation, measurement, and ref is actor/Farm/Plant scoped.
- Missing pH/EC is explicit for downstream advisor/safety behavior.
- Timeline/photo artifacts cannot overwrite runtime authority.
- Backend authorization rejects data submission for Plants absent from ActorContext.

## Steps

1. Build CheckIn persistence, lifecycle states, and command schemas.
2. Add authorized active Plant selector and CheckIn command authorization.
3. Add observation and manual pH/EC/no-data records with trust/freshness metadata.
4. Add accepted photo-ref attachment contract and CheckIn entrypoint for FT-005.
5. Add backend Bus publication triggers for persisted evidence refs.
6. Add daily operations UI and integration/e2e coverage.

## Expected Touched Files

- backend/app/plant_operations/*
- backend/app/plants/*
- backend/app/access/*
- backend/app/publication/*
- backend/app/db/migrations/*
- backend/app/api/*
- frontend/src/*
- backend/tests/plant_operations/*
- backend/tests/integration/*
- frontend/tests/*
- .memory-bank/changelog.md

## Tests

- Unit: CheckIn lifecycle transitions, duplicate/open-window policy, observation and
  measurement schema validation, freshness/no-data projection.
- Integration: selector exclusions, missing/revoked grant denial, archived Plant
  denial, Consultant mutation denial, actor/Farm/Plant scoping.
- Contract: generated OpenAPI validation and BusEventEnvelope validation for published
  refs.
- UI/e2e: Boss and authorized Engineer complete first `tomato_001` check-in flow.
- Security/context: UI Feed/admin text/raw chat/secrets cannot enter Bus or agent
  context through check-in flow.

## Quality Gates

- pytest backend/tests/plant_operations backend/tests/integration
- Frontend/UI smoke or e2e evidence under the task report when a frontend test runner exists; otherwise record the missing-runner reason in /verify
- generated OpenAPI validation after implementation schemas exist
- Bus/event contract tests for persisted refs and redaction
- node scripts/mb-lint.mjs
- node scripts/mb-doctor.mjs
- /verify and /red-verify for T2/T3 closure
- T3 human checkpoint and rollback/recovery note for authorization/publication tasks

## UAT Steps

- Boss and authorized Engineer see only active authorized Plants and complete a
  `tomato_001` check-in.
- Unauthorized user, revoked grant, disabled membership, archived Plant, and
  Consultant mutation attempts fail closed.
- Missing pH/EC is visible as no-data/unknown rather than silently omitted.
- Check-in evidence publishes only safe refs after persistence.

## Task Slice

- TASK-023: CheckIn persistence, lifecycle, and command schema foundation.
- TASK-024: Authorized active Plant selector and CheckIn command authorization.
- TASK-025: Observation and manual pH/EC/no-data evidence records.
- TASK-026: Photo-ref attachment entrypoint and CheckIn ref contract.
- TASK-027: Backend Bus publication triggers for persisted CheckIn evidence.
- TASK-028: Daily operations UI and integration/e2e coverage.

