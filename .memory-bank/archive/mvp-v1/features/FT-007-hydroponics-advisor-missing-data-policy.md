---
description: FT-007 - Hydroponics Advisor and missing data policy.
status: draft
lifecycle: planned
parent_epic: EP-002
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-007-hydroponics-advisor-missing-data-policy.md
  - .memory-bank/tech-specs/FT-001-daily-check-in-observations-manual-measurements.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md
  - .memory-bank/states/safety-approval.md
  - .memory-bank/tech-specs/FT-013-safety-gate-physical-action-advice.md
  - .memory-bank/states/task-follow-up.md
  - .memory-bank/tech-specs/FT-008-tasks-approvals-follow-up-outcomes.md
  - .memory-bank/tech-specs/FT-014-human-approval-action-unlock-semantics.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/testing/first-demo.md
---
# FT-007 Hydroponics Advisor and Missing Data Policy

## Parent Epic

- [EP-002 Agent Advisory and Safety Loop](../epics/EP-002-agent-advisory-safety-loop.md): agent advisory, communication boundaries, and safety loop.

## Purpose

Define the Hydroponics Advisor's reasoning boundary: it can use available hydroponic, environmental, visual, and historical context to produce cautious recommendations and missing-data requests, but it cannot create action tasks, bypass Safety Gate, or issue mandatory physical-action commands.

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): FR-004, FR-013, missing/stale pH/EC handling, Hydroponics Advisor actor definition, edge cases, and verification strategy.
- [.memory-bank/requirements.md](../requirements.md): REQ-004 and advisor portions of REQ-009.
- [.memory-bank/constitution.md](../constitution.md): bounded agent autonomy, human gate for physical actions, no speculation, and KISS.
- [.memory-bank/spec-index.md](../spec-index.md): route map for Hydroponics Advisor policy, pH/EC freshness, and Safety Gate areas.
- [.memory-bank/tech-specs/FT-007-hydroponics-advisor-missing-data-policy.md](../tech-specs/FT-007-hydroponics-advisor-missing-data-policy.md): feature-local advisor input, missing-data policy, cautious wording, MessageEnvelope mapping, Safety Gate handoff, API/service surface, and verification targets.
- [.memory-bank/testing/index.md](../testing/index.md): freshness, cautious recommendation, and safety boundary verification.

## Use Cases

- Hydroponics Advisor reasons over pH, EC, temperature, humidity, light, solution context, visual observations, and history when available.
- Hydroponics Advisor identifies missing critical data and asks for targeted measurements or context.
- Missing or stale pH/EC blocks solution-related advice that depends on those values.
- Hydroponics Advisor emits cautious recommendations that can be reviewed by Safety Gate when they contain or imply physical action.
- Hydroponics Advisor stays advisory and leaves task creation to Task & Follow-up and approval semantics to the dedicated approval feature.

## Acceptance Criteria

- Hydroponics Advisor reasons over pH, EC, temperature, humidity, light, solution context, visual observations, and history when available.
- Hydroponics Advisor issues cautious recommendations and asks for missing critical data.
- Hydroponics recommendations that depend on pH/EC request fresh measurements when pH/EC is missing or stale for analysis.
- pH/EC measurements are fresh for analysis for up to 24 hours.
- Hydroponics Advisor does not create action tasks directly.
- Hydroponics Advisor does not bypass Safety Gate.
- Hydroponics Advisor does not issue mandatory dosing or physical-action commands.
- Physical-action advice or wording is routed to the Safety Gate feature instead of being treated as cleared advice.

## Edge Cases / Failure Modes

- pH/EC is missing or older than 24 hours for analysis: request measurement before solution-related analysis.
- Environmental or solution context is missing for a recommendation that depends on it: ask a targeted clarification instead of guessing.
- Hydroponics Advisor suggests mandatory dosing, immediate correction, or direct device/system changes: fail closed into Safety Gate ownership.
- Hydroponics Advisor attempts to create an action task directly: reject and route through approval/task lifecycle features.
- Advisor output is uncertain but presented as confirmed diagnosis: reject or downgrade to cautious hypothesis.

## Test Strategy Pointers

- `policy:ph-ec-analysis-freshness` for 24-hour analysis freshness and missing measurement requests.
- `workflow:missing-or-stale-measurement-task` for targeted missing-data requests that can feed Task & Follow-up.
- `policy:cautious-hydroponics-advice` for non-mandatory recommendation wording and uncertainty.
- `policy:advisor-no-action-task` for preventing direct action-task creation.
- `policy:advisor-safety-gate-boundary` for routing physical-action advice to Safety Gate.

## Constraints / Invariants

- Hydroponics Advisor is advisory and cannot create action tasks directly.
- Hydroponics Advisor cannot bypass Safety Gate.
- Missing critical data produces clarification or measurement requests, not confident action advice.
- No automated device command or physical actuation is in MVP scope.
- Human approval and action unlock semantics are owned by FT-014; task lifecycle is coordinated with FT-008.

## SDD Design Gate

Global `/spec-design` completed the shared backbone. Feature-local `/spec-improve FT-007` is complete.

Normative design links:

- [.memory-bank/tech-specs/FT-007-hydroponics-advisor-missing-data-policy.md](../tech-specs/FT-007-hydroponics-advisor-missing-data-policy.md): advisor input context, missing/stale data policy, clarification-vs-task handoff, cautious wording, MessageEnvelope mapping, Safety Gate handoff, API/service surface, and verification targets.
- [.memory-bank/tech-specs/FT-001-daily-check-in-observations-manual-measurements.md](../tech-specs/FT-001-daily-check-in-observations-manual-measurements.md): pH/EC manual measurement refs, provenance, and 24-hour analysis freshness.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): recommendation, clarification, task request, and safety block output contract.
- [.memory-bank/tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md](../tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md): agent runtime decision and adapter validation boundary.
- [.memory-bank/states/safety-approval.md](../states/safety-approval.md): freshness windows, physical-action fail-closed behavior, and approval requirements.
- [.memory-bank/tech-specs/FT-013-safety-gate-physical-action-advice.md](../tech-specs/FT-013-safety-gate-physical-action-advice.md): physical-action detection, display checks, and Safety Gate decisions.
- [.memory-bank/states/task-follow-up.md](../states/task-follow-up.md): check/measurement task types and creation rules.
- [.memory-bank/tech-specs/FT-008-tasks-approvals-follow-up-outcomes.md](../tech-specs/FT-008-tasks-approvals-follow-up-outcomes.md): task request handoff and prohibition on direct action-task creation.
- [.memory-bank/tech-specs/FT-014-human-approval-action-unlock-semantics.md](../tech-specs/FT-014-human-approval-action-unlock-semantics.md): pending approval and action unlock boundaries.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): runtime authority for advisor context refs.
- [.memory-bank/testing/first-demo.md](../testing/first-demo.md): Safety Gate, pH/EC freshness, task/follow-up, and anti-cheat gates.

No FT-007 blocker remains for `/prd-to-tasks FT-007`. FT-007 stays advisory: it can request low-risk check/measurement task handoff through FT-008 and can route physical-action wording to FT-013, but it cannot create action tasks, approval records, or device commands.
