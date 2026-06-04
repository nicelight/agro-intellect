---
description: Feature FT-009 for MessageEnvelope, Agent Chat Bus, UI Feed projection, and context hygiene.
status: draft
lifecycle: planned
spec_design_status: needs_spec_improve
epic: EP-003
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/contracts/boundary-map.md
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

Global `/spec-design` is complete. Before `/prd-to-tasks FT-009`, run
`/spec-improve FT-009` using the completed backbone docs: [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md), [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md), [.memory-bank/states/core-lifecycles.md](../states/core-lifecycles.md), [.memory-bank/contracts/index.md](../contracts/index.md), and [.memory-bank/testing/index.md](../testing/index.md). `/spec-improve` must decide runtime decision states, envelope
contracts, Bus publication rules, UI Feed projection rules, context filtering, and
anti-cheat tests.
