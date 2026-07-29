---
description: Authorized real-photo bytes and provider-neutral model-output contract for Vision Observation Agent.
status: active
type: interface_contract
last_updated: 2026-07-29
source_of_truth:
  - .memory-bank/features/FT-009-vision-observation-plant-state-trust.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/domains/photo-artifacts.md
  - .memory-bank/states/plant-state-trust.md
---
# Vision Observation Runtime

## Scope

This contract adds the FT-009 multimodal input path for the canonical
`vision_observation` agent. It loads one already accepted local photo through
current ActorContext authority, sends the exact photo bytes to one provider-
neutral executor call, validates one structured visible finding,
and, for `runtime_decision=speak`, returns the existing pending
`MessageEnvelope` handoff plus a strict state-candidate value. `clarify`
returns only its pending clarification envelope; `silent` returns neither an
envelope nor a candidate.

It does not publish to Bus/UI, persist Plant state, diagnose disease, recommend
physical action, or treat a provider response as confirmed evidence.

## Module boundary

Implementation lives under `backend/app/vision_observation/` and reuses the
current authorization guard, timeline append, outcome, and MessageEnvelope
types under `backend/app/agent_runtime/`.

Project-owned seams:

- `VisionObservationService`: owns one invocation and closed outcome.
- `VisionInputAssembler`: resolves the accepted catalog row and verified bytes.
- `VisionModelExecutor`: accepts only the strict request plus one in-memory
  media value.
- `VisionObservationDefinition`: immutable policy for the canonical roster id.

Callers supply only `run_id`, request time, ActorContext, `plant_id`, and
`photo_id`. They cannot supply a file path, bytes, prompt, provider/model,
finding, source ref, authorization snapshot, or output schema.

## Input shape

`VisionProviderRequestV1` is a strict object constructed from:

- `schema_version=1`;
- `agent_definition`: canonical `agent_id=vision_observation`, competence and
  instructions, allowed decisions `speak|clarify|silent`, and output schema
  `VisionObservationModelResultV1` version 1;
- `records`: exactly two ordered records: `plant`, then `photo`;
- read-only `source_refs` is derived exactly as
  `[plant:<plant_id>, photo:<photo_id>]`; callers cannot supply it separately.
  The outbound compatibility payload may include this derived array.

The strict photo record is
`{record_type=photo, source_ref, payload}`. Its payload contains exactly:

- `photo_id`, `plant_id`, `photo_type`, `captured_at`, `content_type`,
  `size_bytes`, `sha256`, and `local_only=true`.

The plant record keeps the existing `{plant_id,status=active}` payload. UUIDs
are lowercase canonical text and timestamps are UTC RFC 3339.

`VisionMediaV1` is service-side only and contains exactly `source_ref`,
`content_type`, `sha256`, and immutable `content` bytes. It is attached to the
model call in memory; it is not JSON, a public value, or a persisted provider
object. Absolute paths, user filenames, manifest contents, ActorContext,
session/account/membership/grant values, credentials, UI Feed, raw chat,
timeline replay, and hidden reasoning never cross the provider boundary.

## Assembly and file integrity

Before provider I/O the assembler MUST:

1. Resolve current normal-read authority for the same active Plant.
2. Load the accepted `photo_catalog_items` row by the same Farm/Plant/photo.
3. Resolve `original_file_ref` under `LOCAL_ARTIFACT_ROOT` without path escape.
4. Require the regular file to exist and match catalog `size_bytes` and
   lowercase `sha256` after a fresh byte read.
5. Require `image/jpeg|image/png|image/webp` and the existing 20 MiB catalog
   maximum.
6. Build the request and media values internally.

Missing, mismatched, unauthorized, archived, unsafe-path, unsupported-media,
or checksum/size-invalid input returns `context_denied` with
`reason_code=input_contract_violation` before provider or runtime-audit I/O.
The runtime never repairs, resizes, recompresses, uploads from an absolute path,
or substitutes another photo.

For missing or unavailable photo data, this fail-closed denial is the complete
FT-009 runtime outcome. It creates no clarification envelope, state candidate,
or follow-up task. A later FT-016 UI may render an upload/reselect prompt from
the safe denial, while FT-012 owns any actual follow-up task.

## Executor capability

Version 1 requires a provider-neutral executor seam that accepts the strict
JSON request plus exactly one in-memory image value. Current deterministic
tests inject an outbound spy and prove that its bytes, content type, source
ref, and sha256 match the accepted catalog artifact. They do not claim image
interpretation by a real endpoint.

Production remains unbound and returns `AGENT_RUNTIME_NOT_CONFIGURED` before
network I/O until the future OpenAI-compatible endpoint is selected. It MUST
NOT send a local path, persist a provider file URI, choose a default, or fall
back to a fake/canned/alternate executor.

## Model result version 1

`VisionObservationModelResultV1` is a strict object with exactly:

- `schema_version=1`;
- `runtime_decision=speak|clarify|silent`;
- nullable `observation_key` from
  `image_quality|leaf_color_change|leaf_spots|wilting|growth_change|root_color_change|root_damage|other_visible_change`;
- nullable `polarity=present|absent|uncertain|not_assessable`;
- nullable `severity=none|mild|moderate|strong|unknown`;
- nullable normalized `summary` of 1..1000 Unicode code points;
- nullable finite `confidence` from 0 through 1;
- nullable `reason_code`.

Matrix:

| Decision | Finding fields | Trusted provenance | Reason |
|---|---|---|---|
| `speak` | key, polarity, severity, summary, and confidence required | application binds exact `[photo:<photo_id>]` after strict result validation | null |
| `clarify` | key=`image_quality`, polarity=`not_assessable`, severity=`unknown`, summary required, confidence null | application binds exact `[photo:<photo_id>]` after strict result validation | null |
| `silent` | key, polarity, severity, summary, confidence all null | no refs | `no_material_output` |

For `speak`, `absent` requires `severity=none`, `present` requires
`mild|moderate|strong`, and `uncertain|not_assessable` requires `unknown`.
`source_refs` is not a member of the raw untrusted
`VisionObservationModelResultV1`; an extra field is invalid. The provider
cannot select, omit, duplicate, reorder, or foreign-bind Vision provenance.
After the content matrix passes, trusted application code derives the singleton
photo ref from the same authorized, catalog-checked, byte-verified invocation
context used for the media attachment.

Unknown fields (including any provenance/ref field), diagnosis/disease labels,
recommendation/action fields, arbitrary metadata, and invalid combinations
reject the whole result as `AGENT_OUTPUT_INVALID`.

For `speak`, the adapter creates one standard pending, non-consumable
MessageEnvelope. Its candidate claim is `observation` only when polarity is
`present|absent` and confidence is at least `0.50`; otherwise it is
`hypothesis`. The envelope confidence and text are the validated confidence
and summary. A clarification maps to the standard `clarification` envelope.

`candidate_claim_type` is transport metadata, not persisted trust authority.
The Plant State data boundary deterministically stores a lower-confidence or
`uncertain|not_assessable` Vision finding as `trust_status=unknown` even though
its pending envelope claim is `hypothesis`.

For `speak`, the companion `VisionStateCandidateV1` contains only the validated key,
polarity, severity, summary, confidence, exact singleton
`[photo:<photo_id>]`, run/message ids, and observed time. The `speak` envelope
and candidate refs must be equal; the `clarify` envelope carries the same
singleton and `silent` has none. The candidate has no trust, confirmation,
safety, publication, or task authority. It may be persisted only with the same
envelope and a successful project-owned `safe_information` classification under
the Plant State data spec. `clarify|silent` returns no state candidate.

## Invocation flow and failures

The flow follows Agent Runtime ordering: resolve definition and current input,
require an explicitly injected executor, read/verify bytes, call outside DB
transactions, validate result, reload current session/membership/Plant/grant
authority, append one sanitized runtime event for every executor-I/O branch,
and return a closed outcome. Production supplies no executor in the current
code phase and returns `AGENT_RUNTIME_NOT_CONFIGURED` before executor/network
I/O. Archive/revoke after model I/O blocks the envelope/candidate;
restore never replays it.

Provider request/response bodies and photo bytes are never logged, stored in
Timeline/UI/Bus/task evidence, or returned by errors. Safe evidence may contain
only ids/refs, content type, size, sha256, test-scoped executor ref, outcome
kind, and redacted stable error code.

## Verification

Current code-phase tests MUST prove exact shapes and order, real catalog/file/
hash loading, authorization and archive races, no caller/path injection, exact
outbound media identity, timeout/error/invalid-result handling through
fake/spy executors, no production fallback/fake output, strict result
validation, pending-only handoff, no direct state effect, redaction, and full
Agent Runtime regression.

The committed tomato fixture is deterministic schema/flow evidence: the spy
returns a strict `speak` result, producing one pending envelope and matching
`VisionStateCandidateV1`; `clarify` and `silent` exercise their separate valid
branches. A real image/response is deferred to the provider runbook milestone
and is not required or claimed here.
