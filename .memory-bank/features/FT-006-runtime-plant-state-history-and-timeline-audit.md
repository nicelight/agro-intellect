---
description: Feature FT-006 for runtime Plant state, history views, and timeline audit/export separation.
status: active
owner: product
lifecycle: planned
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-006-runtime-plant-state-history-and-timeline-audit.md
epic: EP-002
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/tech-specs/FT-006-runtime-plant-state-history-and-timeline-audit.md
---
# FT-006 Runtime Plant State, History, And Timeline Audit

## Use Cases

- User sees Plant card/history based on authorized runtime state and audit refs.
- Backend persists observations, measurements, task refs, approval refs, and outcome refs.
- Timeline export preserves append-only evidence without becoming mutable authority.

## Acceptance Criteria

- PostgreSQL/read model remains mutable runtime authority for operational state.
- `timeline.jsonl` remains append-only audit/export only.
- Plant card/history is actor/Farm/Plant scoped and excludes unauthorized Plants.
- Runtime records can reference timeline/photo/task/approval/outcome evidence without delegating authority to those artifacts.
- Archived Plant history remains available to authorized roles.

## Edge Cases & Failure Modes

- Timeline replay cannot overwrite runtime state.
- Missing or stale evidence produces explicit unknown/probable/conflict style state, not silent confirmation.
- Unauthorized history and audit refs are filtered.
- Admin UI notices, UI markdown, and UI Feed cards cannot become Plant facts.

## Test Strategy Pointers

- `test:runtime.authority-vs-timeline`
- `test:plant.lifecycle-archive-restore-retention`
- `test:auth.actor-context-all-boundaries`

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): runtime state and timeline requirements.
- [.memory-bank/invariants.md](../invariants.md): PostgreSQL/read model and timeline authority guardrails.
- [.memory-bank/domains/core-domain.md](../domains/core-domain.md): TimelineEvent and runtime authority rules.

## SDD Design Gate

Global `/spec-design` and feature-level `/spec-improve FT-006` are complete. Use
[.memory-bank/tech-specs/FT-006-runtime-plant-state-history-and-timeline-audit.md](../tech-specs/FT-006-runtime-plant-state-history-and-timeline-audit.md)
as the feature-local design hub before `/prd-to-tasks FT-006`.
