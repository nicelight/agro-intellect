---
description: Feature FT-002 for one local Farm, Plant lifecycle, tomato_001 migration, and PlantAccessGrant.
status: draft
lifecycle: planned
spec_design_status: needs_spec_improve
epic: EP-001
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/states/lifecycle-map.md
---
# FT-002 Farm, Plant Lifecycle, And PlantAccessGrant

## Use Cases

- Boss uses the single local Farm workspace.
- Boss creates or confirms `tomato_001` as the initial Plant.
- Boss grants Engineer access to selected Plants.
- Boss archives/restores a Plant while retaining authorized history.

## Acceptance Criteria

- MVP supports exactly one local Farm workspace.
- MVP supports multiple Plants inside that Farm; `tomato_001` is the initial Plant.
- Plant create, archive, and restore are supported; hard delete is absent.
- Archived Plants disappear from normal operational flows but retain authorized history, photos, tasks, outcomes, timeline audit, and admin audit.
- PlantAccessGrant controls per-Plant visibility and work authorization.
- `plant_approve_actions` is the only MVP per-permission override.

## Edge Cases & Failure Modes

- User without PlantAccessGrant cannot see or mutate the Plant and cannot receive its agent context.
- Revoked access removes normal visibility without deleting historical audit.
- Archive cannot erase evidence or make old refs invalid.
- Multi-Farm membership/tenancy is not introduced accidentally.

## Test Strategy Pointers

- `test:farm.single-local-workspace`
- `test:plant.lifecycle-archive-restore-retention`
- `test:auth.plant-access-grants`

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): one Farm, multiple Plants, archive/restore, access grants.
- [.memory-bank/states/lifecycle-map.md](../states/lifecycle-map.md): Plant and PlantAccessGrant lifecycle hints.
- [.memory-bank/invariants.md](../invariants.md): bounded local-first MVP scope.

## SDD Design Gate

Global `/spec-design` is complete. Before `/prd-to-tasks FT-002`, run
`/spec-improve FT-002` using the completed backbone docs: [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md), [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md), [.memory-bank/states/core-lifecycles.md](../states/core-lifecycles.md), [.memory-bank/contracts/index.md](../contracts/index.md), and [.memory-bank/testing/index.md](../testing/index.md). `/spec-improve` must decide Plant lifecycle states,
PlantAccessGrant representation, access filtering, archive visibility, and retained
history semantics.
