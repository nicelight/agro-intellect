---
description: Feature FT-013 for check tasks, measurement tasks, pending approval, human-performed action tasks, and follow-up outcomes.
status: draft
lifecycle: planned
spec_design_status: needs_spec_improve
epic: EP-004
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/states/lifecycle-map.md
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

Global `/spec-design` is complete. Before `/prd-to-tasks FT-013`, run
`/spec-improve FT-013` using the completed backbone docs: [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md), [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md), [.memory-bank/states/core-lifecycles.md](../states/core-lifecycles.md), [.memory-bank/contracts/index.md](../contracts/index.md), and [.memory-bank/testing/index.md](../testing/index.md). `/spec-improve` must decide task types, status lifecycle,
approval records, action unlock semantics, outcome fields, and evidence refs.
