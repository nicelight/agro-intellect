---
description: Feature-local SDD tech spec for FT-004 Agent Chat Bus event stream and publication boundary.
status: active
owner: architecture
last_updated: 2026-05-31
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/features/FT-004-agent-chat-bus-event-stream-publication-boundary.md
  - .memory-bank/spec-index.md
---
# FT-004 Agent Chat Bus Event Stream and Publication Boundary Tech Spec

## Scope

This spec closes the feature-local SDD design gate for FT-004 before `/prd-to-tasks FT-004`.

FT-004 owns:

- `BusEventEnvelope` validation;
- MVP Agent Chat Bus event type set;
- Bus publication boundary;
- Bus working-stream persistence/query behavior;
- filtering rules for agent-consumable context;
- anti-cheat checks that prevent Agno, UI Feed, raw reasoning, or mutable-state shortcuts from becoming Bus events.

FT-004 does not own the detailed `MessageEnvelope` field semantics, runtime decision adaptation, UI Feed event schema, Safety Gate decision logic, or task/approval lifecycles.

## Normative Inputs

- [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md): global Bus envelope, event type set, publication rules, influence levels, and authority boundary.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): publishable agent-output payload contract refined by FT-012.
- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Agno invocation/publication separation and Bus publication module boundary.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): audit/export event boundary and `consumable_by_agents` meaning when events are mirrored/published.
- [.memory-bank/tech-specs/FT-003-runtime-state-timeline-audit.md](FT-003-runtime-state-timeline-audit.md): timeline refs and runtime-authority rules.
- [.memory-bank/testing/index.md](../testing/index.md): Agent Chat Bus, adapter, UI/Bus split, and anti-cheat gates.
- [.memory-bank/invariants.md](../invariants.md): Agno, UI Feed, raw reasoning, and Bus publication prohibitions.

## Design Decisions

### Bus Working Stream

- Agent Chat Bus is a local domain working stream inside the modular monolith.
- The MVP should persist Bus events in PostgreSQL as an append-only working-context table or equivalent local read model so agent context can survive request boundaries and tests can inspect publication behavior.
- Bus persistence is not mutable runtime state authority. Current plant state, tasks, approvals, dataset state, and sync state remain owned by PostgreSQL domain tables, not by replaying Bus events.
- Bus events may reference timeline events, domain records, and message envelopes, but they do not replace `timeline.jsonl` audit/export.
- Existing Bus events must not be edited to represent current state. Corrections are new Bus events or domain state transitions owned by the relevant feature.

Recommended table/read-model boundary:

| Field | Rule |
|---|---|
| `bus_event_id` | Globally unique Bus event ID, recommended prefix `bus_evt_`. |
| `event_type` | One MVP Bus event type. |
| `created_at` | Timezone-aware publication timestamp. |
| `source_type` | `user`, `agent`, `system`, `task`, `sync`, or `safety`. |
| `source_id` | Stable source identifier. |
| `topic` | Routing/audit label, not authority for plant binding. |
| `payload` | Validated event-specific object. |
| `consumable_by_agents` | Required boolean; only `true` events enter agent working context. |
| `audit_log` | Adapter, validation, source refs, and safety/publication evidence. |
| `source_refs` | Timeline/domain/message refs where available. |

### Envelope Validation

Every candidate Bus publication must pass through one backend publication service. The service validates:

- required envelope fields;
- event type is in the MVP Bus event set;
- source type and source ID are present;
- timestamps are timezone-aware;
- payload is structured JSON, not raw unstructured model output;
- `consumable_by_agents` is present and boolean;
- UI Feed refs, spoiler text, raw chain-of-thought, and secrets are absent from agent-consumable payload fields;
- event-specific required refs are present.

Rejected events must not be partially published. Errors use the shared API/error shape when exposed over HTTP; internal publication failures must be auditable without leaking secrets.

### MVP Event Type Payload Minimums

Feature-local specs may add fields, but FT-004 defines minimum refs needed for Bus publication.

| Event type | Source type | Minimum payload |
|---|---|---|
| `user_message` | `user` | `plant_id`, `message_ref` or `observation_ref`, safe user-visible text or structured intake refs. |
| `user_photo` | `user` | `plant_id`, `photo_id`, `photo_type`, photo event/catalog refs. |
| `agent_conclusion` | `agent` | `message_envelope_ref` or inline `message_envelope`; detailed fields owned by FT-012. |
| `agent_clarification_request` | `agent` | `message_envelope_ref` or inline `message_envelope`; optional `target_agent_id` as routing hint. |
| `agent_quoted_detail_reply` | `agent` | `message_envelope_ref` or inline `message_envelope`; source refs. |
| `agent_team_signal` | `agent` | `message_envelope_ref` or inline `message_envelope`; reason/source refs. |
| `safety_block` | `safety` or `agent` | blocked proposal/source ref, `plant_id` when plant-bound, safety reason/code. |
| `task_created` | `task` | `plant_id`, `task_id`, task type, source refs. |
| `human_confirmation` | `user` | `plant_id`, confirmation subject ref, decision/ref metadata. |
| `system_event` | `system` | machine-readable code and safe refs. |
| `sync_event` | `sync` | sync scope ref and `local_only` MVP status unless a future sync spec expands it. |

Plant-bound events must include explicit `plant_id`; `topic` cannot be the only plant binding.

### Publication Boundary

Allowed publication paths:

- domain/application workflow produces a structured Bus candidate;
- Agno adapter produces a runtime decision and, for publishable decisions, a valid `MessageEnvelope` candidate refined by FT-012;
- Safety Gate or task modules publish structured domain events through the same Bus publication service.

Forbidden publication paths:

- raw Agno output directly inserted into Bus;
- Agno workflow events, Team synthesis, memory, storage, or provider message history used as Bus events;
- UI Feed events or spoiler notes routed into Bus;
- timeline import/replay used as normal Bus publication authority;
- controllers constructing Bus events without the publication service.

`agent_clarification_request` may include `target_agent_id`, but this is a routing hint only. It is not a direct command; the target agent decides whether to react through its own competence and runtime decision.

### Context Filtering

- Agent working context builders read only Agent Chat Bus events with `consumable_by_agents=true`.
- Context builders must not read UI Feed events, spoiler notes, raw reasoning, Agno memory/storage, or timeline events directly as agent working context.
- `consumable_by_agents=false` content is excluded from agent context even if it exists in an audit or presentation layer.
- Querying can be scoped by plant, topic, source refs, event type, and recency/limit. Exact pagination fields belong to implementation tasks.

### Influence Levels

- `agent_conclusion`, `user_message`, `user_photo`, `task_created`, `human_confirmation`, `system_event`, and `sync_event` are ordinary/soft context unless an owning feature marks a stronger semantic.
- `agent_team_signal` is strong influence and should be rare.
- `safety_block` is a hard stop for the relevant action flow until the owning Safety Gate / approval feature records unlock conditions.

Influence level affects downstream interpretation; it does not mutate runtime state by itself.

## API Surface

FT-004 primarily owns internal backend publication boundaries. A minimal debug/read surface may exist for local development and tests:

- `GET /api/agent-bus/events`
  - local authenticated/debug endpoint or test-only route;
  - returns validated Bus envelopes with filtering/pagination;
  - must not expose secrets, raw reasoning, UI spoiler text, or local absolute paths.

Normal product workflows should publish Bus events through application services, not through a public arbitrary publish API.

## Verification Targets

Required before FT-004 can be marked implemented:

- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- Schema tests for `BusEventEnvelope` required fields, event type set, source identifiers, timezone-aware `created_at`, structured payload, `consumable_by_agents`, and `audit_log`.
- Event-specific tests for minimum payload refs on `user_message`, `user_photo`, agent-output events, `safety_block`, `task_created`, `human_confirmation`, `system_event`, and `sync_event`.
- Publication-boundary tests proving all Bus writes go through the project-owned publication service.
- Anti-cheat tests proving raw Agno output, workflow events, Team synthesis, memory/storage, raw reasoning, UI Feed events, spoiler notes, and timeline replay cannot enter Bus directly.
- Context-filtering tests proving only `consumable_by_agents=true` Bus events are available to agents.
- Authority tests proving Bus events do not become current mutable plant/task/approval/dataset/sync state.
- Integration tests for representative publication paths: user photo, user message/check-in, task created, safety block, system event, sync event, and agent-originated publishable output after FT-012 exists.

## Gaps And Non-Goals

- No FT-004 blocker remains for `/prd-to-tasks FT-004`.
- Detailed `MessageEnvelope` field validation, `silent` audit behavior, output-size rules, and runtime-decision adaptation are owned by FT-012.
- UI Feed schema/context hygiene is owned by FT-005.
- Safety Gate classification and human approval unlock semantics are owned by FT-013 and FT-014.
- Cross-process brokers, Kafka/NATS/Redis, remote event streaming, agent-to-agent commands, and Agno Team `coordinate` are outside FT-004 MVP scope.
