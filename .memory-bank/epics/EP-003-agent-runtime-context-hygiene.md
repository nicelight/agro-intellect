---
description: EP-003 Agent Runtime And Context Hygiene.
status: draft
type: epic
epic_id: EP-003
lifecycle: planned
last_updated: 2026-06-14
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
---
# EP-003 Agent Runtime And Context Hygiene

## Value

Allow product agents to help with actual scoped Plant data while preventing raw model output, UI presentation, unauthorized context, or unapproved governance content from becoming agent facts.

## Features

- [FT-007 Agent Runtime Decisions And MessageEnvelope](../features/FT-007-agent-runtime-decisions-message-envelope.md)
- [FT-008 Agent Chat Bus And UI Feed Context Hygiene](../features/FT-008-agent-chat-bus-ui-feed-context-hygiene.md)
- [FT-009 Vision Observation And Plant State Trust](../features/FT-009-vision-observation-plant-state-trust.md)
- [FT-010 Hydroponics Advisor Missing Data Policy](../features/FT-010-hydroponics-advisor-missing-data-policy.md)

## Success Metrics

- First demo agent behavior is real model-backed over actual scoped Plant data.
- UI Feed and unapproved proposals are never consumed as agent working context.
- Vision outputs remain observations/hypotheses unless human review or follow-up evidence promotes state.
- Advisor output asks for missing/stale critical data instead of inventing evidence.

## Acceptance Criteria

- Agno/model execution is execution layer only, not source of truth.
- Agent outputs pass through project-owned adapter/runtime decision and MessageEnvelope before publication.
- Agent Chat Bus and UI Feed are separate boundaries.
- Fake, mock, hardcoded, or stubbed product-agent outputs are not accepted as runtime/demo behavior.

## Constraints / Invariants

- Single-competence product-agent boundaries are mandatory.
- Raw reasoning, provider history, UI Feed, spoiler notes, raw chat, and unapproved Companion proposals never enter agent working context.
- Agent hypotheses cannot become confirmed Plant state without human review or follow-up evidence.

## Feature-Local Questions For /spec-improve

- Exact MessageEnvelope, BusEventEnvelope, and UIFeedEvent contracts.
- Exact adapter validation and runtime decision flow.
- Exact agent context-builder filters and anti-cheat verification.
