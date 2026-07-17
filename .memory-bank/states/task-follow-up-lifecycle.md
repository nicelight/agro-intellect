---
description: Human approval, task completion, automatic follow-up, and outcome lifecycle for the Safety and Task Loop.
status: active
type: state_spec
last_updated: 2026-07-17
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

## Ordinary safe-task route

An ordinary Task may be created only from:

1. one immutable validated pending `MessageEnvelopeV1`;
2. one durably persisted matching `SafetyClassificationResultV1` with
   `classification=safe_task_request`;
3. a task kind equal to the classification `safe_task_kind`; and
4. a current ActorContext that permits domain-task creation for the same active
   Plant at the write boundary, with every envelope source ref reloaded from
   its owning PostgreSQL authority and matched to that Plant.

The only permitted ordinary kinds are `check|measurement|follow_up`.
`safe_task_request` can never create `action`. Candidate text remains literal
human-facing task data, not an executable instruction, evidence fact, or
authorization claim. An identical `message_id` retry is idempotent; different
content for the same key conflicts without replacing the first Task.

A future valid DecisionRecord workflow effect may call this same service, but
cannot select `action`, bypass current authorization, or reuse governance
approval as Safety approval.

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
- Services lock the existing parent authority row before first-child inserts
  and rely on database uniqueness for concurrent first-write races. A lost
  uniqueness race is re-read and classified as identical retry or conflict.

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
promotion, no automated actuation, archive/restore freeze, and concurrent
first-insert behavior.

## Related specs

- [.memory-bank/domains/task-approval-outcomes.md](../domains/task-approval-outcomes.md)
- [.memory-bank/contracts/task-approval-http.md](../contracts/task-approval-http.md)
- [.memory-bank/contracts/task-follow-up-runtime.md](../contracts/task-follow-up-runtime.md)
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md)
- [.memory-bank/testing/task-follow-up.md](../testing/task-follow-up.md)
