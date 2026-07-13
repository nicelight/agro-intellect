---
description: PostgreSQL storage and transaction rules for FT-008 Agent Chat Bus, UI Feed, and roster-introduction reconciliation.
status: active
type: data_spec
last_updated: 2026-07-12
source_of_truth:
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/ui-feed.md
  - .memory-bank/contracts/agent-roster-bootstrap.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
---
# Agent Chat And UI Feed Storage

## Scope

Defines the PostgreSQL authority rows, uniqueness rules, transaction boundaries,
and restart-safe reconciliation owned by FT-008. It does not define frontend
layout, Safety classification policy, ordinary tasks, physical-action effects,
or provider/model execution.

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

## Verification

- Migration/model tests inspect UUID PK/FK parity, restricted deletes,
  constraints, uniqueness, and JSON/boolean defaults.
- PostgreSQL integration tests prove introduction 8-or-0 atomicity, duplicate
  identity, content conflict, restart reconciliation, and archive race denial.
- Publication tests prove Bus/UI atomicity, current authorization, strict
  classification routing, typed quotation, literal display data, and zero
  writes on denial.
- Static and integration checks prove UI rows are never loaded by agent context
  builders and Bus rows are never used as mutable Plant authority.

