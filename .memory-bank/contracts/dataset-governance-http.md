---
description: Protected read-only Dataset Candidate projection for the Operator PWA.
status: active
type: api_contract
last_updated: 2026-08-13
source_of_truth:
  - .memory-bank/domains/dataset-governance.md
  - .memory-bank/states/dataset-governance.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/access/actor-context.md
---
# Dataset Governance HTTP

## Scope

Defines the single protected read-only Dataset Candidate list consumed by the
FT-016 Operator PWA. Dataset Governance remains the provider and mutable
authority. This contract adds no review, transition, evidence association,
curator invocation, split assignment, or trainability mutation endpoint.

## Route and authorization

`GET /api/plants/{plant_id}/dataset-candidates`

Query parameters:

- `limit`: optional integer `1..100`, default `50`;
- `cursor`: optional canonical opaque continuation cursor.

The route resolves ActorContext before query work. Boss and a currently granted
Engineer or Consultant may read only the authorized Plant. Active Plants use
normal-read authority; archived Plants use the backend-selected retained-
history read path and perform no mutation. Missing, wrong-Farm, unauthorized,
or revoked access uses the existing no-enumeration denial. Success and error
responses use `Cache-Control: no-store`.

## Response shape

`200 DatasetCandidateListV1` contains exactly:

- `schema_version: 1`;
- `items: DatasetCandidateViewV1[]`;
- `next_cursor: string|null`.

Each `DatasetCandidateViewV1` contains exactly:

- `candidate_id`, `plant_id`;
- `source_kind`, `source_ref`;
- `candidate_status`;
- `quality_tier`;
- nullable `split`;
- nullable `confirmation_source`;
- `evidence_refs`, preserving the canonical ordered typed-ref objects;
- nullable `curator_decision`;
- `corrected`, `follow_up_seen`, `can_train_on`;
- `record_version`, `created_at`, `updated_at`.

The response omits `farm_id`, curator notes, curator run/command identity,
Timeline event refs, internal authorization state, raw labels/provider output,
filesystem paths, credentials, and auth/session material. `can_train_on` is
copied from Dataset Governance authority and is never recomputed by the route.

## Order and cursor

Items are ordered by `(updated_at DESC, candidate_id DESC)`. The cursor is
unpadded base64url canonical compact UTF-8 JSON containing exactly
`v=1`, `plant_id`, `updated_at`, and `candidate_id` for the last returned item.
Decode plus canonical re-encode identity is required. Wrong-Plant, malformed,
padded, non-canonical, unknown-field, or unsupported-version cursors fail
before widening the authorized query. The implementation fetches `limit + 1`,
returns at most `limit`, and emits a cursor only when another row exists.

## Errors

All errors use the global safe envelope.

| Code | HTTP | Meaning |
|---|---:|---|
| existing `AUTH_*` codes | existing mapping | session/account/membership failure |
| `AUTH_PLANT_FORBIDDEN` | 404 | missing, unauthorized, wrong-Farm, revoked, or disallowed Plant access |
| `DATASET_CURSOR_INVALID` | 422 | malformed, non-canonical, wrong-Plant, or unsupported cursor |
| `DATASET_LIMIT_INVALID` | 422 | limit outside `1..100` |
| `DATASET_READ_FAILED` | 500 | safe fail-closed repository/query/serialization failure |
| `VALIDATION_FAILED` | 422 | malformed UUID or unknown query field |

The safe failure contains no SQL, DSN, evidence content, raw exception, secret,
or auth material. A read failure returns no partial list and never falls back
to Timeline, manifests, filesystem, UI Feed, or provider output.

## Verification

- OpenAPI and response tests cover the exact route, fields, enums, timestamps,
  no-store behavior, pagination, and stable errors.
- Authorization covers Boss, granted Engineer/Consultant, revoked/missing
  grant, disabled membership, wrong Farm, active Plant, and archived retained
  history without writes.
- Projection tests prove exact authority values, ordered typed evidence refs,
  `can_train_on` parity, omission of internal/secret fields, complete stable
  pagination, and safe database/serialization failure.
- Route and OpenAPI inspection prove no Dataset mutation endpoint was added.

