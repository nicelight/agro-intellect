---
description: Timeline JSONL append-only audit/export event contract.
status: active
owner: architecture
last_updated: 2026-05-31
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/spec-index.md
---
# Timeline Event

## Purpose

`timeline.jsonl` records append-only audit/export events for daily observations, photo uploads, agent conclusions, task creation, approvals, safety blocks, sync events, and other traceable domain activity.

It is not primary mutable state.

## Event Envelope

Each line is one JSON event. The global envelope contains:

- `event_id`: unique event id;
- `event_type`: event type;
- `created_at`: timestamp;
- `source_type`: `user`, `agent`, `system`, `task`, `sync`, or `safety`;
- `source_id`: source identifier;
- `topic`: routing/audit label;
- `payload`: event-specific data;
- `consumable_by_agents`: eligibility marker for validated Bus publication through the FT-004 Bus publication service;
- `audit_log`: adapter/runtime validation evidence where applicable.

`timeline.consumable_by_agents=true` does not make a timeline event agent working context by itself. Agent context builders must read only validated Agent Chat Bus events; timeline events may be used as `source_ref` evidence during Bus publication, not as authority or replay input.

## MVP Event Types

Timeline may record the MVP event set used by the domain flow:

- `user_message`
- `user_photo`
- `manual_measurement`
- `daily_observation`
- `agent_conclusion`
- `agent_clarification_request`
- `agent_quoted_detail_reply`
- `agent_team_signal`
- `safety_block`
- `task_created`
- `task_updated`
- `human_confirmation`
- `human_approval`
- `human_rejection`
- `system_event`
- `sync_event`
- `ui_spoiler_note_snapshot`

Feature-local specs may refine payloads, but must keep append-only behavior and required identifiers.

## Mandatory Photo Binding

For `event_type=user_photo`, `payload.plant_id` is mandatory and must not be inferred only from `topic`, file path, folder, or UI state.

Minimum `user_photo` payload:

- `plant_id`
- `photo_id`
- `photo_type`

## Append-Only Rules

- Existing lines must not be mutated to represent current state.
- Corrections are represented as new events.
- Timeline import/export may rebuild evidence trails, but current mutable state remains PostgreSQL/read-model authority.
- UI Feed events may be snapshotted for export/audit, but that snapshot does not become agent context or UI authority.
