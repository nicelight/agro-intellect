---
description: Verification contract for FT-012 approvals, tasks, follow-ups, outcomes, and provider-neutral Task and Follow-up Agent.
status: active
type: testing_spec
last_updated: 2026-07-20
source_of_truth:
  - .memory-bank/features/FT-012-human-approval-tasks-follow-up-outcomes.md
  - .memory-bank/states/task-follow-up-lifecycle.md
  - .memory-bank/domains/task-approval-outcomes.md
  - .memory-bank/contracts/task-approval-http.md
  - .memory-bank/contracts/task-follow-up-runtime.md
---
# Task And Follow-Up Verification

## Scope

Defines deterministic, PostgreSQL, HTTP, concurrency, compatibility, and
deterministic executor evidence for FT-012 from an ordinary task or
immutable pending Safety decision through human task completion and Outcome.

## Domain and migration matrix

- Exact `Task.kind`, Task/Approval states, Outcome vocabulary, nullability,
  native UUID/FK parity, restrictive deletes, and one additive post-FT-011
  migration head.
- Natural uniqueness for classification message, Safety decision, Approval,
  parent action, and follow-up Outcome plus persisted request ids and canonical
  fingerprints.
- Exact immutable `ordinary_task_dispatch_dispositions` schema: restrictive
  classification/Farm/Plant UUID FKs, primary-key
  `classification_message_id`, named unique `run_id`, lowercase input
  fingerprint, nullable lowercase `expected_task_create_fingerprint`, closed
  `consumed|denied` plus denial/commitment matrix, no mutable/pending/replay
  fields, and safe downgrade refusal when disposition authority exists. Fresh
  schemas require commitment for consumed and null for denied; the additive
  migration uses the equivalent `NOT VALID` check so new writes are enforced
  while legacy consumed nulls remain untrusted. Migrated and fresh-ORM
  PostgreSQL schemas both contain
  `ft012_enforce_ordinary_dispatch_commitment_write_once()` and
  `trg_ordinary_task_dispatch_commitment_write_once`; a distinct old/new
  commitment value raises SQLSTATE `23514` with diagnostic constraint
  `ck_ordinary_task_dispatch_commitment_write_once`.
- Exact immutable `task_follow_up_runtime_dispositions` schema: primary-key
  `run_id`, restrictive Farm/Plant scope, command fingerprint, unique nullable
  post-guard `message_id`, nullable envelope input hash, closed
  `envelope_handed_off|publication_denied` matrix, sole
  `AGENT_PUBLICATION_BLOCKED` denial, safe model/audit refs, no envelope/body/
  auth snapshot, and populated-table downgrade refusal.
- Parent-row locking plus unique-race re-read: concurrent identical first
  writes return one result; different content conflicts without replacement.
  Named request-id uniqueness losses are rolled back before a clean owner
  re-read; a cross-parent collision is `TASK_VERSION_CONFLICT`, while unrelated
  database errors remain `TASK_PERSISTENCE_FAILED`.
- PostgreSQL read/write smoke proves Task, Approval, Outcome, source refs,
  safe attribution, timestamps, and Timeline refs round-trip through the real
  repository/session path.
- The W1 FT-012 revision uses
  `down_revision=ft011_safety_action_decisions`. TASK-040 adds
  `ft012_runtime_dispositions` directly after
  `ft012_task_approval_outcomes`; all eight current exact-head consumers
  advance to the new runtime-disposition revision in the same W2 repair:
  `tests/backend/access_admin/test_ft002_schema_migration.py`,
  `tests/backend/photo_intake/test_ft005_migration_models.py`,
  `tests/backend/plant_operations/test_ft004_migration_models.py`,
  `tests/backend/agent_chat/test_ft008_migration_models.py`,
  `tests/backend/plant_state/test_migration_models.py`,
  `tests/backend/safety_gate/test_migration_models.py`,
  `tests/backend/safety_gate/test_classification_persistence.py`, and
  `tests/backend/test_foundation_database_contract.py`.

## Ordinary-task matrix

- `create_ordinary_task` is one service with the exact closed
  `classified_message|governance_decision` command union; no second Task writer
  or repository shortcut exists.
- Validated pending MessageEnvelope plus persisted matching
  `safe_task_request/check|measurement|follow_up` creates exactly one Task of
  the same kind only under derived `ordinary_dispatch`.
- Envelope/classification message, scope, task kind, and source refs must
  match; missing persistence, mismatch, conflict, physical action, blocked
  uncertainty, or safe information creates no Task.
- Candidate text is stored/rendered only as literal Task data and cannot
  select action, authorization, completion, Plant state, Bus instruction, or
  device effect.
- Boss and granted Engineer may create; Consultant, missing/revoked grant,
  wrong Farm, disabled identity, or archived Plant fails closed.
- Identical retry returns the same Task and `task_created` ref. Same message or
  request id with different fingerprint conflicts.
- The first classified-message current-guard evaluation atomically commits one
  terminal disposition: `consumed` with Task/audit success or `denied` for the
  exact Plant/archive/authorization failure. The same denied `run_id` or
  `message_id` remains denied after restore without guard re-evaluation; a
  successful later attempt requires a new invocation with both new identities.
- A consumed retry returns the existing Task only under current read/task
  authority; archive/revoke denial leaks no Task and does not alter the
  terminal disposition.
- Disposition insert/commit failure is fail-closed with no Task. Concurrent
  same-message and same-run/different-message probes prove first-write-wins,
  immutable duplicate/conflict classification, and zero Timeline/Bus authority.
- For `task_follow_up`, the runtime-stage and classified dispatch writers use
  the same short transaction-scoped run advisory lock. PostgreSQL races prove
  that one run cannot commit both `publication_denied` and classified
  `consumed|denied`, and no lock/transaction spans Task model or Safety model
  I/O.
- The classified-message branch derives exact message/classification/upstream
  source refs and fingerprint, stores that same fingerprint independently on
  the consumed disposition in the Task/disposition UoW, and rejects canonical
  Companion origin because that classification is governance-held.
- The governance-decision branch accepts only an immutable approved
  DecisionRecord, its proposal that was locked pending version 1 at decision
  start and is now flushed approved version 2 for the same record in the caller
  UoW, satisfied attention, matching classification, exact ordinary kind/text,
  DecisionRecord request identity/fingerprint, and that caller UoW. It derives
  exact refs/fingerprint, flushes without commit, returns created/duplicate or
  typed conflict, and rolls the complete governance transaction back on
  Task/audit failure. Tests also cover committed duplicate plus rejection of
  pending-at-entry, rejected, superseded, and differently linked approved
  proposals.

## Approval and action matrix

- Materialization accepts only one immutable
  `pending_human_approval/ready_for_human_approval` FT-011 decision and copies
  its action, evidence, and expiry exactly.
- Materialization duplicate/conflict and post-commit failure are covered;
  failure cannot alter the source Safety decision, and explicit decision retry
  can materialize later.
- Approve/reject reloads current session/account/membership/grant, active Plant,
  Approval version, immutable decision, selected pH/EC rows, and
  `approval_input=2h` freshness in the write transaction.
- `now == valid_until` is accepted and `now > valid_until` is denied using an
  injected UTC clock. Restore never extends expiry.
- Boss may decide; Engineer requires the current active approval flag;
  Consultant never decides. Governance DecisionRecord is never accepted as
  Safety approval.
- Approve creates exactly one human `action` Task in the same transaction;
  reject creates none. Task/audit/persistence failure leaves Approval pending.
- Approved `approval_decided` contains a required canonical UUID
  `action_task_id`; rejected `approval_decided` omits that key entirely.
- Identical terminal retry returns the first result. Wrong version, opposite
  decision, new terminal request, or reused request id/fingerprint conflict
  returns 409/no effect.
- No target value, quantity, dosage, command, provider payload, or automated
  actuation exists in schema, response, logs, or effect spies.

## Completion and Outcome matrix

- Completing `check|measurement` changes one Task and emits one
  `task_completed` event.
- Completing `action` atomically creates exactly one open follow-up at
  `completed_at+48h`; retries and concurrent attempts return the same pair and
  never duplicate it. Event cardinality is one `task_completed` plus one
  `task_created` for the follow-up.
- Generic completion rejects `follow_up`.
- Recording `improved|worsened|unchanged` requires one through four valid
  same-Plant evidence refs; `no_data` accepts zero through four.
- W1 Outcome validation retains only
  `plant|daily_checkin|manual_measurement|photo_catalog_item|plant_state_record`;
  `task:` and `outcome:` remain rejected. A separate competence-only resolver
  may load Task/Outcome runtime records and is never used by Outcome writes.
- Outcome creation and follow-up completion are atomic and unique. Event
  cardinality is one `task_completed` plus one
  `follow_up_outcome_recorded`; any append/DB failure cannot claim success.
- Outcome evidence does not directly mutate or confirm Plant state.
- Timeline append before later DB failure may leave non-authoritative noise;
  replay never creates or repairs runtime rows.

## HTTP and archive matrix

- Generated OpenAPI exposes the exact strict task/approval list and mutation
  schemas, enums, response unions, and stable error codes.
- Every route resolves ActorContext before service logic, returns no-store,
  preserves no-existence-leak denial, and excludes auth/provider/candidate
  internals.
- A narrow raw ASGI path boundary validates all eight FT-012 UUID occurrences
  before decoded UUID binding. Literal lowercase canonical bytes succeed;
  uppercase, compact, braced, percent-encoded-equivalent, malformed, or
  unavailable raw spellings return the safe `422/no-store` validation envelope
  without service/DB calls, and OpenAPI retains the exact UUID pattern.
- List filters/limits preserve strict ordering and authorized Plant scope.
- Archive with pending Approval and open action/follow-up leaves all records
  unchanged and blocks every command. Restore performs no replay; each new
  request repeats current authority, version, evidence, expiry, and Safety
  checks.
- Archive/grant/revoke races at the write boundary create no unauthorized
  Task, decision, completion, or Outcome.
- A classified ordinary message denied by an archive/current-authority guard
  retains its terminal PostgreSQL denial across restore. Resubmitting the old
  identities creates no Task; a new run/message is evaluated normally.

## Task and Follow-up Agent matrix

- Exact strict `TaskFollowUpCommandV1`, provider request, record union/order,
  result matrix, pending-envelope mapping, and orchestration result; unknown
  fields and invalid enums/matrices reject.
- Provider input contains only authorized PostgreSQL task/outcome/evidence
  records. UI Feed, Bus history, raw chat, Timeline replay,
  ActorContext/session/account/membership/role/grant, prompts, caller refs,
  provider history, hidden reasoning, credentials, paths, and fields outside
  the registered Task Follow-Up request allowlist are absent.
- Persisted Task text remains an explicit quoted untrusted-data field and
  cannot alter instructions, tools, schema, route, or authority.
- Allowed proposal kinds are only `check|measurement|follow_up`; an existing
  automatic follow-up removes `follow_up` from that invocation's allowed set.
  Action, approve/reject, complete, Outcome, Plant-state, and device fields are
  schema-invalid.
- Valid non-silent proposal creates only a pending `task_request` envelope.
  Exactly matching persisted classification plus current ordinary-task guard
  is required for one Task. Class/kind mismatch or any physical/blocked branch
  creates none.
- A Companion-origin safe-task classification is explicitly held: it cannot
  enter the classified-message branch before an approved DecisionRecord, and
  retry/restore/reconciliation cannot replay the suppressed Task effect.
- Pre/post-model, classification-write, and task-write authorization/archive
  races fail closed with no restore replay.
- The exact runtime command fingerprint is stable for an identical command and
  conflicts for changed input under one `run_id`. A committed post-model
  archive/revoke denial survives restore and returns without another model,
  classifier, envelope, or Task call. An eligible run commits one post-guard
  message handoff before classifier I/O; the same run cannot mint another
  message, and only a new command/run may later allocate a new message.
- Concurrent same-run invocations prove first terminal runtime write wins;
  runtime audit/row commit failure proves rollback/no classifier/no Task, with
  any earlier Timeline append treated only as non-authoritative noise.
- Strict `TaskFollowUpDispositionResultV1` tests cover every closed local
  status/code/ref matrix without changing global `AgentRuntimeOutcomeV1`.
  Existing `context_denied`, `runtime_not_configured`, `provider_failed`,
  `output_invalid`, passing-guard `model_silent`, and `audit_failed` create no
  runtime row and repeat their normal pre/model path on same-run retry; only
  committed guard denial or envelope handoff owns the two-value runtime row.
- Provider-neutral fake/spy injection, unbound fail-closed production, no
  default/fallback/fake production result, redaction, and common Agent Runtime
  audit semantics remain compatible.

### Required consumed-Task authority matrix

Every row uses a committed handed-off runtime row, matching persisted
classification, consumed classified disposition, and exact zero replay calls
`model/audit/Safety/Task = 0/0/0/0`. Unless the expected column says otherwise,
the Task-owned fingerprint is recomputed after mutation to prove it cannot
self-confirm against the independent disposition commitment.

| Case | Mutation/evidence | Exact replay result |
|---|---|---|
| Baseline | Task create fingerprint equals the disposition commitment and canonical recomputation; separate run/message/classification/scope/agent/ActorContext checks pass | `duplicate/TASK_FOLLOW_UP_ALREADY_CONSUMED` with exact classification/Task refs |
| Text | mutate normalized `display_text` and recompute the Task-owned fingerprint | `failed/TASK_FOLLOW_UP_RUNTIME_DISPOSITION_FAILED`, null refs |
| Kind | mutate ordinary kind and recompute | same redacted failure |
| Ordered sources | alternate valid same-Plant ref, duplicate, reorder, omission/addition, uppercase/compact/noncanonical ref, each with recomputed Task-owned fingerprint | same redacted failure; valid canonical first/prefix/sparse/all subsets created by the writer remain accepted |
| Actor attribution | mutate account, membership, or role independently | same redacted failure through separate ActorContext comparison |
| Scope/agent/classification | mutate run, Farm, Plant, origin agent, message/classification link/content, or add a same-run Task on an alternate classification | same redacted failure |
| Commitment | disposition commitment is missing, malformed, wrong, or differs from either Task value or canonical recomputation | same redacted failure |
| Migration legacy | a pre-existing consumed row receives no self-derived backfill and retains null | same redacted failure; denied legacy null remains a valid denial |
| Coordinated text replacement | in one transaction mutate normalized Task text, recompute the Task fingerprint, and replace the disposition commitment | PostgreSQL rejects the commitment update with exact `23514`/constraint diagnostic; the complete transaction rolls back, and exact replay of the preserved original graph remains the accepted duplicate |
| Coordinated source replacement | in one transaction select another valid canonical source subset, recompute the Task fingerprint, and replace the disposition commitment | same database rejection and complete rollback; no model/audit/Safety/Task replay call |
| Coordinated kind replacement | in one transaction change Task kind plus matching classification fields/result digest, recompute the Task fingerprint, and replace the disposition commitment | same database rejection and complete rollback; classification, Task, and both digests retain their original values |
| Task-only control | mutate Task text and recompute only the Task-owned fingerprint, leaving the commitment unchanged | mutation may commit, but exact zero-call replay returns the redacted disposition failure with null refs |
| Direct update semantics | replace digest, set digest to null, or set null to digest directly; also probe same-value and unrelated-field updates | every distinct commitment change is rejected by the named trigger at `23514`; same-value assignment and valid-row unrelated updates are trigger-permitted but remain subject to all checks; legacy consumed null cannot be backfilled and any rewritten legacy-invalid tuple fails the existing matrix |
| Atomicity/rollback | fail Task, disposition/commitment flush, audit append, or commit | no Task/consumed success; Task, disposition, and commitment roll back together; Timeline append may remain non-authoritative noise only |
| Compatibility | run the full prior groups 1-7 and exact-head suite after adding the column/check | every group 1-7 row/call/audit/rollback result remains exact; all eight migration-head consumers pass |

The canonical create fingerprint preimage covers normalized text, exact kind,
ordered Task source refs, run/request id, and message/classification identity.
Farm/Plant, `task_follow_up` origin, and human attribution are deliberately
verified separately. The envelope `input_sha256` is not accepted as a
replacement proof because its transient full preimage cannot be reconstructed.

The three coordinated cases assert rejection at the PostgreSQL write boundary,
not a fabricated corrupt-replay result: once the replacement transaction is
rolled back, the unchanged original graph remains a legitimate duplicate. A
future in-service persistence failure retains the existing
`TASK_PERSISTENCE_FAILED` mapping; no new public/domain error code is added.

Upgrade/migration tests also prove the current head remains
`ft012_runtime_dispositions -> ft012_task_approval_outcomes`, the write-once
objects appear exactly once under Alembic and ORM fresh-schema creation, a
second `upgrade head`/`create_all(checkfirst=True)` is a no-op, and downgrade
refuses before any DDL when either a runtime disposition or non-null commitment
exists. An empty-authority downgrade removes runtime table, trigger, function,
matrix check, and column in that order. The eight exact-head consumers named
above must all remain green.

### Required TASK-040 disposition/race matrix

All seven groups below are required canonical acceptance; a rolled-up
"concurrency" or "classification failure" test does not replace them.

For groups 6 and 7, the aggregate call vector is always written as
`Task Follow-Up model / agent_runtime_decided audit appender / Safety
classifier / sole ordinary-Task service`. `C` denotes the exact safe
`safety_classification:<message_id>` ref and `T` the exact `task:<task_id>`
ref. The deterministic success fixture uses one new active Plant-scoped
command, a `speak` proposal, a committed matching `safe_task_request`
classification, and a newly consumed ordinary Task; it does not exercise any
other downstream classification/disposition state from group 5.

1. **Forced advisory-key collision with full UUID isolation.** Inject a
   test-only constant lock-key derivation for two distinct full `run_id` UUIDs
   and execute concurrent denied terminal writes. The shared key serializes,
   but full-UUID/fingerprint comparisons commit two separate
   `publication_denied` rows with their own Farm/Plant scope. Expected
   model/audit/Safety/Task calls are `2/2/0/0`; classification/ordinary/Task
   rows are `0`. Neither run resolves or conflicts
   as the other, and a third new run is independently eligible.
2. **Crash after committed handoff before classifier.** Inject process-stop
   immediately after commit and before the classifier call. Expected committed
   state: one `envelope_handed_off`, one message/input hash and one runtime audit;
   no classification, ordinary disposition, or Task. Calls are model/audit/
   Safety/Task `1/1/0/0`. Exact same-run retry returns
   `incomplete/TASK_FOLLOW_UP_HANDOFF_INCOMPLETE`, null refs, and `0/0/0/0`
   calls; a new run is eligible.
3. **Classifier guard and persistence failures after handoff.** Both subcases
   retain one handoff and no ordinary/Task row. Pre-executor classifier guard
   denial has first-call counts `1/1/0/0`; classifier persistence failure after
   its fake/spy call has `1/1/1/0`; neither commits a classification. The first
   call returns existing `TaskFollowUpRunResultV1 failed/classification`.
   Same-run retry returns the local handoff-incomplete result with null refs and
   `0/0/0/0`; only a new run may retry evaluation.
4. **Classification committed, crash before Task writer.** Commit the exact
   matching safe-task classification, then inject stop before the sole Task
   service call. Rows are one handoff plus one classification, no ordinary
   disposition/Task; first-call counts `1/1/1/0`. Exact retry is
   `incomplete/TASK_FOLLOW_UP_HANDOFF_INCOMPLETE` with the safe classification
   ref, null Task ref, and `0/0/0/0`; a new run is eligible.
5. **Exact handed-off retry resolution.** With no ordinary disposition: absent
   classification returns handoff-incomplete/null refs; exact taskable
   classification returns handoff-incomplete/classification ref; exact
   non-taskable classification returns
   `not_taskable/TASK_FOLLOW_UP_ALREADY_NOT_TASKABLE` with classification ref.
   Downstream `denied` returns `denied/TASK_FOLLOW_UP_DISPATCH_DENIED` with only
   classification ref. Downstream `consumed` plus current authority/exact Task
   returns `duplicate/TASK_FOLLOW_UP_ALREADY_CONSUMED` with classification and
   Task refs; archive/revoke instead returns
   `blocked/TASK_FOLLOW_UP_REPLAY_BLOCKED` with null refs. A conflicting graph or
   missing consumed Task is the null-ref disposition failure. Every retry has
   `0/0/0/0` executor/audit/writer calls, changes no row, and requires a new run
   for reevaluation.
6. **Observable lock order and I/O boundary — fixture
   `lock_order_consumed_success_v1`.** Instrument repository/session events for
   the deterministic success fixture above. The only participant returns
   `TaskFollowUpRunResultV1` with `route_status=task_created`,
   `runtime_outcome=envelope_ready`, no result code, `classification_ref=C`,
   `task_ref=T`, and `failure_stage=null`. Assert the complete ordered trace:
   runtime preflight `advisory -> runtime disposition -> classified disposition
   -> commit`; model spy; post-model terminal selection `advisory -> runtime
   disposition -> classified disposition -> current-scope locks ->
   agent_runtime_decided audit -> runtime insert -> commit`; Safety classifier
   spy; classified writer `advisory -> runtime disposition -> classified
   disposition -> classification -> current/source locks ->
   task_created-audit/Task/consumed-disposition writes -> commit`. At both spy
   entries `session.in_transaction() == false`, the preceding transaction has
   committed, and the transaction advisory lock is not held. Final cardinality
   is exactly runtime/message/classification/ordinary-disposition/Task
   `1 envelope_handed_off / 1 pending task_request / 1 matching safe_task_request
   / 1 consumed / 1`; aggregate calls are `1/1/1/1`; authoritative audit events
   are exactly two (`agent_runtime_decided`, `task_created`), permitted
   non-authoritative noise events are zero, and rollback calls are zero. An
   exact old-run retry returns `TaskFollowUpDispositionResultV1` with
   `duplicate/TASK_FOLLOW_UP_ALREADY_CONSUMED`, refs `C/T`, call vector
   `0/0/0/0`, zero row changes, and zero rollback. In an isolated new-run probe,
   a new command/run/message over the same eligible fixture returns the same
   `task_created` result with new `C2/T2`, calls `1/1/1/1`, two authoritative
   audits, zero noise/rollback, and its own one-row handoff/classification/
   consumed/Task set.
7. **Distinct races with deterministic barriers.** Both contenders finish
   their model calls before either post-model terminal transaction is released.
   The eligible participant `E` and denied participant `D` use the same exact
   command fingerprint and `speak` result; only their injected post-model
   current-guard result differs. For late races, eligible participant/classified
   writer `W` first commits the handoff and matching classification and pauses
   before the sole Task-service lock, while late denied participant `L`, which
   already finished its model call after a clean preflight, pauses before its
   post-model runtime lock. A named barrier releases exactly one participant to
   finish and commit/return before releasing the other; no assertion is sampled
   between unspecified scheduler events.

   Exact result abbreviations used in the table are:

   - `RUN_CREATED(C,T)`: `TaskFollowUpRunResultV1`,
     `route_status=task_created`, `runtime_outcome=envelope_ready`, no result
     code, refs `C/T`, `failure_stage=null`;
   - `RUN_DENIED`: `TaskFollowUpRunResultV1`, `route_status=failed`,
     `runtime_outcome=publication_guard_denied` with
     `AGENT_PUBLICATION_BLOCKED`, null refs, `failure_stage=runtime`;
   - `LOCAL_INCOMPLETE(C)`: `TaskFollowUpDispositionResultV1`,
     `incomplete/TASK_FOLLOW_UP_HANDOFF_INCOMPLETE`, refs `C/null`;
   - `LOCAL_DUPLICATE(C,T)`: `TaskFollowUpDispositionResultV1`,
     `duplicate/TASK_FOLLOW_UP_ALREADY_CONSUMED`, refs `C/T`.

   | Subcase and exact barrier order | First participant return | Second participant return | Final runtime / message / classification / ordinary disposition / Task | Aggregate calls | Authoritative audits / permitted noise / rollback | Exact old-run retry after both finish | Isolated fresh new-run probe |
   |---|---|---|---|---|---|---|---|
   | `eligible-first`: release `E` through handoff, matching classification, consumed disposition, Task, and return; then release `D` | `E = RUN_CREATED(C,T)` | `D = LOCAL_DUPLICATE(C,T)` | `1 envelope_handed_off / 1 pending task_request / 1 matching safe_task_request / 1 consumed / 1` | `2/1/1/1` | `2 (agent_runtime_decided + task_created) / 0 / 0` | `LOCAL_DUPLICATE(C,T)`, calls `0/0/0/0`, no row change | new command/run/message returns `RUN_CREATED(C2,T2)` with its own `1/1/1/1` calls and one handoff/message/classification/consumed/Task set |
   | `denied-first`: release `D` through committed denial and return; then release `E` | `D = RUN_DENIED` | `E = RUN_DENIED`, reconstructed from `D`'s committed safe model/audit refs | `1 publication_denied / 0 / 0 / 0 / 0` | `2/1/0/0` | `1 agent_runtime_decided / 0 / 0` | `RUN_DENIED`, calls `0/0/0/0`, no row change | after current authority is eligible, new command/run/message returns `RUN_CREATED(C2,T2)` with its own `1/1/1/1` calls and one handoff/message/classification/consumed/Task set |
   | `late-denial-first`: after the seeded handoff + matching classification, release `L` to acquire the shared lock, resolve, and return; then release `W` through consumed disposition, Task, and return | `L = LOCAL_INCOMPLETE(C)` | `W = RUN_CREATED(C,T)` | `1 envelope_handed_off / 1 pending task_request / 1 matching safe_task_request / 1 consumed / 1` | `2/1/1/1` | `2 (agent_runtime_decided + task_created) / 0 / 0` | `LOCAL_DUPLICATE(C,T)`, calls `0/0/0/0`, no row change | new command/run/message returns `RUN_CREATED(C2,T2)` with its own `1/1/1/1` calls and one handoff/message/classification/consumed/Task set |
   | `classified-writer-first`: after the seeded handoff + matching classification, release `W` through consumed disposition, Task, and return; then release `L` | `W = RUN_CREATED(C,T)` | `L = LOCAL_DUPLICATE(C,T)` | `1 envelope_handed_off / 1 pending task_request / 1 matching safe_task_request / 1 consumed / 1` | `2/1/1/1` | `2 (agent_runtime_decided + task_created) / 0 / 0` | `LOCAL_DUPLICATE(C,T)`, calls `0/0/0/0`, no row change | new command/run/message returns `RUN_CREATED(C2,T2)` with its own `1/1/1/1` calls and one handoff/message/classification/consumed/Task set |

   Each isolated fresh probe has exactly two authoritative audit events, zero
   permitted noise events, and zero rollback calls. In both late-denial orders,
   `L` inserts no runtime row or classified disposition and calls neither Safety
   nor the Task service; the only final cross-table pair is
   `envelope_handed_off + consumed`. Therefore `publication_denied +
   consumed|denied`, a second runtime row/message/classification/disposition,
   and a duplicate Task all have exact cardinality zero.

## Current code-phase executor evidence

Seed an authorized active Plant through production PostgreSQL paths with a
completed Task and, for the chosen fixture, its real Outcome/evidence refs.
Inject explicit canonical `task_follow_up` and `safety_gate` fake/spy executors
through test-only seams and require:

1. exactly one `task_follow_up` spy call over
   `TaskFollowUpProviderRequestV1`;
2. one schema-valid non-silent ordinary-task proposal;
3. one classifier spy call with the exact matching safe task kind;
4. one matching persisted ordinary Task plus safe runtime/classification/task
   audit refs; and
5. zero action, Approval, completion, Outcome, Plant-state, Bus/UI command, or
   device effect.

Separate fake/spy cases prove timeout, provider failure, output invalid,
not-configured production, guard/audit failure, class/kind mismatch, no
duplicate unintended Task, redaction, and no direct action effect. This is
current deterministic REQ-011 evidence and does not claim real integration.

## Behavior traceability

- `FT-012-BHV-001`: current approval -> one human action -> completion -> one
  +48-hour follow-up -> evidence-aware Outcome, with no device effect.
- `FT-012-BHV-002`: identical retry succeeds idempotently; stale/conflicting
  retry and archived transition have no effect; restore does not replay or
  re-evaluate a denied classified message, and only new run/message identities
  can reach a fresh guard.
- `FT-012-BHV-003`: strict `task_follow_up` typed proposal plus matching
  classification creates exactly one ordinary Task and never action; its
  runtime-stage denial/handoff identity is one-shot across retry and restore.

## Current W1 accepted evidence

- Scheduler closure selects only TASK-039 ATTEMPT 03: implementation `PASS`,
  independent functional `VERDICT: PASS`, separate
  `SEMANTIC_VERDICT: semantic-pass`, and immutable closure evidence. The two
  older failed attempts remain history.
- Core PostgreSQL/domain/migration/API: `22 passed`; current-guard and Safety
  regression: `210 passed`; exact eight-consumer migration compatibility:
  `47 passed`; full deterministic suite: `489 passed, 2 deselected`.
- Independent repair matrix: `10 passed`, including all eight raw UUID
  positions, disposition identity/archive/rollback/concurrency, actual guarded
  publication, request collision mapping, and Timeline branches. Adversarial
  review: `18/18` semantic cases and `20/20` executable matrix cases passed
  with no current finding or blocker.
- The verified product head is `ft012_task_approval_outcomes` directly after
  `ft011_safety_action_decisions`. Scope evidence covers exactly `11/11`
  allowlisted W1 product/test paths and excludes W2, frontend, provider/live,
  actuation, Plant-state mutation, and TASK-041/TASK-042/TASK-043 work.
- W2 deterministic Task and Follow-Up Agent evidence remains open under
  TASK-040. No provider/model/base URL/Gemini/credential/egress/network or
  live-smoke result is claimed by W1.

## Commands

- Core domain/migration/API:
  `.venv/bin/python -m pytest tests/backend/task_follow_up/test_domain_loop.py tests/backend/task_follow_up/test_migration_models.py tests/backend/api/test_ft012_task_follow_up_routes.py -m "not real_model" -q`
- Current-guard/concurrency/Timeline integration:
  `.venv/bin/python -m pytest tests/backend/access_admin tests/backend/plant_operations tests/backend/agent_chat tests/backend/safety_gate tests/backend/task_follow_up -m "not real_model" -q`
- Deterministic competence runtime:
  `.venv/bin/python -m pytest tests/backend/task_follow_up/test_runtime.py tests/backend/agent_runtime -m "not real_model" -q`
- Exact-head compatibility:
  `.venv/bin/python -m pytest tests/backend/access_admin/test_ft002_schema_migration.py tests/backend/photo_intake/test_ft005_migration_models.py tests/backend/plant_operations/test_ft004_migration_models.py tests/backend/agent_chat/test_ft008_migration_models.py tests/backend/plant_state/test_migration_models.py tests/backend/safety_gate/test_migration_models.py tests/backend/safety_gate/test_classification_persistence.py tests/backend/test_foundation_database_contract.py -q`
- TASK-040 bounded repair matrix:
  `.venv/bin/python -m pytest tests/backend/task_follow_up/test_runtime.py tests/backend/task_follow_up/test_domain_loop.py tests/backend/task_follow_up/test_migration_models.py -m "not real_model" -q`
- Full deterministic suite: `.venv/bin/python -m pytest tests -m "not real_model" -q`
- Memory Bank lint: `node scripts/mb-lint.mjs`
- Diff check: `git diff --check`
