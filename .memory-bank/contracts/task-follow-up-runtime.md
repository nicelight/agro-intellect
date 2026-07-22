---
description: Strict provider-neutral Task and Follow-up Agent input, proposal, classification, and ordinary-task handoff contract.
status: active
type: interface_contract
last_updated: 2026-07-20
source_of_truth:
  - .memory-bank/features/FT-012-human-approval-tasks-follow-up-outcomes.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/contracts/agent-roster-bootstrap.md
  - .memory-bank/domains/task-approval-outcomes.md
---
# Task And Follow-Up Agent Runtime

## Scope

Defines one provider-neutral `task_follow_up` competence over current
authorized PostgreSQL Task, Outcome, and evidence records. The model may
propose one ordinary `check|measurement|follow_up` Task. Its typed proposal is
still non-operative: it must become a pending MessageEnvelope, receive the
matching project-owned classification, and pass the deterministic ordinary
Task service before a row is written.

## Out of scope

- Approval decisions, action Task creation, Task completion, Outcome writes,
  Plant-state mutation, Safety clearance, device effects, reminders, workers,
  schedulers, tools, RAG, or agent memory;
- generic `ProviderRequestV1` changes, a public agent HTTP endpoint, caller
  prompts/records, Bus/UI/Timeline replay, or raw provider persistence.

## Related specs

- [.memory-bank/contracts/agent-runtime-adapter.md](agent-runtime-adapter.md):
  shared provider binding, current post-model guard, audit, MessageEnvelope,
  and closed failure semantics.
- [.memory-bank/contracts/agent-model-provider-profiles.md](agent-model-provider-profiles.md):
  provider-neutral executor, fail-closed production, and future endpoint route.
- [.memory-bank/contracts/agent-roster-bootstrap.md](agent-roster-bootstrap.md):
  canonical `task_follow_up` identity.
- [.memory-bank/contracts/message-envelope.md](message-envelope.md): pending
  non-consumable task-request handoff.
- [.memory-bank/contracts/safety-gate-runtime.md](safety-gate-runtime.md):
  project-owned task/physical classification.
- [.memory-bank/domains/task-approval-outcomes.md](../domains/task-approval-outcomes.md):
  ordinary Task authority and idempotency.

## Module and command boundary

Implementation lives under `backend/app/task_follow_up/` and reuses the
project provider factory, post-model authorization guard, sanitized
`agent_runtime_decided` Timeline audit, and common MessageEnvelope types.

The internal `TaskFollowUpCommandV1` contains exactly:

- `schema_version=1`;
- application-generated UUIDv4 `run_id`;
- timezone-aware UTC `requested_at`;
- service-side `actor_context`;
- requested UUID `plant_id`;
- `trigger_kind=task_completed|follow_up_outcome_recorded|manual_review`;
- UUID `trigger_task_id`.

Callers cannot submit task/outcome/evidence rows, source refs, proposal kind,
task text, instructions, prompts, model/provider choice, output schema,
classification, authorization snapshot, approval, completion, or device data.
`manual_review` is an internal application invocation over an existing Task,
not a new public endpoint.

`run_id` is also the command identity. Before model execution the runtime
computes `command_sha256` from compact sorted-key JSON containing exactly the
command schema version, `run_id`, canonical `requested_at`, ActorContext
`request_id|session_id|account_id|farm_id|membership_id`, `plant_id`,
`trigger_kind`, and `trigger_task_id`. Current role, membership/grant status,
permission results, auth provenance, provider data, and candidate output are
not fingerprint inputs; their owning guards remain current authority.

## Provider request version 1

`TaskFollowUpProviderRequestV1` is one strict object with exactly:

- `schema_version=1`;
- canonical project-owned `agent_definition` for `agent_id=task_follow_up`,
  decisions `speak|silent`, and strict output schema
  `TaskFollowUpModelResultV1` version 1;
- `trigger_kind`;
- `allowed_task_kinds`: ordered non-empty subset of
  `check|measurement|follow_up` computed by backend policy;
- `records`: one through four strict records;
- `source_refs`: ordered unique refs exactly equal to record refs.

Unknown fields at every nesting level are rejected. The request contains no
Farm/Plant id, ActorContext, session/account/membership/role/grant, permission
snapshot, credential, provider history, UI Feed, Bus history, raw chat,
Timeline replay, prompt, caller ref, approval payload, raw Safety/model text,
governance content, local path, or arbitrary metadata.

### Record union and order

Each record is exactly `{record_type,source_ref,payload}`. UUIDs and timestamps
are canonical strings. The closed union is:

1. `task`, with `source_ref=task:<task_id>` and payload containing only
   `task_id`, `kind`, `status`, `source_type`, nullable `due_at`, `created_at`,
   nullable `completed_at`, nullable `parent_action_task_ref`, and
   `quoted_task_text`;
2. `outcome`, with `source_ref=outcome:<outcome_id>` and payload containing
   only `outcome_id`, `follow_up_task_ref`, `value`, `recorded_at`, and ordered
   safe `evidence_refs`;
3. `evidence_ref`, with its original safe source ref and payload containing
   only `evidence_kind=manual_measurement|daily_checkin|plant_state_record`,
   the same `record_ref`, and authoritative `recorded_at` or `observed_at`.

`quoted_task_text` is the persisted Task `display_text`, kept in an explicit
untrusted-data field. It is never concatenated into project instructions or a
tool/command channel. Evidence descriptors prove the ref was reloaded from
the owning PostgreSQL repository but do not copy measurement values, Plant
facts, free text, files, UI content, or authorization state.

The assembler first resolves current `normal_read` plus task-mutation authority
for the same active Plant. It then selects records deterministically:

1. trigger Task first;
2. its Outcome second when the trigger follow-up has one;
3. its parent action Task next when present;
4. the first ordered Outcome evidence ref that resolves to the closed evidence
   union, when a slot remains.

Missing required trigger data, scope mismatch, invalid persisted values, or a
forbidden evidence kind returns the shared pre-provider `context_denied` branch
with no model or audit call. Records are never synthesized from Timeline, UI,
raw chat, MessageEnvelope, or provider output.

### Allowed proposal kinds

Backend policy always excludes `action`. It also excludes `follow_up` when the
trigger action already has its unique open automatic follow-up. This prevents
the agent from duplicating the deterministic +48-hour follow-up while keeping
`check|measurement` available.

## Model result version 1

`TaskFollowUpModelResultV1` contains exactly:

- `schema_version=1`;
- `runtime_decision=speak|silent`;
- nullable `proposed_task_kind=check|measurement|follow_up`;
- nullable normalized `candidate_output`, 1..1000 Unicode code points;
- nullable finite `confidence` in `[0,1]`;
- ordered unique `source_refs` subset of request refs;
- nullable `reason_code`.

The exact matrix is:

| Decision | Kind/output/confidence/refs | Reason |
|---|---|---|
| `speak` | kind is one backend-allowed value; output and confidence non-null; 1..4 refs in request order | null |
| `silent` | kind, output, confidence null; refs `[]` | `no_new_task|insufficient_evidence` |

Unknown fields, `action`, approval/rejection, completion, Outcome values,
Plant-state changes, device effects, target values, quantities, schedules,
tools, refs outside the request, or a kind outside `allowed_task_kinds` reject
the whole candidate as `AGENT_OUTPUT_INVALID`. The adapter does not repair or
coerce it.

## Pending envelope and authoritative route

A valid `speak` maps to the common `MessageEnvelopeV1` with:

- `runtime_decision=speak`;
- `candidate_claim_type=task_request`;
- exact candidate output, confidence, and source refs;
- `publication_state=pending_classification`;
- `consumable_by_agents=false`.

The competence-specific `proposed_task_kind` remains service-side orchestration
data and does not widen MessageEnvelope. After the common post-model current
authorization guard and sanitized runtime audit succeed:

1. invoke the canonical Safety classifier for the pending envelope;
2. require a durably persisted
   `safe_task_request/<same proposed_task_kind>` result;
3. call the ordinary Task service with the same current ActorContext,
   envelope, classification, and command request id equal to the envelope
   `run_id`;
4. return the created or identical duplicate Task.

`safe_information`, `physical_action`, `blocked_uncertain`, a different safe
task kind, classifier conflict/failure/guard denial, archive/revoke race, or
ordinary-task conflict produces no Task. The model proposal, classification,
and ActorContext snapshot are never independently sufficient authority.

`silent` creates no MessageEnvelope, classification, or Task. Provider,
validation, guard, audit, or persistence failure cannot be relabeled silence.

### Runtime-stage one-shot disposition

After model output, the runtime owns one narrow immutable PostgreSQL
`task_follow_up_runtime_dispositions` row for this competence. It is keyed by
`run_id` and the exact `command_sha256`; it is neither a generic Agent Runtime
ledger nor Task, Safety, Timeline, Bus, or UI authority. Its closed terminal
runtime-stage outcome is:

- `envelope_handed_off`: the post-model current guard passed, the one
  post-guard `message_id` and exact envelope input fingerprint are stored, and
  the in-memory envelope may proceed once to the canonical Safety classifier;
- `publication_denied`: the post-model current guard denied with the sole safe
  code `AGENT_PUBLICATION_BLOCKED`; no `message_id` or envelope fingerprint
  exists.

Both rows retain only safe `model_ref` and `agent_runtime_decided` event-ref
metadata required to reproduce a strict stored denial. They never persist
candidate text, provider request/response, MessageEnvelope payload, auth or
permission snapshots, credentials, prompts, or raw errors. The disposition
row, not its Timeline ref, is denial authority.

The post-model terminal decision uses a short PostgreSQL transaction: acquire
the FT-012 run-key transaction advisory lock, re-read any runtime or classified
dispatch disposition, lock/re-evaluate current scope, append the sanitized
runtime audit, insert the immutable runtime row, and commit. Model execution
and the later Safety classifier call occur outside this transaction. An
eligible envelope is allocated only after the locked current guard passes and
is never reconstructed or replayed from the row.

An exact retry of a stored `publication_denied` fingerprint returns the same
strict `TaskFollowUpRunResultV1` runtime denial reconstructed only from the
row's safe model/event refs, with zero model, audit, classifier, MessageEnvelope,
or Task calls. Reusing `run_id` with a different fingerprint and every
`envelope_handed_off` retry use the competence-local result contract below;
they never create or reuse another envelope. Runtime-disposition
read/lock/flush/commit failure also uses that local result and never widens the
global `AgentRuntimeOutcomeV1` union.

For `origin_agent_id=task_follow_up`, the ordinary Task service takes the same
short run-key lock and requires the exact immutable
`envelope_handed_off/run_id/message_id/input_sha256/Farm/Plant` row before it
may write its existing classified-message disposition. The runtime denial
writer checks that classified disposition under the same lock. Therefore one
run cannot commit both `publication_denied` and a classified `consumed|denied`
result. Concurrent same-run invocations may complete provider I/O, but only the
first matching terminal runtime write wins; later identical/conflicting calls
perform no classifier or Task effect.

A consumed classified disposition also carries one immutable independent
`expected_task_create_fingerprint`. The existing ordinary-task writer computes
it from the exact canonical classified-message create preimage and stores it in
the same transaction as the Task and consumed disposition. The preimage
contains normalized display text, exact ordinary kind, ordered canonical Task
source refs, run/request id, and message id; message id is also the
classification identity. It does not contain Farm/Plant scope, origin agent,
or human attribution, which replay verifies separately against the runtime,
classification, Task, and command ActorContext. No candidate text or full
MessageEnvelope is persisted.

That commitment is immutable at the PostgreSQL boundary, not only by service
convention. The data spec's named `BEFORE UPDATE` trigger rejects every
distinct old/new commitment value with SQLSTATE `23514`; a coordinated change
to Task/classification fields and both digests therefore aborts and rolls back
instead of creating a newly self-consistent replay graph. The canonical writer
remains insert-only, consumed/denied insert semantics remain owned by the
matrix check, and no new runtime or public error union is introduced.

### Disposition applicability to existing runtime outcomes

The two-value table does not represent every Agent Runtime outcome. Its exact
applicability and same-run behavior are:

| Existing common outcome | Runtime row | Same-run retry |
|---|---|---|
| `context_denied` or `runtime_not_configured` | none | repeats pre-provider checks; model/audit/classifier/Task calls remain `0` for that failed invocation |
| `provider_failed` or `output_invalid` | none | starts one new model attempt and existing audit behavior; it may later reach any normal branch |
| `model_silent` after a passing post-model guard | none | starts one new model attempt; silence is not durable one-shot authority |
| `audit_failed` on any branch | none; any uncommitted runtime row rolls back | starts one new model attempt; no classifier/Task call occurred in the failed invocation |
| successfully audited `publication_guard_denied` | one `publication_denied` | returns the stored strict denial with all executor/writer/audit call counts `0` |
| successfully audited `envelope_ready` | one `envelope_handed_off` | resolves only from the runtime row plus persisted classification/dispatch/Task authority through `TaskFollowUpDispositionResultV1`; all executor/writer/audit call counts `0` |

An `output_invalid` result never reaches the post-model current guard.
`model_silent` reaches the current guard first: a failed guard therefore becomes
the normal durable `publication_denied` branch, while only a passing guard
allows non-durable `model_silent`. The one-row invariant applies only to a
successfully audited guard denial or speak/envelope handoff, not to the other
rows in this matrix.

## Internal orchestration result

`TaskFollowUpRunResultV1` is strict and contains exactly:

- `schema_version=1`, `run_id`;
- the common `runtime_outcome`;
- `route_status=task_created|task_duplicate|not_taskable|silent|failed`;
- nullable `proposed_task_kind`;
- nullable safe `classification_ref`;
- nullable safe `task_ref`;
- nullable `failure_stage=runtime|classification|task`.

The exact matrix is:

| Route status | Common outcome | Kind / classification / task | Failure stage |
|---|---|---|---|
| `task_created|task_duplicate` | `envelope_ready` | kind and both refs present; all kinds equal | null |
| `not_taskable` | `envelope_ready` | kind and persisted non-matching classification ref present; task ref null | null |
| `silent` | `model_silent` | all three null | null |
| `failed` at runtime | any common failure/denial outcome | all three null | `runtime` |
| `failed` at classification | `envelope_ready` | kind present; both refs null | `classification` |
| `failed` at Task write | `envelope_ready` | kind and matching classification ref present; task ref null | `task` |

`not_taskable` records no candidate text. Classifier conflict/persistence/current-
guard failure uses the classification-failure row rather than exposing an
untrusted existing result. This result is an internal orchestration handoff,
not a public API or mutable authority row.

### Competence-local disposition result

`TaskFollowUpDispositionResultV1` is a second strict internal result used only
for run-disposition preflight/replay/failure. It contains exactly:

- `schema_version=1`, `run_id`;
- `result_status=conflict|failed|incomplete|not_taskable|denied|duplicate|blocked`;
- one non-null `result_code` from the closed matrix below;
- nullable safe `classification_ref` and `task_ref`;
- `retry_requires_new_run=true`.

It contains no `AgentRuntimeOutcomeV1`, MessageEnvelope/message ref, proposed
kind, candidate/provider/model/audit payload, denial detail, or auth state.
`TaskFollowUpInvocationResultV1` is the internal return union
`TaskFollowUpRunResultV1 | TaskFollowUpDispositionResultV1`; no global Agent
Runtime contract or code changes.

| Condition | Status / code | Classification / Task refs |
|---|---|---|
| Same `run_id`, different `command_sha256` | `conflict / TASK_FOLLOW_UP_RUN_CONFLICT` | null / null |
| Runtime-disposition read, advisory-lock, flush, or commit failure; or corrupt/mismatched persisted graph | `failed / TASK_FOLLOW_UP_RUNTIME_DISPOSITION_FAILED` | null / null |
| `envelope_handed_off`, no persisted classification | `incomplete / TASK_FOLLOW_UP_HANDOFF_INCOMPLETE` | null / null |
| `envelope_handed_off`, exact matching taskable classification, no classified disposition | `incomplete / TASK_FOLLOW_UP_HANDOFF_INCOMPLETE` | matching classification ref / null |
| `envelope_handed_off`, exact persisted non-taskable classification, no classified disposition | `not_taskable / TASK_FOLLOW_UP_ALREADY_NOT_TASKABLE` | matching classification ref / null |
| Matching classified disposition is `denied` | `denied / TASK_FOLLOW_UP_DISPATCH_DENIED` | matching classification ref / null |
| Matching classified disposition is `consumed`, exact Task exists, and current read/task authority passes | `duplicate / TASK_FOLLOW_UP_ALREADY_CONSUMED` | matching classification ref / existing Task ref |
| Matching consumed disposition exists but current read/task authority fails | `blocked / TASK_FOLLOW_UP_REPLAY_BLOCKED` | null / null |

An existing classification is exposed only when its message, run, Farm/Plant,
input hash, and classification content exactly match the immutable handoff.
A conflicting/untrusted classification or a consumed disposition without its
exact Task is the redacted disposition-failure row. These replay results never
call the model, audit appender, Safety classifier, or Task writer. The old run
remains one-shot in every case; retry or recovery uses a new command/run and an
eligible new post-guard message.

An exact consumed Task additionally requires all three values to agree: the
Task's persisted `create_request_fingerprint`, the disposition's independent
`expected_task_create_fingerprint`, and a fresh canonical recomputation over
the Task row's normalized text/kind/ordered refs plus the trusted run/message
identity. Account, membership, role, Farm, Plant, agent, and classification
attribution are compared separately. A missing or malformed commitment,
including a legacy null, or any mismatch returns
`failed/TASK_FOLLOW_UP_RUNTIME_DISPOSITION_FAILED` with null refs and exact
model/audit/Safety/Task calls `0/0/0/0`. Replay never treats
`input_sha256` as a substitute: the full envelope preimage is transient and
cannot be reconstructed independently.

At first invocation, a disposition read/lock failure before model execution
returns the local failure with model/audit/Safety/Task counts `0/0/0/0`. A
post-model lock failure returns it after exactly one model call and before
audit/Safety/Task (`1/0/0/0`). A flush/commit failure after successful audit
returns it after `1/1/0/0`, leaves no runtime row, and may leave exactly one
non-authoritative audit event. It never reports the normal
`publication_guard_denied` or `envelope_ready` result unless the runtime row
committed.

Deterministic race conformance uses completion barriers, never scheduler
sampling. If an eligible invocation completes the exact matching
classification plus consumed Task before its denied peer resumes, the returns
are normal `task_created(C,T)` then local
`duplicate/TASK_FOLLOW_UP_ALREADY_CONSUMED(C,T)`. If denial commits first,
both participants return the same stored normal `publication_guard_denied /
AGENT_PUBLICATION_BLOCKED` result with null refs. After a handoff and matching
classification are committed, a late denial released before the classified
writer returns local `incomplete/TASK_FOLLOW_UP_HANDOFF_INCOMPLETE(C,null)` and
the writer then returns normal `task_created(C,T)`; with the writer released
first, it returns `task_created(C,T)` and the late denial returns local
`duplicate/TASK_FOLLOW_UP_ALREADY_CONSUMED(C,T)`. Both late orders finish with
the same immutable handoff plus consumed disposition and never with a runtime
denial. Exact row/call/audit/rollback cardinalities and the named lock-order
fixture are canonical in `.memory-bank/testing/task-follow-up.md` group 6/7.

## Executor and failure behavior

`task_follow_up` uses the shared provider-neutral executor. Current production
remains unbound until future endpoint selection. There is no default model,
fallback, fake/canned production result, silent substitution, or retry that
changes the binding.

Provider I/O occurs outside database transactions. Current
session/account/membership/grant and active Plant checks run before assembly,
after model I/O, at classification persistence, and at Task insertion through
their owning boundaries. Restore never replays a denied or already handed-off
run. Reevaluation requires a new `TaskFollowUpCommandV1` with a new `run_id`;
an eligible post-guard path then allocates a new `message_id`.

Errors, logs, Timeline, and evidence exclude request/response bodies, candidate
text, quoted task text, prompts, credentials, auth state, raw exceptions,
hidden reasoning, and local paths. Existing common stable failure codes remain
authoritative; route mismatch adds no mutable failure record.

## Verification

Current code-phase tests must prove exact request/result/orchestration shapes, deterministic
record selection, typed quoted-data isolation, forbidden-source and auth-data
absence, allowed-kind policy, no duplicate automatic follow-up, strict pending
MessageEnvelope mapping, matched classification, ordinary-task idempotency,
runtime command fingerprints, identical/conflicting same-run behavior,
post-model archive/revoke denial retention, concurrent same-run first-write,
runtime/classified-disposition exclusion, disposition rollback, new-identity
eligibility, independent consumed-Task commitment and legacy-null failure,
PostgreSQL write-once rejection of all three coordinated ATTEMPT 05 mutations,
current authorization/archive races, fake/spy success, timeout,
provider-error, invalid-output and classification paths, no production
fallback, redaction, and zero action/approval/completion/outcome/device/Plant-state authority. A
strict fake/spy `task_follow_up` proposal plus strict fake/spy classifier result
may create exactly one ordinary Task as deterministic code-phase evidence.

Real response/classifier calls are deferred to the single provider runbook
milestone after endpoint selection and are not current closure evidence.
