---
description: Local runtime data model backbone for mutable state and references.
status: active
owner: architecture
last_updated: 2026-05-31
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/spec-index.md
---
# Runtime Data Model

## Scope

This is a conceptual data model for `/spec-design`. It defines MVP entities and authority boundaries. It does not choose exact table names, migrations, ORM, endpoint shapes, or column types; those belong to feature-local `/spec-improve` and implementation tasks.

## Core Entities

| Entity | Minimum responsibility | Authority |
|---|---|---|
| Plant | MVP plant identity and current profile for `tomato_001` | PostgreSQL/read model |
| Daily observation | User text/no-data state, timestamp, provenance, plant ref, event refs | PostgreSQL/read model |
| Manual measurement | pH/EC value, measured_at, provenance, freshness status inputs | PostgreSQL/read model |
| Photo catalog item | `photo_id`, `plant_id`, `captured_at`, `photo_type`, file path, `sha256`, review/dataset/sync refs | PostgreSQL/read model |
| Photo manifest snapshot | Initial capture or export snapshot next to the photo file | Local file artifact |
| Timeline event | Append-only event line with trace identifiers | `timeline.jsonl` |
| Bus event | Agent-consumable domain event | Agent Chat Bus |
| Message envelope | Structured publishable agent output | Agent output contract |
| UI Feed event | Human-facing presentation event | UI Feed |
| Task | Check, measurement, pending approval, action, or follow-up work item | PostgreSQL/read model |
| Human approval | Approval/rejection decision and source refs | PostgreSQL/read model |
| Human review | Manual data/label review decision | PostgreSQL/read model |
| Dataset lifecycle | `dataset.status`, split, curator fields, evidence refs, `can_train_on` | PostgreSQL/read model |
| Sync status | MVP `local_only`, storage bytes, prompt state | PostgreSQL/read model |
| Sensor window ref | Future link to sensor readings or manual measurement window | PostgreSQL/read model as ref only |

## Required Cross-Entity References

- Every plant-bound runtime item must reference `plant_id`; MVP accepted value is `tomato_001`.
- Every accepted photo must have globally unique `photo_id`.
- Photo catalog, photo manifest, and `timeline.jsonl` `user_photo` payload all carry `plant_id`.
- Agent outputs and dataset decisions must carry source/evidence refs where they influence state, tasks, approval, review, or trainability.
- Mutable runtime records should keep event refs to timeline entries where the event is part of the evidence trail.

## Freshness Windows

- pH/EC measurements are fresh for analysis for up to 24 hours.
- pH/EC measurements are fresh for physical-action approval for up to 2 hours.
- Freshness can support analysis or approval checks, but never authorizes a physical action without Safety Gate pass and human approval.

## Minimality Rules

- Do not introduce farm-scale abstractions before the MVP needs them.
- Do not introduce full dataset registry tables before the learning loop requires them.
- Do not make InfluxDB a runtime dependency before real sensors exist.
- Keep future sensor links as references (`sensor_window_ref`) rather than sensor storage.
