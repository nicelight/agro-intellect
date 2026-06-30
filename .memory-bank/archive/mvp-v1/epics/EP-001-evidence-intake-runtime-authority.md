---
description: EP-001 - Evidence intake and runtime authority for tomato_001.
status: draft
lifecycle: planned
---
# EP-001 Evidence Intake and Runtime Authority

## Value

Give the daily monitoring loop a trustworthy evidence foundation: daily observations, photos, manual pH/EC measurements, photo manifests, mutable runtime state, and audit/export events are captured for `tomato_001` without mixing their authority boundaries.

## Success metrics

- Daily check-in evidence is traceable to `tomato_001` through state and event references.
- Every accepted photo has canonical catalog metadata, a file reference, `sha256`, and an initial capture manifest.
- Manual pH/EC measurements carry timestamp, provenance, and freshness semantics.
- PostgreSQL/read model remains the runtime authority for mutable operational state.
- `timeline.jsonl` records append-only audit/export events and does not become mutable state.
- Photo manifests remain immutable export/dataset artifacts and do not become mutable runtime authority.

## Acceptance criteria

- The system supports daily check-in observation text for `tomato_001`.
- Manual pH/EC entries include timestamp and provenance.
- pH/EC freshness supports the 24-hour analysis window and the 2-hour physical-action approval window.
- The system accepts photos with required `plant_id`, globally unique `photo_id`, `captured_at`, `photo_type`, file path, and `sha256`.
- Photo binaries are stored as files, not PostgreSQL or InfluxDB blobs.
- Each photo receives an initial capture JSON manifest next to the photo file.
- Initial capture manifests and later export snapshot manifests are distinguishable.
- Photo manifests remain dataset/export artifacts and are not used as runtime authority for mutable state.
- PostgreSQL/read model is the runtime authority for mutable operational state.
- `timeline.jsonl` is append-only audit/export and includes mandatory `payload.plant_id` for `event_type=user_photo`.

## Source artifacts

- [.memory-bank/prd.md](../prd.md): FR-001 through FR-006, authority model, edge cases, acceptance criteria, and verification strategy.
- [.memory-bank/requirements.md](../requirements.md): REQ-001 through REQ-005 and RTM links.
- [.memory-bank/features/FT-001-daily-check-in-observations-manual-measurements.md](../features/FT-001-daily-check-in-observations-manual-measurements.md): daily check-in, observations, and manual measurements.
- [.memory-bank/features/FT-002-photo-intake-catalog-capture-manifests.md](../features/FT-002-photo-intake-catalog-capture-manifests.md): photo intake, catalog, and capture manifests.
- [.memory-bank/features/FT-003-runtime-state-timeline-audit.md](../features/FT-003-runtime-state-timeline-audit.md): runtime state and timeline audit.

## Normative inputs

- [.memory-bank/constitution.md](../constitution.md): AI-first spec discipline, KISS, source-of-truth discipline, Memory Bank, and low-maintenance constraints.
- [.memory-bank/spec-index.md](../spec-index.md): SDD route map for planned runtime data model, photo artifacts, timeline event, source-of-truth, and security specs.
- [.memory-bank/testing/index.md](../testing/index.md): baseline verification strategy.

## Constraints / invariants

- Scope remains one plant: `tomato_001`.
- PostgreSQL/read model owns mutable runtime state.
- `timeline.jsonl` is append-only audit/export, not primary mutable state.
- Photo files and JSON manifests are dataset/export artifacts, not mutable runtime authority.
- File paths or folders cannot replace canonical `plant_id` fields.
- InfluxDB is future-only until real sensors exist.
- Keep the MVP schema minimal and avoid farm-scale abstractions before needed.

## Features included

- [FT-001 Daily Check-in, Observations, and Manual Measurements](../features/FT-001-daily-check-in-observations-manual-measurements.md): user observation text, daily ritual, manual pH/EC entry, provenance, and freshness semantics.
- [FT-002 Photo Intake, Catalog, and Capture Manifests](../features/FT-002-photo-intake-catalog-capture-manifests.md): upload/capture, canonical photo metadata, file storage, `sha256`, MVP photo types, and initial capture manifests.
- [FT-003 Runtime State and Timeline Audit](../features/FT-003-runtime-state-timeline-audit.md): PostgreSQL/read-model authority, mutable state boundaries, append-only timeline events, and audit/export identifiers.
