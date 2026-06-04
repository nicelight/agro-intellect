---
description: Feature FT-006 for runtime Plant state, history views, and timeline audit/export separation.
status: draft
lifecycle: planned
spec_design_status: needs_spec_improve
epic: EP-002
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
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

Global `/spec-design` is complete. Before `/prd-to-tasks FT-006`, run
`/spec-improve FT-006` using the completed backbone docs: [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md), [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md), [.memory-bank/states/core-lifecycles.md](../states/core-lifecycles.md), [.memory-bank/contracts/index.md](../contracts/index.md), and [.memory-bank/testing/index.md](../testing/index.md). `/spec-improve` must decide runtime state ownership, history
projection, timeline event taxonomy, and audit/export refs.
