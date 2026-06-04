---
description: Epic EP-004 for Plant state/advisor behavior, Safety Gate, physical-action approval, tasks, and follow-up.
status: draft
lifecycle: planned
epic_id: EP-004
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/states/lifecycle-map.md
---
# EP-004 Safety-Gated Advisory And Task Loop

## Value

Let users receive useful Plant state and hydroponics assistance while keeping physical
actions fail-closed and human-performed. Recommendations, approvals, tasks, and
follow-up outcomes remain separate from automated actuation and Companion governance.

## Features

- FT-011 Plant State Trust And Hydroponics Advisor.
- FT-012 Safety Gate For Physical-Action Advice.
- FT-013 Tasks, Approvals, And Follow-Up Outcomes.

## Success Metrics

- Hydroponics Advisor asks for missing/stale critical data instead of overreaching.
- Physical-action wording is blocked or routed until fresh evidence, Safety Gate pass,
  authorized human approval, and task/action tracking exist.
- Approved physical actions create only human-performed `action_task` records.
- Follow-up outcomes preserve evidence and audit trail.

## Acceptance Criteria

- Agent hypotheses do not become confirmed Plant state without human review or
  follow-up evidence.
- Boss can approve physical-action proposals for Farm Plants only through Safety Gate
  rules.
- Engineer can approve only with per-Plant `plant_approve_actions`.
- Consultant never approves physical actions in MVP.
- Governance DecisionRecord never substitutes for Safety Gate approval.

## Constraints / Invariants

- Fresh data is required but never sufficient by itself for physical action.
- Human approval does not authorize automated device execution.
- Safety Gate and task/action unlock semantics must be refined by `/spec-design` and
  feature-level `/spec-improve` before task decomposition.

## Verification Targets

- `test:plant-state.advisor-trust-missing-data`
- `test:safety-gate.fail-closed-approval-boundary`
- `test:tasks.approval-action-follow-up-no-actuation`
