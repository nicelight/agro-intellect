---
description: Feature FT-013 for check tasks, measurement tasks, pending approval, human-performed action tasks, and follow-up outcomes.
status: active
owner: product
lifecycle: planned
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-013-tasks-approvals-and-follow-up-outcomes.md
epic: EP-004
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/states/lifecycle-map.md
  - .memory-bank/tech-specs/FT-013-tasks-approvals-and-follow-up-outcomes.md
---
# FT-013 Tasks, Approvals, And Follow-Up Outcomes

## Use Cases

- Advisor or Companion creates safe check/measurement/follow-up task requests through backend rules.
- Safety-cleared physical-action proposal becomes a pending approval path.
- Authorized human approval creates a human-performed `action_task`.
- Follow-up captures improved/worsened/unchanged/no-data outcome with evidence refs.

## Acceptance Criteria

- Tasks, approvals, and outcomes are actor/Farm/Plant scoped.
- Check tasks and measurement tasks do not require physical-action approval.
- `action_task` is created only after Safety Gate pass and authorized human approval.
- No task or approval triggers automated device execution in MVP.
- Follow-up outcomes preserve evidence and audit trail.
- Consultant does not create domain task/recommendation records by default.

## Edge Cases & Failure Modes

- Missing PlantAccessGrant blocks task mutation.
- Rejected approval does not create action task.
- Superseded governance proposal cannot create operative task effects.
- Follow-up without data is represented explicitly rather than backfilling success.

## Test Strategy Pointers

- `test:tasks.approval-action-follow-up-no-actuation`
- `test:plant.authorized-daily-flow`
- `test:safety-gate.fail-closed-approval-boundary`

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): tasks, approvals, and follow-up requirements.
- [.memory-bank/states/lifecycle-map.md](../states/lifecycle-map.md): Task/Approval/Outcome and physical-action lifecycle hints.
- [.memory-bank/user-scenarios.md](../user-scenarios.md): Safety-gated recommendation becomes human-performed task.

## SDD Design Gate

Global `/spec-design` and feature-level `/spec-improve FT-013` are complete. Use
[.memory-bank/tech-specs/FT-013-tasks-approvals-and-follow-up-outcomes.md](../tech-specs/FT-013-tasks-approvals-and-follow-up-outcomes.md)
as the feature-local design hub before `/prd-to-tasks FT-013`.
