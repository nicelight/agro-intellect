---
description: FT-014 - Human approval and action unlock semantics.
status: draft
lifecycle: planned
parent_epic: EP-002
---
# FT-014 Human Approval and Action Unlock Semantics

## Parent Epic

- [EP-002 Agent Advisory and Safety Loop](../epics/EP-002-agent-advisory-safety-loop.md): agent advisory, communication boundaries, and safety loop.

## Purpose

Define how pending physical-action proposals are approved or rejected by the human and what approval unlocks in MVP: human-performed action task tracking only, never automated device execution.

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): FR-014, FR-015, human approval actor/data model, action-task semantics, task/follow-up acceptance criteria, and edge cases.
- [project_dossier.md](../../project_dossier.md): sections 8.5, 8.6, 9.10.1, 13, 22, 23, 28, and 33 for approval and task lifecycle context.
- [.memory-bank/requirements.md](../requirements.md): approval portions of REQ-009 and REQ-010.
- [.memory-bank/constitution.md](../constitution.md): human gate for physical actions, bounded autonomy, and no automated actuation.
- [.memory-bank/spec-index.md](../spec-index.md): route map for safety approval lifecycle, task follow-up lifecycle, runtime data model, and timeline event areas.
- [.memory-bank/testing/index.md](../testing/index.md): approval transition and no-device-execution verification.

## Use Cases

- Safety Gate or advisory flow creates a pending action proposal or pending approval task.
- The user approves or rejects a proposed human-performed physical action.
- Approval unlocks only task tracking/status transition for a human-performed `action_task`.
- Rejection keeps the proposal unapproved and leaves only safe checks or follow-up tasks available.
- Approval/rejection records are traceable through runtime state and event refs.
- FT-008 coordinates the downstream task lifecycle and follow-up outcome after approval.

## Acceptance Criteria

- Safety Gate may convert risky recommendations into pending action proposals or pending approval tasks.
- MVP `action_task` means human-performed checklist/task tracking, not automated device command or physical actuation.
- Approval unlocks task tracking/status transition for a human-performed `action_task`.
- Approval does not authorize automatic device execution in MVP.
- Task & Follow-up Agent creates action tasks only from approved action proposals.
- Approval/rejection records are persisted as traceable runtime state and event refs.
- User rejection keeps the action unapproved and allows only safe check/follow-up tasks.
- Human approval semantics coordinate with FT-008 task lifecycle and follow-up outcomes.

## Edge Cases / Failure Modes

- Approval is mistaken for automated device execution: reject; MVP has no automated physical actuation.
- An action task is created without an approved action proposal: reject.
- A pending approval lacks action summary, source refs, required freshness/safety status, or human decision state where later design requires it: fail validation.
- User rejects approval but the action becomes actionable: reject and keep unapproved.
- Approval is stale relative to required safety/freshness conditions: route back through Safety Gate.
- Follow-up outcome tries to retroactively approve an action: reject; follow-up records outcome only.

## Test Strategy Pointers

- `workflow:approval-prompt-human-action` for approval/rejection records and human decision capture.
- `integration:approved-action-task-transition` for approved proposals becoming human-performed action tasks.
- `policy:no-automated-device-execution` for approval not becoming actuation.
- `integration:safety-block-to-pending-approval` for pending approval creation from blocked risky advice.
- `workflow:task-follow-up-outcome` for FT-008 coordination after approved human action.

## Constraints / Invariants

- Human approval is required before physical action can become an actionable human-performed task.
- Approval unlocks human task tracking only.
- No automated device command or physical actuation is in MVP scope.
- Approval/rejection records must remain traceable through runtime state and event refs.
- Task lifecycle and follow-up outcomes remain coordinated with FT-008.

## SDD Design Gate

Global `/spec-design` completed the shared backbone. Normative backbone inputs for `/spec-improve FT-014`:

- [.memory-bank/states/safety-approval.md](../states/safety-approval.md): human approval semantics and stale-condition routing.
- [.memory-bank/states/task-follow-up.md](../states/task-follow-up.md): approved action-task creation and follow-up coordination.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): approval/task refs and mutable state ownership.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): approval/rejection event refs.
- [.memory-bank/testing/first-demo.md](../testing/first-demo.md): no-device-execution and approval workflow gates.

Do not set feature-local `spec_design_status=complete` yet. `/spec-improve FT-014` still decides or confirms approval/rejection schema, pending action proposal/task states, stale approval handling, FT-008 coordination, and tests before task decomposition.
