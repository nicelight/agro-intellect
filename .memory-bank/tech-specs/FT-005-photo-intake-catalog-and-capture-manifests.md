---
description: Feature-local SDD tech spec for FT-005 photo intake, local catalog, sha256, capture manifests, and refs.
status: active
feature_id: FT-005
owner: spec-improve
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/features/FT-005-photo-intake-catalog-and-capture-manifests.md
  - .memory-bank/requirements.md
  - .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
  - .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
  - .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/states/core-lifecycles.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/agent-chat-bus.md
---
# FT-005 Photo Intake, Catalog, And Capture Manifests Tech Spec

## Purpose

Define the minimum feature-local design needed before task decomposition for local photo
upload intake, validation, file storage, catalog metadata, `sha256`, initial capture
manifests, export-ready refs, timeline audit refs, and authorization checks.

This spec refines global photo artifact rules and depends on FT-001 ActorContext,
FT-002 PlantAccessGrant/Plant lifecycle, and FT-017 privacy/redaction.

## Scope

In scope:

- authorized photo upload for active Plants;
- upload validation before catalog/timeline publication;
- local original file storage;
- backend-generated stable photo refs;
- `sha256` calculation over stored original bytes;
- `PhotoCatalogItem` metadata in PostgreSQL/read model;
- adjacent `PhotoManifest` with `initial_capture` kind;
- timeline audit/export refs and optional Bus photo-ref publication;
- unauthorized metadata/file access denial.

Out of scope:

- Vision Observation Agent processing, model output, diagnosis, or recommendations;
- mutable Plant state updates from photo content;
- dataset trainability changes or full dataset registry;
- object storage, server upload, cloud sync, or external photo hosting;
- broad image editing or derived artifact pipeline beyond optional thumbnails/derived
  refs.

## Authority And Lifecycle

PostgreSQL/read model photo catalog is authority for accepted photo metadata and stable
refs. Local filesystem stores photo binary artifacts. Manifest and timeline refs are
artifact/audit/export layers, not mutable runtime authority.

PhotoArtifact lifecycle follows:

```yaml
pending_validation -> accepted
pending_validation -> rejected
pending_validation -> orphan_recovery
```

Rules:

- invalid upload is rejected before catalog/timeline/Bus publication;
- file write or checksum failure must not create an accepted catalog item;
- if a crash leaves a file without accepted catalog state, recovery must classify it as
  non-authoritative `orphan_recovery` or remove it through a safe local cleanup task;
- accepted photo refs remain valid after Plant archive for authorized history/export.

## Intake Validation

Photo upload must validate, at minimum:

- resolved ActorContext;
- active FarmMembership and active Plant;
- PlantAccessGrant or Boss authority for the target Plant;
- allowed upload content type and actual file signature;
- bounded file size chosen during task decomposition;
- non-empty file;
- safe server-generated filename/path;
- redaction of supplied metadata before persistence;
- local storage policy and local-only deployment constraints.

Use server-generated paths and IDs. User-supplied filenames are display metadata only
after sanitization and must not become filesystem authority.

## Storage Layout And Identity

Minimum identity semantics:

```yaml
photo_id: string
photo_ref: photo:<photo_id>
farm_id: string
plant_id: string
checkin_id: string | null
uploaded_by_actor_ref: string
original_sha256: string
original_mime_type: string
original_size_bytes: integer
storage_relpath: string
manifest_ref: manifest:<manifest_id>
timeline_refs: []
created_at: datetime
state: accepted | rejected | orphan_recovery
redaction_status: redacted | no_sensitive_fields
```

KISS storage path guidance:

```text
photos/<farm_id>/<plant_id>/<photo_id>/original.<ext>
photos/<farm_id>/<plant_id>/<photo_id>/manifest.initial_capture.json
```

Task decomposition may adjust exact directories/extensions, but paths must be
server-generated, scoped, traversal-safe, local-only, and free of secrets/session data.

Duplicate `sha256` handling can remain simple: accepted duplicate bytes may create a new
catalog item when actor/check-in/source refs differ, but must preserve the checksum and
avoid overwriting existing files. A deduplication store is out of FT-005 MVP scope.

## Capture Manifest

Minimum `initial_capture` manifest semantics:

```yaml
manifest_id: string
manifest_kind: initial_capture
schema_version: string
photo_ref: photo:<photo_id>
farm_id: string
plant_id: string
checkin_id: string | null
uploaded_by_actor_ref: string
captured_at: datetime | null
received_at: datetime
original_sha256: string
original_size_bytes: integer
original_mime_type: string
storage_relpath: string
catalog_ref: photo_catalog:<photo_id>
timeline_refs: []
redaction_status: redacted | no_sensitive_fields
```

Manifest rules:

- manifest is created only for accepted photos;
- manifest stores refs and bounded metadata, not raw auth/session material, provider
  credentials, `.env` values, hidden reasoning, raw chat, or UI markdown;
- manifest may include sanitized device/capture metadata only after redaction;
- manifest cannot overwrite runtime Plant state or dataset trainability.

## Publication And Access

After acceptance, backend may create:

- `PhotoCatalogItem` in PostgreSQL/read model;
- local original file;
- `initial_capture` manifest;
- timeline audit/export event ref;
- optional Bus `photo_ref_attached` event with refs only.

Publication rules:

- publish after accepted catalog/file/manifest refs exist;
- Bus payloads include refs, scope, `sha256`, trust label, and redaction status, not raw
  image bytes;
- photo file reads require ActorContext and authorized Plant access;
- revoked PlantAccessGrant blocks future normal retrieval without deleting retained
  evidence;
- archived Plant photos remain available only through authorized history/audit/export
  paths.

## API Surface To Refine In Tasks

Task decomposition may define exact endpoint and schema details for:

- upload photo for a Plant and optional CheckIn;
- read photo catalog item;
- stream/download authorized photo file;
- read initial capture manifest;
- list photo refs for authorized Plant/history view;
- recover or report orphaned local files.

Generated OpenAPI comes from implementation schemas later.

## Verification Targets

Required tests before FT-005 can be considered implemented:

- unauthorized upload/read is denied for missing/revoked PlantAccessGrant, archived
  normal-flow Plant, invalid session, and disabled membership;
- invalid MIME/signature/empty/oversized uploads are rejected before catalog, manifest,
  timeline, or Bus publication;
- accepted upload writes local file, computes `sha256`, creates catalog item, creates
  `initial_capture` manifest, and returns stable refs;
- file write/checksum failure leaves no accepted authoritative catalog state;
- duplicate bytes do not overwrite existing photo files or refs;
- manifest and timeline payloads redact secrets/auth material and exclude user-supplied
  unsafe filenames as authority;
- photo refs remain accessible for authorized history after Plant archive;
- photo files/manifests/timeline refs cannot mutate runtime Plant state or dataset
  trainability;
- real Vision Observation later receives only authorized accepted photo refs and actual
  local photo data, not test-only mock payloads in runtime/demo.

## Open Questions

No blocker for `/prd-to-tasks FT-005`. Exact size limit, MIME allowlist, thumbnail
policy, recovery cleanup command, and route names can be chosen during task
decomposition while preserving local-only storage, failure ordering, stable refs,
authorization, and redaction.
