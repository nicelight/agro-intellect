---
description: Explicit provider-neutral Companion request, result, orchestration, trigger, and proposal handoff contract.
status: active
type: interface_contract
last_updated: 2026-07-19
source_of_truth:
  - .memory-bank/features/FT-013-companion-issuestack-proposals-decisionrecords.md
  - .memory-bank/states/companion-governance.md
  - .memory-bank/domains/companion-governance.md
  - .memory-bank/domains/plant-operations.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/states/safety-action-lifecycle.md
  - .memory-bank/contracts/safety-gate-runtime.md
  - .memory-bank/domains/safety-action-routing.md
---
# Companion Runtime

## Scope

Defines one explicit protected provider-neutral invocation of canonical
`agent_id=companion` over current authorized PostgreSQL Plant/issue evidence.
A valid non-silent result becomes a pending MessageEnvelope, passes the existing
project classifier, and only then may the governance service persist an issue,
attention, and proposal.

## Out of scope

- Automatic/domain-event/Task-completion/feed-refresh triggers;
- raw chat, caller prompts, Agno memory/Team/tools/RAG, generic ProviderRequest
  widening, public provider/model selection, provider-result persistence, or a
  persisted runtime receipt/MessageEnvelope replay store;
- DecisionRecord creation, human approval/rejection, ordinary Task completion,
  Safety approval, action Task, Plant-state mutation, or device effects.

## Module and command boundary

Implementation lives under `backend/app/companion_governance/`, composes the
existing Agent Runtime/provider/classifier seams, and exposes one internal
`CompanionRunCommandV1` containing exactly:

- `schema_version=1`;
- application-supplied UUIDv4 `run_id` from the protected request id;
- timezone-aware UTC `requested_at`;
- service-side `actor_context`;
- requested UUID `plant_id`;
- nullable `issue_id` and nullable `expected_issue_version`, both absent for
  new issue or both present for one existing issue.

The API/caller cannot submit records, text, refs, prompts, instructions,
effects, resolution, provider/model, output schema, classification,
authorization snapshot, or projection data.

The pre-provider assembler requires current active Plant, role
`boss|engineer`, and `can_operate=true`. It locks no row and holds no DB
transaction across provider I/O.

Before provider I/O, the service computes the canonical request fingerprint
from `schema_version`, `run_id`, `plant_id`, nullable `issue_id`, and nullable
`expected_issue_version`, then looks up a committed proposal by `source_run_id`.
An identical committed retry returns `proposal_duplicate` from that proposal
and its matching persisted classification without another provider call. It
does not manufacture an `AgentRuntimeOutcomeV1`, re-create a transient
MessageEnvelope, or claim a current provider call. Reused `run_id` with a
different fingerprint is a version/request conflict without provider I/O.
Concurrent requests with the same `run_id` may both call the provider, but the
governance uniqueness/re-read rule permits only one product effect. Different
`run_id` values are independent explicit commands: they may both reach the
provider and, if every current guard still passes, serialize at governance
persistence and both commit. For one existing issue, the later locking writer
creates the next proposal sequence and supersedes the earlier writer's pending
proposal; for two `new_issue` commands, each creates its own open issue and the
later locking writer becomes the only focused issue. A different run conflicts
only for an independently changed target/version, terminal issue, archive,
authorization loss, or another stated current-guard failure. Provider finish
time and `requested_at` do not establish governance order; successful locked
write order does.

## `CompanionProviderRequestV1`

The provider receives one strict object with exactly:

- `schema_version=1`;
- canonical project-owned `agent_definition` for `agent_id=companion`, allowed
  decisions `speak|silent`, and strict output schema
  `CompanionModelResultV1` version 1;
- `trigger_kind=explicit_user_command`;
- `target_mode=new_issue|existing_issue`;
- `records`: one through four strict records;
- `source_refs`: ordered unique refs exactly equal to record refs.

Each record is exactly `{record_type,source_ref,payload}`. The closed ordered
union is:

1. `plant`, `source_ref=plant:<plant_id>`, payload exactly
   `{plant_id,status:"active"}`;
2. selected `companion_issue` when target mode is existing,
   `source_ref=companion_issue:<issue_id>`, payload exactly
   `{issue_id,status:"open",record_version,is_focused,summary_text}`;
3. latest completed `daily_checkin` when present,
   `source_ref=daily_checkin:<check_in_id>`, payload exactly
   `{check_in_id,observed_at,recorded_at,observation_state,
   observation_text}`, where the observation matrix and 2000-code-point bound
   are the shared Agent Runtime/Plant Operations shape;
4. latest `manual_measurement` when present,
   `source_ref=manual_measurement:<measurement_id>`, payload exactly
   `{measurement_id,measured_at,recorded_at,ph,ec_ms_cm,
   source_type:"manual_user",trust_status:"confirmed"}`. `ph` is the canonical
   fixed two-decimal string or null, `ec_ms_cm` is the canonical fixed
   three-decimal string or null, and at least one is non-null.

Order is Plant, selected issue, check-in, measurement; absent optional records
are omitted without placeholders. Existing issue identity/version must equal
the command. Data comes only from PostgreSQL authority and current Plant scope.

The existing-issue `companion_issue.summary_text` is permitted typed governance
content at provider egress. The assembler
copies the normalized persisted value unchanged only after the current active
Plant, exact open `issue_id`, and `record_version` guards pass. It is
non-authoritative context for this explicit Companion run: it grants no
DecisionRecord, approval, Task, Safety, Plant-state, Bus, general agent-context,
or publication authority. The current FT-013 allowlist does not include attention/proposal/rationale/decision
text, proposal history, UI/Timeline copies, caller text, or arbitrary
governance fields. A new-issue request has no issue record or issue summary,
and no generic provider request or persisted schema is widened.

Selection is deterministic and competence-specific:

- the optional completed check-in is the first same-Plant row ordered by
  `(recorded_at DESC,check_in_id DESC)`, reusing the shared Agent Runtime
  check-in rule;
- the optional manual measurement is the first same-Plant row with
  `source_type=manual_user`, `trust_status=confirmed`, and at least one
  non-null normalized `ph|ec_ms_cm`, ordered by
  `(measured_at DESC,measurement_id DESC)`;
- Companion deliberately sends one authoritative measurement row, not the
  generic Agent Runtime's independently selected latest non-null pH and EC
  rows. If the newest pH and newest EC belong to different rows, only the
  single row that wins the tuple above is sent; its other value remains null.
  Values from different rows MUST NOT be merged into a synthetic measurement.

Equal timestamps resolve by canonical UUID descending. Future-dated retained
measurements participate in the same ordering and keep their actual timestamp;
this runtime does not invent a freshness or Safety claim. Tests cover empty
data, one-value rows, a combined pH/EC row, different latest pH/EC rows, and
equal-timestamp UUID ties.

The request contains no Farm id, ActorContext, session/account/membership/role/
grant, permission flags, credential, provider history, UI Feed, Bus/Timeline
replay, raw chat, proposal/rationale/decision text, hidden reasoning, local
path, caller text/ref, or arbitrary metadata.

## `CompanionModelResultV1`

The strict result contains exactly:

- `schema_version=1`;
- `runtime_decision=speak|silent`;
- nullable `issue_summary`;
- nullable `attention_summary`, `proposal_summary`, `proposal_text`,
  `rationale_text`;
- nullable `proposed_effect`;
- nullable `task_display_text`;
- nullable `suggested_resolution`;
- nullable finite `confidence` in `[0,1]`;
- ordered unique `source_refs` subset of request refs in request order;
- nullable `reason_code`.

Exact matrix:

| Decision/target | Required values | Null values | Reason |
|---|---|---|---|
| `speak/new_issue` | issue, attention, proposal summaries; proposal text; effect; resolution; confidence; 1..4 refs | rationale optional; task text matrix below | null |
| `speak/existing_issue` | attention/proposal summaries; proposal text; effect; resolution; confidence; 1..4 refs | issue summary; rationale optional; task text matrix below | null |
| `silent` | refs exactly `[]` | every content/effect/resolution/confidence field | `no_material_output|insufficient_evidence` |

Summaries are normalized `1..500`; proposal/rationale/task text are normalized
`1..2000`. The closed effect enum is
`discussion_only|check|measurement|follow_up|none`. Task display text is
required exactly for the three Task effects and null for the two non-task
effects. `suggested_resolution` is `keep_open|resolved`.

Unknown fields, `action`, physical/Safety approval, target values, quantities,
device commands, Plant-state mutation, refs outside the request, or a result
that violates target/effect/nullability rejects the whole candidate as
`AGENT_OUTPUT_INVALID`. The adapter never repairs or downgrades it.

## MessageEnvelope and classification

A valid `speak` result maps to the existing pending MessageEnvelope:

- `runtime_decision=speak`;
- `candidate_output=proposal_text`;
- `candidate_claim_type=task_request` for
  `check|measurement|follow_up`, otherwise `team_signal`;
- exact confidence/source refs;
- `publication_state=pending_classification` and
  `consumable_by_agents=false`.

The service then calls the canonical project classifier. Classification
persistence is evidence-only; it performs no automatic downstream dispatch.
Because the validated envelope and persisted classification both identify
canonical `origin_agent_id=companion`, the orchestrator MUST derive the exact
shared `ClassificationConsumerRouteV1=companion_governance_hold` and MUST NOT
accept a caller/provider-selected route.

Under that hold:

- Task effect requires persisted `safe_task_request` with the exact same kind;
- `discussion_only|none` requires persisted `safe_information`;
- `physical_action|blocked_uncertain`, mismatched kind, classifier conflict,
  persistence failure, or current guard denial produces no governance row.

The pending envelope/classification is routing evidence, not proposal,
decision, Task, Safety, or Plant-state authority.
Even a matching result permits only `persist_companion_proposal`: it produces
zero FT-008 Bus/UI candidate publication, zero generic block/Safety-status
projection, zero FT-011 Safety decision, and zero FT-012 classified-message
Task. Provider result/proposal/rationale text is not looped back through Bus or
UI Feed as agent input by this run. This does not restrict the strict typed
governance records explicitly allowed in `CompanionProviderRequestV1`.

## Governance persistence handoff

After model I/O, audit, and classification, the runtime repeats current
session/account/membership/Plant/grant checks. On an allowed route it calls
`persist_companion_proposal` with only:

- current ActorContext and target/new issue intent;
- validated model fields;
- run/message/classification ids and exact source refs;
- canonical request fingerprint.

The governance data spec owns locking, supersede/attention reuse, focus,
projection, Timeline, uniqueness, and commit. An archive/revoke/version race
writes nothing. Restore never replays a denied run; a new explicit command and
run id are required.

Classification retry, process restart, restore, and reconciliation return or
inspect evidence only; none may invoke a suppressed ordinary dispatcher. A
later approved DecisionRecord is a separate human authority and may invoke the
`governance_decision` ordinary-task branch and/or guarded compact
DecisionRecord Bus-fact route under their own current guards.

## `CompanionRunResultV1`

Internal orchestration returns exactly:

- `schema_version=1`, `run_id`;
- nullable common strict `runtime_outcome`; it is null only for the committed
  `proposal_duplicate` branch, which does not invoke or replay Agent Runtime;
- `route_status=proposal_created|proposal_duplicate|not_governable|silent|failed`;
- nullable `classification_ref`, `issue_ref`, `attention_ref`, `proposal_ref`;
- nullable `reason_code=no_material_output|insufficient_evidence|
  physical_action_not_allowed|classification_uncertain|
  classification_mismatch`;
- nullable stable `failure_code` from the closed failures below;
- nullable `failure_stage=runtime|classification|governance`.

| Route status | Common outcome | Refs | Reason / failure | Failure stage |
|---|---|---|---|---|
| `proposal_created` | `envelope_ready` | classification plus all governance refs present | null / null | null |
| `proposal_duplicate` | null | committed classification plus all governance refs present | null / null | null |
| `not_governable` | `envelope_ready` | classification present; governance refs null | one exact physical/uncertain/mismatch reason / null | null |
| `silent` | `model_silent` | all refs null | exact common model-silence reason / null | null |
| `failed` at runtime | common failure/denial | all refs null | null / exact common runtime failure | `runtime` |
| `failed` at classification | `envelope_ready` | governance refs null; classification null on conflict/persistence/guard failure | null / exact classification failure | `classification` |
| `failed` at governance | `envelope_ready` | matching classification present; governance refs null | null / exact governance failure | `governance` |

`not_governable` never records candidate/proposal text and never falls through
to an ordinary classification consumer. Failure or denial is
never relabeled silence. `proposal_duplicate` is reconstructed only from the
committed proposal/classification identities and canonical request
fingerprint. Even when reached after a losing concurrent attempt, its current
call outcome is discarded rather than persisted or returned as the winner's
outcome; sanitized runtime audit remains the evidence that provider I/O
occurred.

## Executor and trigger policy

- Only the explicit protected HTTP command invokes this runtime.
- `companion` and `safety_gate` each use their own provider-neutral executor
  seam. Current production remains unbound until future endpoint selection.
- A deterministic non-silent run invokes one explicitly injected Companion
  fake/spy executor and one explicitly injected Safety classifier fake/spy;
  neither seam may borrow or fall back to the other.
- There is no default, fallback, fake/canned product result, model retry that
  changes binding, scheduler, worker, startup invocation, event listener, or
  refresh side effect.
- Provider I/O is outside DB transactions. Logs, Timeline, evidence, and HTTP
  responses exclude request/result bodies, proposal/rationale text, prompts,
  credentials, auth state, raw exceptions, hidden reasoning, and local paths.

## Stable failures

The closed `failure_code` union is:

- common runtime: `AGENT_CONTEXT_DENIED|AGENT_RUNTIME_NOT_CONFIGURED|
  AGENT_PROVIDER_FAILED|AGENT_OUTPUT_INVALID|AGENT_PUBLICATION_BLOCKED|
  AGENT_AUDIT_FAILED`;
- classification authority:
  `SAFETY_CLASSIFICATION_CONFLICT|SAFETY_CLASSIFICATION_GUARD_DENIED|
  SAFETY_CLASSIFICATION_PERSISTENCE_FAILED`;
- governance authority:
  `COMPANION_COMMAND_FORBIDDEN|COMPANION_PLANT_NOT_ACTIVE|
  COMPANION_ISSUE_NOT_OPEN|COMPANION_PROPOSAL_NOT_CURRENT|
  COMPANION_VERSION_CONFLICT|COMPANION_EFFECT_INVALID|
  COMPANION_READ_INCONSISTENT|COMPANION_AUDIT_FAILED|
  COMPANION_PERSISTENCE_FAILED`.

`SAFETY_CLASSIFIER_NOT_CONFIGURED|SAFETY_CLASSIFIER_PROVIDER_FAILED|
SAFETY_CLASSIFIER_OUTPUT_INVALID` produce the canonical persisted
`blocked_uncertain` evidence when its current write guard succeeds; the
Companion result is then successful `not_governable` with
`reason_code=classification_uncertain`, not `failed`. Classification
kind/effect mismatch is `not_governable/classification_mismatch`, and a
physical classification is `not_governable/physical_action_not_allowed`.
None creates a proposal or Task. The HTTP contract owns the total public
translation while retaining distinct Agent Runtime audit and governance
Timeline audit identities.

## Verification

- Strict request/result tests prove exact union/order, target matrix, bounds,
  effect/task-text matrix, unknown-field rejection, source-ref subset, pending
  envelope mapping, and orchestration nullability.
- Outbound spies prove only authorized PostgreSQL Plant/issue/check-in/
  measurement fields cross egress; an existing-issue request includes exactly
  the persisted matching `companion_issue.summary_text`, a new-issue request
  includes none, and every auth/UI/Bus/Timeline/attention/proposal/rationale/
  decision/caller field is absent.
- Integration tests prove only explicit POST invokes the model; GET, refresh,
  domain event, Task completion, startup, and reconciliation do not.
- Current-guard tests cover session/membership/grant change, archive, issue
  version race, same-run duplicate concurrency, distinct-run serial
  supersede/refocus, classifier mismatch, sequential
  duplicate with `runtime_outcome=null` and no second provider/envelope call,
  concurrent duplicate single effect with no persisted runtime receipt, and
  zero write on every failed/non-governable path.
- Consumer-route tests prove matching Companion safe information creates no
  FT-008 candidate publication, matching Companion safe task creates no FT-012
  Task, held physical/blocked/mismatch/failure creates no ordinary downstream
  row, retry/restore/reconciliation does not replay one, and the only accepted
  matching handoff is guarded proposal persistence.
- Executor tests prove explicit fake/spy injection, unbound production,
  timeout/error/invalid-output paths, no fallback/fake production behavior,
  redaction, and compatibility with the existing Agent Runtime outcome matrix.
- Deterministic integration uses authorized PostgreSQL Plant/check-in/
  measurement data, calls each test seam exactly once, and persists one
  matching classification plus one current proposal without granting direct
  DecisionRecord/Task/action authority.
- Real Companion and classifier responses are deferred to the single provider
  runbook milestone after endpoint selection and are not current closure
  evidence.
