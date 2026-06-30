---
description: FT-004 - Agent Chat Bus event stream and publication boundary.
status: draft
lifecycle: planned
parent_epic: EP-002
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-004-agent-chat-bus-event-stream-publication-boundary.md
---
# FT-004 Agent Chat Bus Event Stream and Publication Boundary

## Parent Epic

- [EP-002 Agent Advisory and Safety Loop](../epics/EP-002-agent-advisory-safety-loop.md): agent advisory, communication boundaries, and safety loop.

## Purpose

Define the domain-owned Agent Chat Bus as the agent-consumable event stream. This feature owns `BusEventEnvelope`, Bus event types, `consumable_by_agents`, and the publication boundary that keeps Agno execution from becoming domain publication.

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): FR-007, Agent Chat Bus acceptance criteria, authority model, edge cases, and verification strategy.
- [.memory-bank/requirements.md](../requirements.md): REQ-006 Bus and Agno boundary coverage.
- [.memory-bank/constitution.md](../constitution.md): source-of-truth discipline, bounded agent autonomy, no speculation, and KISS.
- [.memory-bank/spec-index.md](../spec-index.md): route map for Agent Chat Bus and Agno execution boundary design areas.
- [.memory-bank/testing/index.md](../testing/index.md): agent adapter and Bus envelope verification.

## Use Cases

- User messages, user photos, human confirmations, task creation, safety blocks, system events, and sync events are published only when they are agent-consumable domain events.
- Agent Chat Bus readers consume `BusEventEnvelope` records and independently decide whether to react.
- Agno Agent, Workflow, Team, memory, storage, or step output is treated as execution output until a project-owned domain adapter chooses whether to publish a Bus event.
- Events that are not intended for agent working context remain outside the Bus or carry `consumable_by_agents=false` in their appropriate presentation/audit layer.

## Acceptance Criteria

- The system uses a domain-owned Agent Chat Bus for consumable agent events.
- Agno invocation does not equal Agent Chat Bus publication.
- Every Agent Chat Bus event passes through `BusEventEnvelope`.
- Agent Chat Bus events include `consumable_by_agents`.
- MVP Bus event types include `user_message`, `user_photo`, `agent_conclusion`, `agent_clarification_request`, `agent_quoted_detail_reply`, `agent_team_signal`, `safety_block`, `task_created`, `human_confirmation`, `system_event`, and `sync_event`.
- Agent-originated work output cannot enter the Bus directly from Agno; the output-contract feature owns the agent `MessageEnvelope` payload rules before such output can be published.
- UI Feed events and UI-only explanations are not Agent Chat Bus publications.
- Agent Chat Bus is a working domain stream, not runtime authority for mutable state and not a replacement for `timeline.jsonl`.

## Edge Cases / Failure Modes

- Raw Agno output, workflow events, Team synthesis, memory, or storage attempts to enter Agent Chat Bus directly: reject or require the domain publication boundary.
- A Bus event omits `BusEventEnvelope`, `event_type`, source identifiers, topic, payload, or `consumable_by_agents`: reject.
- A UI Feed event or spoiler note is accidentally routed as an agent-consumable Bus event: reject or reroute to UI Feed ownership.
- An unsupported Bus event type is published: reject until the type is added through the appropriate PRD/spec route.
- Publication attempts treat Bus events as mutable runtime state: reject and route mutable state changes through PostgreSQL/read-model authority.

## Test Strategy Pointers

- `schema:bus-event-envelope` for Bus event fields, event type set, `consumable_by_agents`, source identifiers, payload, and audit metadata.
- `policy:agno-adapter-boundary` for Agno output not entering Agent Chat Bus without a project-owned publication boundary.
- `policy:agent-chat-bus-event-types` for the MVP event type set.
- `policy:ui-feed-not-bus` for keeping presentation-only events outside agent working context.
- `integration:bus-publication-boundary` for user, task, safety, system, sync, and agent-originated events entering through one domain boundary.

## Constraints / Invariants

- Agent Chat Bus is the domain working stream for agent-consumable events.
- Agno is an execution SDK, not source of truth and not the Agent Chat Bus.
- Agents have one competence boundary and do not directly command each other.
- Bus publication is a domain decision, not a side effect of invocation.
- UI Feed remains presentation only.
- PostgreSQL/read model remains mutable runtime authority; `timeline.jsonl` remains append-only audit/export.

## SDD Design Gate

Global `/spec-design` completed the shared backbone. `/spec-improve FT-004` completed the feature-local SDD gate.

- [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md): `BusEventEnvelope`, event type set, and publication rules.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): publishable agent output payload rules.
- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Agno invocation/publication separation and Bus authority boundary.
- [.memory-bank/testing/first-demo.md](../testing/first-demo.md): adapter and Bus anti-cheat gates.
- [.memory-bank/tech-specs/FT-004-agent-chat-bus-event-stream-publication-boundary.md](../tech-specs/FT-004-agent-chat-bus-event-stream-publication-boundary.md): feature-local decisions for Bus working-stream persistence, envelope validation, event payload minimums, publication service, context filtering, influence levels, and verification targets.

No FT-004 design blocker remains for `/prd-to-tasks FT-004`.
