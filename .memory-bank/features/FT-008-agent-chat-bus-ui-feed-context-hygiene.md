---
description: FT-008 Agent Chat Bus And UI Feed Context Hygiene.
status: draft
type: feature
feature_id: FT-008
epic: EP-003
lifecycle: planned
last_updated: 2026-07-12
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
- Every active Plant eventually has exactly one `UIFeedEvent` per deterministic
  roster introduction. The Plant chat/feed UI renders that same event; no copy
  enters Agent Chat Bus. FT-008 reconciles missing batches after failure or
  restart without rolling back Plant creation. Archived Plants receive no new
  projection.
- Archived Plant produces no operational Bus/agent context or new operational
  projection; explicit retained-history UI remains presentation-only.

## Edge Cases & Failure Modes

- Presentation-only summary cannot be replayed into agent context.
- Unauthorized Plant context cannot leak through Bus or UI projections.
- Raw CompanionProposal content remains human-visible only until a valid DecisionRecord produces compact approved governance summary facts.
- UI spoiler notes remain `visible_to_agents=false` and `consumable_by_agents=false` when represented.
- An event prepared before archive cannot publish after archive, and restore
  does not replay it.
- Introduction intent is retained while archived but not projected. After
  restore, a new reconciliation must revalidate current active-Plant state
  before continuing idempotent delivery.

## Verification Targets

- Unit: context filtering and consumability flags.
- Integration: BusEventEnvelope and UIFeedEvent projection boundaries after specs define them.
- Integration: active-Plant scan and durable reconciliation yield exactly eight
  unique, non-agent-consumable `UIFeedEvent` records after retry/restart, with no
  partial batch acceptance or Agent Chat Bus copy.
- Integration: archive race blocks Bus publication and agent context while
  preserving authorized retained-history presentation.
- Anti-cheat: UI Feed and raw chat are absent from agent context builder fixtures.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Bus/UI module boundary.
- [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md): agent-consumable event stream rules.
- [.memory-bank/contracts/agent-roster-bootstrap.md](../contracts/agent-roster-bootstrap.md): deterministic batch/result contract and FT-008 reconciliation ownership.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): MessageEnvelope projection boundary.
- [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): global presentation-only UI Feed contract.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): audit/export refs that cannot publish directly to Bus.
- [.memory-bank/states/plants/plant-and-access-lifecycle.md](../states/plants/plant-and-access-lifecycle.md): archived-Plant publication/context guard.

## Feature-Local Design Pressure

- Exact Bus/UI contracts, context-builder filters, UI Feed projection rules,
  event payloads, and anti-cheat verification.

## SDD Design Gate

- Global/shared status: complete; `AD-007`, `AD-008`, the strict introduction
  batch/result contract, and linked Bus/Message/Safety/Plant lifecycle specs
  define pending classification, durable active-Plant reconciliation, archived
  context, and guarded publication behavior.
- Feature-local status: pending `/prd-to-tasks FT-008` for concrete envelopes,
  filters, projections, ordering, and verification.
