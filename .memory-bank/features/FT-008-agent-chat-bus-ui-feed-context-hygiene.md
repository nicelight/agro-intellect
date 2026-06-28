---
description: FT-008 Agent Chat Bus And UI Feed Context Hygiene.
status: draft
type: feature
feature_id: FT-008
epic: EP-003
lifecycle: planned
last_updated: 2026-06-26
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/contracts/boundary-map.md
---
# FT-008 Agent Chat Bus And UI Feed Context Hygiene

## Use Cases

- Validated domain events are published to the Agent Chat Bus as agent-consumable working context.
- Human-facing messages, cards, prompts, tasks, approvals, history, and storage status are projected to UI Feed.
- UI Feed remains unavailable as agent working context.
- Context builders filter by ActorContext, PlantAccessGrant, and approved consumability flags.

## Acceptance Criteria

- Agent Chat Bus is the domain-owned working stream for agents.
- UI Feed is presentation-only.
- UI Feed, spoiler notes, UI markdown, raw chat, admin notices, and unapproved Companion proposals do not enter agent working context.
- MessageEnvelope and Bus/UI projections preserve source refs and consumability boundaries.

## Edge Cases & Failure Modes

- Presentation-only summary cannot be replayed into agent context.
- Unauthorized Plant context cannot leak through Bus or UI projections.
- Raw CompanionProposal content remains human-visible only until a valid DecisionRecord produces compact approved governance summary facts.
- UI spoiler notes remain `visible_to_agents=false` and `consumable_by_agents=false` when represented.

## Verification Targets

- Unit: context filtering and consumability flags.
- Integration: BusEventEnvelope and UIFeedEvent projection boundaries after specs define them.
- Anti-cheat: UI Feed and raw chat are absent from agent context builder fixtures.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Bus/UI module boundary.
- [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md): agent-consumable event stream rules.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): MessageEnvelope projection boundary.
- [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): global presentation-only UI Feed contract.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): audit/export refs that cannot publish directly to Bus.

## SDD Design Gate

Global `/spec-design` is complete for shared backbone/spec routing. Then run `/prd-to-tasks FT-008`; it must define exact Bus/UI contracts, context-builder filters, UI Feed projection rules, event payloads, and anti-cheat verification during its feature-level SDD design phase before writing tasks. Use standalone `/spec-improve FT-008` only for repair or advanced refresh without task generation.
