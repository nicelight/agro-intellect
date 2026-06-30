---
description: FT-002 - Photo intake, catalog, and capture manifests.
status: draft
lifecycle: planned
parent_epic: EP-001
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-002-photo-intake-catalog-capture-manifests.md
---
# FT-002 Photo Intake, Catalog, and Capture Manifests

## Parent Epic

- [EP-001 Evidence Intake and Runtime Authority](../epics/EP-001-evidence-intake-runtime-authority.md): evidence intake and authority boundaries for `tomato_001`.

## Purpose

Accept photos for `tomato_001` while preserving canonical photo identity, file storage, capture metadata, checksum integrity, and initial JSON capture manifests without making manifests mutable runtime authority.

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): FR-002, FR-003, photo-related edge cases, acceptance criteria, and verification strategy.
- [.memory-bank/requirements.md](../requirements.md): REQ-002 and REQ-003.
- [.memory-bank/constitution.md](../constitution.md): source-of-truth discipline, KISS, and low-maintenance constraints.
- [.memory-bank/spec-index.md](../spec-index.md): route map for photo artifacts, runtime data model, timeline event, local security, and export snapshot packaging areas.
- [.memory-bank/testing/index.md](../testing/index.md): photo intake, manifest, and upload validation checks.

## Use Cases

- The user uploads one or more photos for `tomato_001`.
- The user assigns an MVP photo type.
- The system stores original photo binaries as files.
- The system creates or records canonical photo catalog metadata.
- The system computes and stores `sha256`.
- The system writes an initial capture JSON manifest next to the photo file.
- Later export snapshot manifests, when produced by an export workflow, can be distinguished from initial capture manifests while remaining photo dataset/export artifacts.

## Acceptance Criteria

- Every uploaded photo has `plant_id`, globally unique `photo_id`, `captured_at`, `photo_type`, file path, and `sha256`.
- `photo_catalog.photo_id` is globally unique.
- `photo_catalog.plant_id` is mandatory and canonical for runtime plant binding.
- Supported MVP photo types are `whole_plant`, `leaf_closeup`, `lower_leaf_closeup`, `top_view`, `stem`, `roots`, `solution_tank`, and `problem_area`.
- Photo binaries are stored as files, not PostgreSQL or InfluxDB blobs.
- Each photo receives an initial generated JSON manifest snapshot next to the photo file.
- Initial capture manifests include schema version, photo identity, file identity, `plant_id`, `captured_at`, `photo_type`, file reference, and `sha256`.
- Initial capture manifests and later export snapshot manifests are distinguishable by manifest purpose and `manifest_kind` (`initial_capture` vs `export_snapshot`).
- Export snapshot manifests, when generated, include `manifest_kind`, `snapshot_at`, and either `snapshot_version` or `export_id`.
- `photo_manifest.plant_id` is mandatory and immutable for export.
- Photo JSON manifests are dataset/export artifacts and do not become runtime authority for mutable state.
- FT-002 preserves the photo artifact/manifest boundary and does not own full export package generation.

## Edge Cases / Failure Modes

- Photo upload without `plant_id`: reject.
- Duplicate `photo_id`: reject.
- Unsupported `photo_type`: reject or require correction before publication.
- Missing file path or `sha256`: reject.
- Manifest generation without an existing photo file: fail validation.
- Manifest missing `plant_id` or file identity: reject.
- Export snapshot manifest missing `manifest_kind`, `snapshot_at`, and both `snapshot_version` and `export_id`: reject.
- File path plant folder conflicts with canonical `plant_id`: fail validation or require correction.
- A previous export snapshot tries to overwrite mutable review/dataset/sync state: reject authority use.

## Test Strategy Pointers

- `schema:photo-catalog` for required metadata and globally unique `photo_id`.
- `schema:photo-manifest` for initial capture and export snapshot fields.
- `integration:photo-upload` for file storage, catalog row/link, manifest creation, and event refs.
- `policy:photo-required-plant-id` for mandatory `plant_id` across catalog, manifest, and timeline binding.
- `integration:initial-vs-export-manifest` for manifest kind/version separation.
- `policy:no-runtime-read-from-stale-manifest` for mutable status authority.
- `security:upload-validation` for size, MIME/content type, safe paths, and path traversal rejection once designed.

## Constraints / Invariants

- Scope is one plant: `tomato_001`.
- Photo files and manifests are dataset/export artifacts.
- PostgreSQL/read model owns mutable photo review, dataset, sync, and plant state.
- File paths cannot replace canonical `plant_id` fields.
- Export snapshot manifests are later export artifacts and cannot replace initial capture manifests.
- InfluxDB is future-only and not a photo binary store.
- Local plant photos and manifests are private project data by default.

## SDD Design Gate

Global `/spec-design` completed the shared backbone. `/spec-improve FT-002` completed the feature-local SDD gate.

- [.memory-bank/domains/photo-artifacts.md](../domains/photo-artifacts.md): photo catalog, file storage, `sha256`, and manifest boundary.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): photo catalog refs and mutable review/dataset/sync ownership.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): `user_photo` audit binding and mandatory `payload.plant_id`.
- [.memory-bank/runbooks/local-security.md](../runbooks/local-security.md): upload validation, path traversal, privacy, and lazy-sync constraints.
- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): manifest/export artifacts are not runtime authority.
- [.memory-bank/tech-specs/FT-002-photo-intake-catalog-capture-manifests.md](../tech-specs/FT-002-photo-intake-catalog-capture-manifests.md): feature-local decisions for photo upload API, backend-generated `photo_id`, file path layout, initial capture manifest v1, publication sequence, timeline payload, and verification targets.
- [.memory-bank/tech-specs/FT-010-local-security-privacy-lazy-sync.md](../tech-specs/FT-010-local-security-privacy-lazy-sync.md): upload size/MIME/path safety and privacy/redaction envelope reused by FT-002.

No FT-002 design blocker remains for `/prd-to-tasks FT-002`.
