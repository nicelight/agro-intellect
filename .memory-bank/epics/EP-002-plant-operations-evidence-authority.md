---
description: EP-002 Plant Operations Evidence Authority.
status: draft
type: epic
epic_id: EP-002
lifecycle: planned
last_updated: 2026-06-14
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/user-scenarios.md
  - .memory-bank/domains/core-domain.md
---
# EP-002 Plant Operations Evidence Authority

## Value

Make authorized Plant care workflows useful and traceable while preserving the separation between mutable runtime state, local artifacts, and append-only audit/export.

## Features

- [FT-004 Authorized Plant Operations And Daily Check-In](../features/FT-004-authorized-plant-operations-daily-check-in.md)
- [FT-005 Photo Intake Catalog And Capture Manifests](../features/FT-005-photo-intake-catalog-capture-manifests.md)
- [FT-006 Runtime State Timeline And Plant History](../features/FT-006-runtime-state-timeline-plant-history.md)

## Success Metrics

- Boss and Engineer can complete the first authorized Plant workflow on `tomato_001`.
- Photo upload produces local file, catalog metadata, checksum, manifest, and audit refs.
- Runtime state remains separate from timeline/export artifacts.

## Acceptance Criteria

- Plant operations are scoped by ActorContext and PlantAccessGrant.
- Daily check-in supports observations, manual pH/EC, photos, Plant card/history, tasks, approvals, and follow-up entry points.
- Archived Plants are removed from normal operations but retained for authorized history/audit/export access.
- `timeline.jsonl` remains audit/export only.

## Constraints / Invariants

- PostgreSQL/read model remains mutable runtime authority until an active architecture spec changes it.
- Photo files and manifests are local artifacts, not mutable runtime authority.
- Secrets/auth material never enter timeline, manifests, screenshots, exports, Bus, UI Feed, or agent context.

## Feature-Local Questions For /spec-improve

- Exact storage layout and manifest fields.
- Exact timeline event taxonomy.
- Exact daily check-in state model and persistence sequence.
