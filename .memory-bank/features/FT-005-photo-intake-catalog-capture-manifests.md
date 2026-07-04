---
description: FT-005 Photo Intake Catalog And Capture Manifests.
status: draft
type: feature
feature_id: FT-005
epic: EP-002
lifecycle: planned
last_updated: 2026-06-26
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

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Photo & Artifact Intake module and storage decisions.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): artifact vs runtime authority.
- [.memory-bank/domains/photo-artifacts.md](../domains/photo-artifacts.md): global photo artifact identity, local-only authority, and cross-feature refs.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): upload validation and local-only semantics.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): audit/export event refs for accepted photos.

## Feature-Local Design Pressure

- Exact photo storage layout, manifest schema, validation rules,
  file/catalog/manifest atomicity, failure recovery, and audit/export refs.
