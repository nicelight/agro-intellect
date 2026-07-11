---
description: Project-owned agent runtime adapter, invocation, validation, and publication-handoff contract.
status: active
type: interface_contract
last_updated: 2026-07-11
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/domains/plant-operations.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
---
# Agent Runtime Adapter

## Scope

This contract defines the project-owned boundary around one real model-backed
product-agent invocation. The boundary accepts already authorized Plant
context, calls an execution adapter, validates the candidate result, performs a
fresh publication guard, and returns either a validated `MessageEnvelope` plus
audit ref or an audit-only outcome.

Agno and a configured model provider are execution dependencies only. They do
not own runtime decisions, authorization, audit semantics, MessageEnvelope, or
Plant state.

## Out of scope

- BusEventEnvelope storage, Bus context queries, and UI Feed projection; FT-008
  owns those concerns.
- Vision-specific input and observation semantics; FT-009 owns them.
- Hydroponics Advisor missing-data policy; FT-010 owns it.
- Safety classification and action approval; FT-011 owns them.
- HTTP routes or a new public agent API.
- Agno memory, session history, Team coordination, tools, RAG, fallback models,
  or provider-result persistence.

## Related specs

- [.memory-bank/contracts/message-envelope.md](message-envelope.md): exact
  publishable output.
- [.memory-bank/contracts/agent-model-provider-profiles.md](agent-model-provider-profiles.md):
  provider/model binding, egress, credential, and no-fallback rules.
- [.memory-bank/contracts/agent-roster-bootstrap.md](agent-roster-bootstrap.md):
  canonical identities and post-commit Plant bootstrap handoff.
- [.memory-bank/contracts/access/actor-context.md](access/actor-context.md):
  authorization and safe context boundary.
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
- `allowed_claim_types`: a non-empty subset of the MessageEnvelope claim
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
the typed input records below plus their derived safe authorization scope. The
model input receives only that safe scope and those records; the ActorContext
object and its session provenance never cross the executor boundary.

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
  provider keys, UI Feed, raw chat, admin notices, hidden reasoning, and
  unapproved proposal content never cross this boundary.
- Agent Runtime does not create a second generic context authority. It adds one
  exact PostgreSQL-to-typed-input assembler on top of the existing seam; typed
  Bus producer payloads and Bus context reconstruction remain FT-008 work.

## Typed input version 1

Before provider invocation, each assembler output must validate as exactly one
`AgentInputRecordV1`. Unknown record types and unknown payload fields are
rejected:

| `record_type` / source-ref kind | Exact payload | Canonical source |
|---|---|---|
| `plant` | `plant_id`, `status=active` | persisted Plant identity/status |
| `daily_checkin` | `check_in_id`, `observed_at`, `recorded_at`, `observation_state`, optional non-blank `observation_text` | `.memory-bank/domains/plant-operations.md` |
| `manual_measurement` | `measurement_id`, `measured_at`, `recorded_at`, optional `ph`, optional `ec_ms_cm`, `source_type=manual_user`, `trust_status=confirmed`; at least one measurement value is present | `.memory-bank/domains/plant-operations.md` |

Rules:

- V1 assembly contains exactly one `plant:<plant_id>` record, the latest
  completed daily check-in when one exists, the latest pH measurement when one
  exists, and the latest EC measurement when one exists. If one measurement
  row is latest for both values it appears once.
- The real-model FT-007 smoke requires at least one assembled check-in or
  measurement record; it cannot pass with a synthetic Plant-only payload.
- `plant_id` must equal the authorized scope; check-in and measurement ids must
  equal their source-ref identifiers.
- Timestamps are timezone-aware UTC; pH/EC values use the canonical normalized
  PostgreSQL values, not user text or timeline summaries.
- Latest records use deterministic PostgreSQL ordering: check-ins by
  `(recorded_at DESC, check_in_id DESC)` and measurements independently by
  `(measured_at DESC, measurement_id DESC)` for non-null pH and EC.
- At most four records cross the provider boundary in V1.
- Records are built from PostgreSQL/read-model source objects. UI Feed,
  timeline replay, HTTP response bodies, manifests, raw chat, and provider
  output cannot be adapted into these types.
- Photo binary/metadata is not in FT-007 input v1; FT-009 must define its
  vision-specific typed boundary before sending real photo data to a model.
- The request `source_refs` given to the executor is derived internally and is
  exactly equal to the set of typed-record refs. Model output refs must be a
  non-empty subset of that set for any envelope-producing decision.

## Model execution result

The model is instructed to return one object with unknown fields rejected:

- `runtime_decision`: `speak | silent | clarify | escalate`;
- `claim_type`: one MessageEnvelope claim type, or `null` only for `silent`;
- `consumable_output`: concise plain text, or `null` only for `silent`;
- `confidence`: number from `0` through `1`, or `null` where the envelope
  contract permits it;
- `source_refs`: a subset of request `source_refs`;
- `requires_human_approval`: boolean;
- `safety_gate_route`: `not_applicable | required`;
- `reason_code`: `no_material_output | insufficient_evidence` for `silent`,
  otherwise `null`.

Provider metadata, messages, traces, tool calls, response objects, hidden
reasoning, and parser diagnostics remain transient inside the executor. The
adapter copies only the validated object above.

## Invocation flow

1. Resolve the project-owned definition and assemble typed authorized input
   from current PostgreSQL records.
2. Resolve exactly one deployment binding and invoke its configured real Agno
   model outside any database transaction through `ModelExecutor`.
3. Parse and validate the candidate result with the MessageEnvelope decision
   and claim matrix.
4. Use `RuntimeAuthorizationGuard` to reload the original session/account,
   membership, same-Farm Plant, and PlantAccessGrant state; then resolve current
   `normal_read` permission. The original ActorContext snapshot is insufficient.
5. If current permission is active and authorized, create a new
   MessageEnvelope for `speak`, `clarify`, or `escalate`; `silent` creates no
   envelope.
6. If the Plant became archived or authorization changed, downgrade any
   candidate to final `silent`, reason `publication_guard_denied`, and create no
   MessageEnvelope.
7. Append exactly one `agent_runtime_decided` timeline event for every accepted
   request that reached model execution. Its safe `actor_ref` is exactly
   `account_id`, `membership_id`, and `role_preset` from the service-side
   identity; session ids and auth provenance are excluded.
8. Return `AgentRuntimeOutcome` only after the audit append succeeds.

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

## AgentRuntimeOutcome

The service returns:

- `run_id`;
- `final_decision`;
- `status`: `envelope_ready | silent | blocked | failed`;
- optional validated `message_envelope`;
- one timeline `event_ref` when audit append succeeded;
- safe `reason_code`;
- safe `model_ref` in `provider_profile:model_id` form only for a real configured
  executor.

The service-level `reason_code` is exactly one of:

- `envelope_ready` for a successful handoff;
- `no_material_output` or `insufficient_evidence` for explicit model silence;
- `provider_failed` for provider/executor failure;
- `output_invalid` for adapter/schema rejection;
- `publication_guard_denied` for post-execution Plant/authorization denial.

Pre-invocation `context_denied` and `runtime_not_configured`, plus terminal
`audit_failed`, are stable error outcomes rather than timeline payload reasons.

`message_envelope` is present only when `status=envelope_ready` and the final
decision is `speak`, `clarify`, or `escalate`. It is absent for every other
status.

## Failure catalog

| Code | Condition | Result |
|---|---|---|
| `AGENT_CONTEXT_DENIED` | Input scope is missing, inactive, mismatched, or unauthorized before invocation. | No provider call and no MessageEnvelope. Existing authorization audit owns the denial. |
| `AGENT_RUNTIME_NOT_CONFIGURED` | Production model binding, egress opt-in, provider dependency/credential, competence policy, or approved OAuth broker is unavailable. | Safe failure; no fake/cross-provider fallback and no provider call. |
| `AGENT_PROVIDER_FAILED` | Timeout, rate limit, network, provider, or Agno execution failure. | Audit-only `failed`; no MessageEnvelope. |
| `AGENT_OUTPUT_INVALID` | Candidate output fails schema, decision/claim, refs, content, or safety validation. | Audit-only `blocked`; no MessageEnvelope. |
| `AGENT_PUBLICATION_BLOCKED` | Current Plant/authorization recheck fails after model execution. | Audit-only final `silent`; no MessageEnvelope and no replay. |
| `AGENT_AUDIT_FAILED` | Sanitized timeline append fails. | Fail closed; no MessageEnvelope handoff is returned. |

Errors exposed outside the module use only the stable code and a generic safe
message. Raw exceptions, provider payloads, prompts, credentials, absolute
local paths, and parser details are never returned or logged.

## Storage decision

FT-007 adds no PostgreSQL table for provider output, prompt history, model
sessions, or runtime decisions. The decision is transient; a validated
MessageEnvelope becomes the downstream handoff, and the sanitized
`agent_runtime_decided` timeline event is the required audit/export evidence.

This is intentionally `not_applicable` for mutable persistence: no current
requirement needs resumable agent runs, replay, provider history, or mutable
agent-run state. FT-008 may persist its own Bus/UI projections without turning
timeline or raw provider output into runtime authority.

## Production binding decision

- The runtime recognizes explicit `deepseek`, `gemini`, and
  `chatgpt_oauth` profiles.
- Deployment selects model ids per enabled canonical agent; the SDD defines no
  default model and planning is not blocked while those ids remain unselected.
- External egress of the authorized typed input is owner-approved and still
  requires the explicit runtime opt-in defined by the provider contract.
- DeepSeek and Gemini use their native Agno adapters. `chatgpt_oauth` is a
  recognized fail-closed external broker port because no approved generic
  third-party ChatGPT OAuth runtime contract exists; FT-007 must not read Codex
  credentials or pretend API-key auth is ChatGPT OAuth.
- Plant creation activates the eight-member canonical roster and hands
  deterministic introductions to a downstream sink only after commit; it does
  not invoke a model. Visible/durable chat publication remains downstream and
  is not silently implemented in FT-007.

These decisions close the design gate. Execution still needs at least one
explicit DeepSeek or Gemini model id and matching credential before the
non-skipped real-provider smoke can pass.

## Verification

Tests must prove:

- only authorized active-Plant safe context reaches the executor;
- production input is assembled from PostgreSQL rows rather than caller-built
  safe mappings, and executor refs equal the typed-record ref set;
- the post-model guard reloads current session/account/membership/Plant/grant
  authority while service-only identity never enters model input;
- every decision/claim combination and MessageEnvelope field is validated;
- silent, invalid, provider-failed, and publication-guard-denied outcomes create
  no MessageEnvelope;
- archive during the provider call yields audit-only behavior and restore does
  not replay the candidate;
- timeline audit contains safe metadata only and append failure blocks handoff;
- an archive/revoke before the FT-007 guard blocks the envelope, while an
  archive/revoke after it is blocked by the FT-008 transactional publisher and
  is never replayed;
- production composition has no fake, mock, hardcoded, or stub fallback;
- provider resolution follows the explicit profile/binding contract, keeps
  model selection out of caller input, and never cross-falls back;
- DeepSeek and Gemini construct native production adapters, while unconfigured
  `chatgpt_oauth` fails before credential discovery or network I/O;
- Plant bootstrap runs after commit, produces the exact deterministic roster
  handoff, performs no model call, and never makes introductions agent context;
- a credentialed real-model smoke processes actual authorized Plant data
  through the isolated test-only definition and reports a non-skipped DeepSeek
  or Gemini result before FT-007 transport evidence is accepted; downstream
  competence features retain their own REQ-011 acceptance.
