---
description: Feature-local SDD tech spec for FT-005 UI Feed and context hygiene.
status: active
owner: architecture
last_updated: 2026-05-31
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/features/FT-005-ui-feed-context-hygiene.md
  - .memory-bank/spec-index.md
---
# FT-005 UI Feed and Context Hygiene Tech Spec

## Scope

This spec closes the feature-local SDD design gate for FT-005 before `/prd-to-tasks FT-005`.

FT-005 owns:

- `UIFeedEvent` schema and event type payload minimums;
- controlled `ui_spoiler_note` behavior;
- `ui_spoiler_note_ref` target validation support;
- presentation-only UI Feed storage/read behavior;
- context filtering that prevents UI Feed from becoming agent input;
- raw-reasoning, fact, label, and training-data hygiene rules for UI-only content.

FT-005 does not own Agent Chat Bus publication, `MessageEnvelope` schema, Safety Gate classification, human approval semantics, or the full PWA screen layout.

## Normative Inputs

- [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): global UI Feed event, event types, context hygiene, and safety display rules.
- [.memory-bank/tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md](FT-012-agent-runtime-decisions-message-envelope-output-contracts.md): `ui_spoiler_note_ref` pointer validation and concise-output rules.
- [.memory-bank/tech-specs/FT-004-agent-chat-bus-event-stream-publication-boundary.md](FT-004-agent-chat-bus-event-stream-publication-boundary.md): Bus context filtering and anti-cheat boundary.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): `ui_spoiler_note_ref` contract.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): optional UI Feed audit/export snapshots.
- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): UI Feed publication module boundary.
- [.memory-bank/testing/index.md](../testing/index.md): UI Feed, context filtering, and raw-reasoning gates.
- [.memory-bank/invariants.md](../invariants.md): UI Feed and raw chain-of-thought prohibitions.

## Design Decisions

### UI Feed Presentation Stream

- UI Feed is a local human-facing presentation stream.
- The MVP should persist UI Feed events in a separate local read model/table or equivalent backend-owned presentation store so `ui_spoiler_note_ref` can be validated and the UI can render recent events.
- UI Feed storage is not runtime authority for plant state, agent facts, dataset labels, tasks, approvals, or sync state.
- UI Feed events may reference Bus events, MessageEnvelope refs, timeline events, tasks, approvals, or sync state, but they do not replace those sources.
- UI Feed events are never read by agent context builders.

Recommended read-model boundary:

| Field | Rule |
|---|---|
| `ui_event_id` | Globally unique UI Feed event ID, recommended prefix `ui_evt_`. |
| `event_type` | One MVP UI Feed event type. |
| `stream` | Must equal `ui_feed`. |
| `created_at` | Timezone-aware timestamp. |
| `source_agent_id` / `source_id` | Source identifier; agent source when agent-related. |
| `payload` | Structured presentation payload. |
| `visible_to_agents` | Must be `false` for MVP UI Feed events. |
| `consumable_by_agents` | Must be `false` for MVP UI Feed events. |
| `source_refs` | Optional refs to Bus, timeline, MessageEnvelope, task, approval, or sync records. |

### Event Type Payload Minimums

| Event type | Minimum payload | Notes |
|---|---|---|
| `agent_silent_decision` | `agent_id`, `audit_ref`, safe status text or reason code | Optional user-visible trace of silent work; never Bus context. |
| `ui_spoiler_note` | `source_message_ref`, `spoiler_title`, controlled summary `text` | `visible_to_agents=false` and `consumable_by_agents=false` are mandatory. |
| `agent_ui_status` | `agent_id`, status code/text, source refs | Presentation status only. |
| `system_ui_status` | system status code/text, source refs | Presentation status only. |
| `debug_lite_card` | safe debug title/details, source refs | Must not expose secrets, raw reasoning, provider traces, or local absolute paths. |
| `approval_prompt` | approval/proposal refs and display-safe prompt text | Must pass Safety Gate display rules when physical action is implied. |
| `sync_prompt` | sync scope, `local_only` status, storage bytes/threshold | Must not imply server sync or mutate sync status. |

Payloads must be structured. UI Feed must not store raw provider messages, hidden chain-of-thought, Agno memory/storage, unredacted secrets, or arbitrary unsanitized logs.

### Controlled Spoiler Notes

`ui_spoiler_note` is a controlled user explanation, not model reasoning.

Rules:

- Default spoiler title may be `поразмыслил`.
- The text explains assumptions, uncertainty, missing data, or high-level rationale in user-safe prose.
- It must not contain raw chain-of-thought, hidden reasoning, prompt content, provider traces, or tool internals.
- It must not introduce facts that are absent from source refs.
- It must not become a dataset label, plant state, or agent-consumable context.
- A `ui_spoiler_note_ref` from `MessageEnvelope` points only to the UI Feed event ID; it does not grant agents permission to read the note.
- If a spoiler includes or implies physical-action wording, it must pass the same final display safety check as other user-visible output.

Size guidance:

- Spoiler notes may be longer than Agent Chat Bus conclusions.
- Keep spoiler notes concise enough for MVP display, usually 2-10 short lines.
- Quoted detail replies in Agent Chat Bus remain shorter than the related UI spoiler when both exist.

### Context Filtering

Agent context builders must use an allowlist:

- allowed source: Agent Chat Bus events with `consumable_by_agents=true`;
- forbidden sources: UI Feed store, spoiler notes, UI snapshots, raw reasoning, Agno memory/storage, provider history, screenshots, and debug-lite cards.

Tests must prove that:

- UI Feed event IDs cannot be dereferenced by the agent context builder;
- `ui_spoiler_note_ref` remains a pointer string and is not expanded into agent input;
- exported/timeline snapshots of UI Feed events do not become agent context;
- UI-only content cannot update plant state, dataset labels, or `can_train_on`.

### Timeline And Export Snapshots

- Timeline may store `ui_spoiler_note_snapshot` for audit/export when needed.
- Snapshot events remain audit/export copies and are not UI authority, agent context, or mutable state.
- Export snapshots may include UI Feed copies only as presentation/audit context, never as trainable labels without a separate dataset governance decision.

### Display Safety

- UI Feed publication must redact secrets before persistence/display.
- Companion responses, spoiler notes, quoted detail display, and approval prompts must pass final safety display checks when they contain or imply physical actions.
- Until Safety Gate display checks are implemented, physical-action wording in UI Feed must fail closed by blocking display or replacing it with safe pending-review wording.

## API Surface

Minimum FT-005-owned API/read surface:

- `GET /api/ui-feed/events`
  - returns recent UI Feed presentation events for the operator UI;
  - supports pagination/filtering as implementation detail;
  - never intended for agent context.
- Internal UI Feed publication service
  - validates `UIFeedEvent`, redacts secrets, applies context-hygiene checks, and writes presentation events.

There must be no public API that lets agents retrieve UI Feed as working context.

## Verification Targets

Required before FT-005 can be marked implemented:

- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- Schema tests for `UIFeedEvent` required fields, `stream=ui_feed`, event type set, timezone-aware `created_at`, and structured payloads.
- Policy tests proving all MVP UI Feed events have `visible_to_agents=false` and `consumable_by_agents=false`.
- `ui_spoiler_note` tests proving pointer refs resolve only to UI Feed events and never to Bus/timeline/non-UI artifacts.
- Context-filtering tests proving agent context builders cannot read UI Feed, expand `ui_spoiler_note_ref`, or consume UI snapshots.
- Raw-reasoning tests proving provider traces, hidden chain-of-thought, Agno memory/storage, and prompt internals are rejected from UI Feed.
- Authority tests proving UI Feed content cannot update plant state, task state, dataset labels, or `can_train_on`.
- Redaction tests proving secrets do not appear in UI Feed events, debug-lite cards, screenshots/e2e artifacts, or API responses.
- Display safety tests proving physical-action wording in UI Feed fails closed without Safety Gate clearance.
- Integration test proving `MessageEnvelope.ui_spoiler_note_ref` can point to an existing non-consumable `ui_spoiler_note` while the note remains unavailable to agents.

## Gaps And Non-Goals

- No FT-005 blocker remains for `/prd-to-tasks FT-005`.
- Exact UI components, layout, routing, and PWA screen states are owned by FT-011.
- Physical-action detection and approval prompts are refined by FT-013 and FT-014.
- Full observability dashboards, raw debug log viewers, and model reasoning capture are outside FT-005 MVP scope.
