---
description: Human approval, task completion, automatic follow-up, and outcome lifecycle for the Safety and Task Loop.
status: active
type: state_spec
last_updated: 2026-07-24
source_of_truth:
  - .memory-bank/features/FT-012-human-approval-tasks-follow-up-outcomes.md
  - .memory-bank/states/safety-action-lifecycle.md
  - .memory-bank/domains/safety-action-routing.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
---
# Task And Follow-Up Lifecycle

## Scope

Defines the state transitions after an ordinary safe-task classification or an
FT-011 immutable `pending_human_approval` decision: Approval materialization,
human approve/reject, Task completion, automatic action follow-up, and outcome
recording. It never authorizes or performs a physical device effect.

## Out of scope

- Safety classification, physical-action taxonomy, and pH/EC evidence
  selection before `pending_human_approval`;
- HTTP payloads, database columns, Timeline payload summaries, frontend cards,
  schedulers, workers, reminders, or automated actuation;
- Plant-state confirmation, which remains subject to its owning evidence and
  human-review rules.

## Closed state vocabulary

- `Task.kind`: `check | measurement | action | follow_up`.
- `Task.status`: `open | completed`.
- `Approval.status`: `pending | approved | rejected`.
- `Outcome.value`: `improved | worsened | unchanged | no_data`.

`cancelled` is not an MVP Task state. `expired` is not an Approval state;
expiry is the derived predicate `now > valid_until`. A record is retained when
its Plant is archived; archive does not create another lifecycle state.

## Ordinary safe-task routes

Both source routes below invoke the one closed
`OrdinaryTaskCreateCommandV1` union owned by the Task contract. They are not
separate Task services and cannot bypass the shared persistence, current
authorization, archive, idempotency, Timeline, or authority guards.

An ordinary Task may be created only from:

1. one immutable validated pending `MessageEnvelopeV1`;
2. one durably persisted matching `SafetyClassificationResultV1` with
   `classification=safe_task_request`;
3. a task kind equal to the classification `safe_task_kind`; and
4. a current ActorContext that permits domain-task creation for the same active
   Plant at the write boundary, with every envelope source ref reloaded from
   its owning PostgreSQL authority and matched to that Plant; and
5. derived `ClassificationConsumerRouteV1=ordinary_dispatch`.

The only permitted ordinary kinds are `check|measurement|follow_up`.
`safe_task_request` can never create `action`. Candidate text remains literal
human-facing task data, not an executable instruction, evidence fact, or
authorization claim. A canonical Companion classification is
`companion_governance_hold` and cannot enter this route before an approved
DecisionRecord uses the separate governance branch. The service derives the
exact MessageEnvelope, classification, and upstream source refs plus request
fingerprint defined by the command contract. An identical
`classification_message_id` natural-key retry is idempotent; different content
for that key or request id conflicts without replacing the first Task. This
branch uses the service-owned Session/UoW and commits only after the Task plus
its required Timeline ref are ready.

The classified-message branch also has one immutable PostgreSQL
`ordinary_task_dispatch_dispositions` row per classification message and a
unique `run_id`. The first exact handoff becomes terminal in one of two ways:

- `consumed`: the disposition, Task, required `task_created` ref, and Task
  command fingerprint commit in the same service-owned transaction;
- `denied`: a current Plant/archive/authorization guard denial is evaluated
  under the owning guard locks and the denial disposition commits in that same
  transaction before the typed denial is returned.

The service validates the persisted immutable classification and exact
envelope input identity before recording either result. It re-reads a matching
terminal disposition before any current-guard re-evaluation. An exact consumed
retry may return the existing Task only after the current read/task authority
guard passes; an exact denied retry returns the stored denial without a new
guard evaluation or Task, including after restore. A different message
using the same `run_id`, a different run using the same `message_id`, or any
fingerprint/scope mismatch conflicts and cannot replace the first disposition.
If the disposition cannot be persisted, the command fails closed with no Task.
Timeline, Bus, UI Feed, MessageEnvelope, and classification rows are not this
one-shot authority. A later eligible attempt requires a new Agent Runtime
invocation with both a new `run_id` and a new `message_id`.

Consumed retry resolves the Task through the persisted classification and
ordinary dispatch identities plus the Task's unique classification link. It
returns the existing Task only after current ActorContext/Farm/Plant read/task
authority passes; a missing required Task or mismatched classified disposition
fails through the existing redacted Task persistence boundary. Retry does not
reconstruct the original Task text, kind, source graph, historical
attribution, or create-fingerprint preimage. Coordinated direct PostgreSQL
corruption is outside the current product threat model and adds no independent
commitment, write-once trigger, or hostile mutation lifecycle.

Before classification, `task_follow_up` has no durable runtime lifecycle. One
explicit invocation performs model I/O, repeats the current guard, appends a
sanitized attempt audit, creates a transient MessageEnvelope, invokes Safety,
and calls the sole Task writer. A denial or interruption may be invoked again
and may repeat model/audit/classification work. This is accepted until a real
worker/scheduler defines delivery identity and retry/crash semantics.

The ordinary `consumed|denied` disposition remains the sole one-shot
classified-message authority. Its transaction, unique run/message identities,
current locks, and Task request fingerprint prevent a duplicate Task even when
an internal runtime invocation is repeated. No pre-classification runtime row,
zero-call replay, or exact crash-window recovery is part of this lifecycle.

FT-013 adds one narrow `governance_decision` source route to this same service:

1. one immutable successful DecisionRecord and its proposal source graph,
   either committed for an identical retry or flushed in the caller-owned UoW;
2. effect exactly `check|measurement|follow_up`;
3. the proposal's persisted matching `safe_task_request` classification with
   the same kind;
4. current Boss/granted-Engineer Task authority for the same active Plant; and
5. every proposal/run source ref reloaded from its owning PostgreSQL authority.

At decision start the canonical Companion owner MUST have locked and validated
the proposal as current `pending`, version `1`. At ordinary-Task command entry
that same-UoW proposal MUST already be `approved`, version `2`, linked to the
same DecisionRecord, with its attention satisfied by that record. This required
approved terminal source is eligible; a still-pending, rejected, superseded,
or differently linked approved proposal is not. The rule also permits an
identical committed retry to re-read the same approved graph.

The DecisionRecord id is the natural uniqueness key. The command derives the
exact DecisionRecord/proposal/message/classification/upstream source-ref order
and fingerprint from immutable authority. The caller supplies the existing
SQLAlchemy Session/UoW so Task insertion participates in the complete FT-013
decision transaction; the Task service flushes but never commits or rolls that
UoW back. An identical source/fingerprint returns the same Task; any different
kind/text/refs or request reuse conflicts. This route cannot select `action`,
bypass current authorization, use governance as Safety approval, or create a
Task from `discussion_only|none|rejected`.

## Approval materialization

Only an immutable FT-011 decision with
`safety_status=pending_human_approval` and
`reason_code=ready_for_human_approval` can materialize an Approval.

- Exactly one Approval exists per `safety_decision_id`.
- Initial state is `pending`, `record_version=1`.
- `valid_until` is copied exactly from the source decision `expires_at`; it is
  never recalculated, extended, or refreshed.
- Materialization copies scope, action kind, selected evidence refs, and the
  immutable decision ref; it does not copy raw candidate/model text.
- An identical retry returns the existing Approval. A scope, action, expiry,
  or evidence mismatch conflicts and leaves the original unchanged.

The normal FT-011 handoff invokes materialization only after the immutable
decision commits. Materialization failure cannot roll back or mutate that
decision. An explicit approve/reject command may retry materialization before
evaluating the transition. There is no separate pending-approval Task.

## Human decision transition

The only Approval transitions are:

- `pending -> approved`;
- `pending -> rejected`.

Every command supplies the exact `safety_decision_id`, `expected_version=1`, a
new request id, a canonical request fingerprint, and one decision. The service
locks the Approval and its immutable Safety decision, then re-resolves in the
same PostgreSQL transaction:

- current session, Account, FarmMembership, role, and Plant permission;
- same-Farm active Plant;
- current `approve_action` authority;
- unchanged immutable `pending_human_approval` Safety decision;
- selected authoritative pH/EC rows and their current
  `approval_input=2h` freshness;
- `now <= valid_until`.

The exact boundary is inclusive: `now == valid_until` may transition;
`now > valid_until` fails closed. Restore does not extend expiry.

An approved transition creates exactly one open human-performed `action` Task
for the Approval in the same PostgreSQL transaction. If task creation or an
applicable required audit append fails, Approval remains `pending`. Rejection
creates no Task. A terminal transition increments `record_version` to `2` and
records safe human attribution.

The same request id and fingerprint returns the first committed terminal
result. Wrong version, a new request after a terminal transition, the opposite
decision, or a reused request id with different canonical content returns
conflict and creates no effect.

## Task completion transition

Only an `open` Task on a currently active and authorized Plant may complete.
Boss and a granted Engineer may complete ordinary and human action tasks;
Consultant cannot mutate them. Completion records the current actor, timestamp,
request id/fingerprint, and audit ref.

- Completing `check|measurement` changes only that Task to `completed`.
- Completing `action` atomically marks it `completed` and creates exactly one
  open `follow_up` with `parent_action_task_id` equal to the action Task and
  `due_at = action.completed_at + 48 hours`.
- Generic completion rejects `follow_up`; it cannot bypass Outcome evidence.

The parent action is the automatic follow-up uniqueness key. An identical
completion retry returns the existing completed action/follow-up pair. A
different retry conflicts; it never creates a second follow-up. `due_at` is a
persisted query/UI field only. No scheduler, worker, reminder execution, or
automatic transition is implied.

## Outcome transition

`record_follow_up_outcome` is the only completion path for an open
`follow_up` Task. In one PostgreSQL transaction it:

1. validates current task mutation authority and active Plant;
2. locks the open follow-up and its optional parent action;
3. validates `Outcome.value` and evidence refs;
4. creates exactly one Outcome for the follow-up; and
5. marks the follow-up `completed` at the same timestamp.

`improved|worsened|unchanged` requires at least one authorized safe evidence
ref. `no_data` permits an empty evidence-ref list. Evidence refs are preserved
for audit and later review but do not directly promote confirmed Plant state.
The follow-up Task is the Outcome uniqueness key. Identical retry returns the
first pair; different value, refs, or request fingerprint conflicts with no
mutation.

## Archived Plant and concurrency

- Archive preserves Approval, Task, and Outcome rows and their states.
- While archived, materialization effects, approve/reject, ordinary-task
  creation, completion, automatic follow-up, and outcome recording fail closed
  without changing records.
- Restore changes no dependent record and triggers no retry or resume. A new
  command must pass current ActorContext, state/version, expiry, evidence, and
  Safety guards.
- A classified-message disposition remains terminal across archive/restore.
  Restore never re-evaluates a denied `run_id`/`message_id`; only a new runtime
  invocation with both new identities can reach a fresh guard evaluation.
- A pre-classification `task_follow_up` denial is not durable. An explicit
  later invocation rechecks current authority and may repeat model, audit, or
  classifier work; it must use fresh classified delivery identity before the
  canonical writer can create a Task.
- Concurrent classified writers serialize through the ordinary disposition,
  parent locks, Task uniqueness, and request fingerprint. Identical work
  resolves to the committed Task, conflicting work preserves the winner, and
  denial commits no Task. Runtime-ledger crash windows and same-run replay
  ordering are outside the current lifecycle.
- Services lock the existing parent authority row before first-child inserts
  and rely on database uniqueness for concurrent first-write races. A lost
  uniqueness race is rolled back, then re-read from a clean PostgreSQL
  transaction and classified as identical retry or conflict. For globally
  unique request ids, a different canonical parent or fingerprint is always
  `TASK_VERSION_CONFLICT`; unrelated database failures remain
  `TASK_PERSISTENCE_FAILED`.

## Stable domain failures

- `TASK_COMMAND_FORBIDDEN`: current task mutation authority is absent.
- `TASK_PLANT_NOT_ACTIVE`: the Plant is archived or otherwise non-operative.
- `TASK_SOURCE_INVALID`: envelope/classification, decision, task kind, or
  parent relation is missing, mismatched, or not eligible.
- `APPROVAL_NOT_CURRENT`: expiry or current pH/EC Safety evidence check fails.
- `TASK_VERSION_CONFLICT`: version, request id, fingerprint, terminal state,
  or natural-key content conflicts.
- `TASK_EVIDENCE_REQUIRED`: a non-`no_data` Outcome lacks valid evidence refs.
- `TASK_PERSISTENCE_FAILED`: the authoritative mutation cannot commit.
- `TASK_AUDIT_FAILED`: required Timeline append fails before a successful
  runtime result can be claimed.

Errors expose no candidate text, provider payload, credentials, auth material,
or protected existence details.

## Verification

Tests must prove the complete approval-to-outcome path, exact closed states,
inclusive expiry boundary, current authority/freshness revalidation,
transaction rollback, natural uniqueness, identical-versus-conflicting
retries, automatic +48-hour follow-up, evidence policy, no Plant-state
promotion, no automated actuation, archive/restore freeze, terminal runtime
classified-message denial across restore, classified run/message fingerprint
identical/conflicting retries, fresh delivery identity after a repeated
pre-classification invocation, current-authority consumed retry, missing-link
failure, and concurrent first-insert/request-id collision behavior. No
pre-classification ledger replay or runtime/classified exclusion matrix is
required.

FT-013 compatibility tests additionally prove the DecisionRecord source route
uses the same ordinary-task guards and transaction, creates only one matching
ordinary Task, derives the canonical source refs/fingerprint, does not commit
the caller's UoW, and rolls back the whole governance decision on Task or
required audit failure. Cross-branch tests prove there is one command/service,
not two competing Task creation seams. Phase tests start from a locked pending
proposal, transition and flush its approved version-2/same-DecisionRecord graph
inside the caller UoW, then create the Task without an intermediate commit;
they also cover committed duplicate and pending/rejected/superseded/wrong-
DecisionRecord rejection.

## Related specs

- [.memory-bank/domains/task-approval-outcomes.md](../domains/task-approval-outcomes.md)
- [.memory-bank/contracts/task-approval-http.md](../contracts/task-approval-http.md)
- [.memory-bank/contracts/task-follow-up-runtime.md](../contracts/task-follow-up-runtime.md)
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md)
- [.memory-bank/testing/task-follow-up.md](../testing/task-follow-up.md)
