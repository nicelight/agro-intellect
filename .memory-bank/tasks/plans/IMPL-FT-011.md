---
description: Implementation plan for FT-011 Plant State Trust And Hydroponics Advisor.
status: active
---
# IMPL-FT-011 Plant State Trust And Hydroponics Advisor

## Goals

- Implement Plant State trust mapping so agent hypotheses, memory, raw provider output,
  photo manifests, UI Feed, raw chat, and timeline replay cannot create confirmed
  Plant state.
- Implement Hydroponics Advisor missing/stale/conflict behavior over permission-scoped
  pH/EC, observation, photo, runtime state, and memory refs.
- Route physical-action-implying wording toward Safety Gate boundaries without
  creating `action_task`, approving action, or displaying immediate action wording.

## Constitution Check

- Aligns with Bounded Agent Autonomy, Human Gate for Physical Actions, local privacy,
  Spec Before Code, low-maintenance scope, and risk-based DoD.
- No conflict found with the Constitution.
- Tier policy: all slices are T3 because Plant-state confirmation, pH/EC freshness,
  advisor wording, Safety Gate routing, provider failure, and authorization boundaries
  are safety-sensitive.
- KISS boundary: first-demo trust/advisor behavior only; no crop-specific dosing
  engine, sensor runtime dependency, automated actuation, or full FT-012/FT-013
  Safety Gate/task-loop implementation.

## Source Artifacts

- .memory-bank/features/FT-011-plant-state-trust-and-hydroponics-advisor.md
- .memory-bank/tech-specs/FT-011-plant-state-trust-and-hydroponics-advisor.md
- .memory-bank/epics/EP-004-safety-gated-advisory-and-task-loop.md
- .memory-bank/requirements.md
- .tasks/SPEC-IMPROVE-REVIEW/final-report.md
- .tasks/SPEC-IMPROVE-REVIEW-FIXES/final-report.md

## Normative Inputs

- .memory-bank/invariants.md
- .memory-bank/contracts/agent-harness.md
- .memory-bank/contracts/message-envelope.md
- .memory-bank/contracts/agent-chat-bus.md
- .memory-bank/contracts/safety-gate.md
- .memory-bank/tech-specs/FT-004-authorized-plant-selector-and-daily-check-in.md
- .memory-bank/tech-specs/FT-005-photo-intake-catalog-and-capture-manifests.md
- .memory-bank/tech-specs/FT-006-runtime-plant-state-history-and-timeline-audit.md
- .memory-bank/tech-specs/FT-008-permission-aware-context-builder-and-agent-memory-record.md
- .memory-bank/tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md
- .memory-bank/tech-specs/FT-010-real-model-backed-product-agent-profiles.md
- .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
- .memory-bank/architecture/system-architecture.md
- .memory-bank/domains/runtime-data-model.md
- .memory-bank/states/core-lifecycles.md
- .memory-bank/testing/index.md
- agents-best-practices: model output is proposal/data; the harness validates,
  permission-checks, routes, records observations/traces, enforces stop/budget rules,
  handles provider failure, and proves behavior with realistic and adversarial evals.

## Constraints

- Plant State and Hydroponics Advisor consume only context-builder-provided,
  permission-scoped inputs.
- pH/EC analysis freshness follows the Safety Gate default of up to 24 hours unless a
  later active spec narrows it.
- pH/EC physical-action approval freshness follows the Safety Gate default of up to 2
  hours, but FT-011 only routes to Safety Gate and does not approve.
- Missing/stale/conflicting evidence creates clarify, task request, conflict, or safe
  non-action behavior instead of unsafe recommendation.
- Full Safety Gate decisions, human approval, `action_task` creation, and follow-up
  outcomes remain owned by FT-012 and FT-013.

## Invariants

- Agent hypotheses, AgentMemoryRecord, raw provider output, photo manifests, UI Feed,
  raw chat, and timeline replay cannot create confirmed Plant state.
- Consultant context cannot create domain task/recommendation/action records by
  default.
- Governance DecisionRecord cannot substitute for Safety Gate approval.
- No user-visible wording may imply immediate physical action before Safety Gate
  clearance and authorized human approval.
- No automated actuation command exists in the MVP path.

## Steps

1. Implement Plant State trust mapping and no-promotion rules for first-demo state
   values.
2. Implement pH/EC freshness, missing, stale, conflict, unauthorized, and archived-Plant
   advisor input classification.
3. Implement Hydroponics Advisor output adapter and clarify/measurement-task-request
   handoff without direct task creation.
4. Detect physical-action-implying advisor wording and route/block through Safety Gate
   boundary refs.
5. Build first-demo Plant State and Advisor UI/API visibility for trust labels and
   missing-data prompts.
6. Add integration, provider failure, Safety Gate boundary, UI smoke, and adversarial
   regression coverage.

## Expected Touched Files

- backend/app/runtime_state/*
- backend/app/plant_operations/*
- backend/app/agent_harness/*
- backend/app/advisory/*
- backend/app/safety/*
- backend/app/publication/*
- backend/app/access/*
- backend/app/privacy/*
- backend/app/db/migrations/*
- backend/app/api/*
- frontend/src/*
- backend/tests/runtime_state/*
- backend/tests/advisory/*
- backend/tests/agent_harness/*
- backend/tests/integration/*
- backend/tests/security/*
- frontend/tests/*
- .memory-bank/changelog.md

## Tests

- Unit: trust status transitions, no-promotion guards, freshness classification,
  missing/stale/conflict behavior, advisor output schema, physical-action wording
  detection, and Consultant write denial.
- Integration: authorized context-scoped Plant State/Advisor runs, raw provider output
  adaptation, MessageEnvelope/Bus/UI handoff, Safety Gate route/block refs, and
  missing-data measurement prompt handoff.
- Harness evals: missing pH, stale pH/EC, conflicting evidence, prompt injection in
  observation/photo text, provider failure, model suggests immediate action, governance
  approval substitution attempt, and no fake advisor success.
- UI/e2e: trust labels and missing-data prompt are visible enough for first demo.

## Quality Gates

- pytest backend/tests/advisory backend/tests/runtime_state backend/tests/agent_harness backend/tests/integration backend/tests/security
- Frontend/UI smoke or e2e evidence under the task report when a frontend test runner exists; otherwise record the missing-runner reason in /verify
- Harness eval fixture evidence through the task-specific pytest/eval suite and /red-verify semantic-pass
- generated OpenAPI validation after implementation schemas exist
- node scripts/mb-lint.mjs
- node scripts/mb-doctor.mjs
- /verify and /red-verify before T3 closure
- T3 human checkpoint and rollback/recovery note before closure

## UAT Steps

- Missing pH or EC produces a clear missing-data/measurement prompt, not an unsafe
  recommendation.
- Stale pH/EC may support cautious historical analysis only when labeled stale.
- Conflicting evidence appears as conflict with refs and asks for re-check/follow-up.
- Advisor output that implies pH/EC, dosing, solution, pump, light, watering, pruning,
  transplanting, or similar action is routed/blocked before action wording is shown.
- Plant card/history or advisor surface exposes confirmed/probable/unknown/conflict
  status enough for first-demo verification.

## Task Slice

- TASK-064: Plant State trust mapping and no-promotion rules.
- TASK-065: pH/EC freshness, missing, stale, and conflict advisor input classification.
- TASK-066: Hydroponics Advisor output adapter and clarify/task-request handoff.
- TASK-067: Physical-action wording detection and Safety Gate routing boundary.
- TASK-068: First-demo Plant State and Advisor UI/API visibility.
- TASK-069: Plant State/Advisor integration, provider failure, and safety regression suite.
