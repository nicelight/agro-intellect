---
description: Photo artifact authority, catalog, local storage layout, and capture manifest contract for MVP v2.
status: active
type: domain
last_updated: 2026-07-10
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/contracts/api-guidelines.md
---
# Photo Artifacts

## Scope

Photo artifacts are local files, catalog rows, manifests, and artifact refs
used as evidence for Plant operations, Vision Observation, future dataset
governance, and audit/export. They are not mutable Plant state and cannot
override PostgreSQL/read-model authority.

The verified FT-000 executable baseline provides local artifact root settings.
FT-005 owns the concrete local storage layout, accepted catalog shape, initial
capture manifest, and upload atomicity policy below.

## Contract Scope

- Defines: global photo artifact authority boundary, accepted artifact identity,
  local-only privacy rules, and cross-feature reference requirements.
- Out of scope: multipart endpoint schema, thumbnail/derivative policy, Vision
  Observation payloads, export package generation, remote upload/sync, and
  dataset trainability transitions.
- Related specs:
  - [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md):
    defines upload/authz/error guardrails.
  - [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md):
    defines audit/export refs.
  - [.memory-bank/states/plant-state-trust.md](../states/plant-state-trust.md):
    defines trust/promotion rules for photo-derived observations.
  - [.memory-bank/states/dataset-governance.md](../states/dataset-governance.md):
    defines trainability state.

## Artifact Identity

Feature-local specs may refine fields, but every accepted photo artifact flow
must produce or reference:

- `photo_artifact_id`
- `farm_id`
- `plant_id`
- `captured_or_uploaded_at`
- `actor_ref`
- `original_file_ref`
- `sha256`
- `content_type`
- `size_bytes`
- `catalog_ref`
- `manifest_ref`
- `source_refs`
- `local_only=true`

The file path itself is not a public authority token. Runtime records should
store stable artifact refs and safe metadata.

For FT-005, `photo_artifact_id` and `photo_id` are the same UUID. `photo_id` is
the storage/API field name on `photo_catalog_items`, manifests, and HTTP
responses; cross-feature references may label the same value as
`photo_artifact_id`. FT-005 MUST NOT create a second photo identity.

## Photo catalog storage

All identifiers use PostgreSQL native `uuid`, SQLAlchemy `Uuid(as_uuid=True)`,
Python `uuid.UUID`, and application-generated `uuid.uuid4`.

`photo_catalog_items`:

- `photo_id`: primary UUID and canonical accepted-photo identity; same value as
  `photo_artifact_id`.
- `farm_id`: FK to `farms.farm_id`, `ON DELETE RESTRICT`.
- `plant_id`: FK to `plants.plant_id`, `ON DELETE RESTRICT`.
- nullable `check_in_id`: FK to `daily_checkins.check_in_id`, `ON DELETE
  RESTRICT`, when the photo was submitted from a check-in flow.
- `uploaded_by_account_id`, `uploaded_by_membership_id`: safe actor refs.
- `photo_type`: `whole_plant | leaf_closeup | roots | problem_area | other`.
- `captured_at`: timezone-aware timestamp from user input or server receive
  time.
- `uploaded_at`: timezone-aware server receive time.
- `content_type`: `image/jpeg | image/png | image/webp`.
- `size_bytes`: non-negative integer, maximum 20 MiB.
- `sha256`: lowercase hex SHA-256 digest of the stored original.
- `original_file_ref`: safe relative artifact ref.
- `manifest_ref`: safe relative artifact ref.
- `source_refs`: JSON object with safe Plant/check-in/actor refs.
- `event_refs`: JSON object containing the required timeline event id.
- `local_only`: boolean, true for MVP.
- `can_train_on`: boolean, false for MVP photo intake.
- `created_at`, `updated_at`: timezone-aware server timestamps.

User filenames, absolute paths, credentials, headers, cookies, `.env` values,
provider payloads, and hidden reasoning are forbidden in catalog rows.

## Local storage layout

Accepted originals and initial manifests live under `LOCAL_ARTIFACT_ROOT`.
Default relative layout:

```text
plants/{plant_id}/photos/{photo_id}/original.{ext}
plants/{plant_id}/photos/{photo_id}/manifest.initial_capture.json
```

Rules:

- `{plant_id}` and `{photo_id}` are trusted UUID string path segments derived
  from runtime records.
- `{ext}` is derived from validated content type: `.jpg`, `.png`, or `.webp`.
- User-provided filenames are ignored for destination paths.
- Runtime records store relative refs only, never local absolute paths.
- Existing accepted original files and initial capture manifests must not be
  overwritten. A new upload creates a new `photo_id`.

## Initial capture manifest v1

Initial capture manifests are immutable JSON artifacts adjacent to the stored
original. Minimum shape:

```json
{
  "schema_version": "photo_manifest.v1",
  "manifest_kind": "initial_capture",
  "created_at": "2026-07-10T12:00:00+05:00",
  "photo": {
    "photo_id": "uuid",
    "farm_id": "uuid",
    "plant_id": "uuid",
    "photo_type": "leaf_closeup",
    "captured_at": "2026-07-10T12:00:00+05:00"
  },
  "file": {
    "original_file_ref": "plants/<plant_id>/photos/<photo_id>/original.jpg",
    "content_type": "image/jpeg",
    "size_bytes": 123456,
    "sha256": "hex_sha256"
  },
  "source": {
    "source_type": "manual_user_upload",
    "captured_at_source": "user_input|server_received_at",
    "uploaded_at": "2026-07-10T12:00:00+05:00",
    "source_refs": {}
  },
  "authority": {
    "authoritative_for_mutable_state": false,
    "runtime_authority": "postgresql_read_model",
    "local_only": true,
    "can_train_on": false
  }
}
```

The manifest must match the catalog row for `photo_id`, `farm_id`, `plant_id`,
`photo_type`, `captured_at`, `content_type`, `size_bytes`, and `sha256`. It is
not runtime authority for mutable state, review, dataset, sync, or Plant trust.

## Acceptance sequence

1. Resolve ActorContext and active Plant operate permission.
2. Validate `photo_type`, size, content type, path safety, and optional
   `check_in_id` ownership.
3. Generate `photo_id` and final relative refs.
4. Write upload bytes to a temporary file under `LOCAL_ARTIFACT_ROOT`.
5. Compute `sha256`, content metadata, and size.
6. Atomically move the original into the accepted path.
7. Write `manifest.initial_capture.json` via temp file plus atomic rename.
8. Insert the PostgreSQL catalog row with `local_only=true`,
   `can_train_on=false`, and source refs.
9. Append the `photo_accepted` timeline event through the Timeline Event append
   helper and store its ref on the catalog row.

If any step fails before final success, the API must not report an accepted
photo. Cleanup may remove only files created for the failed upload under the
generated temporary/accepted photo path; unrelated local data and retained
history must never be deleted.

The `photo_accepted` timeline event uses `source_type=photo_catalog_item`,
`source_id=photo_id`, and a redacted `payload_summary` containing
`photo_type`, `captured_at`, `uploaded_at`, `content_type`, `size_bytes`,
`sha256`, `original_file_ref`, `manifest_ref`, `local_only=true`, and
`can_train_on=false`. It must not include user filenames, absolute paths,
credentials, headers, cookies, `.env` values, provider payloads, or hidden
reasoning.

## Rules

- Photo upload must validate ActorContext, PlantAccessGrant, content type, size,
  and path safety before accepting the artifact.
- Accepted artifact metadata lives in PostgreSQL/read model; the binary file
  lives on the local filesystem.
- A photo file or manifest can support evidence but cannot promote an agent
  hypothesis to confirmed Plant state by itself.
- A photo artifact can become Vision Observation input only through authorized
  context and real vision/model-backed processing.
- A photo artifact can become a dataset candidate only through dataset
  governance rules; it is non-trainable by default.
- Manifests, logs, timeline events, UI Feed, exports, and agent context must not
  include secrets or auth material.

## Edge Cases And Errors

- Unsupported content type, invalid file, unsafe path, missing Plant access, or
  missing ActorContext must fail closed.
- The applicable canonical subject spec must define the atomicity policy for file write,
  catalog row, manifest, and timeline refs before task creation.
- If cleanup is needed after partial failure, it must not delete unrelated local
  data or retained authorized history.
- Archived Plant photo access requires explicit retained-history authorization.

## Verification

Tests must prove:

- Upload accepts only authorized Plant photos and rejects unsafe files.
- Accepted photo flow produces `sha256`, catalog ref, manifest ref, and audit
  refs without leaking secrets.
- Photo artifacts cannot override PostgreSQL/read-model Plant state.
- Unauthorized or archived-normal-operation access is filtered correctly.
- Dataset trainability remains false unless dataset governance later changes it.
