---
description: Authorized model input and structured assessment contract for Plant State Agent.
status: active
type: interface_contract
last_updated: 2026-07-29
source_of_truth:
  - .memory-bank/features/FT-009-vision-observation-plant-state-trust.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/domains/plant-state-observations.md
  - .memory-bank/states/plant-state-trust.md
---
# Plant State Runtime

## Scope

This contract defines the canonical `plant_state` product-agent invocation over
authorized PostgreSQL trust records. It produces a structured candidate for one
trend, conflict, or unknown assessment and the common pending MessageEnvelope.
It does not persist the assessment, confirm/reject evidence, publish Bus/UI,
classify physical wording, or create tasks/actions.

## Command and module boundary

Implementation lives under `backend/app/plant_state/` and reuses Agent Runtime
provider binding, current authorization guard, timeline audit, outcome, and
MessageEnvelope semantics.

The internal command contains only `run_id`, request time, ActorContext, and
`plant_id`. Callers cannot submit records, refs, instructions, provider/model,
assessment, output schema, or authorization snapshot.

## Provider request version 1

`PlantStateProviderRequestV1` is constructed from exactly:

- `schema_version=1`;
- canonical `agent_definition` for `agent_id=plant_state`, with allowed
  decisions `speak|clarify|silent` and output schema
  `PlantStateModelResultV1` version 1;
- `records`: 1..4 strict `PlantStateInputRecordV1` objects;
- read-only `source_refs` derived exactly from the records in order. Callers
  cannot supply it independently; the outbound compatibility payload may
  include the derived array.

The assembler selects the latest 1..4 non-rejected PostgreSQL records for the
same currently readable active Plant, then orders them oldest to newest. Each
record is exactly `{record_type=plant_state_record, source_ref, payload}` with
`source_ref=plant_state_record:<state_record_id>` and payload fields:

- `state_record_id`, `observation_key`, nullable `polarity`, nullable
  `severity`, nullable `assessment_kind`, nullable `direction`, `trust_status`, `observed_at`,
  `recorded_at`, `confidence`, and ordered `source_refs`.

Only `unknown|observed|hypothesis|conflicting|confirmed` sources are eligible.
Confirmation actor ids/source, message/run ids, summary text from UI, UI Feed,
raw chat, timeline replay, provider history, hidden reasoning, ActorContext,
session/account/membership/grant fields, and credentials are forbidden.

An empty eligible set returns `context_denied` with
`reason_code=context_denied` and no provider/audit call. Invalid or
cross-Plant rows return `input_contract_violation`.

## Model result version 1

`PlantStateModelResultV1` contains exactly:

- `schema_version=1`;
- `runtime_decision=speak|clarify|silent`;
- nullable `assessment_kind=trend|conflict|unknown`;
- nullable `observation_key` from the Vision Observation catalog;
- nullable `direction=increasing|decreasing|stable|mixed|not_applicable`;
- nullable normalized `summary` of 1..1000 Unicode code points;
- nullable finite `confidence` in `[0,1]`;
- `source_refs`;
- nullable `reason_code`.

Matrix:

| Decision | Assessment | Refs | Reason |
|---|---|---|---|
| `speak` | all fields required; trend uses non-`not_applicable`, conflict/unknown use `not_applicable` | 1..4 unique request refs in request order | null |
| `clarify` | kind=`unknown`, direction=`not_applicable`, key/summary required, confidence null | 1..4 request refs | null |
| `silent` | all assessment fields null | `[]` | `no_material_output|insufficient_evidence` |

Unknown fields, recommendation/action/diagnosis values, confirmation or Safety
fields, refs outside the authoritative request refs derived from records, and
invalid combinations reject the entire result.

## Structural validation and handoff

Before an assessment candidate is returned, project code reloads the referenced
records and applies the structural trend/conflict/unknown rules from
`plant-state-observations.md`. Model labels and confidence cannot override
those checks.

A valid `speak` result creates one standard pending MessageEnvelope with
`candidate_claim_type=hypothesis`, the validated summary/confidence, and the
same ordered refs. A valid `clarify` result creates the standard clarification
envelope. The strict `PlantStateAssessmentCandidateV1` carries the validated
assessment fields plus run/message/Plant identity and remains non-authoritative
until matching `safe_information` classification and guarded persistence.

## Executor and failure behavior

The text-only definition uses the shared provider-neutral executor seam.
Production remains unbound until future endpoint selection and has no default,
fake/canned result, or fallback. Executor I/O occurs outside DB transactions;
current session/membership/grant/active-Plant authority is reloaded afterward.
Archive/revoke, invalid result, provider failure, or audit failure returns the
matching shared closed outcome with no candidate/persistence and no replay.

Provider request/response bodies, summaries, prompts, and hidden reasoning are
not persisted or copied into errors/evidence. Safe evidence follows the common
Agent Runtime redaction contract.

## Verification

Current code-phase tests MUST prove exact closed request/result shapes, latest-four selection and
oldest-to-newest order, source/ref agreement, forbidden-source exclusion,
structural assessment validation, pending-only mapping, current authorization
race behavior, fake/spy success/timeout/error paths, no production fallback,
and redaction. The seeded conflict/trend fixture uses a test-only executor to
return a strict pending assessment; this proves deterministic flow only. A
real response is deferred to the provider runbook milestone.
