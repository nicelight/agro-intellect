---
description: Implementation plan for FT-005 Photo Intake Catalog and Capture Manifests.
status: active
type: implementation_plan
feature_id: FT-005
last_updated: 2026-07-11
source_of_truth:
  - .memory-bank/features/FT-005-photo-intake-catalog-capture-manifests.md
  - .memory-bank/domains/photo-artifacts.md
  - .memory-bank/contracts/photo-intake-http.md
  - .memory-bank/testing/photo-intake.md
---
# IMPL FT-005 Photo Intake Catalog And Capture Manifests

## Goal

Implement local Plant photo intake with safe upload validation, local artifact
storage, accepted catalog rows, `sha256`, initial capture manifests, and
timeline refs.

## Scope

- Add photo catalog persistence and artifact storage helpers.
- Implement manifest v1 and checksum consistency.
- Enforce active Plant operate authorization.
- Expose protected photo upload/catalog HTTP routes and OpenAPI coverage.
- Preserve `local_only=true` and `can_train_on=false` by default.

## Non-goals

- Vision processing, thumbnails, annotations, export packages, remote sync,
  dataset trainability transitions, Plant history UI, timeline/history
  implementation, and PWA components.

## Constitution Check

- Spec Before Code: tasks derive from FT-005 and linked canonical specs.
- KISS: use local filesystem plus PostgreSQL/read model; no object storage or
  async media pipeline.
- Safety/authority: photo artifacts are evidence refs, not mutable Plant state.
- Security: T3 because uploads touch local filesystem, authorization, and
  retained evidence.
- Blockers: none.

## Direct Canonical Design Links

- `.memory-bank/domains/photo-artifacts.md`
- `.memory-bank/contracts/photo-intake-http.md`
- `.memory-bank/contracts/timeline-event.md`
- `.memory-bank/contracts/access/actor-context.md`
- `.memory-bank/states/plants/plant-and-access-lifecycle.md`
- `.memory-bank/states/dataset-governance.md`
- `.memory-bank/testing/photo-intake.md`

## Dependencies

- `TASK-020-T3-FT-004-W2` provides check-in/operations context and optional
  check-in association.

## Ordered Implementation Strategy

### W1 - Catalog, Artifacts, Manifest Service

`TASK-021-T3-FT-005-W1` implements DB model/migration, filesystem helper,
manifest writer, checksum validation, and acceptance service.

### W2 - HTTP And Integrated Evidence

`TASK-022-T3-FT-005-W2` implements protected multipart upload/catalog routes,
OpenAPI tests, integration flow, behavior-spec traceability, and durable FT-005
docs sync.

### W3 - Catalog Continuation Repair

`TASK-026-T2-FT-005-W3` implements the already advertised catalog cursor as
stable keyset pagination, returns a real `next_cursor`, and proves rows beyond
`limit` are reachable without duplicates or omissions. It depends on the
completed W2 HTTP boundary and leaves accepted upload/artifact semantics
unchanged.

## Expected Touched Areas

- `backend/app/photo_intake/`
- `backend/app/api/photos.py`
- `backend/app/api/__init__.py`
- `backend/app/main.py`
- `backend/migrations/versions/`
- `tests/backend/photo_intake/`
- `tests/backend/api/`
- FT-005 protocol/evidence and Memory Bank docs during execution.

## Verification Strategy

- Focused model/service/filesystem/API tests for FT-005.
- Regression tests for existing auth, Plant access, operations, and admin
  routes.
- Full test suite when practical.
- `node scripts/mb-lint.mjs` and `git diff --check`.
- Multi-row service/HTTP continuation probe with `limit=1`, complete
  enumeration, terminal null cursor, and malformed/wrong-Plant cursor cases.

## UAT

1. Engineer with `tomato_001` access uploads a valid JPEG/PNG/WebP photo.
2. Response returns safe catalog refs, `sha256`, manifest ref, timeline ref,
   `local_only=true`, and `can_train_on=false`.
3. Manifest and stored original agree with catalog metadata.
4. Invalid, oversized, unsupported, unauthorized, or archived uploads fail
   without accepted artifacts.
5. A catalog larger than `limit` is fully enumerable through stable opaque
   cursors, and a supplied cursor is never silently ignored.

## Repair Evidence Basis

- `.tasks/FT-005/FT-005-S-RED-VERIFY-final-report-docs-01.md`
- Existing `TASK-021` and `TASK-022` records remain `done` historical evidence.
