---
description: UI Feed presentation contract and context hygiene rules.
status: active
owner: architecture
last_updated: 2026-05-31
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/spec-index.md
---
# UI Feed

## Purpose

UI Feed is the human-facing presentation stream. It may show statuses, controlled spoiler notes, and safe explanatory summaries, but it is never agent working context.

## UI Feed Event

`UIFeedEvent` contains:

- `event_id`
- `event_type`
- `stream`
- `created_at`
- `source_agent_id` or `source_id`
- `payload`
- `visible_to_agents`
- `consumable_by_agents`

For `ui_spoiler_note`, both `visible_to_agents=false` and `consumable_by_agents=false` are mandatory.

## MVP Event Types

- `agent_silent_decision`
- `ui_spoiler_note`
- `agent_ui_status`
- `system_ui_status`
- `debug_lite_card`
- `approval_prompt`
- `sync_prompt`

## Context Hygiene Rules

- Agents must not receive UI Feed events as working context.
- UI-only explanations and spoiler notes are controlled summaries for the user, not raw chain-of-thought.
- UI Feed snapshots in export artifacts or timeline audit remain snapshots only and do not become source of truth.
- `ui_spoiler_note_ref` in a `MessageEnvelope` is a pointer to UI Feed only, not permission to consume the note.

## Safety Display Rules

- Companion responses and UI notes must pass final safety checks before display when they contain or imply physical action.
- Physical-action wording without Safety Gate clearance must fail closed into pending approval wording or be blocked from display.
- Approval prompts must communicate human-performed task tracking, not automated device execution.
