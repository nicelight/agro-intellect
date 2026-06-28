---
description: FT-012 Human Approval Tasks And Follow-Up Outcomes.
status: draft
type: feature
feature_id: FT-012
epic: EP-004
lifecycle: planned
last_updated: 2026-06-26
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/states/lifecycle-map.md
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
- Follow-up outcome captures improved/worsened/unchanged/no-data style results after specs define exact vocabulary.
- Task and approval records preserve ActorContext, Plant scope, source refs, and audit refs.

## Edge Cases & Failure Modes

- Expired or stale approval cannot create action_task.
- Actor without `plant_approve_actions` cannot approve Plant physical action.
- Replayed or superseded approval cannot unlock action.
- Follow-up cannot mutate confirmed Plant state without required evidence/review rules.

## Verification Targets

- Unit: approval authority and task state transitions after spec defines state model.
- Integration: approval creates action_task only through Safety Gate path.
- E2E: approved human-performed action creates follow-up and outcome evidence.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Safety & Task Loop module.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): Task, Approval, Outcome ownership.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): backend approval authority checks.
- [.memory-bank/states/safety-action-lifecycle.md](../states/safety-action-lifecycle.md): approval, human-performed action task, and follow-up boundary.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): audit/export refs for tasks, approvals, and outcomes.

## SDD Design Gate

Global `/spec-design` is complete for shared backbone/spec routing. Then run `/prd-to-tasks FT-012`; it must define exact task/approval/outcome states, action unlock service, replay prevention, follow-up outcome vocabulary, and tests during its feature-level SDD design phase before writing tasks. Use standalone `/spec-improve FT-012` only for repair or advanced refresh without task generation.
