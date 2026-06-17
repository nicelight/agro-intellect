---
description: EP-004 Safety Tasks And Follow-Up.
status: draft
type: epic
epic_id: EP-004
lifecycle: planned
last_updated: 2026-06-14
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
- Approval never triggers automated device execution.
- Follow-up outcomes remain traceable to approved human-performed tasks.

## Acceptance Criteria

- Safety Gate approval remains distinct from Companion governance approval.
- Boss can approve for Farm Plants only through Safety Gate rules.
- Engineer can approve only when granted `plant_approve_actions` for the Plant.
- Consultant never approves physical actions in MVP.

## Constraints / Invariants

- Fresh data alone is never enough for physical action.
- Human approval unlocks only human-performed action tracking.
- No pumps, dosing, pH/EC correction, light-control command, autowatering, or automated actuation in MVP.

## Feature-Local Questions For /spec-improve

- Exact action taxonomy and freshness windows.
- Exact pending approval and action-task state model.
- Exact replay/staleness prevention rules.
