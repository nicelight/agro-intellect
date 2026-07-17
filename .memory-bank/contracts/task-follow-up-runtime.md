---
description: Strict real-model Task and Follow-up Agent input, proposal, classification, and ordinary-task handoff contract.
status: active
type: interface_contract
last_updated: 2026-07-17
source_of_truth:
  - .memory-bank/features/FT-012-human-approval-tasks-follow-up-outcomes.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/contracts/agent-roster-bootstrap.md
  - .memory-bank/domains/task-approval-outcomes.md
---
# Task And Follow-Up Agent Runtime

## Scope

Defines one real model-backed `task_follow_up` competence over current
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
  explicit binding, credentials, egress, and no fallback.
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

## Provider and failure behavior

One explicit DeepSeek or Gemini binding may serve `task_follow_up`.
`chatgpt_oauth` remains fail closed without its approved adapter. There is no
default model, cross-provider fallback, fake/canned product result, silent
substitution, or provider retry that changes the binding.

Provider I/O occurs outside database transactions. Current
session/account/membership/grant and active Plant checks run before assembly,
after model I/O, at classification persistence, and at Task insertion through
their owning boundaries. Restore never replays a denied run; a new command and
run/message id are required.

Errors, logs, Timeline, and evidence exclude request/response bodies, candidate
text, quoted task text, prompts, credentials, auth state, raw exceptions,
hidden reasoning, and local paths. Existing common stable failure codes remain
authoritative; route mismatch adds no mutable failure record.

## Verification

Tests must prove exact request/result/orchestration shapes, deterministic
record selection, typed quoted-data isolation, forbidden-source and auth-data
absence, allowed-kind policy, no duplicate automatic follow-up, strict pending
MessageEnvelope mapping, matched classification, ordinary-task idempotency,
current authorization/archive races, explicit provider/no-fallback behavior,
redaction, and zero action/approval/completion/outcome/device/Plant-state
authority.

One explicitly enabled credentialed smoke must use the canonical production
`task_follow_up` definition and exactly one selected DeepSeek or Gemini model
over real authorized PostgreSQL Task/Outcome evidence. It must produce a valid
non-silent proposal, pass the existing explicitly bound Safety classifier,
and persist exactly one matched ordinary Task. Skip, xfail, fake/canned output,
fallback, model silence, unconfigured/blocked/failed/unaudited outcome,
classification mismatch, or direct action effect fails that smoke and cannot
satisfy FT-012's portion of REQ-011.
