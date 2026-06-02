---
description: Photo catalog, file artifact, and manifest boundary for MVP photo intake.
status: active
owner: architecture
last_updated: 2026-05-31
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/spec-index.md
---
# Photo Artifacts

## Purpose

This spec defines the global photo artifact boundary for `tomato_001`: runtime catalog metadata lives in PostgreSQL/read model, while photo binaries and JSON manifests live in local file storage as dataset/export artifacts.

## MVP Photo Types

- `whole_plant`
- `leaf_closeup`
- `lower_leaf_closeup`
- `top_view`
- `stem`
- `roots`
- `solution_tank`
- `problem_area`

## Catalog Requirements

Every accepted photo must have:

- `photo_id` globally unique;
- `plant_id` mandatory and canonical for runtime binding;
- `captured_at`;
- `photo_type`;
- safe local file path/reference;
- `sha256`;
- refs for review, dataset, sync, and timeline where available.

File path folders may help validation, but they are not canonical plant binding.

## File Storage Rules

- Store original photo binaries as files, not PostgreSQL or InfluxDB blobs.
- Store initial capture JSON manifests next to the photo file at upload/capture time.
- Derived files such as thumbnails or annotations may be local artifacts, but they do not replace originals or catalog authority.
- Upload handling must validate size, MIME/content type, safe paths, and path traversal before accepting files.

## Manifest Kinds

| Kind | Created when | Minimum purpose | Authority |
|---|---|---|---|
| `initial_capture` | Upload/capture time | Immutable identity snapshot for the photo artifact | File artifact only |
| `export_snapshot` | Later export workflow | Immutable snapshot of selected runtime/sensor/agent/review context | File artifact only |

Initial capture manifests must include schema version, photo identity, file identity, `plant_id`, `captured_at`, `photo_type`, file reference, and `sha256`.

Export snapshot manifests must include `manifest_kind`, `snapshot_at`, and `snapshot_version` or `export_id`. They may include plant context, system state, agent reports, review/dataset/sync snapshots, and future sensor window refs when those data exist.

## Forbidden Uses

- Do not read current mutable review, dataset, sync, or plant state from a previous manifest.
- Do not infer `plant_id` only from topic, folder, file name, or UI state.
- Do not overwrite initial capture manifests with export snapshots.
