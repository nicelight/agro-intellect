---
description: FT-008 - Tasks, approvals, and follow-up outcomes.
status: draft
lifecycle: planned
parent_epic: EP-002
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-008-tasks-approvals-follow-up-outcomes.md
  - .memory-bank/states/task-follow-up.md
  - .memory-bank/states/safety-approval.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/contracts/timeline-event.md
  - .memory-bank/tech-specs/FT-014-human-approval-action-unlock-semantics.md
  - .memory-bank/tech-specs/FT-013-safety-gate-physical-action-advice.md
  - .memory-bank/tech-specs/FT-001-daily-check-in-observations-manual-measurements.md
  - .memory-bank/testing/first-demo.md
---
# FT-008 Tasks, Approvals, and Follow-up Outcomes

## Parent Epic

- [EP-002 Agent Advisory and Safety Loop](../epics/EP-002-agent-advisory-safety-loop.md): agent advisory, communication boundaries, and safety loop.

## Purpose

Track safe next steps after advisory output: check tasks, measurement tasks, pending approvals, approved human-performed action tasks, follow-up tasks, and outcome records after 1-3 days.

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): FR-014, FR-015, task/follow-up acceptance criteria, edge cases, and verification strategy.
- [project_dossier.md](../../project_dossier.md): sections 8.5, 8.6, 13, 22, 23, 28, and 33 for task/follow-up context.
- [.memory-bank/requirements.md](../requirements.md): REQ-010, REQ-004 for pH/EC freshness-driven measurement tasks, and task/approval parts of REQ-009.
- [.memory-bank/constitution.md](../constitution.md): human gate for physical actions, bounded agent autonomy, and evidence-based workflow.
- [.memory-bank/spec-index.md](../spec-index.md): route map for task follow-up lifecycle, safety approval lifecycle, runtime data model, and first-demo verification.
- [.memory-bank/tech-specs/FT-008-tasks-approvals-follow-up-outcomes.md](../tech-specs/FT-008-tasks-approvals-follow-up-outcomes.md): feature-local task lifecycle, due/follow-up timing, outcome schema, event refs, API/service surface, and verification targets.
- [.memory-bank/testing/index.md](../testing/index.md): task/follow-up, approval transition, and safety verification.

## Use Cases

- Task & Follow-up creates a check task when more visual or textual data is needed.
- Task & Follow-up creates a measurement task when pH/EC or other measurements are missing/stale.
- Safety Gate creates or requests pending approval for risky action proposals.
- Approved proposals become human-performed action task tracking records.
- The system schedules follow-up after 1-3 days.
- The user records whether the situation improved, worsened, stayed unchanged, or has no data.

## Acceptance Criteria

- Task & Follow-up Agent creates check/measurement tasks without approval when additional data is needed.
- Task & Follow-up Agent creates action tasks only from approved action proposals.
- The system supports follow-up after 1-3 days.
- Follow-up outcome records whether the situation improved, worsened, stayed unchanged, or has no data.
- Approval unlocks task tracking/status transition for a human-performed `action_task`.
- Approval does not authorize automatic device execution.
- Task creation, approval, and follow-up outcomes are traceable through runtime state and event refs.

## Edge Cases / Failure Modes

- An action task is created without approved proposal: reject.
- A check or measurement task is incorrectly treated as a physical intervention: correct classification before Safety Gate routing.
- User rejects approval: action remains unapproved; only safe check/follow-up tasks remain available.
- Follow-up date arrives without new evidence: record no data rather than silently confirming improvement.
- Follow-up outcome contradicts earlier hypothesis: preserve evidence and avoid confirming stale state.
- Task lacks plant, source, due date, status, or evidence refs where required by later design: fail validation.

## Test Strategy Pointers

- `workflow:task-follow-up-outcome` for 1-3 day follow-up and outcome recording.
- `integration:approved-action-task-transition` for approved proposals becoming human-performed action tasks.
- `workflow:missing-or-stale-measurement-task` for missing-data task creation.
- `integration:safety-block-to-pending-approval` for pending approval task/proposal creation.
- `schema:task` and `schema:human-approval` once the SDD design establishes exact fields.
- `policy:no-automated-device-execution` for action-task semantics.

## Constraints / Invariants

- Check and measurement tasks can be created without approval when they do not become physical interventions.
- Measurement tasks driven by pH/EC freshness inherit REQ-004 freshness windows and provenance expectations.
- Action tasks require approved action proposals.
- MVP action tasks are human-performed checklist/task records.
- No automated device command or physical actuation is in MVP scope.
- Follow-up evidence can support confirmation, conflict, or dataset governance decisions later.

## SDD Design Gate

Global `/spec-design` completed the shared backbone. Feature-local `/spec-improve FT-008` is complete.

Normative design links:

- [.memory-bank/tech-specs/FT-008-tasks-approvals-follow-up-outcomes.md](../tech-specs/FT-008-tasks-approvals-follow-up-outcomes.md): task boundaries, statuses, creation sources, FT-014 unlock coordination, due/follow-up timing, outcome capture, event refs, API/service surface, and verification targets.
- [.memory-bank/states/task-follow-up.md](../states/task-follow-up.md): task types, creation rules, and outcome values.
- [.memory-bank/states/safety-approval.md](../states/safety-approval.md): pending approval and action-task unlock semantics.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): task/approval refs and mutable state ownership.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): event refs for task and approval transitions.
- [.memory-bank/tech-specs/FT-014-human-approval-action-unlock-semantics.md](../tech-specs/FT-014-human-approval-action-unlock-semantics.md): approval records, action unlock validation, stale/replay prevention, and consumption rules.
- [.memory-bank/tech-specs/FT-013-safety-gate-physical-action-advice.md](../tech-specs/FT-013-safety-gate-physical-action-advice.md): Safety Gate handoffs and display checks.
- [.memory-bank/tech-specs/FT-001-daily-check-in-observations-manual-measurements.md](../tech-specs/FT-001-daily-check-in-observations-manual-measurements.md): pH/EC freshness and measurement refs for measurement tasks.
- [.memory-bank/testing/first-demo.md](../testing/first-demo.md): task/follow-up workflow gates.

No FT-008 blocker remains for `/prd-to-tasks FT-008`. FT-014 remains the owner of approval/rejection record logic and unlock validation; FT-008 must call it before creating or transitioning any actionable `action_task`.
