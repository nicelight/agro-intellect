---
description: Strict provider-neutral Task and Follow-up Agent input, proposal, classification, and ordinary-task handoff contract.
status: active
type: interface_contract
last_updated: 2026-07-25
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

Backend policy always excludes `action`. When the trigger Task is `action`, it
also excludes `follow_up` in every action state; action completion exclusively
owns that action's deterministic +48-hour follow-up. This immutable-kind policy
prevents both completion-during-provider-I/O and ordinary-first/completion-later
duplication while keeping `check|measurement` available.

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

### Linear runtime boundary

The current MVP has no durable caller, worker, scheduler, delivery identity, or
accepted runtime retry/crash contract for this competence. The runtime
therefore writes no pre-classification disposition and exposes no runtime
replay result union.

Every explicit invocation performs:

1. current authorization and deterministic PostgreSQL input assembly;
2. provider-neutral model execution outside a database transaction;
3. post-I/O current authorization/Plant recheck;
4. sanitized `agent_runtime_decided` attempt audit;
5. one transient pending MessageEnvelope for a valid non-silent result;
6. canonical Safety classification; and
7. the sole ordinary Task writer for an exact matching safe task kind.

Context denial, unbound runtime, provider failure, invalid output, silence,
audit failure, post-I/O denial, classifier failure, and Task failure use the
existing `TaskFollowUpRunResultV1` branches and create no runtime ledger row.
An explicit retry repeats the linear path and may repeat model, audit, or
classification work. This accepted residual remains bounded because the
ordinary writer's persisted classification, unique run/message identities,
transaction, Task request fingerprint, and `consumed|denied` disposition
prevent a duplicate Task.

The ordinary writer may retain its short run-key serialization for real
write-side races, but it does not read or validate
`task_follow_up_runtime_dispositions`. A consumed classified disposition and
the Task commit atomically. Its exact classified retry returns the linked Task
only under current read/task authority, without reconstructing Task
text/kind/source history or storing an independent commitment. Coordinated
direct PostgreSQL corruption is outside this contract.

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

`TaskFollowUpRunResultV1` is the sole competence-local invocation result. The
historical `TaskFollowUpDispositionResultV1` conflict/incomplete/denied/
duplicate/blocked matrix is removed with the runtime ledger and is not mapped
into global `AgentRuntimeOutcomeV1`.

## Executor and failure behavior

`task_follow_up` uses the shared provider-neutral executor. Current production
remains unbound until future endpoint selection. There is no default model,
fallback, fake/canned production result, silent substitution, or retry that
changes the binding.

Provider I/O occurs outside database transactions. Current
session/account/membership/grant and active Plant checks run before assembly,
after model I/O, at classification persistence, and at Task insertion through
their owning boundaries. A pre-classification denial or interrupted invocation
is not durable delivery state; an explicit retry re-runs these checks and may
allocate a new transient message. Once a classified `consumed|denied`
disposition exists, its run/message identities remain terminal under the
ordinary Task contract.

Errors, logs, Timeline, and evidence exclude request/response bodies, candidate
text, quoted task text, prompts, credentials, auth state, raw exceptions,
hidden reasoning, and local paths. Existing common stable failure codes remain
authoritative; route mismatch adds no mutable failure record.

## Verification

Current code-phase tests must prove exact request/result/orchestration shapes,
deterministic record selection, typed quoted-data isolation, forbidden-source
and auth-data absence, allowed-kind policy, no duplicate automatic follow-up,
strict transient MessageEnvelope mapping, matched classification, linear
post-I/O guard routing, ordinary-task write-side idempotency and rollback,
classified-disposition duplicate/conflict behavior, current authorization/
archive races, fake/spy success, timeout, provider-error, invalid-output and
classification paths, no mapped or written runtime ledger, no production
fallback, redaction, and zero action/approval/completion/outcome/device/
Plant-state authority. A strict fake/spy `task_follow_up` proposal plus strict
fake/spy classifier result may create exactly one ordinary Task as
deterministic code-phase evidence.

Real response/classifier calls are deferred to the single provider runbook
milestone after endpoint selection and are not current closure evidence.
