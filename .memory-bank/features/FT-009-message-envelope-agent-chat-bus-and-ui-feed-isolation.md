---
description: Feature FT-009 for MessageEnvelope, Agent Chat Bus, UI Feed projection, and context hygiene.
status: active
owner: product
lifecycle: planned
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md
epic: EP-003
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/contracts/boundary-map.md
  - .memory-bank/tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md
---
# FT-009 MessageEnvelope, Agent Chat Bus, And UI Feed Isolation

## Use Cases

- Agent output becomes a validated MessageEnvelope or remains silent with audit evidence.
- Agent Chat Bus receives only validated agent-consumable events.
- UI Feed displays human-facing cards, prompts, spoiler notes, and messages without becoming agent context.

## Acceptance Criteria

- Agent-originated domain output passes project-owned runtime decision before publication.
- MessageEnvelope and BusEventEnvelope separate agent-consumable working context from UI presentation.
- UI Feed is presentation-only and unavailable as agent working context.
- Raw model output, raw reasoning, UI Feed content, UI spoiler notes, timeline replay,
  raw chat, admin UI text, and unapproved proposals cannot bypass adapters into Bus or agent context.
- Human-facing UI projection can reference agent output without granting agents access to UI text.

## Edge Cases & Failure Modes

- `silent` agent decision produces audit evidence without Bus publication.
- Malformed agent output is rejected or downgraded before publication.
- UI markdown cannot change domain semantics.
- Unapproved CompanionProposal remains human-visible only.

## Test Strategy Pointers

- `test:agent-output.bus-message-ui-isolation`
- `test:harness.loop-permission-observation-trace`
- `test:companion.approved-summary-context-filter`

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): MessageEnvelope, Agent Chat Bus, and UI Feed requirements.
- [.memory-bank/contracts/boundary-map.md](../contracts/boundary-map.md): runtime state to Bus, execution to MessageEnvelope, and MessageEnvelope to UI Feed boundaries.
- [.memory-bank/invariants.md](../invariants.md): publication and UI Feed isolation guardrails.

## SDD Design Gate

Global `/spec-design` and feature-level `/spec-improve FT-009` are complete. Use
[.memory-bank/tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md](../tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md)
as the feature-local design hub before `/prd-to-tasks FT-009`.
