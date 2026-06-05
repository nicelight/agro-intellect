---
description: Feature FT-011 for Plant State trust statuses, Hydroponics Advisor missing-data behavior, and cautious recommendations.
status: active
owner: product
lifecycle: planned
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-011-plant-state-trust-and-hydroponics-advisor.md
epic: EP-004
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/tech-specs/FT-011-plant-state-trust-and-hydroponics-advisor.md
---
# FT-011 Plant State Trust And Hydroponics Advisor

## Use Cases

- Plant State Agent tracks current confirmed, assumed, probable, unknown, or conflicting state.
- Hydroponics Advisor reviews pH/EC and observations, asks for missing critical data, and gives cautious non-action or routed advice.
- User sees missing-data prompts and trust statuses in the Plant workflow.

## Acceptance Criteria

- Agent-labeled hypotheses cannot become confirmed Plant state without human review or follow-up evidence.
- Missing/stale pH/EC and other required evidence produce clarify or measurement task behavior rather than unsafe recommendation.
- Advisor outputs are scoped by ActorContext and PlantAccessGrant.
- Advice implying physical action is routed to Safety Gate before user-visible action wording or action-task creation.
- Plant State trust statuses are visible enough for first demo.

## Edge Cases & Failure Modes

- Conflicting evidence is represented as conflict, not silently resolved by the model.
- Stale measurements cannot be treated as fresh for action approval.
- Consultant advice cannot create domain task/recommendation records by default.
- Agent memory can inform analysis only when scoped and non-authoritative.

## Test Strategy Pointers

- `test:plant-state.advisor-trust-missing-data`
- `test:safety-gate.fail-closed-approval-boundary`
- `test:harness.memory-scope-permission-non-authority`

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): Plant State trust statuses and Hydroponics Advisor first-demo requirement.
- [.memory-bank/invariants.md](../invariants.md): no agent hypothesis promotion, pH/EC freshness, Safety Gate.
- [.memory-bank/glossary.md](../glossary.md): state and safety terms.

## SDD Design Gate

Global `/spec-design` and feature-level `/spec-improve FT-011` are complete. Use
[.memory-bank/tech-specs/FT-011-plant-state-trust-and-hydroponics-advisor.md](../tech-specs/FT-011-plant-state-trust-and-hydroponics-advisor.md)
as the feature-local design hub before `/prd-to-tasks FT-011`.
