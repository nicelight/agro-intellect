---
description: Feature FT-005 for photo intake, local files, catalog metadata, sha256, capture manifests, and timeline refs.
status: active
owner: product
lifecycle: planned
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-005-photo-intake-catalog-and-capture-manifests.md
epic: EP-002
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/contracts/boundary-map.md
  - .memory-bank/tech-specs/FT-005-photo-intake-catalog-and-capture-manifests.md
---
# FT-005 Photo Intake, Catalog, And Capture Manifests

## Use Cases

- Engineer uploads a real Plant photo during check-in.
- Backend stores local photo file, catalog row, `sha256`, initial capture manifest, and timeline refs.
- Real Vision Observation Agent later processes the actual uploaded photo data.

## Acceptance Criteria

- Photo intake stores local photo files and accepted catalog metadata.
- Each accepted photo has `sha256`, stable refs, initial capture manifest, and timeline audit/export refs.
- Photo file and manifest artifacts are not mutable runtime authority.
- Photo refs are actor/Farm/Plant scoped and export-ready.
- Unauthorized users cannot access unauthorized photo metadata or files.

## Edge Cases & Failure Modes

- Invalid upload is rejected before catalog/timeline publication.
- File write failure does not create orphan authoritative runtime state.
- Duplicate or conflicting file identity is handled explicitly in later specs.
- Secret/session/auth material cannot enter photo manifests or filenames.

## Test Strategy Pointers

- `test:photo.file-catalog-sha256-manifest`
- `test:runtime.authority-vs-timeline`
- `test:privacy.secret-redaction-surfaces`

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): photo intake requirements.
- [.memory-bank/contracts/boundary-map.md](../contracts/boundary-map.md): photo intake boundary hints.
- [.memory-bank/states/lifecycle-map.md](../states/lifecycle-map.md): photo artifact lifecycle hints.

## SDD Design Gate

Global `/spec-design` and feature-level `/spec-improve FT-005` are complete. Use
[.memory-bank/tech-specs/FT-005-photo-intake-catalog-and-capture-manifests.md](../tech-specs/FT-005-photo-intake-catalog-and-capture-manifests.md)
as the feature-local design hub before `/prd-to-tasks FT-005`.
