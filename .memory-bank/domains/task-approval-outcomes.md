---
description: PostgreSQL authority for ordinary and action tasks, human approvals, automatic follow-ups, outcomes, and their audit refs.
status: active
type: data_spec
last_updated: 2026-07-24
source_of_truth:
  - .memory-bank/features/FT-012-human-approval-tasks-follow-up-outcomes.md
  - .memory-bank/domains/safety-action-routing.md
  - .memory-bank/states/task-follow-up-lifecycle.md
  - .memory-bank/contracts/timeline-event.md
---
# Task, Approval, And Outcome Data

## Scope

Defines the exact PostgreSQL records, constraints, idempotency fingerprints,
transaction boundaries, and Timeline reference ownership for FT-012. Task,
Approval, and Outcome rows are mutable operational authority; runtime and
classified dispatch dispositions are immutable one-shot authority. Timeline,
UI Feed, MessageEnvelope, and model output are not.

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

## Task Follow-Up runtime persistence boundary

The current MVP has no public endpoint, worker, scheduler, durable delivery
identity, or accepted retry/crash contract for the provider-neutral
`task_follow_up` invocation. It therefore stores no pre-classification runtime
disposition and defines no runtime replay authority.

Each explicit internal invocation performs the normal provider-neutral path,
rechecks current ActorContext/Farm/Plant authority after model I/O, appends only
the sanitized attempt audit, creates an in-memory MessageEnvelope, invokes the
canonical Safety classifier, and then calls the sole ordinary Task writer.
Provider and classifier I/O remain outside Task write transactions. A denied,
failed, or interrupted invocation may be called again and may repeat
non-authoritative model/audit/classification work.

`TaskFollowUpCommandV1.run_id` and its canonical command fingerprint remain
typed invocation inputs, but they do not create a durable runtime ledger or a
zero-call replay result. Duplicate Task prevention belongs to the downstream
`ordinary_task_dispatch_dispositions` and Task request identities. A future
durable worker/scheduler must define delivery identity and retry/crash
semantics before any runtime ledger is reintroduced.

The historical `task_follow_up_runtime_dispositions` table may exist in an
already upgraded deployment. Current code and fresh ORM metadata do not map,
read, or write it. Physical removal requires a forward migration whose
preflight proves the table contains no deployment rows; a populated table is a
data-preservation stop condition rather than permission to discard history.

## `ordinary_task_dispatch_dispositions`

One project-owned immutable row makes each classified-message ordinary-task
handoff one-shot. It is operational PostgreSQL authority, not a Timeline, Bus,
UI, MessageEnvelope, or classification projection:

- `classification_message_id`: primary key and restrictive UUID FK to
  `safety_classifications.message_id`;
- `run_id`: globally unique UUID copied from the exact MessageEnvelope under
  `uq_ordinary_task_dispatch_dispositions_run`;
- `farm_id`, `plant_id`: restrictive UUID FKs equal to the classification and
  envelope scope;
- `input_sha256`: exact lowercase classification input fingerprint for the
  validated envelope;
- `outcome`: `consumed|denied`;
- nullable `denial_code`:
  `TASK_SCOPE_NOT_FOUND|TASK_COMMAND_FORBIDDEN|TASK_PLANT_NOT_ACTIVE`;
- `recorded_at`: timezone-aware UTC server timestamp.

Database checks enforce the exact terminal matrix: `consumed` has no
`denial_code`, while `denied` has exactly one closed current-guard denial code.
There is no pending state, product update/delete path, retry counter, payload
text, authorization snapshot, Timeline ref, Task-create commitment, or Bus/UI
field. `tasks` remains the sole Task authority and its existing unique
`classification_message_id` relates a consumed disposition to the Task without
duplicating `task_id` in the disposition row.

For a first exact handoff, the service validates the immutable persisted
classification and envelope input fingerprint, acquires the established
current ActorContext/Plant/grant guard locks, and re-reads the disposition
before deciding. A guard denial inserts and commits `denied` in that same
guard transaction, then returns the stored typed denial. An eligible handoff
inserts `consumed` in the same transaction as the Task and its persisted
Timeline ref. A matching terminal retry reads the disposition first. `denied`
returns the stored denial without re-evaluating the guard. `consumed` remains
terminal and resolves the Task through the unique
`classification_message_id` relationship only after the current read/task
authority guard passes; a failed guard leaks no Task and changes no row. A
    missing required Task or inconsistent classified-disposition identity fails
redacted. The retry path does not reconstruct the original Task text, kind,
source graph, human attribution, or create-fingerprint preimage. Any reuse of
either unique identity conflicts without replacement. A disposition
persistence failure creates no Task and cannot be treated as success. Restore
never edits or deletes the row and cannot make `denied` operative; a new
runtime invocation requires both a new `run_id` and a new `message_id`.

`Task.create_request_fingerprint` remains the normal service-command
idempotency value. The Task, consumed disposition, and required audit ref
commit or roll back together. The product exposes no Task/disposition update
surface; coordinated direct PostgreSQL edits across authority rows are outside
the current deployment threat model and do not justify a second independent
commitment, update trigger, deep replay-graph validator, or hostile mutation
suite.

For `origin_agent_id=task_follow_up`, the classified-message branch uses the
same ordinary-dispatch run-key serialization, immutable persisted
classification, envelope input fingerprint, current-scope/source locks, and
unique run/message identities as every other accepted classified source. It
does not require or consult a pre-classification runtime row. Other agents
retain the existing classified-message contract unchanged.

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
select `action` or execute anything. Creation additionally requires the exact
terminal `consumed` disposition described above to commit in the same UoW.

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

The existing W1 Outcome evidence resolver remains the closed
`plant|daily_checkin|manual_measurement|photo_catalog_item|plant_state_record`
union. `task:` and `outcome:` are not Outcome evidence and MUST remain rejected.
W2 uses a separate competence-specific source-record resolver for its strict
`task|outcome|daily_checkin|manual_measurement|plant_state_record` provider
record/source-ref union. The W2 resolver is used only to assemble/revalidate
Task Follow-Up runtime inputs and classified envelope refs; it is never called
by `record_follow_up_outcome`.

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

Thus the classified-message create fingerprint covers normalized text, kind,
the exact ordered source graph, run/request id, and message/classification
identity. It does not cover Farm/Plant scope, origin agent, or ActorContext
attribution; those remain current writer-boundary checks.

## Transaction and Timeline ordering

The services use the existing transaction/UoW and Timeline append seam:

- Task Follow-Up appends its sanitized audit after the post-I/O current guard,
  releases any audit-owned work before Safety-classifier I/O, and passes only
  a transient MessageEnvelope to classification;
- classified-message Task creation uses a service-owned UoW, appends
  `task_created`, persists its ref, and commits it with the terminal consumed
  disposition before returning;
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

A classified-message current-guard denial emits no Timeline event. Its
terminal disposition is committed under the same guard locks before the
service surfaces the typed denial. Timeline append success or noise can never
create, deny, consume, or reopen a disposition.

## PostgreSQL uniqueness-loss classification

The globally unique command identities are backed by the named constraints
`uq_approvals_decision_request`, `uq_tasks_create_request`,
`uq_tasks_completion_request`, `uq_outcomes_request`, and
`uq_ordinary_task_dispatch_dispositions_run`. The classified disposition and
Task writer own first-write ordering; there is no pre-classification runtime
row or cross-table runtime advisory protocol. When a flush or commit loses one
of those specific uniqueness races, the service MUST roll back the failed UoW
before any query, then re-read the committed owner in a clean transaction:

- the same canonical parent, request fingerprint, and command content is an
  identical duplicate and returns the first committed result;
- a different parent or any different canonical content is
  `TASK_VERSION_CONFLICT` with no replacement effect;
- if the named owner is not visible after rollback, or the error is for any
  other constraint/SQLAlchemy failure, the result remains
  `TASK_PERSISTENCE_FAILED`.

This mapping does not suppress or reinterpret unrelated database failures.
Any Timeline append already written by the losing transaction remains
non-authoritative noise under the existing contract.

## Migration

One additive FT-012 Alembic revision creates `approvals`, `tasks`, `outcomes`,
and `ordinary_task_dispatch_dispositions` after the actual implemented FT-011
head. It adds exact enums/checks, restrictive UUID FKs, partial/natural unique
indexes, request-id/fingerprint constraints, and no cascade delete. Execution
must inspect the then-current head; planning does not hardcode the present
FT-008 revision as `down_revision`.

Existing exact-head migration assertions advance to this revision in the same
wave. Downgrade removes only FT-012 objects in reverse FK order and never
rewrites FT-011 or earlier rows.

TASK-040 historically added the narrow `ft012_runtime_dispositions` revision
directly after `ft012_task_approval_outcomes`. The target design removes all
code/ORM use of its pre-classification runtime table and removes the
`expected_task_create_fingerprint` column, matrix check, write-once function,
and trigger from the classified disposition.

Because that historical revision may already be applied, the reopened
TASK-040 adds one forward cleanup revision after the executor-confirmed current
head. Upgrade always drops the redundant trigger, function, check, and column.
It drops `task_follow_up_runtime_dispositions` only after an explicit
preflight proves the table empty; any row aborts before DDL and routes to a
data-preservation handoff. The revision does not rewrite Task, classified
disposition, Safety, MessageEnvelope, Approval, Outcome, or FT-013 rows.
Downgrade may restore the historical schema objects only for code rollback
compatibility; they are not active product acceptance requirements. Fresh ORM
metadata contains none of those objects. Exact-head consumers advance without
rewriting the existing FT-013 migration.

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
raw candidate, provider, auth, or Plant-state side effects. They also prove
the exact disposition matrix, atomic consumed/denied writes, immutable retry,
same-identity denial after restore, new-identity eligibility, and deterministic
post-rollback request-owner classification.

TASK-040 PostgreSQL tests additionally prove strict separation of the W1
Outcome evidence resolver from the competence source resolver, linear
post-I/O guard/classifier/Task routing, and absence of a mapped or written
pre-classification runtime ledger. They prove normal classified writes
atomically persist Task, audit, and `consumed|denied` disposition; exact
classified retry, current-authority duplicate reads, missing-link failure,
write-side concurrency/rollback/idempotency, and no duplicate Task. Migration
tests prove commitment cleanup and empty-table runtime cleanup, plus
before-DDL refusal when historical runtime rows exist. Runtime-ledger
crash/replay/advisory-order and coordinated direct-row corruption probes are
not required.

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
