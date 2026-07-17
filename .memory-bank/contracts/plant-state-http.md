---
description: Protected Plant state record list and human review HTTP contract.
status: active
type: api_contract
last_updated: 2026-07-15
source_of_truth:
  - .memory-bank/domains/plant-state-observations.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
---
# Plant State HTTP

## Scope

This API exposes authoritative Plant state trust records for later PWA display
and explicit human confirm/reject decisions. It does not expose a public model
prompt, raw provider response, pending MessageEnvelope, classifier endpoint,
or physical-action approval.

All responses use `Cache-Control: no-store`, the global safe error envelope,
and backend ActorContext authorization before record/cursor processing.

## List records

`GET /api/plants/{plant_id}/state-records`

Query:

- `limit`: optional integer 1..100, default 50;
- `cursor`: optional canonical base64url JSON cursor containing exactly
  `v=1`, `recorded_at`, `state_record_id`, and `plant_id`.

Response `200 PlantStateRecordListV1`:

```json
{
  "items": [],
  "next_cursor": null
}
```

Each item contains exactly `state_record_id`, `plant_id`, `record_kind`,
`agent_id`, `observation_key`, `polarity`, `severity`, `assessment_kind`, `direction`,
`summary`, `confidence`, `trust_status`, `source_refs`, `observed_at`,
`recorded_at`, nullable `confirmation_source`, nullable `confirmed_at`, and
`version`. Confirmation actor ids, message/run ids, provider/model refs, local
paths, and internal classification values are not public.

Order and continuation are exactly `(recorded_at DESC, state_record_id DESC)`.
A cursor for another Plant or any malformed/noncanonical cursor returns
`422 VALIDATION_FAILED` and never widens the authorized query.

Active Plant reads use normal-read authority. `include_archived=true` is not a
query switch; archived history is reached only through the existing retained-
history authorization behavior selected by the backend from current Plant
state and ActorContext.

## Review record

`POST /api/plants/{plant_id}/state-records/{state_record_id}/review`

Request body is strict:

```json
{
  "decision": "confirm",
  "expected_version": 1
}
```

`decision` is `confirm|reject`; unknown fields are rejected. Success returns
`200 PlantStateRecordV1` with the post-commit item shape from the list endpoint.

Review requires current active-Plant operate authority for Boss or Engineer.
Consultant, read-only access, wrong Farm/Plant, archived Plant, or stale
authorization fails before mutation. `expected_version` mismatch returns
`409 PLANT_STATE_VERSION_CONFLICT`; unresolved opposite evidence returns
`409 PLANT_STATE_CONFLICT_UNRESOLVED`; missing/inaccessible record uses the
project no-enumeration not-found behavior.

The endpoint never accepts `trust_status`, source refs, confirmation actor,
agent id, message id, provider/model, summary, confidence, or Safety fields
from the client.

## Non-goals

- No HTTP endpoint invokes a model in FT-009. Invocation remains an internal
  application command until the owning orchestration/UI feature composes it.
- No UI implementation or claim that trust is browser-visible.
- No batch confirmation, delete, hard reset, conflict auto-resolution,
  Safety approval, task creation, or automated action.

## Verification

OpenAPI and integration tests MUST cover exact schemas, no-store, Boss and
Engineer review, Consultant/unauthorized/archived denial, retained-history
list behavior, conflict/version 409s, stable complete pagination, wrong-Plant
cursor rejection, no-enumeration errors, and absence of internal/provider/auth
fields.
