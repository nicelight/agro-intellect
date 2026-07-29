---
description: PostgreSQL storage and transaction rules for Agent Chat Bus, UI Feed, and lazy roster-introduction materialization.
status: active
type: data_spec
last_updated: 2026-07-28
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
and FT-008 lazy introduction materialization on authorized active-Plant Feed
access. FT-011 and FT-013 reuse the same UI table only for derived Safety and
Companion projections; authoritative Safety/governance records remain in their
owning storage. This
spec does not define frontend layout, Safety classification policy, ordinary
tasks, physical-action effects, or provider/model execution.

## Tables

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

`(plant_id, agent_id, roster_version)` is unique for introductions. The lazy
path treats an existing key as already materialized and never rewrites its
payload or `created_at`. UI rows are presentation records and never runtime
facts or Bus input.

### `agent_bus_events`

- `event_id`: native UUID primary key.
- `farm_id`, `plant_id`: native UUID foreign keys with `ON DELETE RESTRICT`.
- `created_at`, `event_type`, `source_type`, `source_id`.
- `actor_ref`: strict safe attribution JSON or `null` for a system/domain source.
- `payload`, `source_refs`: strict JSON values validated against the Agent Chat
  Bus contract before persistence.
- `authorization_scope`: strict non-null JSON for actor-originated
  `classified_publication`, and `null` only for a backend-owned
  `domain_record` written after the owning domain transaction has completed
  its own authorization and active-Plant checks.
- `consumable_by_agents`: non-null boolean fixed to `true`.

`(plant_id, source_type, source_id, event_type)` is unique. An identical retry
is idempotent; a conflicting retry fails closed. No UI payload, raw chat,
provider history, hidden reasoning, credential, session/token material, or
unapproved proposal may be stored.

## Lazy introduction materialization transaction

The protected Plant Feed application boundary owns one transaction for current
authorization, active-state validation, missing-row insertion, and the
subsequent ordered page read:

1. resolve and lock the current active Account/FarmMembership identity;
2. lock the Plant in the ActorContext Farm and, for Engineer/Consultant, the
   current active PlantAccessGrant;
3. preserve the existing no-leak denial if current read authorization fails;
4. if the Plant is archived and the actor has retained-history permission,
   perform the read only and insert nothing;
5. if the Plant is active, derive canonical roster version 1 introduction
   metadata, load the existing introduction keys, and insert only missing
   `UIFeedEvent` rows;
6. read the page using the unchanged `(created_at ASC, ui_event_id ASC)` order
   and cursor grammar, then commit.

Cursor/limit validation and every documented authorization/error precedence
remain compatible. A failing validation or persistence operation rolls back all
new rows from that request. A storage failure maps through the existing
`FEED_PERSISTENCE_FAILED` boundary; a later authorized active-Plant Feed open
retries from durable rows.

The current Plant lock serializes concurrent materializers for one Plant.
Deterministic `ui_event_id` plus
`(plant_id, agent_id, roster_version)` uniqueness is the final duplicate guard.
Existing introduction rows retain their identity, payload, and `created_at`;
the materializer never updates, replaces, or deletes them. There is no batch
row, digest, sink/result matrix, pending intent, worker, startup scan,
maintenance reconciliation, Agent Chat Bus write, provider call, or
agent-context effect.

Plant creation and its `201` transaction perform no introduction work. Archive
and restore mutate only Plant lifecycle state. Archived retained-history reads
and restore insert nothing; after restore, only a later currently authorized
active-Plant Feed open may fill missing rows.

## Forward migration

The forward migration removes only the presentation-only
`agent_introduction_batches` table and its batch metadata. It preserves every
existing `ui_feed_events` row, including introduction ids, payloads,
`created_at`, uniqueness, foreign keys, ordering index, and agent-consumability
constraints. It performs no introduction backfill, rewrite, delete, or
reordering and adds no replacement lifecycle table.

## Classified publication transaction

An FT-008 safe-information publisher writes its `agent_bus_events` row and
matching `agent_message` UI row in one transaction after validating the
immutable MessageEnvelope, matching `SafetyClassificationResultV1`, current
ActorContext authorization, current active Plant, and derived
`ClassificationConsumerRouteV1=ordinary_dispatch`. Either both rows commit or
neither does. The Bus row stores candidate text only inside the typed quoted
payload; the UI row stores the same text only inside the literal display
payload.

Under `ordinary_dispatch`, `blocked_uncertain` may create only one generic
`block_notice` UI row and must not store candidate text.
`safe_task_request` and `physical_action` create no FT-008 rows and remain
owned by FT-012 and FT-011 respectively.

Canonical `origin_agent_id=companion` derives
`companion_governance_hold` and is rejected by every ordinary FT-008/FT-011/
FT-012 consumer. Its safe-information/task classifications may be read only by
the guarded proposal writer; held physical/blocked/mismatch/failure has no
downstream writer. No Bus/UI/Safety/Task row is queued for retry, restore, or
reconciliation. Dedicated Companion UI summaries are written later only from
authoritative governance rows under the separate projection rules below and
never copy raw candidate/proposal/rationale/provider text.

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
  decision payload from the UI Feed contract. `visible_to_roles` is exactly
  `boss|engineer|consultant`; protected reads still apply current Plant
  authorization, and Consultant visibility grants no command authority. Both
  agent flags remain false.
- Bus/UI rows are derived projections. They cannot approve/reject/supersede a
  proposal, create a DecisionRecord, advance its workflow effect, or replace
  authoritative FT-013 records.
- FT-013 must update the strict model validators and any affected database
  constraints in the same implementation slice before emitting a new variant.
  Existing FT-008 rows and variants remain valid and unchanged.
- Projection writes recheck current authorization and active Plant at their
  write boundary. Archive blocks new rows; restore causes no replay.
- Companion projection identity is exact: attention uses
  `ui_event_id=attention_id`; each proposal uses
  `ui_event_id=proposal_id` and updates that one presentation row in place as
  its authoritative state becomes `approved|rejected|superseded`; each
  DecisionRecord uses `ui_event_id=decision_record_id`.
- Decision Bus publication uses `event_id=decision_record_id`,
  `source_type=domain_record`, `source_id=decision_record_id`,
  `event_type=domain_event_ref`, and null `actor_ref`/`authorization_scope`.
  Human attribution remains inside the referenced authoritative
  DecisionRecord and is not copied into the agent-consumable fact.
- On authorized active-Plant context read, that Bus reference resolves the
  DecisionRecord plus its approved version-2 proposal into exactly the
  non-persisted `ApprovedGovernanceSummaryV1` owned by the Companion Governance
  data spec. The builder never persists that DTO or substitutes
  `CompanionConclusionV1`, UI payloads, mutable focus/attention, or Task state.
- The authoritative FT-013 write and every required Companion Bus/UI
  projection commit in the same PostgreSQL transaction. Proposal terminal
  updates rebuild and overwrite the derived projection from authoritative
  proposal data, including recovery of a missing or stale presentation row.
  A real projection persistence failure still aborts the owning transaction;
  presentation mismatch alone does not.
- The attention UI row is the immutable literal notification created for that
  attention cycle; current proposal/status are read from governance detail,
  not copied into this payload. Derived CompanionConclusion is resolved by the
  governance read model and is never persisted in Bus or UI.

## Verification

- Migration/model tests inspect UUID PK/FK parity, restricted deletes,
  constraints, uniqueness, and JSON/boolean defaults.
- Migration/model tests prove the batch table is removed without changing or
  deleting existing `UIFeedEvent` rows and that introduction uniqueness,
  restricted foreign keys, and non-consumability constraints remain.
- PostgreSQL integration tests prove authorized active-Plant Feed access
  inserts only missing canonical introductions; repeat, concurrent, failure,
  and client-retry paths are idempotent; existing rows are unchanged; and
  Plant create/startup/restore/archived-read paths write none.
- Publication tests prove Bus/UI atomicity, current authorization, strict
  classification/consumer routing, typed quotation, literal display data, zero
  writes on denial, zero ordinary effect for every held Companion branch, no
  replay after retry/restore/reconciliation, and unchanged non-Companion
  behavior.
- Safety projection tests prove exact payload/status constraints,
  decision/UI atomicity, idempotent duplicate versus conflict, candidate-text
  absence, current active-Plant guard, and unchanged existing FT-008 rows.
- Static and integration checks prove UI rows are never loaded by agent context
  builders and Bus rows are never used as mutable Plant authority.
- Companion integration checks prove existing FT-008 variants remain valid,
  only a valid approved DecisionRecord reference can enter Bus, all Companion
  UI rows remain non-consumable, backend domain records alone permit null
  authorization scope, exact projection identities are retry-safe, proposal
  terminal projection repair is authority-derived, real write failures roll
  back the owning transaction, exact `ApprovedGovernanceSummaryV1`
  reconstruction/omission rules hold, and no projection becomes governance or
  Safety authority.
