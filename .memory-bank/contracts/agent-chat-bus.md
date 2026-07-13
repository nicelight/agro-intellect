---
description: Global Agent Chat Bus contract boundary for MVP v2.
status: active
type: contract
last_updated: 2026-07-12
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/ui-feed.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/states/companion-governance.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
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
    validated pending agent-originated output before classification and Bus/UI
    projection.
  - [.memory-bank/contracts/ui-feed.md](ui-feed.md): defines human-facing
    projection rules.
  - [.memory-bank/contracts/timeline-event.md](timeline-event.md): defines
    audit/export event rules.

## Publication Rule

Only backend/domain adapters may publish Bus events. Raw Agno/model output, provider history, raw reasoning, UI Feed content, raw chat, admin UI text, unapproved Companion proposals, and timeline replay cannot publish directly to the Bus.

For a Plant-scoped event, the publisher must verify current
`Plant.status=active` and authorization at the publication boundary. An event
prepared before archive cannot be published after archive. Existing retained
events may remain audit/reference data but are excluded from archived Plant
working context.

## BusEventEnvelope version 1

FT-008 implements one strict Plant-scoped object with unknown fields rejected:

- `schema_version=1`;
- `event_id`: application-generated UUIDv4;
- `event_type`: `domain_event_ref | agent_safe_information`;
- `created_at`: timezone-aware UTC timestamp;
- `farm_id`, `plant_id`: native UUID identities;
- `actor_ref`: nullable safe `{account_id,membership_id,role_preset}`; null only
  for a backend-owned system/domain adapter;
- `source_type`: `domain_record | message_envelope`;
- `source_id`: authoritative UUID string;
- `payload`: exactly one discriminated payload below;
- `source_refs`: one through four unique safe `kind:identifier` refs;
- `consumable_by_agents=true`;
- `authorization_scope`: current safe
  `{farm_id,plant_id,role_preset,operation_kind,permission_source,grant_id}` for
  actor-originated publication, or null for a backend-owned domain adapter.

`domain_event_ref` payload is exactly:

```json
{"payload_kind":"domain_event_ref","record_type":"daily_checkin|manual_measurement|photo_catalog_item","record_ref":"kind:identifier"}
```

It is a compact trigger/reference, not a copied runtime snapshot. A consumer
loads current authoritative data through its owning repository and current
authorization boundary.

`agent_safe_information` payload is exactly:

```json
{"payload_kind":"quoted_candidate","message_id":"uuid","classification_ref":"safety_classification:uuid","candidate_claim_type":"observation|hypothesis|recommendation|clarification|team_signal","quoted_text":"opaque text"}
```

`quoted_text` equals the immutable MessageEnvelope `candidate_output` and has
no instruction, prompt, tool, command, routing, or authority semantics.
`task_request` and `safety_block` claims do not use this safe-information route.

## Consumability

- `consumable_by_agents=true` is required before event content can enter agent working context.
- UI Feed events are not Bus events.
- When an authorized `safe_information` route preserves candidate content, the
  Bus payload carries it only in an explicit typed quoted-data member. Exact
  feature-local field naming may be refined by FT-008, but the payload type
  must distinguish untrusted quotation from instructions and routing data.
- Context construction must preserve that quotation boundary and must never
  concatenate candidate content into system, developer, instruction, prompt,
  tool, command, or routing channels. Prompt-like text cannot instruct a
  downstream agent.
- Approved governance summary facts can be consumable only when derived from a valid DecisionRecord and must include `safety_gate_authority=not_granted`.
- Unapproved proposals and raw chat remain non-consumable.

## Context Builders

- Context builders must resolve ActorContext and PlantAccessGrant before returning events.
- Context builders must exclude archived Plant operational context; only an
  explicit retained-history projection may read retained events, and it is not
  agent working context.
- Agents may receive only scoped Plant/Farm context they are authorized to process.
- Candidate-derived quoted data, when allowed, remains visibly typed and
  untrusted in the assembled agent input; it cannot become an agent definition,
  policy, competence, instruction, tool call, or runtime decision.
- Context builders must exclude UI Feed, spoiler notes, raw model reasoning, raw chat, admin notices, and unapproved Companion content.

FT-008 context reads are Plant-scoped, require current `normal_read`
authorization and `Plant.status=active`, and return at most 100 events ordered
by `(created_at ASC, event_id ASC)`. Archived retained history is never an
agent-context mode. The builder returns typed payload records; it never
flattens or concatenates `quoted_text` with instructions.

## Ordering And Replay

- MVP relies on `created_at` and `event_id` for ordering hints.
- Bus payloads are event references and compact consumable facts, not full
  runtime state snapshots.
- Timeline replay cannot rehydrate mutable runtime state or bypass Bus publication rules.
- FT-008 persists events uniquely by
  `(plant_id, source_type, source_id, event_type)`. An identical retry is an
  idempotent duplicate; conflicting content fails closed.
- Ordering uses `(created_at,event_id)` and does not imply mutable-state order.

## Safety Handoff

- A pending MessageEnvelope cannot publish to Bus. `safe_information` requires
  its matching `SafetyClassificationResultV1` and the canonical current
  publication guard. Neither artifact is authorization.
- A `safe_task_request` first creates its ordinary task record; any Bus event
  references that authoritative task rather than treating candidate text as a
  command.
- `physical_action|blocked_uncertain` candidate text never enters agent working
  context. Physical action routes to Safety Gate; uncertainty permits only a
  non-consumable UI block notice.
- Bus publication alone never authorizes physical action.
- Candidate content cannot alter event routing or consumability by stating a
  prompt, command, safety label, or publication instruction; only the matching
  validated classification and current guard select the route.

For `safe_information`, FT-008 validates the immutable envelope plus matching
strict classification, re-resolves current ActorContext, checks the active
Plant in the write transaction, and atomically writes the Bus event plus its UI
Feed projection. `safe_task_request|physical_action` write no FT-008 event;
`blocked_uncertain` may write only the generic UI notice defined by UI Feed.

## Verification

Tests must prove:

- unauthorized Plant events are filtered out;
- UI Feed/raw chat/unapproved proposal content is absent from agent context;
- raw provider output cannot bypass adapters;
- classified candidate content uses a typed quotation field and never an
  instruction/prompt channel; prompt-like text cannot alter downstream agent
  behavior or routing authority;
- Safety Gate and DecisionRecord authority remain separate;
- adversarially mislabeled physical wording cannot enter Bus, while a verified
  safe check/measurement request avoids physical-action approval and never
  creates an `action_task`;
- archive between model execution and Bus publication fails closed without a
  Plant-scoped Bus event, and restore does not replay the blocked publication.
