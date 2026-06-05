---
description: Implementation plan for FT-005 Photo Intake, Catalog, And Capture Manifests.
status: active
---
# IMPL-FT-005 Photo Intake, Catalog, And Capture Manifests

## Goals

- Implement authorized photo upload validation before any catalog, manifest, timeline,
  or Bus publication.
- Store local original files with server-generated safe paths, calculate `sha256`, and
  create authoritative `PhotoCatalogItem` metadata plus initial capture manifests.
- Provide authorized photo/catalog/manifest reads and CheckIn/Bus integration without
  treating files, manifests, or timeline refs as mutable runtime authority.

## Constitution Check

- Aligns with Spec Before Code, local-first/private scope, data authority separation,
  secret redaction, and risk-based DoD.
- No conflict found with the Constitution.
- Tier policy: all slices are T3 because authorized file upload/read, local paths,
  user-supplied metadata, manifests, Bus refs, and redaction-sensitive surfaces are
  security-sensitive.
- KISS boundary: local filesystem only; no object storage, server upload, cloud sync,
  broad derived-artifact pipeline, or dataset trainability changes.

## Source Artifacts

- .memory-bank/features/FT-005-photo-intake-catalog-and-capture-manifests.md
- .memory-bank/tech-specs/FT-005-photo-intake-catalog-and-capture-manifests.md
- .memory-bank/epics/EP-002-plant-evidence-and-runtime-authority.md
- .memory-bank/requirements.md
- .tasks/SPEC-IMPROVE-REVIEW/final-report.md

## Normative Inputs

- .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
- .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
- .memory-bank/tech-specs/FT-004-authorized-plant-selector-and-daily-check-in.md
- .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
- .memory-bank/architecture/system-architecture.md
- .memory-bank/domains/runtime-data-model.md
- .memory-bank/states/core-lifecycles.md
- .memory-bank/contracts/api-guidelines.md
- .memory-bank/contracts/agent-chat-bus.md
- .memory-bank/testing/index.md
- agents-best-practices: uploads are untrusted data; storage and publication tools
  must be narrow, schema-validated, permissioned, failure-safe, traceable, redacted,
  and return bounded refs rather than raw blobs.

## Constraints

- PostgreSQL/read model photo catalog is authority for accepted metadata and stable
  refs; local files store binary artifacts; manifests/timeline are artifact/audit
  layers.
- Invalid upload is rejected before catalog/timeline/Bus publication.
- File write or checksum failure creates no accepted authoritative catalog state.
- Server-generated paths and IDs are authority; user filenames are sanitized display
  metadata only.
- Photo files, manifests, timeline refs, and Bus refs cannot mutate runtime Plant state
  or dataset trainability.

## Invariants

- Photo upload/read requires resolved ActorContext and authorized Plant access.
- Secret/session/auth material cannot enter filenames, manifests, timeline, Bus, UI
  Feed, screenshots, exports, logs, or agent context.
- Accepted duplicate bytes do not overwrite existing files or refs.
- Accepted photo refs remain available after Plant archive only through authorized
  history/audit/export paths.

## Steps

1. Implement authorized photo upload validation, safe local storage paths, and sha256.
2. Persist `PhotoCatalogItem`, initial capture manifest, and timeline/export refs in a
   failure-safe sequence.
3. Add authorized catalog/file/manifest reads and archive-history access filters.
4. Integrate accepted photo refs with CheckIn and optional Bus `photo_ref_attached`
   publication.
5. Add photo upload/catalog UI and e2e smoke.
6. Add failure-ordering, orphan recovery, duplicate bytes, OpenAPI, and security
   regression coverage.

## Expected Touched Files

- backend/app/photo_artifacts/*
- backend/app/plant_operations/*
- backend/app/access/*
- backend/app/publication/*
- backend/app/db/migrations/*
- backend/app/api/*
- frontend/src/*
- backend/tests/photo_artifacts/*
- backend/tests/integration/*
- backend/tests/security/*
- frontend/tests/*
- .memory-bank/changelog.md

## Tests

- Unit: MIME/signature/size/path validation, sha256, manifest shaping, redaction.
- Integration: unauthorized upload/read denial, accepted upload sequence, failure
  ordering, duplicate bytes, archive-history access.
- Contract: generated OpenAPI validation and BusEventEnvelope validation for
  `photo_ref_attached`.
- UI/e2e: upload a real photo during check-in and view catalog/manifest refs.
- Security: no secrets/auth material/user filename authority in manifests, filenames,
  timeline, Bus, UI Feed, screenshots, exports, or agent context.

## Quality Gates

- pytest backend/tests/photo_artifacts backend/tests/integration backend/tests/security
- Frontend/UI smoke or e2e evidence under the task report when a frontend test runner exists; otherwise record the missing-runner reason in /verify
- generated OpenAPI validation after implementation schemas exist
- Bus/event contract tests for accepted photo refs and redaction
- node scripts/mb-lint.mjs
- node scripts/mb-doctor.mjs
- /verify and /red-verify before T3 closure
- T3 human checkpoint and rollback/recovery note before closure

## UAT Steps

- Authorized Engineer uploads a real `tomato_001` photo during check-in and receives a
  stable photo ref, sha256, catalog item, manifest ref, and timeline/export refs.
- Unauthorized user cannot upload, list, read, stream, or download photo artifacts.
- Invalid/empty/oversized/mismatched uploads create no accepted catalog or Bus event.
- Archived Plant photos remain available through authorized history, not normal
  operations.

## Task Slice

- TASK-029: Authorized photo upload validation, local storage, and sha256 foundation.
- TASK-030: PhotoCatalogItem, initial capture manifest, and timeline refs.
- TASK-031: Authorized photo catalog/file/manifest read and archive-history filters.
- TASK-032: CheckIn photo integration and Bus `photo_ref_attached` publication.
- TASK-033: Photo upload/catalog UI and e2e smoke.
- TASK-034: Photo failure, orphan recovery, duplicates, OpenAPI, and security tests.

