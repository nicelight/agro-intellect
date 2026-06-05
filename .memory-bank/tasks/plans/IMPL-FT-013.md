---
description: Implementation plan for FT-013 Tasks, Approvals, And Follow-Up Outcomes.
status: active
---
# IMPL-FT-013 Tasks, Approvals, And Follow-Up Outcomes

## Goals

- Implement actor/Farm/Plant-scoped check_task, measurement_task, follow_up_task, and
  action_task records with task lifecycle guardrails.
- Implement Approval request/result records from current FT-012 SafetyGateDecision
  clearance and exact PhysicalActionProposal scope.
- Create human-performed action_task records only after Safety Gate clearance and
  authorized human approval.
- Record follow-up Outcomes with evidence refs and explicit improved, worsened,
  unchanged, no_data, conflict, and superseded semantics.
- Publish Bus/UI/timeline/history refs only after authoritative persistence, while
  preserving no-actuation and redaction boundaries.

## Constitution Check

- Aligns with Human Gate for Physical Actions, Bounded Agent Autonomy, Spec Before
  Code, Schema-Backed Task Execution, and risk-based DoD.
- No conflict found with the Constitution.
- Tier policy: all slices are T3 because task/approval/outcome mutations cross
  authorization, safety approval, audit, publication, and no-actuation boundaries.
- KISS boundary: first-demo task/approval/follow-up loop only; no scheduler engine,
  notifications, email delivery, automatic device control, sensor runtime dependency,
  or broad farm-management task system.

## Source Artifacts

- .memory-bank/features/FT-013-tasks-approvals-and-follow-up-outcomes.md
- .memory-bank/tech-specs/FT-013-tasks-approvals-and-follow-up-outcomes.md
- .memory-bank/epics/EP-004-safety-gated-advisory-and-task-loop.md
- .memory-bank/requirements.md
- .tasks/SPEC-IMPROVE-REVIEW/final-report.md
- .tasks/SPEC-IMPROVE-REVIEW-FIXES/final-report.md

## Normative Inputs

- .memory-bank/constitution.md
- .memory-bank/invariants.md
- .memory-bank/contracts/safety-gate.md
- .memory-bank/contracts/agent-harness.md
- .memory-bank/contracts/agent-chat-bus.md
- .memory-bank/contracts/message-envelope.md
- .memory-bank/contracts/api-guidelines.md
- .memory-bank/states/core-lifecycles.md
- .memory-bank/testing/index.md
- .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
- .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
- .memory-bank/tech-specs/FT-004-authorized-plant-selector-and-daily-check-in.md
- .memory-bank/tech-specs/FT-006-runtime-plant-state-history-and-timeline-audit.md
- .memory-bank/tech-specs/FT-007-shared-agent-harness-and-agent-profile-runtime.md
- .memory-bank/tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md
- .memory-bank/tech-specs/FT-011-plant-state-trust-and-hydroponics-advisor.md
- .memory-bank/tech-specs/FT-012-safety-gate-for-physical-action-advice.md
- .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
- agents-best-practices: narrow typed task/action proposals, schema validation,
  draft/commit separation, runtime permission decisions, approval records, structured
  observations, traces/evals, budgets, and no automated actuation.

## Constraints

- check_task and measurement_task do not require physical-action approval.
- action_task creation requires valid FT-012 `cleared_for_approval` and authorized
  human Approval scoped to the exact proposal.
- Rejected, expired, revoked, stale, or mismatched Approval creates no action_task.
- Consultant does not create domain task/recommendation/action records by default.
- Task, Approval, and Outcome records never trigger automated device execution.
- Outcome text alone cannot promote confirmed Plant state.
- Failed or denied mutations must not publish successful Bus/UI/timeline refs.

## Invariants

- Every task, approval, and outcome mutation resolves ActorContext and PlantAccessGrant.
- Approval is scoped to exact proposal and cannot be replayed after scope, evidence,
  ActorContext, PlantAccessGrant, or wording changes.
- Governance DecisionRecord cannot create action_task or replace Safety Gate approval.
- UI Feed and timeline refs are projections/audit evidence only, not mutable authority.
- No automated actuation command, tool, or side effect exists in the task loop.

## Steps

1. Implement Task schemas, lifecycle transitions, check/measurement/follow-up creation,
   and authorized reads/mutations.
2. Implement Approval request/result records from current SafetyGateDecision clearance.
3. Implement action_task unlock from exact approved proposal with no device execution.
4. Implement Outcome recording, no_data/conflict/supersede semantics, and evidence refs.
5. Publish task/approval/outcome Bus/UI/timeline/history refs after authoritative
   persistence and redaction.
6. Add task/approval/follow-up tests, harness evals, UI/e2e smoke, and no-actuation
   regressions.

## Expected Touched Files

- backend/app/tasks/*
- backend/app/approvals/*
- backend/app/outcomes/*
- backend/app/safety/*
- backend/app/plant_operations/*
- backend/app/runtime_state/*
- backend/app/publication/*
- backend/app/timeline/*
- backend/app/access/*
- backend/app/privacy/*
- backend/app/db/migrations/*
- backend/app/api/*
- frontend/src/*
- backend/tests/tasks/*
- backend/tests/approvals/*
- backend/tests/outcomes/*
- backend/tests/integration/*
- backend/tests/security/*
- frontend/tests/*
- .memory-bank/changelog.md

## Tests

- Unit: task payload validation, status transitions, Approval lifecycle,
  exact-proposal matching, action_task unlock guards, Outcome no_data/conflict/supersede
  semantics, and Consultant denial.
- Integration: ActorContext and PlantAccessGrant denials, SafetyGateDecision lookup,
  Approval approve/reject/expire/revoke, no action_task from invalid approval,
  Bus/UI/timeline publication after persistence, and generated OpenAPI after schemas
  exist.
- Harness evals: approval bypass attempts, unknown tool, invalid args, stale approval,
  mismatched proposal, governance substitution, prompt injection, and false success.
- UI/e2e: pending approval card, approved human-performed action task, rejected/no-task
  path, and follow-up outcome capture once UI exists.
- Security/safety: no automated actuation command/tool/side effect exists.

## Quality Gates

- pytest backend/tests/tasks backend/tests/approvals backend/tests/outcomes backend/tests/integration backend/tests/security
- Frontend/UI smoke or e2e evidence under the task report when a frontend test runner exists; otherwise record the missing-runner reason in /verify
- Harness eval fixture evidence through the task-specific pytest/eval suite and /red-verify semantic-pass
- generated OpenAPI validation after implementation schemas exist
- node scripts/mb-lint.mjs
- node scripts/mb-doctor.mjs
- /verify and /red-verify before T3 closure
- T3 human checkpoint and rollback/recovery note before closure

## UAT Steps

- Authorized Boss or Engineer creates check/measurement/follow-up tasks for active
  granted Plant without physical-action approval.
- Pending physical-action approval appears only from current Safety Gate clearance.
- Boss or eligible Engineer approval creates only a human-performed action_task.
- Rejected, expired, revoked, stale, or mismatched approval creates no action_task.
- Follow-up outcome records evidence refs and explicit no_data when data is missing.

## Task Slice

- TASK-076: Task schemas, lifecycle, and check/measurement/follow-up services.
- TASK-077: Approval request/result records from Safety Gate clearance.
- TASK-078: action_task unlock from exact approved proposal with no actuation.
- TASK-079: Follow-up Outcome recording, no_data, conflict, and supersede semantics.
- TASK-080: Task, approval, and outcome Bus/UI/timeline/history publication.
- TASK-081: Task/approval/follow-up regression, harness eval, UI, and no-actuation suite.
