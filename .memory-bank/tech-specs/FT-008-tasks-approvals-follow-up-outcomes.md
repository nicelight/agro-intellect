---
description: Feature-local SDD tech spec for FT-008 tasks, approvals, and follow-up outcomes.
status: active
owner: architecture
last_updated: 2026-06-01
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/features/FT-008-tasks-approvals-follow-up-outcomes.md
  - .memory-bank/spec-index.md
---
# FT-008 Tasks, Approvals, and Follow-up Outcomes Tech Spec

## Scope

This spec closes the feature-local SDD design gate for FT-008 before `/prd-to-tasks FT-008`.

FT-008 owns:

- task type boundaries for check, measurement, pending approval, action, and follow-up tasks;
- task record minimum fields, statuses, due dates, transitions, and event refs;
- creation sources for missing-data, pending approval, approved action, and follow-up tasks;
- follow-up scheduling after 1-3 days;
- follow-up outcome capture;
- API/service surfaces and verification targets for task and follow-up workflows.

FT-008 does not own Safety Gate classification, human approval/rejection record lifecycle,
approval stale/replay rules, action unlock validation, UI layout, plant-state confirmation,
dataset trainability decisions, or automated device execution.

## Normative Inputs

- [.memory-bank/states/task-follow-up.md](../states/task-follow-up.md): task types, creation rules, outcome values, and traceability.
- [.memory-bank/states/safety-approval.md](../states/safety-approval.md): Safety Gate outcomes, freshness windows, approval semantics, and fail-closed behavior.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): PostgreSQL/read-model authority for tasks and human approvals.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): `task_created` / `task_updated` audit/export events and append-only rules.
- [.memory-bank/tech-specs/FT-003-runtime-state-timeline-audit.md](FT-003-runtime-state-timeline-audit.md): `tasks` table boundary, timeline append semantics, and event refs.
- [.memory-bank/tech-specs/FT-001-daily-check-in-observations-manual-measurements.md](FT-001-daily-check-in-observations-manual-measurements.md): pH/EC measurement refs and freshness projection.
- [.memory-bank/tech-specs/FT-013-safety-gate-physical-action-advice.md](FT-013-safety-gate-physical-action-advice.md): `SafetyGateDecision`, task handoff, and display safety checks.
- [.memory-bank/tech-specs/FT-014-human-approval-action-unlock-semantics.md](FT-014-human-approval-action-unlock-semantics.md): approval records, action unlock validation, stale/replay prevention, and consumption rules.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): agent task requests and source-ref requirements.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): API shape, stable identifiers, and structured errors.
- [.memory-bank/testing/first-demo.md](../testing/first-demo.md): task/follow-up and approval workflow gates.
- [.memory-bank/invariants.md](../invariants.md): runtime authority, human gate, no automated device execution, and source-of-truth guardrails.

## Design Decisions

### Task Type Boundaries

Allowed task types are the global task-follow-up types, refined as follows:

| Task type | Meaning | Approval required |
|---|---|---|
| `check_task` | Low-risk request for observation, photo, inspection, or textual context. It must not instruct a physical plant-system intervention. | No. |
| `measurement_task` | Request for missing or stale pH/EC or other manual measurements. It asks the user to measure or record data, not change the system. | No. |
| `pending_approval_task` | Work item pointing the user to a pending FT-014 approval/rejection decision. The task is not the approval record. | Human decision required through FT-014. |
| `action_task` | Human-performed checklist/tracking record for an approved physical action proposal. | Yes, through FT-014 unlock validation. |
| `follow_up_task` | Time-boxed task to capture outcome after 1-3 days. | No new action approval by itself. |

Boundary rules:

- `check_task` and `measurement_task` may be created without approval only while their display wording remains low-risk and non-intervention.
- If wording for a check or measurement task implies changing pH, EC, solution, dosing, pumps, lights, pruning, transplanting, root trimming, or another physical intervention, FT-013 must reclassify it before display or task creation.
- `pending_approval_task` must reference the pending FT-014 `approval_id` and the originating `safety_decision:<safety_decision_id>` PostgreSQL/read-model Safety Gate decision; completing the task must not approve the proposal by itself.
- `action_task` must not be created from raw agent output, UI Feed prompt state, timeline replay, Safety Gate output alone, rejected approval, stale approval, mismatched approval, or unapproved proposal.
- `action_task` remains human-performed task tracking only. It must not contain device command or actuator dispatch fields.

### Task Record Shape

The exact ORM and column types belong to implementation tasks, but each task record must be able to persist these fields:

| Field | Rule |
|---|---|
| `task_id` | Backend-generated globally unique task ID. |
| `plant_id` | Mandatory for plant-bound tasks; MVP value `tomato_001`. |
| `task_type` | One of `check_task`, `measurement_task`, `pending_approval_task`, `action_task`, or `follow_up_task`. |
| `status` | One of the FT-008 task statuses. |
| `created_at` | Timezone-aware creation timestamp. |
| `due_at` | Timezone-aware due timestamp. Required for every task. |
| `display_summary` | Short user-visible task text that has passed applicable safety display checks. |
| `source_type` | Machine-readable source such as `user`, `agent_task_request`, `safety_needs_data`, `safety_pending_approval`, `approval_unlock`, or `system_follow_up_scheduler`. |
| `source_refs` | Non-empty refs to the evidence or domain objects that caused the task. |
| `measurement_kind` | Required for measurement tasks when known, such as `ph`, `ec`, or `ph_ec`. |
| `approval_id` | Required for `pending_approval_task` and `action_task`; absent otherwise unless used as context. |
| `safety_decision_ref` | Required `safety_decision:<safety_decision_id>` ref when created from FT-013 `needs_data` or `pending_approval`. |
| `unlock_decision_ref` | Required for `action_task` creation or actionable transition. |
| `parent_task_id` | Optional link to the task that caused a follow-up task. |
| `follow_up_after_days` | Required for follow-up scheduling when `due_at` is derived; must be an integer from 1 to 3. |
| `outcome` | Required only when completing a `follow_up_task`; one of the allowed outcome values. |
| `outcome_recorded_at` | Required when outcome is recorded. |
| `outcome_evidence_refs` | Refs to observations, photos, measurements, human notes, tasks, approvals, or events used for the outcome; required unless outcome is `no_data`. |
| `event_refs` | Timeline event refs for creation, transitions, and outcome capture where emitted. |

Task records must not store raw model reasoning, UI spoiler content, secrets, `.env` values, credentials, or automation command payloads.

### Task Statuses And Transitions

Allowed task statuses:

| Status | Meaning |
|---|---|
| `open` | Task is actionable by the human or waiting for human input. |
| `in_progress` | Human or workflow has started the task. |
| `blocked` | Task cannot proceed until a missing prerequisite is resolved. |
| `completed` | Task reached its intended outcome or was answered by a recorded decision/outcome. |
| `cancelled` | Task is intentionally abandoned or superseded. |

Transition rules:

- New tasks start as `open` unless the owning workflow can prove the prerequisite is currently missing, in which case `blocked` is allowed.
- `open -> in_progress -> completed` is the normal path.
- `open` or `in_progress` may transition to `blocked` when data, approval, or safety preconditions become stale or missing.
- `blocked -> open` requires a source ref proving the prerequisite was resolved.
- `completed` and `cancelled` are terminal for the same task ID.
- `pending_approval_task` may become `completed` only after FT-014 records `approved` or `rejected`, or `cancelled` when the proposal is explicitly superseded.
- `action_task` creation and any transition into an actionable status must call FT-014 `check_action_unlock` first. If unlock is denied, no actionable `action_task` state is written.
- Completing an `action_task` may schedule a `follow_up_task` when the source proposal or workflow includes a 1-3 day follow-up requirement.
- Completing a `follow_up_task` requires an outcome value.

### Creation Sources

FT-008 accepts these task creation sources:

| Source | Allowed task output | Required refs |
|---|---|---|
| User/manual workflow | `check_task`, `measurement_task`, or `follow_up_task` | User/source actor and plant ref. |
| `MessageEnvelope` with `claim_type=task_request` or `clarification_request` | `check_task` or `measurement_task` | Canonical `message:<message_id>` ref plus evidence refs; Bus event ref is optional publication provenance. |
| FT-001 freshness projection or FT-007 missing-data policy | `measurement_task` | Measurement context refs and missing/stale fields. |
| FT-013 `SafetyGateDecision.outcome=needs_data` | `measurement_task` or `check_task` | `safety_decision_ref` and required measurement/context refs. |
| FT-013 `SafetyGateDecision.outcome=pending_approval` plus FT-014 pending approval | `pending_approval_task` | `approval_id`, `safety_decision_ref`, source refs. |
| FT-014 unlock decision with `allowed=true` | `action_task` | `approval_id`, `unlock_decision_ref`, proposal/source refs. |
| Follow-up scheduler | `follow_up_task` | Parent task or source evidence ref plus 1-3 day due window. |

The task service must reject source/task combinations outside this table unless a later spec extends the matrix.

### Action Task Unlock Coordination

FT-008 must delegate approval validity to FT-014 and must not duplicate FT-014 approval record logic.

Required flow for an `action_task`:

1. Receive an approved proposal request with `approval_id`, proposed action payload, and source refs.
2. Call FT-014 `check_action_unlock(approval_id, proposed_action, task_ref?)`.
3. Continue only when the unlock decision returns `allowed=true`, `action_task_allowed=true`, and `device_execution_allowed=false`.
4. Run FT-013 final display check for the task wording.
5. Create or transition the human-performed `action_task` with `approval_id`, `unlock_decision_ref`, source refs, due date, and event refs.
6. Call FT-014 `mark_approval_consumed(approval_id, task_id)` or equivalent idempotent consumption path.

If any step fails, FT-008 must fail closed:

- no actionable `action_task` is created or transitioned;
- the denial is audited through `task_updated`, `system_event`, or the owning workflow event when a durable denial trail is required;
- the flow routes to measurement/check task, pending approval, or Safety Gate reevaluation according to the reason.

### Due Dates And Follow-up Timing

- `due_at` is required for all tasks so task lists and verification can reason about overdue work.
- Check and measurement tasks created for missing critical data should be due immediately by default (`due_at=created_at`) unless the source explicitly supplies a later due time.
- A `pending_approval_task` with an approval `expires_at` must have `due_at` no later than that expiry. Without an expiry, it is due immediately.
- An `action_task` must have a due time from the approved proposal or workflow. If absent, it is due immediately after unlock.
- A `follow_up_task` must be due 1-3 calendar days after the triggering event, normally action-task completion or a workflow-specific follow-up trigger.
- Follow-up creation must reject values outside the 1-3 day window.
- FT-008 does not define agronomic timing heuristics beyond the PRD 1-3 day window. The creating workflow must provide `follow_up_after_days` or an explicit `due_at` in that window.

### Follow-up Outcome Capture

Allowed outcome values come from `states/task-follow-up.md`:

- `improved`
- `worsened`
- `unchanged`
- `no_data`

Outcome rules:

- Outcome is recorded on a `follow_up_task`, not on the original task as a hidden side effect.
- `improved`, `worsened`, and `unchanged` require `outcome_evidence_refs`.
- `no_data` is required when follow-up is due but no new evidence exists; it must not silently confirm improvement or unchanged state.
- Follow-up outcome may be used later as evidence for plant-state review or dataset governance, but FT-008 does not promote plant state to confirmed and does not set trainability.
- A contradictory follow-up outcome must preserve source refs and may route later workflows to conflict/review; it must not overwrite earlier evidence.
- Follow-up outcome cannot approve or reject a physical-action proposal retroactively.

### Event And Audit Refs

Timeline remains append-only audit/export and is not task state authority.

Minimum FT-008 timeline payloads:

| Event type | Minimum payload identifiers |
|---|---|
| `task_created` | `plant_id`, `task_id`, `task_type`, `status`, `due_at`, `source_type`, `source_refs`, optional `approval_id`, optional `safety_decision_ref`, optional `parent_task_id`. |
| `task_updated` | `plant_id`, `task_id`, previous and new `status` when status changes, `reason_code`, source refs, optional `approval_id`, optional `unlock_decision_ref`, optional `outcome`. |

When an action task is unlocked from approval, task events must preserve refs to the approval and unlock decision. Human approval/rejection events remain owned by FT-014.

If a task event is published to Agent Chat Bus, it must use FT-004 Bus publication and must not be created by replaying `timeline.jsonl` directly into agent context.

### API And Service Surface

Feature tasks may implement these as internal services, HTTP endpoints, or both. Behavior is normative either way.

Service surface:

- `create_task(command)` for validated non-action tasks and internal workflow task creation.
- `create_measurement_task_from_freshness(plant_id, missing_fields, source_refs, due_at?)`.
- `create_pending_approval_task(approval_id, safety_decision_ref, source_refs, due_at?)`.
- `create_action_task_from_approval(approval_id, proposed_action, source_refs, due_at?)`.
- `transition_task(task_id, target_status, actor, reason_code, source_refs)`.
- `schedule_follow_up(parent_task_id, follow_up_after_days, source_refs)`.
- `record_follow_up_outcome(task_id, outcome, actor, outcome_evidence_refs?)`.

Minimal HTTP surface for the PWA/backend boundary:

- `GET /api/plants/{plant_id}/tasks`
  - returns current tasks from PostgreSQL/read model, with optional type/status filters.
- `POST /api/plants/{plant_id}/tasks`
  - creates user/workflow-visible `check_task`, `measurement_task`, or `follow_up_task`;
  - must reject direct client creation of `action_task` unless routed through the approved action task service.
- `POST /api/tasks/{task_id}/transitions`
  - applies a validated task status transition.
- `POST /api/tasks/{task_id}/follow-up-outcome`
  - records a follow-up outcome for a `follow_up_task`.
- `POST /api/tasks/action-from-approval`
  - optional internal/workflow endpoint for creating a human-performed action task from an approval;
  - must call FT-014 unlock validation and FT-013 display safety checks.

All API errors use the shared structured error envelope. Expected machine-readable codes include:

- `task_not_found`
- `invalid_task_type`
- `invalid_task_status`
- `invalid_task_transition`
- `unsupported_plant`
- `missing_source_refs`
- `missing_due_at`
- `invalid_follow_up_window`
- `invalid_follow_up_outcome`
- `action_task_requires_approval`
- `approval_unlock_denied`
- `physical_action_display_not_cleared`
- `device_execution_forbidden`

## Verification Targets

Required before FT-008 can be marked implemented:

- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- Schema/model tests proving task records require plant, type, status, due date, source refs, display summary, event refs where emitted, and type-specific approval/follow-up fields.
- Policy tests proving allowed task type/status transitions and rejecting invalid transitions, terminal-state mutation, unsupported plant, missing source refs, missing due dates, and invalid follow-up windows.
- Workflow test proving missing or stale pH/EC creates a `measurement_task` without approval and preserves freshness/source refs.
- Workflow test proving low-risk check requests create `check_task` without approval only when wording is non-intervention.
- Integration test proving FT-013 `needs_data` creates check/measurement tasks and FT-013 `pending_approval` plus FT-014 pending approval creates `pending_approval_task`.
- Authority test proving task `safety_decision_ref` resolves to a PostgreSQL/read-model Safety Gate decision record and cannot be satisfied by timeline, Bus, UI Feed, or transient object refs.
- Integration test proving `action_task` creation calls FT-014 unlock validation, stores `approval_id` and `unlock_decision_ref`, marks the approval consumed, and rejects pending/rejected/stale/mismatched/already-consumed approvals.
- Display safety test proving physical-action task wording cannot be shown as cleared action without FT-013 approval of the display text.
- Workflow test proving action-task completion or source follow-up request creates a `follow_up_task` due 1-3 days after the trigger.
- Outcome tests proving `improved`, `worsened`, and `unchanged` require evidence refs, while `no_data` records lack of evidence without confirming plant state.
- Timeline tests proving `task_created` and `task_updated` events include required identifiers and remain append-only.
- Runtime authority test proving task state is read from PostgreSQL/read model, not `timeline.jsonl`, UI Feed, or Agent Chat Bus replay.
- Policy test proving task creation, approval, and outcome refs do not produce automated device commands, command payloads, automation targets, or actuator dispatch statuses.
- Anti-cheat test proving raw agent output, UI Feed prompt state, Safety Gate output alone, or timeline replay cannot create or unlock an `action_task`.

## Gaps And Non-Goals

- No FT-008 blocker remains for `/prd-to-tasks FT-008`.
- Exact Pydantic class names, ORM names, Alembic revision names, route implementation names, fixture shapes, and frontend layout behavior belong to implementation tasks.
- FT-014 owns approval/rejection records, stale/replay prevention, and action unlock validation.
- FT-013 owns physical-action classification, Safety Gate decisions, and final display safety checks.
- FT-011 owns PWA task-list and approval-prompt layout.
- Plant-state confirmation and dataset trainability effects from follow-up evidence are owned by their state/governance specs and later feature workflows.
- Automated pumps, dosing, lighting control, pH/EC correction, and device command execution are outside MVP scope.
