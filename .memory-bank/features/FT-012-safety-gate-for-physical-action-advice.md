---
description: Feature FT-012 for Safety Gate routing and fail-closed physical-action advice.
status: active
owner: product
lifecycle: planned
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-012-safety-gate-for-physical-action-advice.md
epic: EP-004
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/tech-specs/FT-012-safety-gate-for-physical-action-advice.md
---
# FT-012 Safety Gate For Physical-Action Advice

## Use Cases

- Agent output implies pH/EC change, solution change, pump/light/dosing change, pruning, transplanting, or other physical action.
- Safety Gate blocks, routes, or clears wording based on evidence, freshness, policy, and approval state.
- Authorized human sees pending physical-action proposal only after Safety Gate path permits it.

## Acceptance Criteria

- Physical-action advice fails closed when required evidence is missing/stale, Safety Gate fails, or actor approval authority is missing.
- Fresh data alone is insufficient for physical action.
- Safety Gate approval is separate from Companion governance approval.
- Boss can approve physical-action proposals for Farm Plants; Engineer can approve only with `plant_approve_actions`; Consultant never approves.
- Human approval unlocks only human-performed task tracking, never device execution.

## Edge Cases & Failure Modes

- Governance DecisionRecord cannot replace Safety Gate approval.
- UI wording cannot imply immediate physical action before clearance.
- Expired/stale approval context cannot be replayed.
- Safety Gate denial produces visible safe next step or missing-data request.

## Test Strategy Pointers

- `test:safety-gate.fail-closed-approval-boundary`
- `test:tasks.approval-action-follow-up-no-actuation`
- `test:companion.proposal-decision-authority`

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): Safety Gate and physical-action approval requirements.
- [.memory-bank/invariants.md](../invariants.md): Human Gate and NEVER automated actuation guardrails.
- [.memory-bank/user-scenarios.md](../user-scenarios.md): Safety-gated recommendation scenario.

## SDD Design Gate

Global `/spec-design` and feature-level `/spec-improve FT-012` are complete. Use
[.memory-bank/tech-specs/FT-012-safety-gate-for-physical-action-advice.md](../tech-specs/FT-012-safety-gate-for-physical-action-advice.md)
as the feature-local design hub before `/prd-to-tasks FT-012`.
