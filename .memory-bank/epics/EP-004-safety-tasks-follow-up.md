---
description: EP-004 Safety Tasks And Follow-Up.
status: draft
type: epic
epic_id: EP-004
lifecycle: planned
last_updated: 2026-07-27
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
---
# EP-004 Safety Tasks And Follow-Up

## Value

Make physical-action advice safe and accountable by requiring freshness, Safety Gate pass, authorized human approval, human-performed task tracking, and follow-up evidence.

## Features

- [FT-011 Safety Gate Physical-Action Routing](../features/FT-011-safety-gate-physical-action-routing.md)
- [FT-012 Human Approval Tasks And Follow-Up Outcomes](../features/FT-012-human-approval-tasks-follow-up-outcomes.md)

## Success Metrics

- Physical-action wording fails closed when evidence is stale/missing, Safety Gate fails, or actor authority is missing.
- Safe missing/stale-data requests create traceable check or measurement tasks.
- Approval never triggers automated device execution.
- Tasks, approvals, and follow-up outcomes retain Plant/evidence refs that
  audit/history projections can consume without owning their state.

## Acceptance Criteria

- Safety Gate approval remains distinct from Companion governance approval.
- Check/measurement task creation, pending approval records,
  human-performed `action_task` records, and follow-up outcomes are owned by
  the Safety & Task Loop, not Plant Operations.
- Boss can approve for Farm Plants only through Safety Gate rules.
- Engineer can approve only when granted `plant_approve_actions` for the Plant.
- Consultant never approves physical actions in MVP.
- Archived-Plant tasks, approvals, and outcomes remain retained and
  non-operative; restore requires a new request through current authorization,
  freshness, safety, and owning lifecycle guards.

## Constraints / Invariants

- Fresh data alone is never enough for physical action.
- Human approval unlocks only human-performed action tracking.
- No pumps, dosing, pH/EC correction, light-control command, autowatering, or automated actuation in MVP.

## Feature-Local Design Pressure

- Exact action taxonomy and freshness windows.
- Exact pending approval and action-task state model.
- Exact replay/staleness prevention rules.

## Current Boundary Evidence

- FT-011 W1 provider-neutral classification and W2 deterministic Safety
  decision/projection are scheduler-recorded complete from their current
  implementation, independent functional, semantic, and closure evidence; the
  two earlier W1 failed attempts remain immutable history.
- The FT-011 task boundary now ends at one immutable
  `pending_human_approval` decision and inert UI projection. FT-012 W1 is now
  scheduler-recorded complete and owns the implemented PostgreSQL human
  decision, action/ordinary Task, automatic follow-up, and Outcome
  transitions. FT-012 W2 provider-neutral `task_follow_up` runtime is
  explicit-owner `done`.
- Current W1 evidence records `ft012_task_approval_outcomes` as the product
  migration head directly after `ft011_safety_action_decisions`, with
  immutable classified-message dispositions, current authority/evidence
  guards, atomic Approval/Task/follow-up/Outcome writes, archive/no-replay,
  strict HTTP and Timeline contracts, concurrency/rollback, and zero automated
  actuation or Plant-state authority.
- FT-011, FT-012, and EP-004 lifecycle values remain `planned` pending
  explicit feature/epic decisions; no requirement or dependent task is
  promoted by this sync.
- Current code-phase evidence selects no provider/model and claims no
  credential, egress, network, or live-provider result.
