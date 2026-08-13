---
description: Concrete HTTP contract for Plant photo upload, catalog reads, artifact refs, and Farm-wide accepted-photo storage status.
status: active
type: api_contract
last_updated: 2026-08-12
source_of_truth:
  - .memory-bank/domains/photo-artifacts.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/access/actor-context.md
---
# Photo Intake HTTP

## Scope

Defines the protected multipart upload and catalog-read API for Plant photo
artifacts accepted by FT-005 plus the FT-015 Farm-wide accepted-photo storage
status read.

## Out of scope

Vision model processing, thumbnails, annotations, export package generation,
remote upload/sync, dataset trainability transitions, durable prompt
interaction state, and PWA components.

## Upload policy

- Accepted content types: `image/jpeg`, `image/png`, `image/webp`.
- Maximum accepted file size: 20 MiB.
- Accepted `photo_type`: `whole_plant | leaf_closeup | roots | problem_area | other`.
- User-provided filenames are never used as destination paths.
- Upload success is local-only and must not imply server sync.

## Response shapes

`PhotoCatalogSummary`:

- `photo_id`, `farm_id`, `plant_id`;
- `photo_type`, `captured_at`, `uploaded_at`;
- `content_type`, `size_bytes`, `sha256`;
- `original_file_ref`, `manifest_ref`;
- nullable `check_in_id`;
- `source_refs`, `event_refs`;
- `local_only: true`;
- `can_train_on: false`.

`photo_id` is the API name for the same UUID that cross-feature artifact specs
may call `photo_artifact_id`; FT-005 exposes only this single accepted-photo
identity.

`PhotoCatalogList`:

- `items: PhotoCatalogSummary[]`;
- nullable `next_cursor`.

`PhotoStorageStatus` is exact:

- `farm_id`: authorized Farm UUID;
- `sync_status`: literal `local_only`;
- `accepted_original_photo_bytes`: non-negative integer from the canonical
  Photo Catalog aggregation;
- `prompt_threshold_bytes`: literal `209715200`;
- `prompt_eligible`: boolean equal to
  `accepted_original_photo_bytes > prompt_threshold_bytes`.

It contains no Account preference, acknowledgment, dismiss, upload, server,
remote target, filesystem path, or Dataset Candidate field.

## Routes

| Method and path | Request | Success | Authorization and behavior |
|---|---|---|---|
| `POST /api/plants/{plant_id}/photos` | multipart `file`, `photo_type`, optional `captured_at`, optional `check_in_id` | `201 PhotoCatalogSummary` | active Boss or granted Engineer with operate permission; validates upload, writes local file/manifest/catalog/timeline refs through the Timeline Event append helper |
| `GET /api/plants/{plant_id}/photos` | optional `cursor`, `limit` | `200 PhotoCatalogList` | active normal read; archived retained access is outside FT-005 intake routes |
| `GET /api/plants/{plant_id}/photos/{photo_id}` | none | `200 PhotoCatalogSummary` | active normal read for same Plant/Farm; no cross-Plant leaks |
| `GET /api/photos/storage-status` | none | `200 PhotoStorageStatus` | any active authenticated Farm member; resolves ActorContext, aggregates accepted Photo Catalog `size_bytes` for that Farm, and returns `Cache-Control: no-store` without writing state |

## Storage-status behavior

- The route is Farm-wide and does not require a PlantAccessGrant. Boss,
  Engineer, and Consultant use the same active Account/FarmMembership gate.
- It uses the Photo Intake repository/service owner and the canonical
  [Farm photo storage pressure](../domains/photo-artifacts.md#farm-photo-storage-pressure)
  query. Filesystem scanning and partial/fallback totals are forbidden.
- `acknowledge` and `dismiss` are local consumer actions. FT-015 exposes no
  POST/PATCH/DELETE prompt route and persists no interaction state or Timeline
  event. A fresh authorized GET may remain eligible after either local action.
- The response is presentation input only. It cannot mutate `sync_status`,
  approve upload, imply server availability, or become agent context.
- FT-016 owns Svelte/PWA rendering and transient Account-isolated state; it
  consumes this response without redefining the aggregation or authority.

## Catalog pagination

- The default `limit` is 50; accepted values are `1..100`.
- Catalog order is stable newest-first by `uploaded_at DESC, photo_id ASC`.
- The implementation fetches `limit + 1` rows. It returns at most `limit`
  items and emits `next_cursor` only when another row exists.
- The opaque unpadded base64url cursor contains canonical JSON with exactly
  `v=1`, `plant_id`, `uploaded_at`, and `photo_id` for the last returned item.
  The cursor applies the strict keyset continuation after that tuple; it is not
  an offset and MUST NOT repeat or skip rows in an unchanged catalog.
- A cursor is valid only when it uses the unpadded base64url alphabet,
  decode/re-encode is byte-for-byte canonical, fields and timestamp/UUIDs are
  valid, `v=1`, and `plant_id` matches the authorized route Plant.
- Empty, malformed, non-canonical, wrong-version, or wrong-Plant cursors return
  `422 VALIDATION_FAILED`. A supplied cursor MUST NOT be accepted and ignored.

## Error catalog

All errors use the global error envelope.

| Code | HTTP | Meaning |
|---|---:|---|
| existing `AUTH_*` codes | existing mapping | session/account/membership/role failures |
| `AUTH_PLANT_FORBIDDEN` | 404 | missing, unauthorized, revoked, wrong-Farm, or archived for normal route |
| `PHOTO_NOT_FOUND` | 404 | missing or unauthorized photo without existence leak |
| `PHOTO_TYPE_INVALID` | 422 | `photo_type` outside the accepted set |
| `UPLOAD_FILE_REQUIRED` | 422 | multipart file part is missing |
| `UPLOAD_TOO_LARGE` | 413 | file exceeds 20 MiB |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | content type is not accepted |
| `PHOTO_CHECKSUM_MISMATCH` | 500 | stored file digest fails internal verification |
| `PHOTO_ARTIFACT_WRITE_FAILED` | 500 | local file or manifest write failed safely |
| `TIMELINE_APPEND_FAILED` | 500 | accepted photo cannot claim audit/export evidence |
| `PHOTO_PERSISTENCE_FAILED` | 500 | unclassified rollback-safe persistence failure |
| `PHOTO_DATASET_AUDIT_FAILED` | 500 | Dataset Governance audit append failed; the accepted-photo UoW rolled back |
| `PHOTO_STORAGE_STATUS_FAILED` | 500 | authoritative Farm photo-pressure aggregation failed safely; no filesystem fallback or partial total is returned |
| `VALIDATION_FAILED` | 422 | malformed UUID/body/query or unknown field |

## Verification

- API/OpenAPI tests cover multipart body, response shapes, accepted content
  types, max-size rejection, UUIDs, timestamps, enums, and error statuses.
- Authorization tests cover Boss, Engineer, Consultant, unauthorized Plant,
  revoked grant, disabled membership, and archived normal-operation denial.
- Security tests prove no user filename controls a path and no absolute local
  path or auth material appears in responses, manifests, timeline events, or
  evidence.
- Catalog reads prove PostgreSQL/read model authority instead of filesystem
  scanning.
- Storage-status tests cover active Boss/Engineer/Consultant sessions,
  disabled/invalid sessions, exact response/OpenAPI shape, `no-store`,
  empty/below/exact/above-threshold totals, cross-Farm isolation, archived
  retained bytes, safe database failure, absence of mutation routes/state, and
  fresh-load/per-Account consumer semantics.
- Multi-row pagination tests prove real continuation, stable ordering,
  non-overlapping pages, complete enumeration beyond `limit`, terminal
  `next_cursor=null`, and `422` for malformed or wrong-Plant cursors.
