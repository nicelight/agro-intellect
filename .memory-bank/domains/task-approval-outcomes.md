---
description: PostgreSQL authority for ordinary and action tasks, human approvals, automatic follow-ups, outcomes, and their audit refs.
status: active
type: data_spec
last_updated: 2026-07-18
source_of_truth:
  - .memory-bank/features/FT-012-human-approval-tasks-follow-up-outcomes.md
  - .memory-bank/domains/safety-action-routing.md
  - .memory-bank/states/task-follow-up-lifecycle.md
  - .memory-bank/contracts/timeline-event.md
---
# Task, Approval, And Outcome Data

## Scope

Defines the exact PostgreSQL records, constraints, idempotency fingerprints,
transaction boundaries, and Timeline reference ownership for FT-012. These
rows are mutable operational authority; Timeline, UI Feed, MessageEnvelope,
and model output are not.

## Out of scope

- FT-011 Safety classification/decision fields before
  `pending_human_approval`;
- endpoint payloads, frontend state, reminders, schedulers, workers, outbox,
  automated devices, and Plant-state promotion;
- a generic idempotency framework or a second mutable action proposal.

## Shared storage rules

- Primary and foreign keys are PostgreSQL native UUID mapped to Python
  `uuid.UUID`; new ids are application-generated UUIDv4.
- Authority/history FKs use `ON DELETE RESTRICT`. No task, approval, or outcome
  row is hard-deleted in MVP.
- Timestamps are timezone-aware UTC server values.
- Safe refs use the existing unique ordered `kind:identifier` grammar and are
  stored as strict JSON arrays, never arbitrary metadata objects.
- Canonical fingerprints are lowercase SHA-256 of compact UTF-8 JSON with
  sorted object keys, original Unicode, canonical UUID/timestamp strings, and
  no insignificant whitespace.
- Each mutation stores its request id and fingerprint on the authoritative row
  affected by that command. Reusing one request id with different canonical
  content is always a conflict.

## `approvals`

One row materializes one immutable FT-011 pending decision:

- `approval_id`: UUID primary key;
- `safety_decision_id`: unique UUID FK to
  `safety_action_decisions.decision_id`, `ON DELETE RESTRICT`;
- `farm_id`, `plant_id`: restrictive UUID FKs equal to the Safety decision;
- `action_kind`: `ph_adjustment|ec_adjustment|solution_change`, equal to the
  source decision;
- `status`: `pending|approved|rejected`;
- `record_version`: positive integer, `1` while pending and `2` after the sole
  terminal decision;
- `valid_until`: exact copy of the non-null source decision `expires_at`;
- `source_refs`: ordered source decision plus selected pH/EC evidence refs;
- `created_at`;
- nullable terminal fields `decided_at`, `decision_actor_account_id`,
  `decision_actor_membership_id`, `decision_actor_role_preset`,
  `decision_permission_source`, and `decision_grant_id`;
- nullable `decision_request_id`, `decision_request_fingerprint`;
- nullable `decision_event_ref` in the canonical Timeline ref shape.

Database checks enforce the exact pending/terminal nullability matrix. A
pending row has no decision attribution/request/event. A terminal row has all
required fields, and `decision_actor_role_preset` is `boss|engineer` only.
There is no approval text, target value, quantity, device command, candidate
output, provider payload, arbitrary metadata, or mutable expiry field.

`materialize_pending_approval(safety_decision_id)` locks the immutable Safety
decision. It creates a row only when the source is exactly
`pending_human_approval/ready_for_human_approval` with a non-null expiry and
the three supported action kinds. The unique source decision is the natural
key. A uniqueness race is re-read: identical scope/action/expiry/evidence is a
duplicate success; any mismatch is `TASK_VERSION_CONFLICT`.

## `tasks`

Every operational Task row contains:

- `task_id`: UUID primary key;
- `farm_id`, `plant_id`: restrictive UUID FKs;
- `kind`: `check|measurement|action|follow_up`;
- `status`: `open|completed`;
- `display_text`: normalized literal UTF-8 text, 1..2000 Unicode code points;
- `source_type`:
  `safe_task_request|governance_decision|approved_action|automatic_follow_up`;
- `source_refs`: ordered safe refs;
- nullable `classification_message_id`: restrictive unique FK to
  `safety_classifications.message_id` for `safe_task_request` only;
- nullable `decision_record_id`: restrictive unique FK to
  `decision_records.decision_record_id` for `governance_decision` only;
- nullable `approval_id`: restrictive unique FK to `approvals.approval_id` for
  `approved_action` only;
- nullable `parent_action_task_id`: restrictive self-FK, unique for
  `automatic_follow_up` only;
- nullable `due_at`; automatic action follow-up requires it, other Tasks may
  leave it null;
- creation attribution `created_by_account_id`,
  `created_by_membership_id`, `created_by_role_preset`, nullable
  `created_by_agent_id`, and `created_at`;
- nullable `create_request_id`, `create_request_fingerprint` for ordinary
  command idempotency;
- `created_event_ref`;
- nullable completion fields `completed_at`, `completed_by_account_id`,
  `completed_by_membership_id`, `completed_by_role_preset`,
  `completion_request_id`, `completion_request_fingerprint`, and
  `completed_event_ref`.

Checks enforce:

- exactly one source identity appropriate to `source_type`;
- `governance_decision` iff kind is `check|measurement|follow_up`,
  `decision_record_id` is non-null, and classification/approval/parent ids are
  null; its source refs still retain the validated proposal message and
  classification refs;
- `action` iff `source_type=approved_action` with non-null unique Approval;
- `automatic_follow_up` iff `kind=follow_up`, parent is an `action`, and
  `due_at=parent.completed_at + 48 hours` at service validation;
- a completed Task has the complete completion field set, while an open Task
  has none;
- a non-null `create_request_id` is unique and paired with its fingerprint;
- agent-originated attribution is supplementary; the current human
  ActorContext remains the authority for the write;
- `display_text` is literal data and never contains a serialized command,
  approval, provider object, auth state, or arbitrary JSON payload.

For a classified-message ordinary task, `classification_message_id` is the
natural uniqueness key. The row stores source refs exactly as
`message_envelope:<message_id>`, `safety_classification:<message_id>`, then the
ordered authoritative envelope refs. The service
loads both artifacts, requires identical `message_id` and scope, matching
`safe_task_kind`, derived `ordinary_dispatch`, and current task-creation
authority. Canonical `origin_agent_id=companion` is governance-held and is
rejected by this source branch. The service reloads every
envelope source ref from the owning PostgreSQL repository and requires the same
Farm/Plant scope; Timeline, UI, missing, unauthorized, or mismatched refs fail
closed. The envelope text is stored literally as `display_text`; it cannot
select `action` or execute anything.

For a governance-decision ordinary Task, `decision_record_id` is the natural
uniqueness key. Its source refs are exactly the DecisionRecord, owning
proposal, proposal message, matching classification, then the remaining
ordered authoritative proposal refs after stable duplicate removal. FT-013
loads the immutable approved DecisionRecord, the owning proposal that was
locked current-pending version `1` at decision start and is now approved
version `2` for that same record in the caller-owned UoW, matching persisted
classification, satisfied attention, issue/Plant scope, and every source ref;
requires the same `check|measurement|follow_up` kind at every boundary; and
calls the ordinary-task insert inside the owning governance transaction. The
Task stores literal proposal task text, never proposal rationale or an
executable instruction. An insertion/audit failure aborts the whole
DecisionRecord transaction.

The approved proposal source may be flushed-but-uncommitted in that UoW or
already committed for an identical retry. It is not rejected merely because it
is terminal: `approved`, `record_version=2`, and the same non-null
`decision_record_id` are the required command-entry state. Pending-at-entry,
rejected, superseded, or approved-for-another-record sources are invalid.

For an approved action, `approval_id` is the natural uniqueness key. Approval
`pending -> approved` and Task insert are one transaction. Rejection inserts no
Task. A failed insert or required audit append rolls the Approval transition
back to pending.

For automatic follow-up, `parent_action_task_id` is the natural uniqueness
key. Action completion and the follow-up insert are one transaction. The
follow-up `display_text` is a project-owned non-imperative request to record
the result after the approved action; it never copies model candidate text.

## `outcomes`

One Outcome completes one follow-up:

- `outcome_id`: UUID primary key;
- `follow_up_task_id`: unique restrictive UUID FK to `tasks.task_id`;
- `farm_id`, `plant_id`: equal to the Task scope;
- `value`: `improved|worsened|unchanged|no_data`;
- `evidence_refs`: ordered unique safe refs;
- `recorded_at`;
- `recorded_by_account_id`, `recorded_by_membership_id`,
  `recorded_by_role_preset`;
- `request_id`: unique UUID;
- `request_fingerprint`: lowercase SHA-256;
- `outcome_event_ref` and `task_completed_event_ref`.

The FK must resolve to an open `follow_up` Task. Non-`no_data` values require
one through four authorized evidence refs; `no_data` permits zero through four.
The evidence-ref records are reloaded through their owning PostgreSQL
repositories and must match Farm/Plant scope. Timeline/UI/model text is not
accepted as evidence authority.

Outcome insertion and follow-up completion share one transaction and one
timestamp. The follow-up Task is the natural uniqueness key. A uniqueness race
is re-read and becomes identical retry only when the request id, fingerprint,
value, and refs match exactly.

## Mutation fingerprints

The one internal `create_ordinary_task` service accepts the closed
`classified_message|governance_decision` source union defined by the Task
contract. The command bodies used for persisted fingerprints are exact:

- classified-message ordinary task: schema version,
  `source_branch=classified_message`, request id equal to the immutable
  MessageEnvelope `run_id`, message id, safe task kind, normalized envelope
  candidate output as display text, and ordered revalidated source refs;
- governance ordinary task: schema version,
  `source_branch=governance_decision`, DecisionRecord request id and request
  fingerprint, DecisionRecord id, proposal id, exact ordinary kind, normalized
  task display text, and ordered revalidated source refs;
- approval decision: schema version, request id, safety decision id,
  expected version, and `approved|rejected`;
- task completion: schema version, request id, task id;
- follow-up outcome: schema version, request id, follow-up task id, value, and
  ordered evidence refs.

Derived server timestamps, ActorContext, UI text, Timeline ids, and database
row order are not fingerprint inputs. They are revalidated/current output, not
caller-controlled identity.

## Transaction and Timeline ordering

The services use the existing transaction/UoW and Timeline append seam:

- classified-message Task creation uses a service-owned UoW, appends
  `task_created`, persists its ref, and commits before returning;
- governance-decision Task creation uses the caller-owned DecisionRecord UoW,
  appends `task_created`, persists its ref, flushes, and never commits or rolls
  back independently;
- reject appends `approval_decided` then commits the terminal Approval;
- approve appends `approval_decided` and `task_created`, then commits the
  Approval and exactly one action Task together;
- ordinary/action completion appends `task_completed`; action completion also
  appends `task_created` for the automatic follow-up before committing both
  Task rows;
- outcome recording appends `task_completed` and
  `follow_up_outcome_recorded`, then commits Outcome and Task completion.

If an append fails, the PostgreSQL mutation is rolled back and success is not
returned. If append succeeds but the later PostgreSQL commit fails, the event
may remain non-authoritative audit noise under the Timeline contract. Runtime
reads never use it to create, repair, complete, or replay a row.

Approval materialization emits no Timeline event; the immutable FT-011
decision is its source trace until a human decision occurs.

## Migration

One additive FT-012 Alembic revision creates `approvals`, `tasks`, and
`outcomes` after the actual implemented FT-011 head. It adds exact enums/checks,
restrictive UUID FKs, partial/natural unique indexes, request-id/fingerprint
constraints, and no cascade delete. Execution must inspect the then-current
head; planning does not hardcode the present FT-008 revision as `down_revision`.

Existing exact-head migration assertions advance to this revision in the same
wave. Downgrade removes only FT-012 objects in reverse FK order and never
rewrites FT-011 or earlier rows.

The later FT-013 migration adds only the `governance_decision` source value,
nullable unique restrictive `decision_record_id`, and the extended exact source
check after DecisionRecord storage exists. Existing FT-012 rows and source
matrices remain unchanged.

## Verification

Migration/model tests inspect UUID/FK parity, enum/check matrices, uniqueness,
no-cascade behavior, and head order. PostgreSQL integration tests prove
read/write round trips, parent-row locking plus uniqueness races, approval/task
and action/follow-up rollback, Outcome atomicity, exact fingerprints,
Timeline failure behavior, archive/current-guard races, and absence of device,
raw candidate, provider, auth, or Plant-state side effects.

FT-013 integration additionally proves DecisionRecord/Task atomicity,
identical-versus-conflicting DecisionRecord retries, exact classification-kind
matching, same-UoW pending-to-approved phase eligibility without an intermediate
commit, rejection of every wrong proposal terminal/link state, and zero
Task/DecisionRecord effect on archive or insert failure.

## Related specs

- [.memory-bank/states/task-follow-up-lifecycle.md](../states/task-follow-up-lifecycle.md)
- [.memory-bank/contracts/task-approval-http.md](../contracts/task-approval-http.md)
- [.memory-bank/contracts/task-follow-up-runtime.md](../contracts/task-follow-up-runtime.md)
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md)
- [.memory-bank/domains/safety-action-routing.md](safety-action-routing.md)
