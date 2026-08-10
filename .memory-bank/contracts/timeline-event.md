---
description: Global timeline audit/export event contract for MVP v2.
status: active
type: contract
last_updated: 2026-08-10
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/domains/task-approval-outcomes.md
---
# Timeline Event

## Scope

`timeline.jsonl` is the append-only audit/export trace for significant local
Farm/Plant events. It is not mutable runtime authority, not Agent Chat Bus, not
UI Feed, and not a state rebuild source.

The verified FT-000 executable baseline provides a local timeline root setting.
This contract owns the minimum append writer seam and active event registry
needed by current emitters. Subject specs own their payload summaries and
runtime mutation rules. Timeline history UI, pagination, file rotation, and
export packaging remain outside this contract.

## Contract Scope

- Defines: global timeline authority boundary, minimum event identity, reference
  shape, append writer seam, active event registry, redaction rules, replay
  limits, and verification requirements.
- Out of scope: complete future event taxonomy, all payload fields, JSONL
  rotation, export UI, history projection endpoint schemas, or DB table schemas.
- Related specs:
  - [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md):
    defines mutable runtime authority and shared entity relationships.
  - [.memory-bank/contracts/ui-feed.md](ui-feed.md): defines human-facing
    projection rules.
  - [.memory-bank/domains/photo-artifacts.md](../domains/photo-artifacts.md):
    defines local photo artifact authority.

## Event Shape

Feature-local specs may add event-specific fields, but every timeline event
must carry:

- `timeline_event_id`
- `created_at`
- `farm_id`
- `plant_id` when Plant-scoped
- `actor_ref` or `source_ref`
- `event_type`
- `source_type`
- `source_id`
- `source_refs`
- `payload_summary`
- `redaction_status`

`payload_summary` is an audit/export summary. It must not carry auth material,
raw provider payloads, hidden reasoning, raw proposal text, or full binary data.

`event_refs` stored by runtime rows use this minimum shape:

- `timeline_event_id`: UUID string.
- `timeline_ref`: stable relative ref in the form
  `timeline.jsonl#<timeline_event_id>`.
- `event_type`: the emitted event type.
- `created_at`: the event creation timestamp.

## Active Event Registry

The following event types are registered for the current taskable features:

| Event type | Producer | `source_type` | `source_id` | Payload summary owner |
|---|---|---|---|---|
| `daily_checkin_recorded` | Plant operations service | `daily_checkin` | `check_in_id` | `.memory-bank/domains/plant-operations.md` |
| `manual_measurement_recorded` | Plant operations service | `manual_measurement` | `measurement_id` | `.memory-bank/domains/plant-operations.md` |
| `photo_accepted` | Photo intake service | `photo_catalog_item` | `photo_id` | `.memory-bank/domains/photo-artifacts.md` |
| `agent_runtime_decided` | Agent Runtime service | `agent_runtime_attempt` | `run_id` correlation UUID | `.memory-bank/contracts/agent-runtime-adapter.md` |
| `task_created` | Task and Follow-Up service | `task` | `task_id` | `.memory-bank/domains/task-approval-outcomes.md` |
| `task_completed` | Task and Follow-Up service | `task` | `task_id` | `.memory-bank/domains/task-approval-outcomes.md` |
| `approval_decided` | Task and Follow-Up service | `approval` | `approval_id` | `.memory-bank/domains/task-approval-outcomes.md` |
| `follow_up_outcome_recorded` | Task and Follow-Up service | `outcome` | `outcome_id` | `.memory-bank/domains/task-approval-outcomes.md` |
| `companion_issue_opened` | Companion Governance service | `companion_issue` | `issue_id` | `.memory-bank/domains/companion-governance.md` |
| `companion_proposal_created` | Companion Governance service | `companion_proposal` | `proposal_id` | `.memory-bank/domains/companion-governance.md` |
| `companion_proposal_superseded` | Companion Governance service | `companion_proposal` | superseded `proposal_id` | `.memory-bank/domains/companion-governance.md` |
| `companion_decision_recorded` | Companion Governance service | `decision_record` | `decision_record_id` | `.memory-bank/domains/companion-governance.md` |
| `companion_issue_resolved` | Companion Governance service | `companion_issue` | `issue_id` | `.memory-bank/domains/companion-governance.md` |
| `companion_issue_closed` | Companion Governance service | `companion_issue` | `issue_id` | `.memory-bank/domains/companion-governance.md` |
| `dataset_candidate_created` | Dataset Governance service | `dataset_candidate` | `candidate_id` | `.memory-bank/domains/dataset-governance.md` |
| `dataset_candidate_evidence_linked` | Dataset Governance service | `dataset_candidate` | `candidate_id` | `.memory-bank/domains/dataset-governance.md` |
| `dataset_candidate_reviewed` | Dataset Governance service | `dataset_candidate` | `candidate_id` | `.memory-bank/states/dataset-governance.md` |
| `dataset_agent_runtime_decided` | Dataset Governance service | `dataset_agent_attempt` | `run_id` correlation UUID | `.memory-bank/contracts/dataset-agents-runtime.md` |

New event types require the emitting feature's subject spec to define producer,
source identity, payload summary, redaction, failure behavior, and verification
before task creation.

### Task, Approval, and Outcome payload summaries

The FT-012 event payloads are strict correlation summaries:

- `task_created`: `task_kind`, `task_source_type`, nullable `due_at`, and
  `source_ref_count`;
- `task_completed`: `task_kind`, `completion_kind=ordinary|action|outcome`, and
  `source_ref_count`;
- `approval_decided` has a branch-exact payload: both branches contain
  `decision=approved|rejected`, `action_kind`, and `record_version=2`;
  `approved` additionally requires non-null canonical UUID `action_task_id`,
  while `rejected` MUST omit `action_task_id` entirely;
- `follow_up_outcome_recorded`: `follow_up_task_id`,
  `outcome_value=improved|worsened|unchanged|no_data`, and
  `evidence_ref_count` from 0 through 4.

The event's standard `actor_ref` owns safe human attribution. These summaries
MUST NOT contain Task display text, MessageEnvelope candidate text, target
values, quantities, device commands, measurement values, Outcome evidence
payloads, request ids/fingerprints, ActorContext/session/grant objects,
provider data, prompts, credentials, or arbitrary metadata.

Cardinality follows the authoritative FT-012 transaction:

- ordinary Task creation: one `task_created`;
- reject: one `approval_decided`;
- approve: one `approval_decided` plus one `task_created` for the action;
- ordinary completion: one `task_completed`;
- action completion: one `task_completed` plus one `task_created` for its
  automatic follow-up;
- Outcome recording: one `task_completed` plus one
  `follow_up_outcome_recorded`.

Approval materialization alone emits no event. The task/approval/outcome data
spec owns append-before-commit behavior and persisted refs. An appended event
left by a later failed PostgreSQL commit is non-authoritative audit noise;
Timeline replay cannot create or repair the missing row.

### Companion governance payload summaries

The FT-013 payloads are strict redacted correlation summaries:

- `companion_issue_opened`: `issue_status=open`, `is_focused=true`, and
  `source_ref_count`;
- `companion_proposal_created`: `proposal_sequence`,
  `proposed_effect=discussion_only|check|measurement|follow_up|none`,
  `suggested_resolution=keep_open|resolved`, `attention_sequence`, and
  `source_ref_count`;
- `companion_proposal_superseded`: `proposal_sequence`,
  `replacement_proposal_id`, and `record_version=2`;
- `companion_decision_recorded`: `decision=approved|rejected`, exact
  `allowed_workflow_effect`, `issue_resolution=keep_open|resolved`, nullable
  safe `workflow_effect_ref`, and
  `safety_gate_authority=not_granted`;
- `companion_issue_resolved`: `issue_status=resolved` and
  `decision_record_id`;
- `companion_issue_closed`: `issue_status=closed`.

Actor attribution uses the standard safe actor ref. Payloads MUST NOT contain
issue/proposal/attention/decision text, rationale, Task display text, raw model
output, MessageEnvelope candidate text, request ids/fingerprints, ActorContext,
session/grant objects, prompts, provider data, credentials, or arbitrary
metadata.

Cardinality follows the authoritative transaction:

- new-issue run: one `companion_issue_opened` plus one
  `companion_proposal_created`;
- existing-issue run: one `companion_proposal_created` and, when replacing a
  pending proposal, one `companion_proposal_superseded` first;
- decision: one `companion_decision_recorded`, plus one
  `companion_issue_resolved` when selected, plus the existing `task_created`
  only for an operative ordinary-task effect;
- close: one `companion_issue_closed`.

No event exists for derived CompanionConclusion or attention satisfaction by
itself. The Companion data spec owns append-before-commit refs and rollback;
Timeline replay cannot create, supersede, decide, focus, resolve, close, or
publish governance state.

### Dataset Candidate payload summaries

The FT-014 candidate events use strict redacted summaries:

- `dataset_candidate_created`: `source_kind`, `candidate_origin=raw`,
  `candidate_status=candidate`, `evidence_ref_count=1`,
  `quality_tier=standard`, and `can_train_on=false`;
- `dataset_candidate_evidence_linked`:
  `added_evidence_kind=follow_up_outcome`, `candidate_status` limited to
  `candidate|needs_review`, `evidence_ref_count`, `distinct_evidence_kind_count`,
  `follow_up_seen=true`, and `can_train_on=false`;
- `dataset_candidate_reviewed`: `from_status`, `to_status`, nullable
  `confirmation_source`, `quality_tier`, `evidence_ref_count`, and derived
  `can_train_on`.

The standard `actor_ref` carries safe human attribution. Payloads and
`source_refs` MUST NOT contain evidence bodies, filenames, absolute paths,
photo bytes/hashes, measurement values, observation or Outcome text, curator
notes, raw model output, ActorContext/session/grant objects, request
fingerprints, credentials, or arbitrary metadata.

Cardinality follows Dataset Governance authority:

- every newly inserted candidate appends one `dataset_candidate_created`;
- every candidate actually enriched by the follow-up association command
  appends one `dataset_candidate_evidence_linked`; an idempotent retry that
  adds no ref appends none;
- every successful lifecycle transition appends one
  `dataset_candidate_reviewed`; a conflict/forbidden/no-op request appends
  none.

Candidate insert/association/transition and their returned event refs are in
the owning PostgreSQL unit of work. Append failure rolls the owning mutation
back; an append that succeeds before a later PostgreSQL commit failure is
non-authoritative audit noise. Timeline replay cannot create a candidate,
associate evidence, change lifecycle/quality/confirmation, or derive
trainability.

### `dataset_agent_runtime_decided` payload summary

AD-011 registers this dedicated event for the advisory-only Dataset Agents
route. It contains only:

- `agent_id=dataset_governance|training_data_curator`;
- nullable safe `model_ref`;
- `outcome_kind` from the exact
  [DatasetAgentRuntimeOutcomeV1](dataset-agents-runtime.md#datasetagentruntimeoutcomev1)
  union;
- `status`, `reason_code`, nullable `error_code`,
  `provider_call_status`, and `curator_gate_result` from that outcome;
- `candidate_ref_count=0|1`;
- `advisory_persisted=true|false`; and
- `lifecycle_changed=true|false`.

The event MUST NOT contain the provider request/result, assessment notes,
curator notes, evidence bodies, candidate row snapshot, lifecycle command,
prompts, hidden reasoning, raw exceptions, auth/session/grant material, or
credentials. `source_type=dataset_agent_attempt` and `source_id=run_id` are a
correlation-only identity, not a PostgreSQL FK or replay key. When pre-I/O
authorization has validated the candidate, `source_refs` is exactly
`{"candidate_refs":["dataset_candidate:<candidate_id>"]}` and
`candidate_ref_count=1`; a pre-I/O context denial uses
`{"candidate_refs":[]}` and count `0` to avoid protected-existence leakage.

Every accepted explicit Dataset Agent attempt tries exactly one append,
including pre-I/O denial, unbound runtime, provider failure, invalid output,
post-I/O denial, silence, policy block, and success. `audit_failed` has no
event/event ref and rolls back pending advisory/lifecycle state. If append
succeeds and the later advisory/lifecycle PostgreSQL commit fails, the event
remains non-authoritative audit noise; it cannot replay the attempt or repair
Dataset state.

### `agent_runtime_decided` payload summary

The FT-007 event contains only:

- `agent_id`;
- safe `model_ref` in `provider_profile:model_id` form when a real executor was
  reached, otherwise `null`;
- `outcome_kind`: `envelope_ready | model_silent | provider_failed |
  output_invalid | publication_guard_denied`;
- `candidate_decision`, `final_decision`, `outcome_status`, `reason_code`,
  `error_code`, `message_id`, and `candidate_claim_type` according to the
  closed matrix below;
- `source_ref_count` as an integer from 1 through 4, equal to the number of
  `source_refs.input_refs`.

| `outcome_kind` | Candidate / final decision | Status | Reason / error | Message / candidate claim |
|---|---|---|---|---|
| `envelope_ready` | same `speak|clarify|escalate` / same value | `envelope_ready` | `envelope_ready` / `null` | `message_id` present / validated non-null claim |
| `model_silent` | `silent` / `silent` | `silent` | `no_material_output|insufficient_evidence` / `null` | `null` / `null` |
| `provider_failed` | `null` / `null` | `failed` | `provider_failed` / `AGENT_PROVIDER_FAILED` | `null` / `null` |
| `output_invalid` | `null` / `null` | `blocked` | `output_invalid` / `AGENT_OUTPUT_INVALID` | `null` / `null` |
| `publication_guard_denied` | validated `speak|silent|clarify|escalate` / `null` | `blocked` | `publication_guard_denied` / `AGENT_PUBLICATION_BLOCKED` | `null` / validated claim for a non-silent candidate, otherwise `null` |

Unvalidated provider fields are never retained in the `output_invalid` event.
`context_denied` and `runtime_not_configured` do not reach provider I/O and
therefore create no event. `audit_failed` means append failed, so it likewise
has no event or event ref.

The payload MUST NOT contain `candidate_output`, observation text, pH/EC
values, prompts, provider response text/objects, parser diagnostics, hidden
reasoning, credentials, provider keys, headers, cookies, session/auth material,
or a serialized ActorContext. The event's `source_refs` is exactly
`{"input_refs": ["kind:identifier", ...]}` with 1 through 4 unique safe refs
already authorized for the invocation; it never copies their payloads.

This registered event is an explicit correlation-only exception to the normal
runtime-record source rule: `source_id=run_id` identifies the transient attempt
and is not a PostgreSQL FK, lookup target, or mutable authority. Its
`source_refs.input_refs` MUST reference the actual authoritative Plant,
check-in, and/or measurement rows that formed the invocation. The event cannot
be used to reconstruct a run or MessageEnvelope.

Its `actor_ref` is exactly authenticated service-side `account_id`,
`membership_id`, and request-time `role_preset`. These safe attribution values
remain available for provider failure and invalid output; they are not reused
as publication authority. The event excludes `session_id`, auth provenance,
token/digest, headers, cookies, and credentials.

One accepted request that reaches provider I/O produces exactly one
`agent_runtime_decided` event, including provider failure, invalid output,
explicit silence, and post-execution publication denial. A request denied
before provider I/O, or rejected because runtime is not configured, does not
create this event. `audit_failed` cannot create an event or event ref and
returns no MessageEnvelope.

## Append Writer Seam

The implementation exposes one backend-owned append helper for current feature
emitters. The helper:

- resolves `LOCAL_TIMELINE_ROOT` from application settings;
- creates or opens the MVP `timeline.jsonl` file under that root;
- validates the minimum event shape and registered `event_type`;
- writes one UTF-8 JSON object per line and returns the minimum `event_refs`
  shape above;
- rejects or redacts forbidden payload content before writing;
- never reads timeline events to compute mutable runtime state.

Feature services generate runtime ids before append, call the helper inside
their service boundary, persist returned `event_refs` on the owning runtime
row, and return success only after runtime persistence and timeline append have
both succeeded. For FT-004 and FT-005, append failure is fail-safe: the service
returns the documented `TIMELINE_APPEND_FAILED` error and must not report a
successful check-in, measurement, or accepted photo. Any task that adds a new
filesystem artifact must also clean up files it created for the failed attempt.

FT-007 has no owning PostgreSQL agent-run row. It appends the sanitized event
after final runtime decision/current publication guard and before returning a
MessageEnvelope handoff. Append failure returns `AGENT_AUDIT_FAILED` and no
handoff; a timeline event that already appended remains non-authoritative audit
noise if a later downstream publisher rejects the envelope.

## Rules

- Runtime state remains in PostgreSQL/read model; timeline events reference
  runtime records/artifact refs, except a registry-declared correlation-only
  source such as `agent_runtime_attempt`, whose source refs still point to the
  authoritative input records and never create runtime authority.
- Timeline replay must not rehydrate mutable runtime state.
- Timeline events cannot publish directly to Agent Chat Bus.
- Timeline events cannot make UI Feed content, raw chat, or raw model output
  agent-consumable.
- Timeline events that reference physical-action wording must reference the
  relevant Safety Gate/task records instead of becoming action authority.
- Task, Approval, and Outcome events cannot create, decide, complete, retry, or
  schedule their referenced records and cannot authorize a physical action.
- Timeline events that reference DecisionRecord must preserve
  `safety_gate_authority=not_granted` when governance summary is involved.
- Timeline events that reference dataset candidates cannot set or imply
  `can_train_on=true`.
- `dataset_agent_runtime_decided` cannot persist or replay advisory fields,
  evidence association, lifecycle, confirmation, or trainability.
- Feature success responses must not claim audit/export evidence when the
  append helper failed.

## Edge Cases And Errors

- If runtime persistence would succeed but timeline append fails, the current
  FT-004 and FT-005 operations fail and roll back/clean up task-owned runtime
  changes instead of claiming success.
- If timeline append succeeds but the runtime commit fails, the API must return
  the owning persistence error and the event remains non-authoritative audit
  noise; replay still cannot create or repair runtime state.
- If a timeline payload would include secrets or auth material, redact or block
  the event before writing.
- If event ordering matters for a feature, the feature-level spec must define
  the stricter ordering/idempotency rule before task creation.
- If an Agent Runtime audit append fails, do not return a MessageEnvelope
  handoff or claim an audited runtime outcome.

## Verification

Tests must prove:

- Timeline events reference authoritative runtime/artifact records rather than
  replacing them.
- Timeline replay cannot mutate runtime state or Agent Chat Bus context.
- Secret/auth material is redacted from event payloads.
- Unauthorized Plant timeline/history reads fail closed.
- Feature-specific audit writes are transactionally consistent with their
  owning runtime mutation policy.
- Agent Runtime audit tests prove exactly one safe event per invoked run, no
  content/provider/auth leakage, and no envelope handoff after append failure.
- FT-014 tests prove the Dataset Candidate and Dataset Agent event registries,
  exact redacted summaries/cardinality, no-I/O Dataset Agent branches, append
  failure rollback, append-success/commit-failure noise, and zero replay
  authority.
- FT-012 tests prove the registered task/approval/outcome cardinality, strict
  redacted summaries, branch-exact `approval_decided` field sets, persisted
  event refs, rollback on append failure, and no Timeline-based replay or state
  repair.
