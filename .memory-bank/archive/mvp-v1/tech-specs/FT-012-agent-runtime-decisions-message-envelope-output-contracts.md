---
description: Feature-local SDD tech spec for FT-012 agent runtime decisions and MessageEnvelope output contracts.
status: active
owner: architecture
last_updated: 2026-06-01
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/features/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md
  - .memory-bank/spec-index.md
---
# FT-012 Agent Runtime Decisions and MessageEnvelope Output Contracts Tech Spec

## Scope

This spec closes the feature-local SDD design gate for FT-012 before `/prd-to-tasks FT-012`.

FT-012 owns:

- exactly-one runtime decision handling for invoked agents;
- Agno/mock execution output adaptation into domain decisions;
- `MessageEnvelope` validation for publishable agent work output;
- backend-generated `message_id` lifecycle and canonical `message:<message_id>` refs;
- `silent` audit evidence with no MessageEnvelope and no Bus publication;
- output-size and raw-reasoning rejection rules;
- Team Signal / Safety Block routing shape before FT-004 Bus publication;
- `ui_spoiler_note_ref` pointer validation.

FT-012 does not own Agent Chat Bus persistence/envelope validation, UI Feed event schema, physical-action classification, approval lifecycle, or dataset lifecycle transitions.

## Normative Inputs

- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): global runtime decision and `MessageEnvelope` contract.
- [.memory-bank/tech-specs/FT-004-agent-chat-bus-event-stream-publication-boundary.md](FT-004-agent-chat-bus-event-stream-publication-boundary.md): Bus publication service and event payload minimums.
- [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md): Bus event types and influence levels.
- [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): `ui_spoiler_note_ref` target and context hygiene rules.
- [.memory-bank/states/dataset-governance.md](../states/dataset-governance.md): `can_train_on` restrictions and agent-labeled hypothesis handling.
- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Agno boundary and adapter rules.
- [.memory-bank/testing/index.md](../testing/index.md): runtime decision, envelope, silent audit, and concise-output gates.
- [.memory-bank/invariants.md](../invariants.md): raw Agno output, raw reasoning, UI Feed, and trainability prohibitions.

## Design Decisions

### Runtime Decision State Machine

Every agent invocation must produce exactly one runtime decision:

| Decision | MessageEnvelope | Bus publication | Required audit |
|---|---|---|---|
| `speak` | required | `agent_conclusion` or `agent_quoted_detail_reply` through FT-004 | runtime decision + adapter evidence |
| `clarify` | required | `agent_clarification_request` through FT-004 | runtime decision + adapter evidence |
| `escalate` | required | `agent_team_signal` or `safety_block` through FT-004 | runtime decision + adapter evidence |
| `silent` | forbidden | forbidden | audit-only record |

Invalid conditions:

- no decision;
- multiple decisions;
- `silent` with a `MessageEnvelope`;
- publishable decision without a valid `MessageEnvelope`;
- raw Agno output or raw reasoning presented as a domain envelope;
- physical-action wording routed to display/tasking without Safety Gate ownership.

### Adapter Boundary

The domain adapter receives execution output from Agno, mock agents, or future provider-specific tools and produces a normalized `AgentRuntimeResult`.

Minimum normalized result:

| Field | Rule |
|---|---|
| `agent_id` | Stable agent identifier. |
| `runtime_decision` | Exactly one of `speak`, `silent`, `clarify`, `escalate`. |
| `source_refs` | Non-empty refs for evidence/context that informed the decision. |
| `model_version` | Required when a real model/provider was used; `mock` value allowed for mock adapters. |
| `prompt_version` | Required when prompt-based output was used; `mock` value allowed for mock adapters. |
| `created_at` | Timezone-aware adapter result time. |
| `message_envelope` | Required only for publishable decisions; after validation it includes canonical `message_id`. |
| `audit` | Adapter name, validation status, and rejection/fail-closed reason when applicable. |

Provider messages, Agno step output, Team synthesis, tool traces, memory, storage, and raw reasoning are execution artifacts only. They cannot become Bus events or `MessageEnvelope` content without this adapter.

### MessageEnvelope Schema

Publishable agent work output must validate this schema-level contract:

| Field | Rule |
|---|---|
| `message_id` | Required backend-generated stable ID for publishable decisions; recommended prefix `msg_`. |
| `agent_id` | Required; matches the runtime result agent. |
| `claim_type` | Required MVP enum: `observation`, `hypothesis`, `recommendation`, `safety_block`, `task_request`, `clarification_request`, `quoted_detail_reply`, `team_signal`. |
| `confidence` | Required enum: `unknown`, `low`, `medium`, `high`. |
| `requires_human_approval` | Required boolean. |
| `can_train_on` | Required boolean; defaults to `false` for ordinary agent output. |
| `source_refs` | Required non-empty list of stable evidence/domain refs. |
| `consumable_output` | Required concise working text for agents/domain consumers. |
| `ui_spoiler_note_ref` | Optional UI Feed event ref only; never inline spoiler text. |

Rules:

- `message_id` is assigned only after FT-012 validates a publishable `MessageEnvelope`; canonical ref format is `message:<message_id>`.
- Bus event IDs, timeline event IDs, UI Feed event IDs, and provider message IDs do not replace `message_id`.
- Downstream source refs for publishable agent output use `message:<message_id>`; Bus/timeline/UI refs may be included only as publication, audit, or presentation refs.
- `can_train_on=true` is forbidden for raw or ordinary agent-labeled output unless dataset governance has already produced an eligible selected train item with evidence refs.
- `source_refs` must reference domain evidence such as photo, observation, measurement, task, approval, timeline, review, or dataset refs.
- `consumable_output` must be safe to give to another agent as working context; it must not contain raw chain-of-thought, hidden reasoning, secrets, or UI-only prose.
- `ui_spoiler_note_ref`, when present, must point to a UI Feed event with `visible_to_agents=false` and `consumable_by_agents=false`.

### MessageEnvelope Identity And Publication Lifecycle

Publishable agent output follows this lifecycle:

1. The adapter normalizes provider or mock output into an `AgentRuntimeResult` candidate.
2. For `speak`, `clarify`, and `escalate`, FT-012 validates the `MessageEnvelope` fields and assigns backend-owned `message_id`.
3. The validated envelope becomes an immutable agent-output record or equivalent backend-visible snapshot addressable as `message:<message_id>`.
4. FT-004 Bus publication receives `message_ref=message:<message_id>` and maps the runtime decision to the Bus event type. The Bus event ID is a publication ref, not the MessageEnvelope identity.
5. Timeline, UI Feed, and dataset refs may point to the same `message:<message_id>` while keeping their own audit, presentation, or governance identities.

Rejected candidates and `silent` decisions get no `message_id`. If Bus publication fails after envelope validation, no agent-consumable Bus event exists; implementation must either roll back the visible envelope or leave only non-consumable audit evidence.

### Decision To Event Mapping

| Runtime decision | Claim type | Bus event type |
|---|---|---|
| `speak` | `observation`, `hypothesis`, `recommendation`, `task_request` | `agent_conclusion` |
| `speak` | `quoted_detail_reply` | `agent_quoted_detail_reply` |
| `clarify` | `clarification_request` | `agent_clarification_request` |
| `escalate` | `team_signal` | `agent_team_signal` |
| `escalate` | `safety_block` | `safety_block` |

Other combinations are invalid until a feature-local spec adds a grounded route.

### Output Size Rules

Validation should be simple and testable:

- Ordinary `agent_conclusion` output: 1-3 short lines.
- `clarification_request`: one short targeted request, preferably one missing-data ask.
- `agent_quoted_detail_reply`: 3-7 lines and shorter than the linked UI spoiler note when both exist.
- `agent_team_signal` and `safety_block`: may be longer than ordinary conclusions, but must remain structured and focused on source refs, reason, and required next routing.
- Large user-facing prose belongs to UI presentation/Companion behavior, not Agent Chat Bus working output.

### Silent Audit

`silent` means:

- no `MessageEnvelope`;
- no Agent Chat Bus event;
- optional UI Feed status/spoiler only through FT-005 and always non-consumable by agents;
- required audit evidence.

The MVP audit record for `silent` may be a timeline `system_event` or a local agent invocation audit record. It must include:

- `agent_id`;
- `runtime_decision=silent`;
- `created_at`;
- source refs/input refs;
- adapter name;
- reason code such as `not_relevant`, `no_material_change`, `insufficient_confidence`, or `curator_deferred`;
- model/prompt version when applicable.

### Safety And Escalation Boundary

- `requires_human_approval=true` does not itself create approval or unlock action.
- Physical-action wording must route through the Safety Gate feature before display or task/action routing.
- `safety_block` envelopes carry the structured block message and source refs, but FT-013 owns physical-action detection, freshness checks, and fail-closed policy.
- `team_signal` is strong influence, not a command.

## API Surface

FT-012 primarily owns internal adapter/schema behavior. If exposed for local tests or debug, routes must be protected and must not accept arbitrary raw model text into Bus.

Useful implementation surfaces:

- schema validators for `AgentRuntimeResult` and `MessageEnvelope`;
- adapter function from Agno/mock output to runtime result;
- validated envelope storage/read/ref lookup if needed by Bus, UI, task, dataset, or audit flows;
- internal publish handoff to FT-004 Bus service for publishable decisions;
- local debug endpoint only if needed for test inspection, with secrets/raw reasoning redacted.

### FT-004 Coordination Note

FT-012 depends on the FT-004 foundation `BusPublicationService` and `BusEventEnvelope` validation stub for agent-originated publication. Task decomposition should implement FT-004 foundation first, then FT-012 `AgentRuntimeResult` / `MessageEnvelope` validation, `message_id` assignment, and adapter mapping, then cross-feature integration tests proving publishable agent output carries `message_ref=message:<message_id>` before FT-004 Bus publication.

## Verification Targets

Required before FT-012 can be marked implemented:

- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- Schema tests for `AgentRuntimeResult` and `MessageEnvelope` required fields, backend-generated `message_id`, canonical `message:<message_id>` ref shape, enum values, non-empty `source_refs`, `can_train_on` default/guard, and `ui_spoiler_note_ref` pointer shape.
- Runtime-decision tests proving exactly one decision is required.
- Mapping tests for `speak`, `clarify`, `escalate`, and `silent` to valid Bus/no-Bus outcomes.
- `silent` audit tests proving no `MessageEnvelope`, no `message_id`, and no Bus event are created while audit evidence exists.
- Lifecycle tests proving rejected candidates get no `message_id` and agent-originated Bus events carry `message_ref=message:<message_id>` instead of inline-only envelopes.
- Concise-output tests for ordinary conclusions, clarification requests, quoted detail replies, and large-message routing.
- Anti-cheat tests proving raw Agno output, raw reasoning, provider message history, Team synthesis, memory/storage, and UI spoiler text cannot become `MessageEnvelope.consumable_output`.
- Safety-boundary tests proving physical-action wording is not displayed or routed to task/action handling by FT-012 alone.
- Integration tests proving publishable agent output flows through FT-012 `MessageEnvelope` validation and then FT-004 Bus publication service.

## Gaps And Non-Goals

- No FT-012 blocker remains for `/prd-to-tasks FT-012`.
- Exact Pydantic class names, adapter module names, prompt output parser details, and debug endpoint shape belong to implementation tasks.
- UI Feed event schema is owned by FT-005.
- Physical-action detection/freshness and human approval are owned by FT-013 and FT-014.
- Real multi-agent coordination, Agno Team `coordinate`, hidden chain-of-thought capture, and training-data selection are outside FT-012 MVP scope.
