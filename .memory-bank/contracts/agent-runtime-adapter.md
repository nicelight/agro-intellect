---
description: Project-owned agent runtime adapter, invocation, validation, and publication-handoff contract.
status: active
type: interface_contract
last_updated: 2026-07-18
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/domains/auth/session-storage.md
  - .memory-bank/domains/identity/account-membership.md
  - .memory-bank/domains/plant-operations.md
  - .memory-bank/states/auth/session-lifecycle.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
---
# Agent Runtime Adapter

## Scope

This contract defines the project-owned boundary around one real model-backed
product-agent invocation. The boundary accepts already authorized Plant
context, calls an execution adapter, validates the candidate result, performs a
fresh publication guard, and returns one strict `AgentRuntimeOutcomeV1`. A
non-silent success carries a validated pre-safety `MessageEnvelope`; it is a
handoff to the project-owned classifier, not Bus/UI publication authority.

Agno and a configured model provider are execution dependencies only. They do
not own runtime decisions, authorization, audit semantics, MessageEnvelope, or
Plant state.

## Out of scope

- BusEventEnvelope storage, Bus context queries, and UI Feed projection; FT-008
  owns those concerns.
- Vision-specific input and observation semantics are owned by
  [.memory-bank/contracts/vision-observation-runtime.md](vision-observation-runtime.md),
  which composes this outcome/authorization/audit boundary without widening
  generic `ProviderRequestV1`.
- Plant State trust-record input and structured assessment semantics are owned
  by [.memory-bank/contracts/plant-state-runtime.md](plant-state-runtime.md)
  under the same shared outcome/authorization/audit boundary.
- Hydroponics Advisor missing-data policy; FT-010 owns it.
- Companion IssueStack/proposal input and orchestration semantics are owned by
  [.memory-bank/contracts/companion-runtime.md](companion-runtime.md), which
  composes this outcome/authorization/audit boundary without widening generic
  `ProviderRequestV1`.
- Safety classifier implementation and action approval; the shared
  `SafetyClassificationResultV1` wire contract lives in the Safety Action
  Lifecycle, while FT-011 owns the concrete classifier/policy implementation.
- HTTP routes or a new public agent API.
- Agno memory, session history, Team coordination, tools, RAG, fallback models,
  or provider-result persistence.

## Related specs

- [.memory-bank/contracts/message-envelope.md](message-envelope.md): exact
  validated pre-safety output handoff.
- [.memory-bank/contracts/agent-model-provider-profiles.md](agent-model-provider-profiles.md):
  provider/model binding, egress, credential, and no-fallback rules.
- [.memory-bank/contracts/agent-roster-bootstrap.md](agent-roster-bootstrap.md):
  canonical identities and post-commit Plant bootstrap handoff.
- [.memory-bank/contracts/access/actor-context.md](access/actor-context.md):
  authorization and safe context boundary.
- [.memory-bank/domains/auth/session-storage.md](../domains/auth/session-storage.md),
  [.memory-bank/domains/identity/account-membership.md](../domains/identity/account-membership.md),
  and [.memory-bank/states/auth/session-lifecycle.md](../states/auth/session-lifecycle.md):
  exact identity/session rows and validity rules reloaded after model I/O.
- [.memory-bank/contracts/agent-chat-bus.md](agent-chat-bus.md): downstream
  publication boundary.
- [.memory-bank/contracts/timeline-event.md](timeline-event.md): append-only
  audit event and ref.
- [.memory-bank/states/plants/plant-and-access-lifecycle.md](../states/plants/plant-and-access-lifecycle.md):
  active-Plant publication guard.

## Module boundary

The implementation lives under `backend/app/agent_runtime/` and exposes these
project-owned seams:

- `AgentRuntimeService`: owns the invocation flow and final outcome.
- `AgentDefinitionResolver`: returns only project-owned immutable definitions by
  id; callers cannot submit instructions or claim policy.
- `AgentInputAssembler`: loads and converts canonical PostgreSQL Plant evidence
  into the typed provider payload; callers cannot submit candidate records.
- `ModelExecutor`: narrow execution protocol returning provider output only to
  the project adapter.
- `ProviderBindingResolver` and `AgnoModelExecutorFactory`: resolve exactly one
  deployment binding and construct its production executor with no fallback.
- `RuntimeAuthorizationGuard`: reloads current session/account/membership,
  Plant, and grant authority after model execution and before an envelope may
  leave Agent Runtime.
- `TimelineAppender`: writes the canonical sanitized runtime audit event.
- `PlantAgentBootstrapService`: activates the static roster and builds
  deterministic post-commit introduction handoffs without model I/O.

Test definitions, assemblers, and executors may be supplied only through
explicit test dependency injection. Production composition MUST NOT select any
of them when data, model configuration, credentials, imports, or provider calls
fail.

## Agent definition

Each invocation uses a project-owned immutable `AgentDefinition` composed from
the canonical roster and its owning feature policy:

- `agent_id`: lowercase slug matching `[a-z][a-z0-9_]{2,63}`;
- `competence`: one concise project-owned competence statement;
- `instructions`: project-owned instructions, never raw UI/chat content;
- `allowed_candidate_claim_types`: a non-empty subset of the MessageEnvelope candidate-claim
  catalog;
- `output_schema_version`: exactly `1` for this contract version.

Callers cannot supply or override system instructions, provider/model choice,
tools, memory, output schema, or allowed claim types. FT-009 through FT-014 add
their competence policies without changing this execution boundary. The exact
eight identities and bootstrap metadata are defined in
`agent-roster-bootstrap.md`; FT-009 through FT-014 own detailed behavior and
triggers. A roster member without its owning-feature runtime policy and a
deployment model binding is not invocable and fails closed rather than
borrowing another agent's policy or binding.

An isolated test-only `runtime_contract_smoke` may exercise the production
provider executor and typed Plant-data path through the explicit test seam. It
is absent from production definition resolution and cannot satisfy a canonical
product-agent or REQ-011 competence criterion. Detailed acceptance remains
distributed to each owning feature in the RTM.

## Invocation input

`AgentRunCommand` contains only service-side identity and intent:

- `run_id`: application-generated UUIDv4, unique per attempt;
- `requested_at`: timezone-aware UTC timestamp;
- `agent_definition_id`: id resolved by `AgentDefinitionResolver`;
- `actor_context`: the already authenticated project ActorContext, retained
  service-side only;
- `plant_id`: requested Plant UUID.

Callers do not submit context mappings, source refs, prompts, instructions,
model ids, output schemas, or authorization snapshots.

`AgentInputAssembler` receives the service-side ActorContext and `plant_id`,
reuses the existing `build_authorized_plant_context`/Plant permission seam, and
loads the canonical Plant/check-in/measurement rows from PostgreSQL. It returns
the service-side safe authorization snapshot plus exactly one strict
`ProviderRequestV1`. This pre-call authorization snapshot never enters that
request and is not reused as the final envelope scope; the post-model guard
builds a fresh current scope.

`ProviderRequestV1` has exactly these fields; unknown fields at every nested
level are rejected:

- `schema_version=1`;
- `agent_definition`: strict object with `agent_id`, `competence`,
  `instructions`, ordered unique `allowed_candidate_claim_types`, and
  `output_schema={name=AgentModelResultV1,schema_version=1,strict=true}`;
- `records`: ordered array of 1 through 4 strict `AgentInputRecordV1` objects;
- `source_refs`: ordered unique array exactly equal, item for item, to the
  records' `source_ref` values.

No `run_id`, ActorContext, account/membership/role/grant field, authorization
scope, session provenance, model/provider selection, credential, arbitrary
metadata, or caller text exists in `ProviderRequestV1`. The provider adapter
binds the project-owned stack-native `AgentModelResultV1` schema named by the
descriptor; callers cannot replace or extend it.

Rules:

- The ActorContext `farm_id`, assembled authorization scope, Plant row, and
  every evidence row must agree.
- The pre-call permission snapshot must be `Plant.status=active` with
  `can_read=true` for `operation_kind=normal_read`.
- The production assembler, not the route/caller, creates candidates and passes
  them through ActorContext/PlantAccessGrant plus existing forbidden-source and
  auth-material checks.
- Only safe JSON values and source refs matching the existing
  `kind:identifier` grammar cross into the model input.
- ActorContext objects, session ids, tokens, cookies, headers, credentials,
  provider keys, UI Feed, raw chat, admin notices, and hidden reasoning never
  cross this boundary.
- The generic `ProviderRequestV1` has no governance record union. Registered
  agent-specific contracts may define an authorized typed governance subset;
  such input remains untrusted and non-authoritative and does not widen this
  generic request.
- Agent Runtime does not create a second generic context authority. It adds one
  exact PostgreSQL-to-typed-input assembler on top of the existing seam; typed
  Bus producer payloads and Bus context reconstruction remain FT-008 work.

## Typed input version 1

Every `AgentInputRecordV1` is exactly
`{record_type, source_ref, payload}`. UUIDs use lowercase canonical strings;
timestamps use UTC RFC 3339 strings. Unknown outer fields, record types, and
payload fields are rejected. The discriminated payloads are:

| `record_type` | `source_ref` | Exact `payload` |
|---|---|---|
| `plant` | `plant:<plant_id>` | `plant_id`, `status=active` |
| `daily_checkin` | `daily_checkin:<check_in_id>` | `check_in_id`, `observed_at`, `recorded_at`, `observation_state=observed|no_observation_provided`, `observation_text` as normalized 1..2000-code-point string only for `observed`, otherwise `null` |
| `manual_measurement` | `manual_measurement:<measurement_id>` | `measurement_id`, `measured_at`, `recorded_at`, `ph` as fixed two-decimal string or `null`, `ec_ms_cm` as fixed three-decimal string or `null`, `source_type=manual_user`, `trust_status=confirmed`; at least one value is non-null |

Rules:

- V1 order is exact: Plant first; latest completed daily check-in second when
  present; latest non-null pH row next when present; latest non-null EC row last
  when present. If one measurement row is latest for both pH and EC it appears
  once in the pH position and is omitted from the EC position.
- The real-model FT-007 smoke requires at least one assembled check-in or
  measurement record; it cannot pass with a synthetic Plant-only payload.
- `plant_id` must equal the service-side authorized scope; each record id must
  equal its source-ref identifier.
- Timestamps are timezone-aware UTC; pH/EC values use the canonical normalized
  PostgreSQL values, not user text or timeline summaries.
- Latest records use deterministic PostgreSQL ordering: check-ins by
  `(recorded_at DESC, check_in_id DESC)` and measurements independently by
  `(measured_at DESC, measurement_id DESC)` for non-null pH and EC.
- At most four records cross the provider boundary in V1.
- Records are built from PostgreSQL/read-model source objects. UI Feed,
  timeline replay, HTTP response bodies, manifests, raw chat, and provider
  output cannot be adapted into these types.
- Agent Runtime never truncates, chunks, or summarizes `observation_text` to
  make it fit provider input. If an existing persisted row violates the current
  2000-code-point Plant Operations contract, assembly returns the stable
  pre-invocation `outcome_kind=context_denied` result with
  `reason_code=input_contract_violation` and makes no provider or audit call.
- Photo binary/metadata is not in FT-007 input v1. FT-009 now defines its
  vision-specific typed boundary in `vision-observation-runtime.md`; generic
  `ProviderRequestV1` remains text/domain-record only.
- `ProviderRequestV1.source_refs` is derived internally in record order and is
  exactly equal to the typed-record refs. A non-silent model result uses a
  non-empty unique subset in the same relative order as the request;
  model-declared silence uses an empty list.

## Model execution result

`AgentModelResultV1` is one strict object with exactly
`{schema_version, runtime_decision, candidate_claim_type, candidate_output,
confidence, source_refs, reason_code}` and `schema_version=1`. Unknown fields
are rejected. Its matrix is:

| Decision | Candidate claim | Output/confidence/refs | Reason |
|---|---|---|---|
| `speak` | `observation|hypothesis|recommendation|task_request|team_signal` | opaque untrusted normalized text 1..2000 code points; confidence `0..1` except nullable for `team_signal`; 1..4 request refs | `null` |
| `clarify` | `clarification` | opaque untrusted normalized text 1..2000; confidence `null`; 1..4 request refs | `null` |
| `escalate` | `safety_block|team_signal` | opaque untrusted normalized text 1..2000; confidence `null`; 1..4 request refs | `null` |
| `silent` | `null` | output and confidence `null`; refs exactly `[]` | `no_material_output|insufficient_evidence` |

The candidate claim is untrusted model data. The provider result has no
`requires_human_approval`, `safety_gate_route`, final physical-action class, or
publication flag. For every non-silent result Agent Runtime creates only a
MessageEnvelope with `publication_state=pending_classification`; the project-
owned Safety & Task Loop classifier decides the final route.

`candidate_output` is not parsed as Markdown, HTML, a prompt, an instruction,
or a command. Such syntax is accepted unchanged when the strict schema,
decision/claim matrix, refs, normalization, and 1..2000-code-point bound are
valid. It remains opaque data and cannot alter runtime routing or authority.

Provider metadata, messages, traces, tool calls, response objects, hidden
reasoning, and parser diagnostics remain transient inside the executor. The
adapter copies only the validated object above.

## Invocation flow

1. Resolve the definition and assemble `ProviderRequestV1`; a pre-call scope or
   strict-record failure returns `context_denied` with no provider/audit call.
   Authorization/scope denial uses `reason_code=context_denied`; a selected
   authoritative record outside the strict V1 contract uses
   `reason_code=input_contract_violation`.
2. Resolve exactly one deployment binding; unavailable composition returns
   `runtime_not_configured` with no provider/audit call.
3. Invoke the configured real model outside every database transaction. A call
   failure becomes the pending `provider_failed` outcome.
4. Parse `AgentModelResultV1`. Schema, decision/claim matrix, ref, type,
   normalization, or length failure becomes the pending `output_invalid`
   outcome. Markup- or prompt-looking syntax alone does not.
5. After any schema-valid provider result, reload the original LocalSession by
   `session_id`, require it unexpired/unrevoked and bound to the same active
   Account, reload the exact active Membership in the same Farm, then resolve
   current same-Farm active Plant/grant permission. Current role/grant state replaces
   the stale snapshot and supplies the MessageEnvelope authorization scope. Any
   denial becomes `publication_guard_denied`; no
   synthetic `silent` decision is invented.
6. For an authorized valid non-silent candidate, create the pending-safety
   MessageEnvelope. For a valid model-declared silent candidate, create no
   envelope.
7. Append exactly one sanitized `agent_runtime_decided` event for every request
   that reached provider I/O, including provider failure, invalid output, model
   silence, and guard denial. Safe `actor_ref` is exactly the authenticated
   service-side `account_id`, `membership_id`, and request-time `role_preset`;
   session/auth data is absent.
8. Audit failure overrides the pending result with `audit_failed` and returns
   no envelope/event ref. Otherwise return the matching strict outcome.

The FT-007 guard is a pre-handoff check, not publication atomicity. Agent
Runtime holds no database lock across the provider call, filesystem audit
append, or caller return. `envelope_ready` means schema-valid transient handoff,
not current authority to publish.

The downstream FT-008 publisher must repeat session/membership/Plant/grant
authorization and `Plant.status=active` in the same transactional/locking
boundary as its Bus/UI write. If archive/revoke occurs after the FT-007 guard,
FT-008 rejects the handoff; the envelope remains transient/audit-only and is
never replayed after restore. Until FT-008 exists, FT-007 performs no Bus/UI
publication, so this later race window cannot create an operational event.

## AgentRuntimeOutcomeV1

Every expected branch returns one strict object with exactly these fields;
unknown fields are rejected and none is conditionally omitted:

- `schema_version=1`, `run_id`, and discriminant `outcome_kind`;
- `status=envelope_ready|silent|blocked|failed`;
- nullable `final_decision=speak|silent|clarify|escalate`;
- `reason_code` and nullable stable `error_code`;
- nullable `message_envelope`, `event_ref`, and safe
  `model_ref=provider_profile:model_id`;
- `provider_call_status=not_attempted|completed|failed`;
- `audit_status=not_attempted|appended|failed`.

| `outcome_kind` | Status / final decision | Reason / error | Envelope / event / model | Provider / audit |
|---|---|---|---|---|
| `envelope_ready` | `envelope_ready` / candidate `speak|clarify|escalate` | `envelope_ready` / `null` | present / present / present | `completed` / `appended` |
| `model_silent` | `silent` / `silent` | `no_material_output|insufficient_evidence` / `null` | null / present / present | `completed` / `appended` |
| `context_denied` | `blocked` / null | `context_denied|input_contract_violation` / `AGENT_CONTEXT_DENIED` | null / null / null | `not_attempted` / `not_attempted` |
| `runtime_not_configured` | `failed` / null | `runtime_not_configured` / `AGENT_RUNTIME_NOT_CONFIGURED` | null / null / null | `not_attempted` / `not_attempted` |
| `provider_failed` | `failed` / null | `provider_failed` / `AGENT_PROVIDER_FAILED` | null / present / present | `failed` / `appended` |
| `output_invalid` | `blocked` / null | `output_invalid` / `AGENT_OUTPUT_INVALID` | null / present / present | `completed` / `appended` |
| `publication_guard_denied` | `blocked` / null | `publication_guard_denied` / `AGENT_PUBLICATION_BLOCKED` | null / present / present | `completed` / `appended` |
| `audit_failed` | `failed` / null | `audit_failed` / `AGENT_AUDIT_FAILED` | null / null / present | `completed|failed` / `failed` |

`message_envelope` exists only for `envelope_ready`; `event_ref` exists only
after a successful append. An `audit_failed` result may preserve whether the
real provider call completed or failed but never exposes the discarded pending
outcome. Its `model_ref` is present because audit is attempted only after a
configured provider call has started. No failure/denial branch may use
`status=silent`, `final_decision=silent`, or a model-silence reason. Expected
branches do not use exceptions as the service contract;
unexpected internal exceptions are redacted and fail closed at the module
boundary without inventing another outcome kind.

## Failure catalog

| Code | Condition | Result |
|---|---|---|
| `AGENT_CONTEXT_DENIED` | Input scope is missing, inactive, mismatched, unauthorized, or contains a selected authoritative record that violates the strict V1 input bounds before invocation. | No provider call and no MessageEnvelope. No `agent_runtime_decided` event is created because model execution did not begin. |
| `AGENT_RUNTIME_NOT_CONFIGURED` | Production model binding, egress opt-in, provider dependency/credential, competence policy, or approved OAuth broker is unavailable. | Safe failure; no fake/cross-provider fallback and no provider call. |
| `AGENT_PROVIDER_FAILED` | Timeout, rate limit, network, provider, or Agno execution failure. | Audited `provider_failed`; no final decision or MessageEnvelope. |
| `AGENT_OUTPUT_INVALID` | Candidate output fails schema, decision/claim, refs, type, normalization, or length validation. Markup- or prompt-looking syntax alone is not invalid. | Audited `output_invalid`; no final decision or MessageEnvelope. |
| `AGENT_PUBLICATION_BLOCKED` | Current session/Account/Membership/Plant/grant recheck fails after model execution. | Audited `publication_guard_denied`; no final decision, MessageEnvelope, or replay. |
| `AGENT_AUDIT_FAILED` | Sanitized timeline append fails. | Fail closed; no MessageEnvelope handoff is returned. |

Errors exposed outside the module use only the stable code and a generic safe
message. Raw exceptions, provider payloads, prompts, credentials, absolute
local paths, and parser details are never returned or logged.

## Storage decision

FT-007 adds no provider-output, prompt-history, model-session, or agent-run
table. MessageEnvelope is the transient handoff; `agent_runtime_decided` is
audit/export evidence. FT-008 owns any downstream projection persistence.

## Production binding decision

Provider profiles own model binding, egress, credentials, and fail-closed
`chatgpt_oauth`; Roster Bootstrap owns post-commit introductions. Execution
still needs an explicit DeepSeek/Gemini model id, matching credential, and
egress opt-in.

For that smoke, successful real transport is proven by exactly one of two
audited terminal results: `outcome_kind=envelope_ready` with a valid pending
MessageEnvelope, or strict `outcome_kind=model_silent` with
`reason_code=no_material_output|insufficient_evidence`.
A runtime failure, invalid output, current-publication denial, pre-call denial,
missing configuration, or audit failure cannot be reclassified as acceptable
silence and always fails the smoke.

## Verification

The canonical [Agent Runtime testing spec](../testing/agent-runtime.md) covers:

- ProviderRequest/input allowlists, order, observation bounds, and auth absence;
- model/envelope/outcome/event matrices, acceptance of schema-valid opaque
  markup-/prompt-looking candidate text, current guard, and audit failure;
- provider composition, no fallback, and the exact smoke rule above;
- post-commit batch handoff without FT-008 implementation claims.

Downstream competence features retain their own REQ-011 acceptance.
