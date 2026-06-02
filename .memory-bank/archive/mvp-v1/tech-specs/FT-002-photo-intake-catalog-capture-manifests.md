---
description: Feature-local SDD tech spec for FT-002 photo intake, catalog, and capture manifests.
status: active
owner: architecture
last_updated: 2026-05-31
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/features/FT-002-photo-intake-catalog-capture-manifests.md
  - .memory-bank/spec-index.md
---
# FT-002 Photo Intake, Catalog, and Capture Manifests Tech Spec

## Scope

This spec closes the feature-local SDD design gate for FT-002 before `/prd-to-tasks FT-002`.

FT-002 owns the photo intake workflow for `tomato_001`:

- photo upload API shape;
- photo identity and catalog publication;
- local file path layout for original photo artifacts;
- initial capture manifest shape and write rules;
- `user_photo` timeline publication requirements;
- consistency checks across PostgreSQL, photo file, manifest, checksum, and timeline refs.

FT-002 does not own general upload security limits, LAN auth, CORS, export package generation, mutable review/dataset/sync policy, Vision Agent behavior, or UI layout.

## Normative Inputs

- [.memory-bank/domains/photo-artifacts.md](../domains/photo-artifacts.md): global photo artifact boundary, MVP photo types, manifest kinds, and forbidden uses.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): photo catalog as PostgreSQL/read-model authority and required refs.
- [.memory-bank/tech-specs/FT-003-runtime-state-timeline-audit.md](FT-003-runtime-state-timeline-audit.md): `photo_catalog` table boundary and `user_photo` timeline minimum identifiers.
- [.memory-bank/tech-specs/FT-010-local-security-privacy-lazy-sync.md](FT-010-local-security-privacy-lazy-sync.md): upload limits, MIME allowlist, path traversal rejection, privacy, and redaction boundary.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): append-only timeline envelope and mandatory `user_photo.payload.plant_id`.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): HTTP API shape and error envelope.
- [.memory-bank/testing/index.md](../testing/index.md): photo intake, manifest, upload, and source-of-truth verification gates.
- [.memory-bank/invariants.md](../invariants.md): photo, timeline, privacy, and runtime-authority invariants.

## Design Decisions

### Photo Identity

- The backend generates `photo_id`; clients must not choose authoritative IDs.
- `photo_id` is globally unique and opaque, with a stable `photo_` prefix recommended for readability.
- `photo_id` must not encode mutable state, local absolute paths, user filenames, or future sync status.
- The accepted MVP plant is `tomato_001`. The route `plant_id`, catalog `plant_id`, manifest `plant_id`, and timeline payload `plant_id` must match.
- `captured_at` is required in the accepted catalog record. If the user/client does not provide it, the backend uses upload receive time and records that provenance in the manifest/source metadata.

### File Path Layout

Photo binaries and manifests live under a configured local artifact root. The default MVP relative layout is:

```text
data/plants/{plant_id}/photos/{photo_id}/original.{ext}
data/plants/{plant_id}/photos/{photo_id}/manifest.initial_capture.json
```

Rules:

- `{plant_id}` and `{photo_id}` are generated or validated trusted path segments.
- `{ext}` is derived from the validated MIME/extension allowlist in the FT-010 security spec.
- User-provided filenames are never used as destination paths.
- Stored catalog paths and manifest paths must be relative file references, not local absolute paths.
- The plant folder is a consistency check only; canonical plant binding remains the explicit `plant_id` fields in PostgreSQL, manifest, and timeline payload.
- Existing original files and initial capture manifests must not be overwritten. Re-upload creates a new `photo_id`.

### Upload And Publication Workflow

The accepted photo is published only after the system has all of these artifacts:

- validated upload input;
- original file stored under the safe photo directory;
- computed `sha256`;
- initial capture manifest written next to the photo;
- PostgreSQL `photo_catalog` row with required metadata and refs;
- append-only `user_photo` timeline event with required identifiers.

Recommended MVP sequence:

1. Validate route `plant_id`, `photo_type`, upload size, MIME/content, and safe path constraints.
2. Generate `photo_id` and resolve the final safe photo directory.
3. Write the uploaded binary to a temporary file under the artifact root.
4. Compute `sha256`, `size_bytes`, and validated extension/content metadata.
5. Atomically move the temporary binary to `original.{ext}`.
6. Write `manifest.initial_capture.json` through a temporary file plus atomic rename.
7. Insert or update the PostgreSQL `photo_catalog` row as accepted/ready with file and manifest refs.
8. Append the validated `user_photo` timeline event and store the resulting event ref on the catalog row when supported by the implementation.

If any step fails before publication, the API must not report an accepted photo. Partial files should be cleaned up or left in a non-cataloged quarantine/debug location outside the accepted photo path. A failed upload must not publish `user_photo` to the timeline or Agent Chat Bus.

### Photo Catalog Minimum

The `photo_catalog` boundary from FT-003 remains authoritative. FT-002 refines the minimum accepted-photo fields:

| Field | Rule |
|---|---|
| `photo_id` | Globally unique backend-generated ID. |
| `plant_id` | Mandatory; MVP value `tomato_001`. |
| `captured_at` | Timezone-aware timestamp; user-provided or server receive time. |
| `photo_type` | One of the MVP photo types from photo-artifacts. |
| `file_ref` | Relative path/reference to `original.{ext}`. |
| `manifest_ref` | Relative path/reference to `manifest.initial_capture.json`. |
| `sha256` | SHA-256 digest of the stored original file. |
| `content_type` | Validated MIME/content type from the FT-010 allowlist. |
| `size_bytes` | Non-negative stored original size. |
| `event_refs` | Timeline refs including the accepted `user_photo` event when append succeeds. |
| `review/dataset/sync refs` | Nullable mutable refs owned by their respective features/states. |

Implementation may name columns differently, but the accepted photo must preserve these facts and refs.

### Initial Capture Manifest V1

Initial capture manifests are immutable file-side JSON artifacts. They are not runtime authority for mutable review, dataset, sync, or plant state.

Minimum `manifest.initial_capture.json` shape:

```json
{
  "schema_version": "photo_manifest.v1",
  "manifest_kind": "initial_capture",
  "created_at": "2026-05-31T12:00:00+05:00",
  "photo": {
    "photo_id": "photo_example",
    "plant_id": "tomato_001",
    "captured_at": "2026-05-31T12:00:00+05:00",
    "photo_type": "leaf_closeup"
  },
  "file": {
    "file_ref": "data/plants/tomato_001/photos/photo_example/original.jpg",
    "content_type": "image/jpeg",
    "size_bytes": 123456,
    "sha256": "hex_sha256"
  },
  "source": {
    "source_type": "user",
    "source_id": "local_user",
    "captured_at_source": "user_input|server_received_at",
    "upload_received_at": "2026-05-31T12:00:00+05:00"
  },
  "authority": {
    "authoritative_for_mutable_state": false,
    "runtime_authority": "postgresql_read_model"
  }
}
```

Rules:

- `schema_version`, `manifest_kind`, `photo.photo_id`, `photo.plant_id`, `photo.captured_at`, `photo.photo_type`, `file.file_ref`, and `file.sha256` are mandatory.
- `photo.plant_id` is immutable for this artifact and must match the catalog row and timeline event.
- The manifest must not include secrets, bearer tokens, database URLs, local absolute paths, or raw model reasoning.
- Initial capture manifests must not be overwritten by export snapshots.

### Export Snapshot Compatibility

FT-002 only preserves distinguishability for later export snapshots. It does not implement export package generation.

When a later export workflow creates an `export_snapshot` manifest, the artifact must include:

- `manifest_kind=export_snapshot`;
- `snapshot_at`;
- `snapshot_version` or `export_id`;
- immutable `plant_id` and `photo_id` for the exported photo context.

Export snapshots may copy runtime review/dataset/sync state as a snapshot, but current mutable state must still be read from PostgreSQL/read model.

### Timeline And Bus Boundary

- A successful photo publication must append a `user_photo` timeline event.
- The `user_photo` payload must include at least `plant_id`, `photo_id`, and `photo_type`; implementations should also include `captured_at`, `sha256`, and safe file/manifest refs when available.
- `payload.plant_id` must not be inferred from `topic`, folder, file name, or UI state.
- FT-002 may publish or mirror a photo event to the Agent Chat Bus only through the Bus publication boundary owned by FT-004. Until FT-004 is implemented, timeline/catalog publication remains sufficient for FT-002.

## API Surface

Minimum FT-002-owned API surface:

- `POST /api/plants/{plant_id}/photos`
  - multipart upload with file plus `photo_type`;
  - optional `captured_at`;
  - returns `photo_id`, `plant_id`, `captured_at`, `photo_type`, `sha256`, `file_ref`, `manifest_ref`, and event refs when accepted.
- `GET /api/plants/{plant_id}/photos`
  - returns catalog summaries from PostgreSQL/read model, not by scanning manifest files as authority.
- `GET /api/plants/{plant_id}/photos/{photo_id}`
  - returns one catalog item and artifact refs from PostgreSQL/read model.

All errors use the API guidelines error envelope. Expected machine-readable codes include `validation_error`, `unsupported_photo_type`, `duplicate_photo_id`, `upload_too_large`, `unsupported_media_type`, `unsafe_path`, `manifest_write_failed`, `photo_file_missing`, and `checksum_mismatch`.

## Verification Targets

Required before FT-002 can be marked implemented:

- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- Schema tests for accepted MVP `photo_type`, required catalog fields, globally unique `photo_id`, mandatory `plant_id`, and timezone-aware `captured_at`.
- Upload integration tests proving the FT-010 upload security envelope is applied before accepted-photo publication.
- File artifact tests proving original files are stored under the safe default layout, no absolute paths leak, and user filenames cannot control destination paths.
- Manifest tests proving `manifest.initial_capture.json` is created next to the original file, validates `photo_manifest.v1`, includes required identity/file fields, and excludes secrets/absolute paths.
- Checksum test proving catalog and manifest `sha256` match the stored original file.
- Timeline test proving accepted uploads append `user_photo` with `payload.plant_id`, `photo_id`, and `photo_type`.
- Authority test proving catalog reads come from PostgreSQL/read model, not from scanning photo manifests.
- Failure tests for missing `plant_id`, unsupported `photo_type`, missing file, unsafe path, duplicate `photo_id`, manifest write failure, checksum mismatch, and orphan cleanup/quarantine behavior.

## Gaps And Non-Goals

- No FT-002 blocker remains for `/prd-to-tasks FT-002`.
- Exact ORM model names, Alembic revision names, storage helper names, and fixture file names belong to implementation tasks.
- Thumbnail generation, image annotation, EXIF normalization, HEIC/RAW support, export package generation, remote upload/sync, server-side verification, and Vision Agent analysis are outside FT-002 MVP scope.
