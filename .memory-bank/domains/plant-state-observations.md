---
description: PostgreSQL Plant-state observation, assessment, conflict, and human-promotion data specification.
status: active
type: data_spec
last_updated: 2026-07-19
source_of_truth:
  - .memory-bank/features/FT-009-vision-observation-plant-state-trust.md
  - .memory-bank/states/plant-state-trust.md
  - .memory-bank/contracts/vision-observation-runtime.md
  - .memory-bank/contracts/plant-state-runtime.md
  - .memory-bank/domains/photo-artifacts.md
  - .memory-bank/domains/runtime-data-model.md
---
# Plant State Observations

## Scope

This specification defines the mutable PostgreSQL authority for FT-009 visual
observations, Plant State assessments, trust display, contradiction handling,
and explicit human promotion. It does not make model output authoritative,
classify physical-action wording, publish Bus/UI events, or define frontend
layout.

## Storage shape

`plant_state_records` uses native PostgreSQL UUIDs and contains:

- `state_record_id`: application-generated UUID primary key;
- `farm_id`, `plant_id`: restrictive FKs to the owning Farm and Plant;
- `record_kind`: `vision_observation | plant_state_assessment`;
- `agent_id`: matching `vision_observation | plant_state`;
- `run_id`, `message_id`: UUIDs; `message_id` is unique and identifies the
  classified immutable MessageEnvelope;
- `observation_key`: the Vision Runtime catalog value;
- nullable `polarity`: `present|absent|uncertain|not_assessable`, required only
  for `vision_observation`;
- nullable `severity`: `none|mild|moderate|strong|unknown`, required only for
  `vision_observation` and compatible with polarity as defined by the Vision
  Runtime contract;
- nullable `assessment_kind`: `trend|conflict|unknown`, required only for
  `plant_state_assessment`;
- nullable `direction`: `increasing|decreasing|stable|mixed|not_applicable`,
  required for an assessment and `not_applicable` for conflict/unknown;
- `summary`: normalized 1..1000-code-point text copied only from a validated
  candidate;
- `confidence`: finite decimal in `[0,1]`;
- `trust_status`: `unknown|observed|hypothesis|conflicting|confirmed|rejected`;
- `source_refs`: non-empty ordered JSON array of unique safe refs;
- `observed_at`, `recorded_at`: timezone-aware timestamps;
- nullable `confirmation_source`: `human_review|manual_measurement|follow_up`;
- nullable `confirmed_by_account_id`, `confirmed_by_membership_id` restrictive
  FKs, and nullable `confirmed_at`;
- `version`: integer starting at 1 for optimistic review updates;
- `created_at`, `updated_at`: timezone-aware server timestamps.

Unknown JSON extensions, provider payloads, absolute paths, credentials,
authorization snapshots, raw chat/UI, hidden reasoning, diagnosis labels, and
physical-action fields are forbidden.

Database checks MUST enforce record-kind field compatibility, agent identity,
confidence bounds, confirmation-field all-or-none rules, `version >= 1`, and
that only `confirmed` has confirmation metadata. Indexes cover
`(plant_id, recorded_at DESC, state_record_id DESC)`,
`(plant_id, observation_key, recorded_at DESC)`, and unique `message_id`.
Authority FKs use `ON DELETE RESTRICT`; migration downgrade refuses while rows
exist.

## Creation boundary

One record may be created only from:

1. an immutable pending MessageEnvelope;
2. its matching strict feature candidate;
3. a matching successful project-owned classification with
   `classification=safe_information` and the same `message_id` as the envelope;
4. a fresh same-Farm current authorization and active-Plant guard in the same
   transaction as the insert.

The envelope/candidate ids, agent id, Plant/Farm, source refs, summary, and
confidence must agree. For a Vision `speak` handoff, source refs are exactly
`[photo:<photo_id>]` or `[plant:<plant_id>, photo:<photo_id>]` in that order:
there is exactly one photo ref, and the optional explicit Plant ref is first and
equals the envelope Plant. The service loads the authoritative
`PhotoCatalogItem` by `photo_id` and requires its `farm_id` and `plant_id` to
equal the envelope Farm and Plant. Current authorization, active-Plant guard,
catalog lookup, and insert share one transaction. This persistence check reads
catalog metadata only; it does not reopen or revalidate photo bytes/files.

An envelope/authorization-scope mismatch with current actor authority returns
`AUTH_PLANT_FORBIDDEN`. Any malformed, missing, duplicated, reordered,
unknown, or cross-Plant Vision provenance returns
`PLANT_STATE_CANDIDATE_INVALID`. Both failures write zero Plant-state rows and
must occur before insert/flush so a raw `IntegrityError` cannot escape.
Duplicate identical `message_id` is idempotent; different content for the same
id returns `PLANT_STATE_CONTENT_CONFLICT` and writes nothing.
Pending/blocked/physical/uncertain classifications create no record. Model
output, MessageEnvelope, Bus event, UI Feed, or timeline event by itself cannot
create or mutate a record.

Initial trust mapping is project-owned:

- Vision finding with `present|absent` polarity and confidence `>=0.50` ->
  `observed`;
- lower-confidence or `uncertain|not_assessable` Vision finding -> `unknown`,
  regardless of its pending envelope `candidate_claim_type`;
- Plant State `conflict` -> `conflicting` only after structural conflict
  validation;
- Plant State `trend` -> `hypothesis`;
- Plant State `unknown` -> `unknown`.

No agent-created record starts `confirmed` or `rejected`.

## Plant State Agent assessment

The canonical `plant_state` definition reads 1..4 latest non-rejected records
for one authorized active Plant, ordered oldest to newest in the outbound
request. It receives only record ids, key, polarity/severity/assessment kind, direction,
trust status, observed/recorded time, confidence, and safe source refs. It does
not receive confirmation actor ids, ActorContext, UI Feed, raw chat, timeline
replay, provider history, or hidden reasoning.

`PlantStateAssessmentCandidateV1` contains exactly:

- `assessment_kind=trend|conflict|unknown`;
- `observation_key`;
- `direction=increasing|decreasing|stable|mixed|not_applicable`;
- normalized `summary`, confidence, and 1..4 ordered `source_refs` that are a
  subset of the request refs.

Project validation requires:

- `trend`: at least two records for the same key with comparable severity and a
  non-`not_applicable` direction. Using `none=0`, `mild=1`, `moderate=2`, and
  `strong=3`, `increasing` is non-decreasing with at least one rise,
  `decreasing` is non-increasing with at least one fall, `stable` has one value,
  and `mixed` is every other comparable sequence;
- `conflict`: at least two records for the same key with opposing
  `present|absent` polarity, or an already `conflicting` source; direction is
  `not_applicable`;
- `unknown`: at least one insufficient/unknown source; direction is
  `not_applicable`.

If the structural evidence does not support the selected kind, the result is
invalid and no envelope/state candidate is returned. A valid assessment still
uses the common pending MessageEnvelope and classification boundary before
persistence. The Plant State agent never confirms, rejects, or resolves a
record.

## Conflict rules

When a validated conflict assessment is inserted, every referenced current
non-rejected, non-confirmed record for the same key is changed to
`conflicting` in the same transaction and version-incremented. Confirmed rows
are never silently demoted; an opposite confirmed row makes the new assessment
and affected unconfirmed rows `conflicting` and requires human review.

Conflict resolution is explicit. Confirming one record is rejected with
`PLANT_STATE_CONFLICT_UNRESOLVED` while another non-rejected opposite-polarity
record for the same key remains. The reviewer must reject the unsupported row
or provide a later authoritative measurement/follow-up decision through the
same promotion service. No newest-wins or highest-confidence collapse exists.

## Human promotion

The review command contains `plant_id`, `state_record_id`, `expected_version`,
and `decision=confirm|reject`. It is accepted only from current Boss or
Plant-operate Engineer authority; Consultant, disabled membership, missing or
revoked grant, wrong Farm, or archived Plant fails before mutation.

`confirm` sets `trust_status=confirmed`,
`confirmation_source=human_review`, current safe actor ids, `confirmed_at`, and
increments version only after conflict checks. `reject` sets `rejected`, clears
confirmation fields, and increments version. Repeating the same decision with
the current resulting version is idempotent; stale version returns
`PLANT_STATE_VERSION_CONFLICT`.

Later owning features may call the same service with
`manual_measurement|follow_up` only when they provide an existing authorized
source ref and their canonical evidence contract permits it. This feature does
not invent those downstream records.

Confirmation is Plant-state trust only. It does not clear physical-action
wording, grant Safety approval, create a task, or authorize actuation.

## Read model and retention

Lists use `(recorded_at DESC, state_record_id DESC)` keyset pagination and
return only the safe fields above plus current version. Normal reads require
current Plant read authority and active Plant. Archived Plants are available
only through the existing retained-history authorization operation; no review,
agent invocation, or new assessment is allowed while archived.

Records are retained across archive/restore. Restore does not replay a model
run, reclassify an envelope, resolve a conflict, or resume review.

## Errors

- `PLANT_STATE_NOT_FOUND`
- `PLANT_STATE_CONTENT_CONFLICT`
- `PLANT_STATE_CLASSIFICATION_REQUIRED`
- `PLANT_STATE_CANDIDATE_INVALID`
- `PLANT_STATE_CONFLICT_UNRESOLVED`
- `PLANT_STATE_VERSION_CONFLICT`
- existing authorization, archived-Plant, and validation error codes

Errors expose no candidate text, provider payload, local path, credential, or
authorization material.

## Verification

Tests MUST cover migration constraints, classified-only atomic creation,
same-Plant/Farm catalog provenance and zero-write rejection on real PostgreSQL,
idempotency/conflict, exact trust mapping at confidence `0`, `0.499`, `0.50`,
and `1`, structural trend/conflict validation, no silent conflict collapse,
human-only promotion, optimistic versioning, archive/restore retention,
retained-history reads, Safety separation, pagination, and secret/source
exclusion.
