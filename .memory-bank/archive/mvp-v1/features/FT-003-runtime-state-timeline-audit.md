---
description: FT-003 - Runtime state and timeline audit.
status: draft
lifecycle: planned
parent_epic: EP-001
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-003-runtime-state-timeline-audit.md
---
# FT-003 Runtime State and Timeline Audit

## Parent Epic

- [EP-001 Evidence Intake and Runtime Authority](../epics/EP-001-evidence-intake-runtime-authority.md): evidence intake and authority boundaries for `tomato_001`.

## Purpose

Define the runtime authority and audit/export boundary for mutable operational state: PostgreSQL/read model owns current state, while `timeline.jsonl` records append-only audit/export events with enough identifiers to reconstruct evidence trails.

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): FR-005, FR-006, authority model, source-of-truth discipline, acceptance criteria, and verification strategy.
- [project_dossier.md](../../project_dossier.md): sections 14 and 20 for PostgreSQL/read-model authority and timeline JSONL context.
- [.memory-bank/requirements.md](../requirements.md): REQ-005, plus runtime-authority parts of REQ-001 through REQ-004.
- [.memory-bank/constitution.md](../constitution.md): Memory Bank, source-of-truth discipline, KISS, and low-maintenance constraints.
- [.memory-bank/spec-index.md](../spec-index.md): route map for source-of-truth, runtime data model, timeline event, and first-demo verification areas.
- [.memory-bank/testing/index.md](../testing/index.md): runtime authority and timeline verification.

## Use Cases

- The system persists current operational state in PostgreSQL/read model.
- Daily observations, photo uploads, agent conclusions, task creation, approvals, safety blocks, and sync events leave audit/export entries.
- Timeline events carry identifiers that trace back to plant, photo, task, approval, agent output, or sync state.
- Mutable review/dataset/sync/plant state is read from runtime authority, not previous JSON snapshots.

## Acceptance Criteria

- PostgreSQL is part of the MVP.
- PostgreSQL/read model is runtime authority for mutable operational state.
- Minimal runtime state includes plants, photo catalog, tasks, human approvals, review statuses, dataset statuses, `can_train_on`, event refs, sync status, and future `sensor_window_ref`.
- The MVP schema stays minimal and avoids broad farm-scale abstractions before needed.
- The system maintains `timeline.jsonl` as an append-only audit/export log.
- Each timeline line represents one event.
- Timeline events include enough identifiers to trace daily observations, photo uploads, agent conclusions, task creation, approvals, safety blocks, and sync events.
- For `event_type=user_photo`, `payload.plant_id` is mandatory and is not inferred only from `topic`.
- `timeline.jsonl` is not primary mutable state.

## Edge Cases / Failure Modes

- A component reads mutable state from `timeline.jsonl` instead of PostgreSQL/read model: reject by design/tests.
- A component reads current mutable state from a photo manifest snapshot: reject by design/tests.
- `user_photo` timeline event lacks `payload.plant_id`: fail validation.
- Timeline event lacks trace identifiers for its domain object: fail validation where identifiers are required.
- Attempted timeline mutation after append: fail append-only verification.
- Schema grows into farm-scale abstractions before PRD need: stop and re-scope.

## Test Strategy Pointers

- `integration:postgres-runtime-authority` for mutable state reads from PostgreSQL/read model.
- `schema:timeline-event` for event shape, identifiers, and mandatory `payload.plant_id` on `user_photo`.
- `policy:append-only-jsonl` for append-only timeline behavior.
- `integration:observation-state-events` for daily observations linked to state/event refs.
- `integration:photo-upload` for photo event refs and catalog linkage.
- `workflow:daily-check-in-smoke` for timeline-backed end-to-end traceability.

## Constraints / Invariants

- PostgreSQL/read model owns mutable runtime state.
- `timeline.jsonl` is append-only audit/export, not primary mutable state.
- Photo files and manifests are dataset/export artifacts, not runtime authority.
- Agno storage, memory, workflow state, and workflow events are not domain authority.
- Keep the runtime schema minimal for one plant.

## SDD Design Gate

Global `/spec-design` completed the shared backbone. Normative backbone inputs for `/spec-improve FT-003`:

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): modular monolith, data flow, sequence, and runtime/audit/artifact authority hierarchy.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): conceptual mutable state entities and refs.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): timeline envelope, append-only rules, and mandatory identifiers.
- [.memory-bank/testing/first-demo.md](../testing/first-demo.md): authority and timeline verification.

Feature-local `/spec-improve FT-003` is complete.

Linked feature-local tech spec:

- [.memory-bank/tech-specs/FT-003-runtime-state-timeline-audit.md](../tech-specs/FT-003-runtime-state-timeline-audit.md): table/migration boundaries, runtime-authority reads, timeline append semantics, payload identifier minimums, API read surface, and verification targets.
