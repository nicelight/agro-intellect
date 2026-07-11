---
description: Concrete HTTP contract for daily Plant check-ins and manual pH/EC measurements.
status: active
type: api_contract
last_updated: 2026-07-11
source_of_truth:
  - .memory-bank/domains/plant-operations.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/access/actor-context.md
---
# Plant Operations HTTP

## Scope

Defines the protected JSON API for active Plant check-in prompt, check-in
creation, manual pH/EC measurement creation, and latest measurement freshness
projection.

## Out of scope

Photo multipart upload, history/timeline pagination, agent output, tasks,
approvals, follow-up outcomes, and frontend/PWA layout.

## Common rules

- Every route resolves ActorContext before business logic.
- Write routes require `OperationKind.OPERATE` and current
  `Plant.status=active` in the same transaction boundary as the write.
- Read routes require active normal Plant read unless a route is explicitly
  owned by a retained-history contract outside FT-004.
- Protected responses set `Cache-Control: no-store`.
- Request bodies reject unknown fields.
- Responses exclude credentials, password hashes, session tokens, cookies,
  headers, raw SQL errors, provider payloads, and hidden reasoning.

## Response shapes

`FreshnessProjection`:

- nullable `latest_ph_ref`, `latest_ec_ref`;
- nullable `latest_ph`, `latest_ec_ms_cm`;
- `ph_fresh_for_analysis`, `ec_fresh_for_analysis`;
- `ph_fresh_for_approval_input`, `ec_fresh_for_approval_input`;
- `missing_or_stale: string[]`;
- `computed_at`.

`CheckInSummary`:

- `check_in_id`, `farm_id`, `plant_id`;
- `observation_state`, nullable `observation_text`;
- `observed_at`, `recorded_at`;
- `measurement_refs: uuid[]`;
- `event_refs`;
- `freshness: FreshnessProjection`;
- `photo_upload_available: boolean`.

`MeasurementSummary`:

- `measurement_id`, nullable `check_in_id`, `farm_id`, `plant_id`;
- nullable `ph`, nullable `ec_ms_cm`;
- `measured_at`, `recorded_at`;
- nullable `provenance_note`;
- `trust_status`;
- `event_refs`.

## Routes

| Method and path | Request | Success | Authorization and behavior |
|---|---|---|---|
| `GET /api/plants/{plant_id}/operations/check-in-prompt` | none | `200 {plant_id, prompt, photo_upload_available}` | active normal read; archived and unauthorized share no-leak denial |
| `POST /api/plants/{plant_id}/operations/check-ins` | observation fields plus optional measurement | `201 CheckInSummary` | active Boss or granted Engineer with operate permission; writes check-in, optional measurement, and required timeline refs through the Timeline Event append helper before claiming success |
| `POST /api/plants/{plant_id}/operations/measurements` | manual pH/EC payload | `201 MeasurementSummary` | active Boss or granted Engineer with operate permission; writes standalone manual measurement and timeline ref through the Timeline Event append helper before claiming success |
| `GET /api/plants/{plant_id}/operations/measurements/latest` | optional `purpose=analysis|approval_input` | `200 FreshnessProjection` | active normal read; computes from PostgreSQL measurement records |

`POST /check-ins` payload:

- nullable `observed_at`; defaults to receive time.
- `observation_state: observed|no_observation_provided`.
- nullable `observation_text`.
- optional `measurement` object with nullable `measured_at`, nullable `ph`,
  nullable `ec_ms_cm`, nullable `provenance_note`.

When `observation_text` is non-blank, `observation_state` is required. If both
observation fields are omitted, a valid measurement payload may still make the
check-in non-empty. Text without state returns `422 VALIDATION_FAILED`; it is
never discarded or rewritten as `no_observation_provided`.

`POST /measurements` payload:

- nullable `measured_at`; defaults to receive time only when the user did not
  supply a measurement time.
- nullable `ph`.
- nullable `ec_ms_cm`.
- nullable `provenance_note`.

pH and EC accept finite JSON numeric values in their documented ranges. The
success response exposes the canonical PostgreSQL value: pH at scale 2 and EC
at scale 3, normalized with decimal `ROUND_HALF_UP` before persistence and
timeline append. A subsequent read and the audit summary for the same
measurement MUST agree with the creation response.

Future-aware timestamps remain valid historical input, but a `measured_at`
later than the freshness projection's `computed_at` is stale for both
`analysis` and `approval_input`.

## Error catalog

All errors use the global `{error: {code, message, request_id}}` envelope.

| Code | HTTP | Meaning |
|---|---:|---|
| existing `AUTH_*` codes | existing mapping | session/account/membership/role failures |
| `AUTH_PLANT_FORBIDDEN` | 404 | missing, unauthorized, revoked, wrong-Farm, or archived for normal route |
| `CHECK_IN_EMPTY` | 422 | no observation state and no measurement payload |
| `OBSERVATION_TEXT_REQUIRED` | 422 | `observed` without non-blank text |
| `OBSERVATION_TEXT_FORBIDDEN` | 422 | `no_observation_provided` with text |
| `MEASUREMENT_VALUE_REQUIRED` | 422 | neither pH nor EC was provided |
| `PH_INVALID` | 422 | pH outside `0..14` or wrong type |
| `EC_INVALID` | 422 | EC negative or wrong type |
| `TIMELINE_APPEND_FAILED` | 500 | runtime write cannot claim audit/export evidence |
| `OPERATION_PERSISTENCE_FAILED` | 500 | unclassified rollback-safe persistence failure |
| `VALIDATION_FAILED` | 422 | malformed UUID/body/query or unknown field |

## Verification

- API/OpenAPI tests cover every route, body, response, UUID, timestamp, enum,
  no-store response, and documented error status.
- Authorization tests cover Boss, Engineer, Consultant, missing grant, revoked
  grant, disabled membership, unauthorized Plant, and archived Plant.
- Freshness tests prove latest measurement projection reads PostgreSQL state
  and uses the documented closed windows, including future-dated evidence.
- PostgreSQL/API tests prove excess-scale values have one normalized value in
  the creation response, timeline summary, database reread, and latest
  projection.
- Validation tests prove non-blank observation text without
  `observation_state` returns `422 VALIDATION_FAILED` and writes nothing.
- Failure-injection tests prove persistence or timeline failures do not return
  success and do not leak raw exception or credential details.
