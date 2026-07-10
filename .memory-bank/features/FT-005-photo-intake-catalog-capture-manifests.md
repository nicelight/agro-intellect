---
description: FT-005 Photo Intake Catalog And Capture Manifests.
status: active
type: feature
feature_id: FT-005
epic: EP-002
lifecycle: planned
last_updated: 2026-07-10
spec_design_status: complete
spec_design_links:
  - .memory-bank/domains/photo-artifacts.md
  - .memory-bank/contracts/photo-intake-http.md
  - .memory-bank/contracts/timeline-event.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
  - .memory-bank/states/dataset-governance.md
  - .memory-bank/testing/photo-intake.md
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/contracts/boundary-map.md
---
# FT-005 Photo Intake Catalog And Capture Manifests

## Use Cases

- Authorized user uploads a Plant photo during check-in.
- Backend stores the original local photo file.
- Backend records accepted catalog metadata, `sha256`, initial capture manifest, export-ready refs, and timeline audit refs.
- Photo evidence becomes available to real vision processing and future dataset governance through refs.

## Acceptance Criteria

- Photo intake stores local files and catalog rows for accepted photos.
- `sha256` is recorded for file identity/integrity.
- Initial capture manifest is created at upload/capture time.
- Timeline audit/export refs are created without making timeline the runtime authority.
- Photo artifacts remain local and private by default.

## Edge Cases & Failure Modes

- Unauthorized upload fails closed.
- Unsupported or invalid file is rejected.
- File write/catalog/manifest sequence cannot leave accepted metadata without retrievable local artifact after final success.
- Secrets/auth material never enter photo manifests or export snapshots.

## Verification Targets

- Unit: upload validation and checksum behavior.
- Integration: file/catalog/manifest/timeline refs are created and linked.
- E2E: upload photo for `tomato_001` and verify visible authorized history refs.

## Behavior specs

- `.memory-bank/behavior-specs/FT-005-BHV-001-accepted-photo-artifacts.behavior.json`
- `.memory-bank/behavior-specs/FT-005-BHV-002-invalid-photo-no-accepted-artifact.behavior.json`
- `.memory-bank/behavior-specs/FT-005-BHV-003-archived-photo-upload-denied.behavior.json`

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Photo & Artifact Intake module and storage decisions.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): artifact vs runtime authority.
- [.memory-bank/domains/photo-artifacts.md](../domains/photo-artifacts.md): global photo artifact identity, local-only authority, and cross-feature refs.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): upload validation and local-only semantics.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): audit/export event refs for accepted photos.

## Feature-Local Design Pressure

- Exact photo storage layout, manifest schema, validation rules,
  file/catalog/manifest atomicity, failure recovery, and audit/export refs.

## Specification Composition

Status: complete.

- [Photo Artifacts](../domains/photo-artifacts.md) defines artifact authority,
  accepted catalog rows, storage layout, manifest v1, upload atomicity, and
  local-only/default trainability rules.
- [Photo Intake HTTP](../contracts/photo-intake-http.md) defines multipart
  upload and catalog read routes, accepted MIME/size policy, response shapes,
  and stable errors.
- [Timeline Event](../contracts/timeline-event.md) defines the `photo_accepted`
  event and append/replay rules.
- [ActorContext](../contracts/access/actor-context.md) and [Plant And Access Lifecycle](../states/plants/plant-and-access-lifecycle.md)
  define operate permission, retained-history constraints, and archived-Plant
  upload denial.
- [Dataset Governance](../states/dataset-governance.md) keeps accepted photos
  non-trainable by default.
- [Photo Intake Verification](../testing/photo-intake.md) defines the focused
  evidence matrix.

Vision processing, Plant history display, and PWA UI remain outside FT-005.

## Implementation

- [Implementation plan](../tasks/plans/IMPL-FT-005.md): ordered task queue,
  dependencies, verification strategy, and UAT.
