---
description: Global Agent Chat Bus contract boundary for MVP v2.
status: active
type: contract
last_updated: 2026-07-18
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/ui-feed.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/states/companion-governance.md
  - .memory-bank/domains/companion-governance.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
---
# Agent Chat Bus

## Scope

Agent Chat Bus is the domain-owned working event stream for agent-consumable context. It is not Agno memory, not UI Feed, not timeline replay, and not a replacement for PostgreSQL/read-model runtime authority.

The verified FT-000 executable baseline does not implement Agent Chat Bus
runtime code. This contract is a global guardrail for future product features;
field refinements and implementation tasks belong to `/feature-to-tasks FT-<NNN>`.

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

Persisted Safety classification is evidence, not automatic publication
authority. Candidate publication additionally requires the derived
`ClassificationConsumerRouteV1=ordinary_dispatch`. Canonical
`origin_agent_id=companion` always derives
`companion_governance_hold` and cannot use `agent_safe_information`, even when
its classification is `safe_information`.

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
{"payload_kind":"domain_event_ref","record_type":"daily_checkin|manual_measurement|photo_catalog_item|decision_record","record_ref":"kind:identifier"}
```

It is a compact trigger/reference, not a copied runtime snapshot. A consumer
  loads current authoritative data through its owning repository and current
  authorization boundary. For `decision_record`, the exact resolved DTO is
  `ApprovedGovernanceSummaryV1` from the Companion Governance data spec; it is
  not `CompanionConclusionV1` and is not a copied HTTP/UI projection.

`record_type=decision_record` is the only Companion-governance entry into the
Bus. It uses `source_type=domain_record`, `source_id=decision_record_id`, and
`record_ref=decision_record:<decision_record_id>`. Before publication, the
publisher reloads the authoritative valid `DecisionRecord`, requires its
approved compact governance-summary projection and exact
`safety_gate_authority=not_granted`, and applies the current active-Plant and
authorization guard. The Bus row stores only the reference; it never copies
proposal text, rationale, raw chat, UI text, or mutable governance state.

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
- Approved governance summary facts can be consumable only when derived from a
  valid DecisionRecord and must use the exact non-persisted
  `ApprovedGovernanceSummaryV1` field/type/order/source-ref schema with
  `safety_gate_authority=not_granted`.
- A `decision_record` event is resolved by the context builder into the exact
  compact approved-summary shape owned by the Companion Governance data spec.
  The resolved facts remain typed data; the event reference is not itself a
  governance decision or a Safety/task command. Current issue focus/status,
  HumanAttentionNeeded, CompanionConclusion, proposal/task text, rationale,
  and mutable Task state are never substituted into that immutable summary.
- Proposal rows and raw chat do not become Bus-consumable merely by existing. An owning agent-specific provider contract may separately load an authorized typed governance subset without publishing it to Bus.

## Context Builders

- Context builders must resolve ActorContext and PlantAccessGrant before returning events.
- Context builders must exclude archived Plant operational context; only an
  explicit retained-history projection may read retained events, and it is not
  agent working context.
- Agents may receive only scoped Plant/Farm context they are authorized to process.
- Candidate-derived quoted data, when allowed, remains visibly typed and
  untrusted in the assembled agent input; it cannot become an agent definition,
  policy, competence, instruction, tool call, or runtime decision.
- Bus context builders must exclude UI Feed, spoiler notes, raw model reasoning, raw chat, and admin notices. Agent-specific direct provider assemblers may load only the governance fields registered by their own strict contract.
- For `record_type=decision_record`, the builder reloads the current
  authoritative DecisionRecord plus its approved version-2 proposal, rechecks
  Plant scope, and returns exactly `ApprovedGovernanceSummaryV1`. Missing,
  rejected, superseded, mismatched, stale, archived, unauthorized, or
  non-projectable governance state is omitted.

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
  publication guard under `ordinary_dispatch`. Neither artifact is
  authorization.
- Under `ordinary_dispatch`, a `safe_task_request` first creates its ordinary
  task record; any Bus event references that authoritative task rather than
  treating candidate text as a command. A Companion-held request does not
  create that Task.
- `physical_action|blocked_uncertain` candidate text never enters agent working
  context. Under `ordinary_dispatch`, physical action routes to Safety Gate and
  uncertainty permits only a non-consumable UI block notice; under the
  Companion hold both have no downstream effect.
- Bus publication alone never authorizes physical action.
- A DecisionRecord Bus reference can direct only the FT-013-approved workflow
  effect through its owning backend rule. It cannot create `action_task`,
  confirm Plant state, or substitute for Safety Gate or human action approval.
- Candidate content cannot alter event routing or consumability by stating a
  prompt, command, safety label, or publication instruction; only the matching
  validated classification, server-derived consumer route, and current guard
  select the boundary.

For `companion_governance_hold`, `safe_information` and
`safe_task_request` are classification-only proposal evidence. They write no
candidate Bus row; `physical_action|blocked_uncertain|mismatch|failure` also
write no Bus row. Only a later valid approved DecisionRecord may use the
separate `domain_event_ref/decision_record` path, which reconstructs a compact
typed fact and never the held candidate/proposal/rationale/provider text.

For `safe_information`, FT-008 validates the immutable envelope plus matching
strict classification, re-resolves current ActorContext, checks the active
Plant in the write transaction, requires `ordinary_dispatch`, and atomically
writes the Bus event plus its UI Feed projection.
`safe_task_request|physical_action` write no FT-008 event; under
`ordinary_dispatch`, `blocked_uncertain` may write only the generic UI notice
defined by UI Feed.
Classification retry, restore, startup, or reconciliation never replays either
ordinary or held classified publication.

## Verification

Tests must prove:

- unauthorized Plant events are filtered out;
- UI Feed/raw chat content is absent from Bus-built agent context; agent-specific typed governance input is verified against its owning allowlist;
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
- only a valid approved and currently authorized DecisionRecord can produce the
  `decision_record` domain reference; raw/superseded proposal content never
  enters the Bus, and the resolved summary matches every
  `ApprovedGovernanceSummaryV1` field and ordered ref exactly while preserving
  `safety_gate_authority=not_granted`.
- Companion `safe_information` creates no FT-008 Bus candidate, held
  task/physical/blocked/mismatched/failed results create no Bus row, and
  ordinary non-Companion safe-information publication remains unchanged.
