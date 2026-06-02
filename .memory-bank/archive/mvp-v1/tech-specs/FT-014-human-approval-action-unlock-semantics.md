---
description: Feature-local SDD tech spec for FT-014 human approval and action unlock semantics.
status: active
owner: architecture
last_updated: 2026-06-01
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/features/FT-014-human-approval-action-unlock-semantics.md
  - .memory-bank/spec-index.md
---
# FT-014 Human Approval and Action Unlock Semantics Tech Spec

## Scope

This spec closes the feature-local SDD design gate for FT-014 before `/prd-to-tasks FT-014`.

FT-014 owns:

- pending physical-action proposal representation for human decision;
- human approval and rejection record lifecycle;
- approval stale-condition and replay-prevention rules;
- action unlock semantics for human-performed `action_task` tracking;
- approval event/audit refs and minimal API/service surface.

FT-014 does not own Safety Gate physical-action classification, Hydroponics Advisor reasoning,
the full task/follow-up lifecycle, UI layout, or any automated device execution.

## Normative Inputs

- [.memory-bank/states/safety-approval.md](../states/safety-approval.md): Safety Gate outcomes, human approval semantics, and stale-condition routing.
- [.memory-bank/states/task-follow-up.md](../states/task-follow-up.md): task types, action-task creation rule, and follow-up boundary.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): PostgreSQL authority for tasks and human approvals.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): `human_approval` and `human_rejection` timeline events.
- [.memory-bank/tech-specs/FT-003-runtime-state-timeline-audit.md](FT-003-runtime-state-timeline-audit.md): `human_approvals` table boundary and event refs.
- [.memory-bank/tech-specs/FT-013-safety-gate-physical-action-advice.md](FT-013-safety-gate-physical-action-advice.md): `SafetyGateDecision`, pending approval handoff, display safety, and anti-cheat boundary.
- [.memory-bank/tech-specs/FT-008-tasks-approvals-follow-up-outcomes.md](FT-008-tasks-approvals-follow-up-outcomes.md): task lifecycle, due/follow-up ownership, outcome schema, and FT-014 unlock coordination.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): API shape, identifiers, and structured errors.
- [.memory-bank/testing/first-demo.md](../testing/first-demo.md): approval/task transition and no-device-execution gates.
- [.memory-bank/invariants.md](../invariants.md): human gate, runtime authority, and no automated device execution.

## Design Decisions

### Approval Boundary

- A pending physical-action proposal is represented by a PostgreSQL/read-model `human_approvals` record with `status=pending`.
- FT-014 does not introduce a separate `action_proposals` table for the MVP.
- A `pending_approval_task` may reference the pending approval record, but the task is not the approval.
- A `SafetyGateDecision` is not human approval. It is a PostgreSQL/read-model safety decision record referenced as `safety_decision:<safety_decision_id>` and used as policy input for a pending approval.
- Approval is not a device command, automation authorization, or permission for backend code to actuate pumps, dosing, lights, pH/EC correction, or any other physical device.

### Approval Lifecycle

Allowed approval statuses:

| Status | Meaning |
|---|---|
| `pending` | Human decision is required before a physical-action proposal can unlock an action task. |
| `approved` | Human approved the exact pending proposal; it may unlock one matching human-performed action task if still valid. |
| `rejected` | Human rejected the proposal; it cannot unlock action tasks. |

Lifecycle rules:

- Create `pending` only from a Safety Gate handoff whose `SafetyGateDecision.outcome` is `pending_approval`.
- `pending -> approved` requires a human actor and a validity check against the linked Safety Gate decision and freshness refs.
- `pending -> rejected` requires a human actor and leaves the proposal unapproved.
- `rejected -> approved` is forbidden; create a new pending approval from a new Safety Gate decision instead.
- Follow-up outcomes cannot approve or reject proposals retroactively.
- `approved` records remain audit records. Reuse is blocked by `consumed_by_task_id` / `consumed_at` rather than mutating history.
- Stale or mismatched approvals route back through Safety Gate instead of being repaired locally.

### Pending Approval Record Shape

The exact database column types belong to implementation tasks, but the record must be able to persist these fields:

| Field | Rule |
|---|---|
| `approval_id` | Globally unique approval ID. |
| `plant_id` | Mandatory for plant-bound approvals; MVP value `tomato_001`. |
| `status` | `pending`, `approved`, or `rejected`. |
| `created_at` | Timezone-aware creation timestamp. |
| `action_category` | Safety Gate action category, such as `ph_change`, `ec_change`, `dosing`, `pump_change`, `light_change`, or `high_risk_manual`. |
| `proposal_summary` | Display-safe summary of the proposed human-performed action; no raw reasoning or secrets. |
| `proposal_fingerprint` | Stable hash/fingerprint of the normalized proposal and source refs used for replay prevention. |
| `safety_decision_ref` | Required `safety_decision:<safety_decision_id>` ref to the PostgreSQL/read-model `SafetyGateDecision` that produced `pending_approval`. |
| `source_refs` | Non-empty refs to MessageEnvelope, Bus event, timeline event, observation, photo, measurement, task, or other domain evidence. |
| `required_measurement_refs` | pH/EC or other freshness refs required by FT-013 for this action, when relevant. |
| `required_context_refs` | Non-chemistry freshness refs required by FT-013 for pump, light, or high-risk manual interventions, when relevant. |
| `unlock_conditions` | Explicit AND-set; at minimum includes safety check and human approval, plus fresh data where relevant. |
| `expires_at` | Required for physical-action approvals; derived from the earliest linked Safety Gate, measurement, or context freshness expiry. |
| `decision_actor` | Human/user actor that approved or rejected. Required after decision. |
| `decided_at` | Timezone-aware decision timestamp. Required after decision. |
| `decision_note` | Optional safe human note. |
| `rejection_reason` | Optional safe rejection reason. Required only when the UI/API captures one. |
| `consumed_by_task_id` | Optional `action_task` ref that consumed this approval. |
| `consumed_at` | Timezone-aware timestamp when a matching action task consumed the approval. |
| `event_refs` | Timeline event refs for creation context, human decision, and unlock/consumption where emitted. |

`proposal_fingerprint` is not a security primitive. It is a deterministic guardrail proving that the task being unlocked matches the proposal the human reviewed.

### Stale And Replay Prevention

Approval validity is checked both when the human approves and when FT-008 or a workflow tries to create/transition an `action_task`.

An approval is valid for unlock only when all of the following hold:

- `status=approved`;
- `plant_id` matches the proposed task and source refs;
- `proposal_fingerprint` matches the proposed action task payload;
- the linked Safety Gate decision record is present in PostgreSQL/read model, source-bound, has `outcome=pending_approval` for the original proposal, and is not expired;
- required pH/EC measurement refs remain within the FT-013/FT-001 physical-action approval freshness window at decision time and unlock time;
- required non-pH/EC context refs remain within the FT-013 physical-action freshness policy at decision time and unlock time;
- physical-action approvals have `expires_at`; missing expiry for a physical-action proposal fails closed;
- `consumed_by_task_id` is empty, or the request is an idempotent retry for the same task;
- no rejected record is being reused.

If any condition fails, the unlock attempt must fail closed:

- no `action_task` is created or made actionable;
- no user-visible action instruction is displayed as cleared;
- the flow routes back to Safety Gate or a measurement/check task as appropriate;
- an audit ref is recorded through `system_event`, `task_updated`, or the owning workflow event when implementation needs a durable denial trail.

FT-014 does not invent freshness windows. It uses FT-013 freshness policy: the 2-hour pH/EC approval window where relevant, the MVP non-pH/EC context freshness rule for pump/light/high-risk manual interventions, and the `expires_at` carried by the Safety Gate decision.

### Action Unlock Semantics

Approval unlocks only a task-state transition for a human-performed `action_task`.

The unlock service returns a structured decision, conceptually:

| Field | Rule |
|---|---|
| `unlock_decision_id` | Unique decision/audit ID. |
| `approval_id` | Approval being checked. |
| `plant_id` | Plant binding. |
| `allowed` | Boolean; true only when all validity rules pass. |
| `reason_code` | Machine-readable reason such as `approved`, `not_approved`, `rejected`, `stale`, `proposal_mismatch`, `already_consumed`, or `device_execution_forbidden`. |
| `action_task_allowed` | True only for `execution_mode=human_performed`. |
| `device_execution_allowed` | Always false in the MVP. |
| `source_refs` | Approval, Safety Gate, proposal, measurement, and event refs used for the decision. |

The resulting action task must remain a checklist/tracking record for a human. It must not contain or dispatch:

- `device_id`;
- `command_payload`;
- `automation_target`;
- `dispatch_status`;
- pump, dosing, light, pH/EC correction, or other actuator command instructions for automatic execution.

Task wording visible to the user still passes FT-013 display checks. Approval does not bypass the final display safety check.

### FT-008 Coordination

- FT-014 validates whether an approved proposal can unlock an `action_task`.
- FT-008 owns task statuses, due dates, completion, follow-up creation, and outcome schema.
- FT-008 must call FT-014 unlock validation before creating or transitioning an `action_task`.
- FT-008 may create check/measurement tasks without approval when more data is needed.
- FT-008 may create `pending_approval_task` records pointing to `approval_id`.
- FT-008 must not create an `action_task` from a rejected, stale, mismatched, unapproved, or already consumed approval.

FT-008 design is complete and owns task lifecycle/follow-up. FT-014 owns approval/unlock semantics. `/prd-to-tasks` decomposition must link both FT-008 and FT-014 specs where action-task approval transitions are planned.

### Event And Audit Refs

Timeline remains append-only audit/export, not mutable approval authority.

Minimum FT-014 timeline payloads:

| Event type | Minimum payload identifiers |
|---|---|
| `human_approval` | `plant_id`, `approval_id`, `status=approved`, `proposal_fingerprint`, `safety_decision_ref`, `source_refs`, optional `task_id`. |
| `human_rejection` | `plant_id`, `approval_id`, `status=rejected`, `proposal_fingerprint`, `safety_decision_ref`, `source_refs`, optional rejection reason code. |

Pending approval creation may be audited through the source `safety_block`, `task_created` for a `pending_approval_task`, or `system_event` with a safe reason code. FT-014 does not add a new global timeline event type for pending creation.

If approval outcome should become agent-consumable, publish through existing FT-004 Bus event types such as `human_confirmation` or `task_created` with safe source refs, including `safety_decision:<safety_decision_id>` where relevant. Do not replay timeline events directly into Agent Chat Bus.

UI approval prompts are UI Feed presentation records and must communicate that approval unlocks only human-performed task tracking.

### API And Service Surface

Feature tasks may implement these as internal application services, HTTP endpoints, or both. Behavior is normative either way.

Service surface:

- `create_pending_approval(safety_decision_ref, proposal, source_refs, pending_task_ref?)`
- `record_approval(approval_id, actor, note?)`
- `record_rejection(approval_id, actor, reason?)`
- `check_action_unlock(approval_id, proposed_action, task_ref?)`
- `mark_approval_consumed(approval_id, task_id)`

Minimal HTTP surface for the PWA/backend boundary:

- `GET /api/approvals/{approval_id}` returns current approval/proposal state for display.
- `POST /api/approvals/{approval_id}/approve` records the human approval decision.
- `POST /api/approvals/{approval_id}/reject` records the human rejection decision.
- `POST /api/approvals` may exist as an internal/workflow endpoint for Safety Gate handoff; it must reject client attempts that lack a valid Safety Gate decision ref.

All API errors use the shared structured error envelope. Expected machine-readable codes include:

- `approval_not_found`
- `approval_not_pending`
- `approval_not_approved`
- `approval_rejected`
- `approval_stale`
- `proposal_mismatch`
- `approval_already_consumed`
- `invalid_safety_decision`
- `device_execution_forbidden`
- `unsupported_plant`

## Verification Targets

Required before FT-014 can be marked implemented:

- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- Schema/model tests proving pending approvals require plant, status, proposal summary, proposal fingerprint, Safety Gate ref, source refs, unlock conditions, and event refs where emitted.
- Workflow test proving a Safety Gate `pending_approval` handoff can create a pending approval record and optional `pending_approval_task`.
- Authority test proving `safety_decision_ref` resolves to a PostgreSQL/read-model Safety Gate decision record and cannot be satisfied by timeline, Bus, UI Feed, or transient object refs.
- Approval/rejection tests proving human decision capture persists `approved` and `rejected` records and emits `human_approval` / `human_rejection` audit refs.
- Stale tests proving expired Safety Gate decisions or stale required pH/EC refs cannot unlock an action task and route back through Safety Gate or measurement/check task flow.
- Stale tests proving missing or stale non-pH/EC context refs cannot unlock pump, light, or high-risk manual action tasks.
- Replay tests proving a consumed approval cannot create a second action task and a mismatched `proposal_fingerprint` is rejected.
- Negative tests proving rejected, pending, unsupported-plant, missing-source-ref, missing-Safety-Gate-ref, and malformed approval records cannot unlock `action_task`.
- Integration test proving FT-008 action-task creation calls FT-014 unlock validation and stores the approval ref on the resulting human-performed task.
- Policy test proving approval never produces automated device execution, command payloads, or actuator dispatch fields.
- Display safety test proving approval prompt and action-task wording still pass FT-013 final display checks.
- Anti-cheat test proving timeline replay, UI Feed prompt state, raw agent output, or Safety Gate output alone cannot be treated as human approval.

## Gaps And Non-Goals

- No FT-014 blocker remains for `/prd-to-tasks FT-014`.
- Exact Pydantic class names, ORM model names, Alembic revision names, hash implementation, and HTTP response field ordering belong to implementation tasks.
- FT-008 remains the owner of full task status transitions, due dates, completion, follow-up scheduling, and outcome schema.
- FT-011 remains the owner of PWA layout and visual behavior for approval prompts.
- Automated pumps, dosing, lighting control, pH/EC correction, and device command execution are outside MVP scope even after human approval.
