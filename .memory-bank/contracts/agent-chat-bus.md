---
description: Global Agent Chat Bus contract boundary for MVP v2.
status: active
type: contract
last_updated: 2026-06-30
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/ui-feed.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/states/companion-governance.md
---
# Agent Chat Bus

## Scope

Agent Chat Bus is the domain-owned working event stream for agent-consumable context. It is not Agno memory, not UI Feed, not timeline replay, and not a replacement for PostgreSQL/read-model runtime authority.

The verified FT-000 executable baseline does not implement Agent Chat Bus
runtime code. This contract is a global guardrail for future product features;
field refinements and implementation tasks belong to `/prd-to-tasks FT-<NNN>`.

## Contract Scope

- Defines: agent-consumable working event boundary, BusEventEnvelope minimum,
  consumability rules, context-builder constraints, ordering/replay limits, and
  Safety Gate handoff requirements for Bus events.
- Out of scope: raw model/provider messages, UI Feed projection payloads,
  timeline event taxonomy, DB table schemas, or feature-specific event payloads.
- Related specs:
  - [.memory-bank/contracts/message-envelope.md](message-envelope.md): defines
    publishable agent-originated output before Bus/UI projection.
  - [.memory-bank/contracts/ui-feed.md](ui-feed.md): defines human-facing
    projection rules.
  - [.memory-bank/contracts/timeline-event.md](timeline-event.md): defines
    audit/export event rules.

## Publication Rule

Only backend/domain adapters may publish Bus events. Raw Agno/model output, provider history, raw reasoning, UI Feed content, raw chat, admin UI text, unapproved Companion proposals, and timeline replay cannot publish directly to the Bus.

## BusEventEnvelope Minimum

Feature-local specs may add fields, but every Bus event must have:

- `event_id`
- `event_type`
- `created_at`
- `farm_id`
- `plant_id` when Plant-scoped
- `actor_ref` or `source_ref`
- `source_type`
- `source_id`
- `payload`
- `source_refs`
- `consumable_by_agents`
- `authorization_scope`

## Consumability

- `consumable_by_agents=true` is required before event content can enter agent working context.
- UI Feed events are not Bus events.
- Approved governance summary facts can be consumable only when derived from a valid DecisionRecord and must include `safety_gate_authority=not_granted`.
- Unapproved proposals and raw chat remain non-consumable.

## Context Builders

- Context builders must resolve ActorContext and PlantAccessGrant before returning events.
- Agents may receive only scoped Plant/Farm context they are authorized to process.
- Context builders must exclude UI Feed, spoiler notes, raw model reasoning, raw chat, admin notices, and unapproved Companion content.

## Ordering And Replay

- MVP relies on `created_at` and `event_id` for ordering hints.
- Bus payloads are event references and compact consumable facts, not full
  runtime state snapshots.
- Timeline replay cannot rehydrate mutable runtime state or bypass Bus publication rules.
- Feature-level specs define any stricter per-Plant ordering or idempotency requirements before tasks.

## Safety Handoff

- Bus events that imply physical action must route through Safety Gate before user-visible action wording or action-task creation.
- Bus publication alone never authorizes physical action.

## Verification

Tests must prove:

- unauthorized Plant events are filtered out;
- UI Feed/raw chat/unapproved proposal content is absent from agent context;
- raw provider output cannot bypass adapters;
- Safety Gate and DecisionRecord authority remain separate.
