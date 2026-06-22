---
description: Foundation-scoped executable contract for the critical smoke path before product tasking.
status: active
owner: architecture
type: contract
last_updated: 2026-06-23
source_of_truth:
  - .memory-bank/foundation.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/invariants.md
  - .memory-bank/testing/index.md
---
# Foundation Critical Path Contract

## Scope

This contract defines the minimum executable contract set that `FT-000`
foundation tasks must prove before product feature tasking.

It is foundation-scoped. It does not create `REQ-000`, `FT-000`, task records,
packets, protocols, implementation plans, public route names, database table
names, provider configuration, or a final foundation gate task id.

Feature-local specs may refine field names and schemas later, but they must not
weaken these Foundation boundaries:

```text
Photo/User input
  -> BusEventEnvelope
  -> Agent invocation
  -> Project-owned adapter
  -> MessageEnvelope
  -> UIFeedEvent projection split
  -> Safety / State / Task transitions
  -> PostgreSQL mutable state + timeline.jsonl append-only audit
  -> photo JSON export snapshot
```

## Contract Records

| ID | Boundary | Foundation proof |
|---|---|---|
| C-FND-001 | `FoundationInput` | Authorized user observation/manual measurement plus optional photo fixture enters the backend with source refs. |
| C-FND-002 | Foundation BusEventEnvelope | Input becomes a domain-owned agent-consumable Bus event, not UI Feed or raw chat. |
| C-FND-003 | `AgentInvocationRecord` | Agent invocation crosses a project-owned adapter boundary with auditable runtime evidence. |
| C-FND-004 | `MessageEnvelope` and `UIFeedEvent` split | Publishable agent output and human presentation are separate records with refs. |
| C-FND-005 | `SafetyRouteResult` and task transition | Safe clarification and physical-action implication route through fail-closed policy. |
| C-FND-006 | Runtime persistence evidence | PostgreSQL/read-model assertions prove mutable state authority. |
| C-FND-007 | `timeline.jsonl` smoke event | Append-only audit/export refs are present and cannot mutate state. |
| C-FND-008 | Photo JSON export snapshot | Export includes photo/source/runtime refs and remains non-authoritative for state. |
| C-FND-009 | Redaction and context hygiene | Secrets, raw provider output, UI Feed, and unauthorized context stay out of agent context and artifacts. |

## C-FND-001 - FoundationInput

`FoundationInput` is the minimal backend input object for the foundation smoke.
It may be delivered by an internal service, integration test fixture, or
smoke-only route selected by `/foundation-to-tasks`.

Minimum fields:

| Field | Requirement |
|---|---|
| `input_id` | Stable local id for the smoke input. |
| `created_at` | Timestamp generated or validated by backend code. |
| `actor_context_ref` | Ref to an authorized ActorContext fixture or record. |
| `farm_id` | Single local Farm id. |
| `plant_id` | Plant id; `tomato_001` is acceptable for the foundation path. |
| `source_type` | `user_observation` or `manual_measurement`. |
| `observation_text` | Optional concise user observation; no secrets or auth material. |
| `manual_measurements` | Optional array of typed manual measurements with metric, value, unit, observed_at, and provenance. |
| `photo_fixture` | Optional local fixture ref with content_type, byte_size, and sha256 or equivalent identity proof. |
| `source_refs` | Canonical refs to accepted input/photo/runtime records. |
| `local_only` | Must be `true` for foundation evidence. |

Rules:

- Missing or unauthorized ActorContext must fail before Bus publication or agent
  invocation.
- A photo fixture must prove byte/file identity, but foundation does not need the
  final product storage layout.
- `FoundationInput` cannot contain raw UI Feed payloads, raw chat history, raw
  provider output, tokens, credentials, API keys, `.env` values, or session
  secrets.

## C-FND-002 - Foundation BusEventEnvelope

The foundation event type is:

```text
foundation.input_recorded.v1
```

Minimum envelope fields are inherited from
[Agent Chat Bus](agent-chat-bus.md). Foundation evidence must include:

| Field | Foundation value |
|---|---|
| `event_id` | Stable Bus event id. |
| `event_type` | `foundation.input_recorded.v1`. |
| `created_at` | Backend timestamp. |
| `farm_id` | Same Farm as `FoundationInput`. |
| `plant_id` | Same Plant as `FoundationInput`. |
| `actor_ref` | Authorized actor or ActorContext ref. |
| `source_type` | `foundation_input`. |
| `source_id` | `FoundationInput.input_id`. |
| `payload` | Redacted summary and refs only; no raw secrets or UI projection. |
| `source_refs` | Input, measurement, and optional photo refs. |
| `consumable_by_agents` | `true` only after backend authorization and context-hygiene checks pass. |
| `authorization_scope` | Farm/Plant scope resolved from ActorContext and PlantAccessGrant. |

Rules:

- UI Feed events, timeline replay, raw chat, raw provider output, and admin UI
  text cannot publish this event.
- Unauthorized Plant scope must fail closed and produce no agent-consumable Bus
  event.
- The Bus event may reference photo artifacts, but photo artifacts cannot mutate
  Plant state.

## C-FND-003 - AgentInvocationRecord

`AgentInvocationRecord` proves that the agent path crossed a project-owned
adapter boundary. A record counts as an agent invocation only when all of these
conditions are true:

- scoped Bus context is selected through backend authorization;
- a project-owned adapter function/object is called;
- the adapter receives refs or redacted context, not UI Feed text or raw chat;
- a runtime decision is produced or recorded;
- audit evidence is available without exposing raw reasoning or secrets.

Minimum fields:

| Field | Requirement |
|---|---|
| `invocation_id` | Stable invocation id. |
| `agent_id` | Product or foundation smoke agent id. |
| `adapter_id` | Project-owned adapter id or implementation boundary. |
| `created_at` | Invocation timestamp. |
| `runtime_mode` | `real_model`, `real_adapter_pending_provider`, or `test_double`. |
| `input_event_refs` | Refs to authorized Bus events. |
| `actor_context_ref` | Authorized ActorContext ref. |
| `authorization_scope` | Farm/Plant scope used for context. |
| `runtime_decision` | `speak`, `silent`, `clarify`, or `escalate`. |
| `model_config_ref` | Safe provider/config ref when available; no secrets. |
| `raw_provider_output_ref` | Optional redacted audit ref; never agent-consumable and never exported as domain content. |

Runtime/demo rule:

- `test_double` is allowed only inside automated tests and can prove adapter
  shape, contract validation, redaction, and context filtering.
- `test_double`, fake, hardcoded, or stubbed agent output cannot satisfy MVP
  runtime/demo acceptance and cannot be wired as the product runtime path.
- If real provider secrets are unavailable during Foundation tasks, the task
  must record that provider-backed runtime acceptance remains pending; it may
  still prove the adapter contract if `/foundation-to-tasks` scopes that task as
  a compatibility probe rather than final runtime/demo acceptance.

## C-FND-004 - MessageEnvelope And UIFeedEvent Split

Foundation must produce a `MessageEnvelope` that follows
[MessageEnvelope](message-envelope.md) and a separate UI projection record.

`UIFeedEvent` minimum fields:

| Field | Requirement |
|---|---|
| `ui_event_id` | Stable UI event id. |
| `created_at` | Projection timestamp. |
| `farm_id` | Same Farm as the MessageEnvelope. |
| `plant_id` | Same Plant when Plant-scoped. |
| `message_ref` | Canonical ref to the MessageEnvelope. |
| `presentation_kind` | `agent_message`, `clarification`, `safety_block`, or `task_prompt`. |
| `display_payload` | Human-facing redacted text/card data. |
| `source_refs` | Message, Bus, input, and optional safety/task refs. |
| `consumable_by_agents` | Must be `false`. |
| `authorization_scope` | Display scope, not agent context authorization. |
| `redaction_status` | `checked` or stricter implementation value. |

Rules:

- `UIFeedEvent` is presentation-only and cannot be accepted by agent context
  builders.
- `MessageEnvelope.consumable_output` cannot contain raw provider messages,
  hidden reasoning, raw UI markdown, secrets, or unauthorized Plant context.
- A UI projection may quote or summarize a MessageEnvelope only through refs and
  redacted display payload.

## C-FND-005 - SafetyRouteResult And Task Transition

Foundation must prove two minimal branches:

1. Safe clarification or missing-data request.
2. Physical-action implication that fails closed.

`SafetyRouteResult` minimum fields:

| Field | Requirement |
|---|---|
| `safety_route_id` | Stable safety route id. |
| `created_at` | Backend timestamp. |
| `source_message_ref` | MessageEnvelope ref. |
| `farm_id` | Scoped Farm. |
| `plant_id` | Scoped Plant. |
| `route` | `safe_clarification` or `physical_action_blocked` for foundation. |
| `physical_action_implication` | Boolean. |
| `requires_human_approval` | Boolean carried from MessageEnvelope/safety policy. |
| `allowed_task_transition` | `clarification_task_created`, `measurement_request_created`, or `none`. |
| `blocked_reason` | Required when route is `physical_action_blocked`. |
| `safety_gate_authority` | `not_granted` unless a future feature-local Safety Gate contract proves full approval. |
| `source_refs` | Input, Bus, invocation, message, and evidence refs. |

Rules:

- Safe clarification may create only a non-action clarification or measurement
  request task/state.
- Physical-action implication must not create an executable `action_task`, must
  not imply automated device execution, and must not treat DecisionRecord or
  human discussion as Safety Gate approval.
- Fresh data alone is not enough to unlock a physical action.

## C-FND-006 - PostgreSQL / Read-Model Evidence

The foundation smoke must assert that mutable runtime state is represented in
PostgreSQL/read-model records or test database assertions.

Required evidence categories:

- authorized ActorContext or equivalent fixture was resolved;
- input/observation/manual measurement was accepted or rejected through backend
  rules;
- optional photo catalog identity was recorded when a photo fixture is used;
- agent invocation audit evidence exists;
- MessageEnvelope and UIFeedEvent are distinct records or assertions;
- SafetyRouteResult and any allowed non-action task transition are represented;
- refs connect state records to Bus, timeline, and export artifacts.

Rules:

- Exact table names and migrations belong to `FT-000` task design and later
  feature-local specs.
- Timeline replay, UI Feed, photo manifest, photo JSON export, and raw agent
  output cannot overwrite PostgreSQL/read-model state.

## C-FND-007 - timeline.jsonl Smoke Event

Foundation must append at least one `timeline.jsonl` event for the smoke path.
Multiple stage events are allowed when useful.

Minimum event fields:

| Field | Requirement |
|---|---|
| `timeline_event_id` | Stable event id. |
| `schema_version` | Foundation smoke schema version. |
| `event_type` | `foundation.input_recorded`, `foundation.agent_message_recorded`, `foundation.safety_route_recorded`, or `foundation.photo_export_recorded`. |
| `created_at` | Append timestamp. |
| `farm_id` | Scoped Farm. |
| `plant_id` | Scoped Plant when relevant. |
| `actor_ref` or `source_ref` | Attribution/source ref. |
| `runtime_refs` | Refs to input, Bus, invocation, message, safety route, state/task records as applicable. |
| `artifact_refs` | Optional photo/export refs. |
| `payload_summary` | Redacted compact summary. |
| `redaction_status` | `checked` or stricter implementation value. |
| `local_only` | Must be `true`. |

Rules:

- `timeline.jsonl` is append-only audit/export evidence.
- Timeline replay cannot publish Bus events, rehydrate mutable runtime state, or
  bypass authorization.

## C-FND-008 - Photo JSON Export Snapshot

When the foundation smoke uses a photo fixture, it must produce a photo JSON
export snapshot.

Minimum fields:

| Field | Requirement |
|---|---|
| `export_id` | Stable export id. |
| `schema_version` | Foundation export schema version. |
| `created_at` | Export timestamp. |
| `farm_id` | Scoped Farm. |
| `plant_id` | Scoped Plant. |
| `photo_ref` | Canonical photo artifact/catalog ref. |
| `photo_sha256` | Photo identity proof. |
| `source_refs` | Input and actor/source refs. |
| `runtime_state_refs` | PostgreSQL/read-model refs, not inline state authority. |
| `bus_event_refs` | Bus refs that used the photo/input evidence. |
| `message_refs` | MessageEnvelope refs derived from the path. |
| `timeline_refs` | Timeline event refs. |
| `dataset_defaults` | Must keep `can_train_on` false or absent. |
| `local_only` | Must be `true`. |
| `redaction_status` | `checked` or stricter implementation value. |

Rules:

- The export snapshot is evidence/export only and cannot become mutable Plant
  state authority.
- The export must not include raw provider output, hidden reasoning, auth
  material, session tokens, `.env` values, or secrets.

## C-FND-009 - Redaction And Context Hygiene

Foundation evidence must include assertions over every generated artifact:

- Bus payloads;
- adapter invocation records;
- MessageEnvelope records;
- UIFeedEvent records;
- SafetyRouteResult records;
- PostgreSQL/read-model rows or test assertions;
- `timeline.jsonl`;
- photo JSON export;
- logs or captured smoke output when used.

Assertions:

- no secrets, tokens, credentials, API keys, `.env` values, or auth material;
- no hidden reasoning or raw provider message history in publishable artifacts;
- no UI Feed payload in agent working context;
- no raw chat, admin UI text, unapproved Companion proposal, or spoiler note in
  agent working context;
- no unauthorized Farm/Plant context;
- `local_only` is preserved in smoke evidence and export artifacts.

## Foundation Acceptance

`/foundation-to-tasks` should use this contract as a normative input when
creating `FT-000` task records and exactly one final foundation gate task.

The final foundation gate evidence must show:

- one authorized `FoundationInput` with optional photo fixture;
- one valid `foundation.input_recorded.v1` BusEventEnvelope;
- one `AgentInvocationRecord` crossing the project-owned adapter boundary;
- one MessageEnvelope/UIFeedEvent split with `UIFeedEvent.consumable_by_agents=false`;
- safe clarification and physical-action blocked safety branches;
- PostgreSQL/read-model assertions;
- `timeline.jsonl` append evidence;
- photo JSON export snapshot when a photo fixture is included;
- redaction/context-hygiene assertions.

