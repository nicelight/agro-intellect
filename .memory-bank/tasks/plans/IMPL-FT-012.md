---
description: Implementation plan for FT-012 Safety Gate For Physical-Action Advice.
status: active
---
# IMPL-FT-012 Safety Gate For Physical-Action Advice

## Goals

- Convert physical-action-implying output into typed PhysicalActionProposal records
  before any Safety Gate decision.
- Evaluate fresh evidence, ActorContext, PlantAccessGrant, runtime state, and proposal
  scope through a fail-closed Safety Gate.
- Record SafetyGateDecision refs, structured observations, traces, and safe next
  actions without creating Approval records, action_task records, or device commands.
- Decide approver eligibility for Boss, Engineer with `plant_approve_actions`, and
  Consultant denial.
- Preserve safe MessageEnvelope/Bus/UI handoffs so no user-visible wording implies
  immediate physical action before clearance and authorized human approval.

## Constitution Check

- Aligns with Human Gate for Physical Actions, Bounded Agent Autonomy, Spec Before
  Code, low-maintenance MVP scope, and risk-based DoD.
- No conflict found with the Constitution.
- Tier policy: all slices are T3 because Safety Gate routing, authorization,
  approval eligibility, physical-action boundaries, traces, and no-actuation behavior
  are critical safety/security surfaces.
- KISS boundary: first-demo Safety Gate service and decision records only; no actuator
  integrations, sensor runtime dependency, dosing engine, or broad agronomy rule base.

## Source Artifacts

- .memory-bank/features/FT-012-safety-gate-for-physical-action-advice.md
- .memory-bank/tech-specs/FT-012-safety-gate-for-physical-action-advice.md
- .memory-bank/epics/EP-004-safety-gated-advisory-and-task-loop.md
- .memory-bank/requirements.md
- .tasks/SPEC-IMPROVE-REVIEW/final-report.md
- .tasks/SPEC-IMPROVE-REVIEW-FIXES/final-report.md

## Normative Inputs

- .memory-bank/constitution.md
- .memory-bank/invariants.md
- .memory-bank/contracts/safety-gate.md
- .memory-bank/contracts/agent-harness.md
- .memory-bank/contracts/message-envelope.md
- .memory-bank/contracts/agent-chat-bus.md
- .memory-bank/contracts/api-guidelines.md
- .memory-bank/states/core-lifecycles.md
- .memory-bank/testing/index.md
- .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
- .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
- .memory-bank/tech-specs/FT-006-runtime-plant-state-history-and-timeline-audit.md
- .memory-bank/tech-specs/FT-007-shared-agent-harness-and-agent-profile-runtime.md
- .memory-bank/tech-specs/FT-008-permission-aware-context-builder-and-agent-memory-record.md
- .memory-bank/tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md
- .memory-bank/tech-specs/FT-011-plant-state-trust-and-hydroponics-advisor.md
- .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
- agents-best-practices: typed proposals, strict tool schemas, draft/commit
  separation, runtime permission decisions, structured observations, traces/evals,
  budgets, and no automated actuation.

## Constraints

- PhysicalActionProposal creation does not create Approval, action_task, or device
  command records.
- Fresh data is required but never sufficient for physical action.
- pH/EC physical-action approval freshness is up to 2 hours.
- Missing, stale, conflicting, unauthorized, untrusted, redaction-failed, out-of-scope,
  malformed, over-budget, or uncertain evidence fails closed.
- Governance DecisionRecord, UI Feed, raw chat, AgentMemoryRecord, provider memory, and
  raw model output cannot substitute for Safety Gate approval.
- SafetyGateDecision `cleared_for_approval` is not human approval.

## Invariants

- The model never approves or executes physical actions.
- Physical-action advice must pass Safety Gate and authorized human approval before
  becoming cleared user-visible action wording or an action task.
- Consultant never approves physical actions in MVP.
- Human approval never authorizes automated device execution.
- No automated actuation command, tool, or side effect exists in the Safety Gate path.

## Steps

1. Implement PhysicalActionProposal schema, taxonomy classifier, and strict validation.
2. Implement Safety Gate input resolver for ActorContext, PlantAccessGrant, runtime
   evidence, pH/EC freshness, source refs, redaction, and trace refs.
3. Persist SafetyGateDecision records with fail-closed decisions, reason codes,
   structured observations, and trace/audit refs.
4. Implement approver eligibility and exact-proposal invalidation semantics.
5. Wire missing-data and cleared-for-approval handoffs to Bus/UI/FT-013 refs without
   creating action_task or device execution.
6. Add Safety Gate contract tests, harness evals, UI wording regressions, and
   no-actuation checks.

## Expected Touched Files

- backend/app/safety/*
- backend/app/agent_harness/*
- backend/app/advisory/*
- backend/app/runtime_state/*
- backend/app/plant_operations/*
- backend/app/publication/*
- backend/app/access/*
- backend/app/privacy/*
- backend/app/db/migrations/*
- backend/app/api/*
- frontend/src/*
- backend/tests/safety/*
- backend/tests/advisory/*
- backend/tests/agent_harness/*
- backend/tests/integration/*
- backend/tests/security/*
- frontend/tests/*
- .memory-bank/changelog.md

## Tests

- Unit: physical-action taxonomy, proposal schema validation, freshness classification,
  fail-closed reason mapping, eligibility matrix, exact-proposal invalidation, and
  safe wording rewrite/block behavior.
- Integration: advisor Safety Gate routing, SafetyGateDecision persistence, runtime
  evidence refs, Bus/UI handoff refs, ActorContext/PlantAccessGrant denial, redaction,
  and generated OpenAPI after schemas exist.
- Harness evals: approval bypass attempts, governance approval substitution, fresh data
  alone, stale pH/EC, unknown action category, malformed proposal, model suggests
  immediate action, provider/tool unavailable, budget stop, and prompt injection.
- Security/safety: no automated actuation command/tool/side effect exists.

## Quality Gates

- pytest backend/tests/safety backend/tests/advisory backend/tests/agent_harness backend/tests/integration backend/tests/security
- Frontend/UI smoke or e2e evidence under the task report when a frontend test runner exists; otherwise record the missing-runner reason in /verify
- Harness eval fixture evidence through the task-specific pytest/eval suite and /red-verify semantic-pass
- generated OpenAPI validation after implementation schemas exist
- node scripts/mb-lint.mjs
- node scripts/mb-doctor.mjs
- /verify and /red-verify before T3 closure
- T3 human checkpoint and rollback/recovery note before closure

## UAT Steps

- Advisor output implying pH/EC, dosing, solution, pump, light, watering, pruning,
  transplanting, root trimming, or unknown intervention routes through Safety Gate.
- Missing/stale/conflicting evidence shows a safe next action or measurement/check
  request instead of actionable wording.
- Boss is eligible only after Safety Gate clearance; Engineer needs
  `plant_approve_actions`; Consultant is denied.
- Governance DecisionRecord and UI Feed replay cannot substitute for Safety approval.
- No action_task or automated device command is created by FT-012.

## Task Slice

- TASK-070: PhysicalActionProposal schema and physical-action taxonomy classifier.
- TASK-071: Safety Gate input resolver and freshness/evidence policy.
- TASK-072: SafetyGateDecision persistence, fail-closed observations, and traces.
- TASK-073: Approver eligibility and exact-proposal invalidation.
- TASK-074: Safe missing-data and approval-path handoff without action unlock.
- TASK-075: Safety Gate regression, harness eval, UI wording, and no-actuation suite.
