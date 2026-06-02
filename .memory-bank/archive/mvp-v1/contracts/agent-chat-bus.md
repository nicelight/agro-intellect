---
description: Agent Chat Bus event stream and publication boundary contract.
status: active
owner: architecture
last_updated: 2026-05-31
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/spec-index.md
---
# Agent Chat Bus

## Purpose

Agent Chat Bus is the domain-owned working event stream for agent-consumable events. It lets single-competence agents observe shared context without directly commanding each other.

## Bus Event Envelope

Every Bus event uses `BusEventEnvelope`:

- `event_id`
- `event_type`
- `created_at`
- `source_type`
- `source_id`
- `topic`
- `payload`
- `consumable_by_agents`
- `audit_log`

## MVP Event Types

- `user_message`
- `user_photo`
- `agent_conclusion`
- `agent_clarification_request`
- `agent_quoted_detail_reply`
- `agent_team_signal`
- `safety_block`
- `task_created`
- `human_confirmation`
- `system_event`
- `sync_event`

Feature-local specs may add payload details, but cannot add broad event classes without PRD/spec evidence.

## Publication Rules

- Agno invocation is not Bus publication.
- Agent-originated work output must pass through runtime decision handling and `MessageEnvelope` before Bus publication.
- `silent` creates no Bus event.
- UI Feed events, spoiler notes, raw reasoning, and presentation-only explanations must not be published as agent-consumable Bus events.
- `consumable_by_agents=true` means the event may be included in agent working context.
- `consumable_by_agents=false` content must be filtered out from agent working context.

## Influence Levels

- Ordinary conclusions and observations are soft influence.
- Team Signals are strong influence and should be rare.
- Safety Blocks are hard stops for the relevant action flow until unlock conditions are satisfied.

## Authority Boundary

Agent Chat Bus is not runtime state authority. State changes must be persisted through PostgreSQL/read model and audited through timeline events where relevant.
