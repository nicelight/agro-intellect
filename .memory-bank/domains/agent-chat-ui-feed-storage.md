---
description: PostgreSQL storage and transaction rules for Agent Chat Bus, UI Feed, and roster-introduction reconciliation.
status: active
type: data_spec
last_updated: 2026-07-17
source_of_truth:
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/ui-feed.md
  - .memory-bank/contracts/agent-roster-bootstrap.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/domains/safety-action-routing.md
  - .memory-bank/states/companion-governance.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
---
# Agent Chat And UI Feed Storage

## Scope

Defines the PostgreSQL Bus/UI rows, uniqueness rules, transaction boundaries,
and FT-008 restart-safe introduction reconciliation. FT-011 and FT-013 reuse
the same UI table only for derived Safety and Companion projections;
authoritative Safety/governance records remain in their owning storage. This
spec does not define frontend layout, Safety classification policy, ordinary
tasks, physical-action effects, or provider/model execution.

## Tables

### `agent_introduction_batches`

- `batch_id`: native UUID primary key supplied by `AgentIntroductionBatchV1`.
- `farm_id`, `plant_id`: native UUID foreign keys with `ON DELETE RESTRICT`.
- `roster_version`: positive integer; version 1 is the only current value.
- `content_sha256`: lowercase 64-character digest of the canonical strict batch.
- `created_at`: timezone-aware UTC timestamp assigned on first acceptance.

`(plant_id, roster_version)` is unique. The same batch id, uniqueness key, and
canonical digest is an idempotent duplicate. Any mismatch is
`content_conflict` and writes nothing.

### `ui_feed_events`

- `ui_event_id`: native UUID primary key. For an introduction it is exactly the
  deterministic `introduction_id`.
- `farm_id`, `plant_id`: native UUID foreign keys with `ON DELETE RESTRICT`.
- `created_at`: timezone-aware UTC timestamp preserved from the first write.
- `source_type`, `source_id`, `display_kind`: values from the UI Feed contract.
- `source_refs`, `display_payload`, `visible_to_roles`: strict JSON values
  validated before persistence.
- `visible_to_agents`: non-null boolean fixed to `false`.
- `consumable_by_agents`: non-null boolean fixed to `false`.
- `agent_id`, `roster_version`: non-null only for `agent_introduction`.

`(plant_id, agent_id, roster_version)` is unique for introductions. Duplicate
canonical content succeeds without changing `created_at`; conflicting content
fails closed. UI rows are presentation records and never runtime facts or Bus
input.

### `agent_bus_events`

- `event_id`: native UUID primary key.
- `farm_id`, `plant_id`: native UUID foreign keys with `ON DELETE RESTRICT`.
- `created_at`, `event_type`, `source_type`, `source_id`.
- `actor_ref`: strict safe attribution JSON or `null` for a system/domain source.
- `payload`, `source_refs`, `authorization_scope`: strict JSON values validated
  against the Agent Chat Bus contract before persistence.
- `consumable_by_agents`: non-null boolean fixed to `true`.

`(plant_id, source_type, source_id, event_type)` is unique. An identical retry
is idempotent; a conflicting retry fails closed. No UI payload, raw chat,
provider history, hidden reasoning, credential, session/token material, or
unapproved proposal may be stored.

## Introduction sink transaction

The concrete `AgentIntroductionSink.store_batch(batch)`:

1. validates the complete strict eight-item batch and canonical digest;
2. reloads the Plant inside the write transaction and requires the same Farm
   plus `status=active`;
3. inserts one batch row and exactly eight `agent_introduction` UI rows in one
   transaction, or inserts nothing;
4. returns `accepted(true,8,null)` only after commit;
5. returns `duplicate(true,8,null)` only when the existing batch and all eight
   UI rows have identical canonical content;
6. maps inactive/missing/wrong-Farm to `plant_not_publishable`, malformed input
   to `batch_invalid`, canonical mismatch to `content_conflict`, and storage
   failure to `persistence_failed`, always with zero accepted on rejection or
   failure.

There is no partial batch, per-item result, fake durable sink, in-memory
delivery authority, or provider call.

## Active-Plant reconciliation

One idempotent `reconcile_active_plants()` service scans current active Plants,
builds the deterministic current roster batch through the FT-007 builder, and
passes each missing/incomplete key through the same concrete sink transaction.
It may run at local app startup and through an internal test/maintenance entry
point; no distributed worker, broker, or outbox is required.

- Archived Plants are excluded before batch construction and rechecked by the
  sink transaction.
- Archive racing the scan produces no new rows.
- Existing introduction UI rows remain retained while archived.
- Restore performs no replay. A later fresh reconciliation sees the current
  active Plant and idempotently fills only a missing current roster batch.
- A process crash before commit leaves no accepted batch. A crash after commit
  is an identical duplicate on retry.

## Classified publication transaction

An FT-008 safe-information publisher writes its `agent_bus_events` row and
matching `agent_message` UI row in one transaction after validating the
immutable MessageEnvelope, matching `SafetyClassificationResultV1`, current
ActorContext authorization, and current active Plant. Either both rows commit
or neither does. The Bus row stores candidate text only inside the typed quoted
payload; the UI row stores the same text only inside the literal display
payload.

`blocked_uncertain` may create only one generic `block_notice` UI row and must
not store candidate text. `safe_task_request` and `physical_action` create no
FT-008 rows and remain owned by FT-012 and FT-011 respectively.

## Safety status projection storage

FT-011 reuses `ui_feed_events` for one derived `safety_status` row per immutable
Safety action decision:

- `ui_event_id` is exactly the UUIDv4 `decision_id` and `source_id` is its
  canonical UUID text;
- `source_type=safety`, `display_kind=safety_status`, both agent flags are
  false, and `agent_id`/`roster_version` are null;
- `source_refs` and `display_payload` validate against the exact UI Feed Safety
  variant; candidate/model text is forbidden;
- `visible_to_roles` is exactly `boss|engineer`; the protected feed read still
  applies current per-Plant authorization;
- the authoritative `safety_action_decisions` row and UI row insert in one
  database transaction, or neither commits;
- an identical `decision_id` retry is idempotent; any different canonical
  content is a conflict and writes nothing.

This projection cannot mutate a Safety decision, approve/reject it, create an
`action_task`, enter Agent Chat Bus, or trigger a device. Archive races fail the
owning atomic decision/UI transaction; restore does not replay an earlier
denied handoff.

## Companion projection storage

FT-013 reuses the existing tables; no parallel Bus/UI tables or mutable
governance copy is allowed.

- `agent_bus_events` accepts the existing `domain_event_ref` payload with
  `record_type=decision_record`. The row stores only the authoritative
  DecisionRecord reference and is unique/idempotent under the existing
  `(plant_id,source_type,source_id,event_type)` key.
- `ui_feed_events` accepts `source_type=companion_governance`,
  `display_kind=companion_governance`, and one strict attention, proposal, or
  decision payload from the UI Feed contract. Both agent flags remain false.
- Bus/UI rows are derived projections. They cannot approve/reject/supersede a
  proposal, create a DecisionRecord, advance its workflow effect, or replace
  authoritative FT-013 records.
- FT-013 must update the strict model validators and any affected database
  constraints in the same implementation slice before emitting a new variant.
  Existing FT-008 rows and variants remain valid and unchanged.
- Projection writes recheck current authorization and active Plant at their
  write boundary. Archive blocks new rows; restore causes no replay.

Exact DecisionRecord creation/projection atomicity and UI transition
idempotency belong to the FT-013 data specification because they depend on its
record/version and workflow-effect model.

## Verification

- Migration/model tests inspect UUID PK/FK parity, restricted deletes,
  constraints, uniqueness, and JSON/boolean defaults.
- PostgreSQL integration tests prove introduction 8-or-0 atomicity, duplicate
  identity, content conflict, restart reconciliation, and archive race denial.
- Publication tests prove Bus/UI atomicity, current authorization, strict
  classification routing, typed quotation, literal display data, and zero
  writes on denial.
- Safety projection tests prove exact payload/status constraints,
  decision/UI atomicity, idempotent duplicate versus conflict, candidate-text
  absence, current active-Plant guard, and unchanged existing FT-008 rows.
- Static and integration checks prove UI rows are never loaded by agent context
  builders and Bus rows are never used as mutable Plant authority.
- Companion integration checks prove existing FT-008 variants remain valid,
  only a valid DecisionRecord reference can enter Bus, all Companion UI rows
  remain non-consumable, and no projection becomes governance or Safety
  authority.
