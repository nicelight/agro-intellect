---
description: FT-012 Human Approval Tasks And Follow-Up Outcomes.
status: draft
type: feature
feature_id: FT-012
epic: EP-004
lifecycle: planned
last_updated: 2026-07-17
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/states/lifecycle-map.md
spec_design_status: complete
spec_design_links:
  - .memory-bank/states/task-follow-up-lifecycle.md
  - .memory-bank/domains/task-approval-outcomes.md
  - .memory-bank/contracts/task-approval-http.md
  - .memory-bank/contracts/task-follow-up-runtime.md
  - .memory-bank/testing/task-follow-up.md
  - .memory-bank/domains/safety-action-routing.md
  - .memory-bank/states/safety-action-lifecycle.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
  - .memory-bank/states/plant-state-trust.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/contracts/safety-gate-runtime.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/contracts/agent-roster-bootstrap.md
  - .memory-bank/contracts/timeline-event.md
  - .memory-bank/runbooks/agent-runtime-providers.md
---
# FT-012 Human Approval Tasks And Follow-Up Outcomes

## Use Cases

- Authorized Boss or Engineer approves or rejects a physical-action proposal after Safety Gate pass.
- Approved physical action creates a human-performed `action_task`.
- Users complete checks, measurements, approved action tasks, and follow-up tasks.
- Follow-up outcome preserves evidence and audit trail.

## Acceptance Criteria

- Human approval unlocks only human-performed task tracking, never automated execution.
- `action_task`, `check_task`, measurement tasks, and follow-up outcomes are separated.
- A `safe_task_request` classification may create only its ordinary
  check/measurement/follow-up task through backend rules; it bypasses neither
  task authorization nor evidence checks and can never create `action_task`.
- Follow-up outcome captures exactly
  `improved|worsened|unchanged|no_data`; non-`no_data` values require evidence
  refs.
- Task and approval records preserve ActorContext, Plant scope, source refs, and audit refs.
- Archived Plant preserves task/approval/follow-up records but blocks their
  transitions until restore and current-guard revalidation.

## Edge Cases & Failure Modes

- Expired or stale approval cannot create action_task.
- Actor without `plant_approve_actions` cannot approve Plant physical action.
- Replayed or superseded approval cannot unlock action.
- Follow-up cannot mutate confirmed Plant state without required evidence/review rules.
- Archive must not complete, cancel, execute, or advance an open task; restore
  must not resume it automatically.

## Verification Targets

- Unit: approval authority and task state transitions after spec defines state model.
- Integration: approval creates action_task only through Safety Gate path.
- Integration: open task/approval/follow-up state is unchanged by archive,
  blocked while archived, and revalidated after restore.
- E2E: approved human-performed action creates follow-up and outcome evidence.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Safety & Task Loop module.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): Task, Approval, Outcome ownership.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): backend approval authority checks.
- [.memory-bank/states/safety-action-lifecycle.md](../states/safety-action-lifecycle.md): approval, human-performed action task, and follow-up boundary.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): audit/export refs for tasks, approvals, and outcomes.
- [.memory-bank/states/plants/plant-and-access-lifecycle.md](../states/plants/plant-and-access-lifecycle.md): global archived-Plant operational guard.

## Feature-Local Design Pressure

- Resolved by the linked Task/Approval/Outcome data, lifecycle, HTTP, real
  `task_follow_up` runtime, Timeline, and verification subject specs.

## Behavior specs

- `.memory-bank/behavior-specs/FT-012-BHV-001-approval-follow-up-outcome.behavior.json`
- `.memory-bank/behavior-specs/FT-012-BHV-002-retry-conflict-archive.behavior.json`
- `.memory-bank/behavior-specs/FT-012-BHV-003-real-agent-ordinary-task.behavior.json`

## SDD Design Gate

- Global/shared status: complete; `AD-008` and Safety Action Lifecycle define the exact
  safe-task versus physical-action route; `AD-007` and Plant lifecycle define
  retained-but-frozen records and restore revalidation.
- Feature-local status: complete. The canonical design defines closed
  Task/Approval/Outcome states, exact FT-011 handoff and expiry reuse,
  transactional approval/action/follow-up/outcome uniqueness, persisted
  idempotency fingerprints, protected HTTP commands, Timeline refs, archive
  races, and the real typed `task_follow_up` path. No scheduler, worker,
  outbox, device effect, or second proposal state machine is introduced.
