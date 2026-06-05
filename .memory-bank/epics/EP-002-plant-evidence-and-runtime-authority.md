---
description: Epic EP-002 for authorized Plant operations, evidence intake, runtime state, timeline, and history.
status: active
owner: product
lifecycle: planned
epic_id: EP-002
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/contracts/boundary-map.md
  - .memory-bank/states/lifecycle-map.md
---
# EP-002 Plant Evidence And Runtime Authority

## Value

Make the daily Plant workflow useful and auditable: authorized check-ins, observations,
manual pH/EC, photo evidence, runtime state, Plant history, local artifacts, and
append-only export/audit refs.

## Features

- FT-004 Authorized Plant Selector And Daily Check-In.
- FT-005 Photo Intake, Catalog, And Capture Manifests.
- FT-006 Runtime Plant State, History, And Timeline Audit.

## Success Metrics

- Boss and Engineer can complete the first authorized Plant workflow on `tomato_001`.
- Photo upload produces a local file, catalog row, `sha256`, initial capture manifest,
  and audit/export refs.
- Mutable Plant state is persisted in PostgreSQL/read model, not timeline or files.
- Archived Plants disappear from normal operations but remain available for authorized
  history/audit/export access.

## Acceptance Criteria

- Authorized users can select only authorized Plants.
- Daily check-in captures observations, photos, pH/EC, and relevant refs.
- Runtime state and history remain actor/Farm/Plant scoped.
- `timeline.jsonl` remains append-only audit/export and cannot replace runtime state.
- Photo files and manifests remain local artifacts and cannot replace runtime state.

## Constraints / Invariants

- `tomato_001` is the initial Plant and migration seed, not a permanent limit.
- Photo catalog, file, manifest, upload-validation, and photo timeline details are
  specified by the active FT-005 tech spec and task records.
- Secrets/session/auth material must never enter manifests, timeline, Bus, UI Feed,
  screenshots, exports, or agent context.

## Verification Targets

- `test:plant.authorized-daily-flow`
- `test:photo.file-catalog-sha256-manifest`
- `test:runtime.authority-vs-timeline`
