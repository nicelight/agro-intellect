---
description: FT-013 - Safety Gate for physical-action advice.
status: draft
lifecycle: planned
parent_epic: EP-002
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-013-safety-gate-physical-action-advice.md
---
# FT-013 Safety Gate for Physical-Action Advice

## Parent Epic

- [EP-002 Agent Advisory and Safety Loop](../epics/EP-002-agent-advisory-safety-loop.md): agent advisory, communication boundaries, and safety loop.

## Purpose

Define the Safety Gate that detects physical-action advice or wording, fails closed without required inputs, and prevents immediate plant-system commands from reaching the user or task lifecycle as cleared actions.

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): FR-004, FR-014, Safety Gate actor definition, physical-action edge cases, acceptance criteria, and verification strategy.
- [.memory-bank/requirements.md](../requirements.md): REQ-004 freshness coverage and Safety Gate portions of REQ-009.
- [.memory-bank/constitution.md](../constitution.md): human gate for physical actions, bounded autonomy, and fail-closed safety expectations.
- [.memory-bank/spec-index.md](../spec-index.md): route map for safety approval lifecycle, pH/EC freshness, companion output, and task follow-up design areas.
- [.memory-bank/testing/index.md](../testing/index.md): safety, freshness, and user-visible action-advice gates.

## Use Cases

- Safety Gate detects wording that instructs or implies physical plant-system action.
- Safety Gate blocks physical-action advice when fresh data, safety check, or human approval is missing.
- pH/EC-dependent physical action requires pH/EC freshness for approval within 2 hours.
- High-risk manual interventions such as pruning, transplanting, and root trimming go through Safety Gate in the first demo.
- Companion responses and UI notes are checked before display when they contain or imply physical action.
- Unsafe advice is converted into safe pending-approval wording or blocked from display.

## Acceptance Criteria

- The system blocks any immediate physical-action command without fresh data, safety check, and human approval.
- Physical actions include changing pH, changing EC, changing solution, changing pumps, changing dosing, changing light regime, and similar plant-system interventions.
- pH/EC measurements are fresh for physical action approval for up to 2 hours.
- First-demo Safety Gate also covers high-risk manual interventions such as pruning, transplanting, and root trimming.
- Low-risk manual observations or checks do not require approval unless they become physical interventions.
- Safety Gate may convert risky recommendations into pending action proposals or pending approval tasks.
- User-visible outputs, including Companion responses and UI spoiler notes, pass a final safety check before display when they contain or imply a physical action.
- Any user-visible phrase that instructs or implies a physical action fails closed into Safety Gate review.
- Safety Gate does not issue direct action commands or automated device instructions.

## Edge Cases / Failure Modes

- pH/EC is older than 2 hours for physical action approval: block action flow and request fresh measurement.
- Physical-action advice appears in Companion output, UI spoiler note, or quoted detail reply without clearance: block display or replace with safe pending-approval wording.
- Safety Gate is unavailable, uncertain, or cannot classify a risky phrase: fail closed.
- Hydroponics Advisor or another agent tries to express mandatory dosing/action wording: fail closed into Safety Gate review.
- A low-risk check is misclassified as physical intervention: require classification correction before approval/task routing.
- Safety Gate output is treated as approval: reject; approval semantics are owned by FT-014.

## Test Strategy Pointers

- `policy:ph-ec-approval-freshness` for 2-hour pH/EC freshness before physical-action approval.
- `policy:safety-gate-physical-actions` for pH/EC, solution, pumps, light, dosing, and high-risk manual interventions.
- `policy:user-visible-action-advice-fail-closed` for Companion responses and UI notes containing physical-action language.
- `integration:safety-block-to-pending-approval` for converting risky advice to pending proposal/task.
- `policy:no-direct-action-command` for forbidding device commands and immediate physical-action instructions.

## Constraints / Invariants

- Physical plant-system changes require fresh data, Safety Gate pass, and human approval.
- Safety Gate fail-closed behavior has priority over user-facing wording.
- No automated device command or physical actuation is in MVP scope.
- Safety Gate can block or route to pending approval; it does not approve actions itself.
- Approval records and unlock semantics are owned by FT-014 and coordinated with FT-008.

## SDD Design Gate

Global `/spec-design` completed the shared backbone. `/spec-improve FT-013` completed the feature-local SDD gate.

- [.memory-bank/states/safety-approval.md](../states/safety-approval.md): physical-action classification, freshness windows, fail-closed behavior, and approval semantics.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): safety block/recommendation output routing.
- [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): user-visible display checks for action wording.
- [.memory-bank/states/task-follow-up.md](../states/task-follow-up.md): pending approval/task handoff.
- [.memory-bank/testing/first-demo.md](../testing/first-demo.md): Safety Gate anti-cheat and workflow gates.
- [.memory-bank/tech-specs/FT-013-safety-gate-physical-action-advice.md](../tech-specs/FT-013-safety-gate-physical-action-advice.md): feature-local decisions for deterministic Safety Gate policy, action taxonomy, freshness requirements, `SafetyGateDecision`, outcome semantics, display checks, Bus/UI/task handoffs, API surface, and verification targets.
- [.memory-bank/tech-specs/FT-001-daily-check-in-observations-manual-measurements.md](../tech-specs/FT-001-daily-check-in-observations-manual-measurements.md): pH/EC measurement refs and computed approval freshness inputs.
- [.memory-bank/tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md](../tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md): `safety_block` MessageEnvelope and escalation route.
- [.memory-bank/tech-specs/FT-005-ui-feed-context-hygiene.md](../tech-specs/FT-005-ui-feed-context-hygiene.md): final display safety checks for UI Feed and spoiler notes.

No FT-013 design blocker remains for `/prd-to-tasks FT-013`.
