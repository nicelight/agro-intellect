---
description: Feature FT-004 for authorized Plant selector and daily check-in workflow.
status: active
owner: product
lifecycle: planned
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-004-authorized-plant-selector-and-daily-check-in.md
epic: EP-002
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/user-scenarios.md
  - .memory-bank/tech-specs/FT-004-authorized-plant-selector-and-daily-check-in.md
---
# FT-004 Authorized Plant Selector And Daily Check-In

## Use Cases

- Engineer selects only assigned Plants and starts daily check-in for `tomato_001`.
- Boss performs the same workflow with admin/owner access.
- Consultant, when present, sees only granted advisory/read/comment context.

## Acceptance Criteria

- Authorized users can select only authorized active Plants.
- Daily check-in supports observations, photo upload entry point, manual pH/EC entry,
  Plant card/history, tasks, approvals, and follow-up entry points.
- Every check-in record is actor/Farm/Plant scoped.
- Archived Plants are removed from normal operations.
- Check-in events can trigger agent-consumable publication only through allowed backend boundaries.

## Edge Cases & Failure Modes

- Missing PlantAccessGrant blocks Plant selector visibility and mutations.
- Stale or missing pH/EC is represented explicitly for downstream advisor/safety behavior.
- UI cannot submit data for a Plant not present in ActorContext.
- Check-in cannot write secrets or session material to audit/export surfaces.

## Test Strategy Pointers

- `test:plant.authorized-daily-flow`
- `test:auth.plant-access-grants`
- `test:runtime.authority-vs-timeline`

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): first working flow and daily Plant operations requirements.
- [.memory-bank/user-scenarios.md](../user-scenarios.md): Engineer performs authorized Plant operations.
- [.memory-bank/contracts/boundary-map.md](../contracts/boundary-map.md): Plant operations UI to runtime state boundary.

## SDD Design Gate

Global `/spec-design` and feature-level `/spec-improve FT-004` are complete. Use
[.memory-bank/tech-specs/FT-004-authorized-plant-selector-and-daily-check-in.md](../tech-specs/FT-004-authorized-plant-selector-and-daily-check-in.md)
as the feature-local design hub before `/prd-to-tasks FT-004`.
