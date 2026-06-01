---
description: Feature-local SDD tech spec for FT-003 runtime state and timeline audit.
status: active
owner: architecture
last_updated: 2026-05-31
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/features/FT-003-runtime-state-timeline-audit.md
  - .memory-bank/spec-index.md
---
# FT-003 Runtime State and Timeline Audit Tech Spec

## Scope

This spec closes the feature-local SDD design gate for FT-003 before `/prd-to-tasks FT-003`.

FT-003 owns the minimum runtime-state and audit/export foundation for the MVP:

- PostgreSQL/read-model authority for mutable operational state.
- Minimal table boundaries and migration policy for current-state entities.
- `timeline.jsonl` append-only audit/export implementation rules.
- Common timeline payload identifier requirements.
- Runtime-authority and append-only verification targets.

FT-003 does not own photo file storage, photo manifest content, agent output contracts, UI Feed contracts, Safety Gate policy, or dataset-trainability policy beyond storing their mutable refs/statuses in PostgreSQL.

## Normative Inputs

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): local modular monolith, backend responsibility for persistence and timeline append, source-of-truth hierarchy, and module boundaries.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): conceptual entity/ref model.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): global event envelope, event types, and append-only rules.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): API shape, generated OpenAPI, error envelope, and security baseline.
- [.memory-bank/testing/first-demo.md](../testing/first-demo.md): first-demo verification gates.
- [.memory-bank/invariants.md](../invariants.md): cross-cutting authority and timeline invariants.

## Design Decisions

### Persistence And Migration

- Use PostgreSQL as the only runtime authority for mutable MVP state.
- Use Alembic migrations for schema changes in backend tasks. Migration files are implementation artifacts and must be reviewed against this spec and the feature task acceptance criteria.
- Use the backend's Python persistence layer for all PostgreSQL access. Controllers must call application services; controllers must not encode authority decisions directly.
- Keep the initial schema single-plant friendly. `plant_id` remains explicit on plant-bound records even though the MVP accepted value is `tomato_001`.
- Do not add farm/greenhouse/zone/tenant abstractions, event-sourcing infrastructure, server-sync tables, or sensor time-series storage in FT-003.
- `sensor_window_ref` is nullable reference metadata only. It must not introduce InfluxDB as a runtime dependency.

### Minimal Runtime Tables

The first FT-003 migration should provide the smallest durable read model that can support the current PRD feature set. Exact column types may be implementation-specific, but the boundaries below are normative.

| Table boundary | Required responsibility | Required refs/statuses |
|---|---|---|
| `plants` | Canonical MVP plant identity and current profile for `tomato_001` | `plant_id`, created/updated timestamps |
| `daily_observations` | User daily observation text/no-data state and provenance | `observation_id`, `plant_id`, `observed_at`, provenance, `event_refs` |
| `manual_measurements` | Manual pH/EC values and freshness inputs | `measurement_id`, `plant_id`, `measured_at`, pH/EC value fields, provenance, `event_refs` |
| `photo_catalog` | Accepted photo metadata and mutable photo-related refs | globally unique `photo_id`, `plant_id`, `captured_at`, `photo_type`, file reference, `sha256`, review/dataset/sync refs, `event_refs`, optional `sensor_window_ref` |
| `tasks` | Check, measurement, pending approval, approved action, and follow-up task tracking | `task_id`, `plant_id`, task type/status, source refs, optional approval ref, outcome fields, `event_refs` |
| `safety_decisions` | Deterministic Safety Gate decisions used by display, task handoff, pending approval, and action unlock flows | `safety_decision_id`, `plant_id`, action/risk/outcome fields, checked input ref/hash, required measurement/context refs, `expires_at`, safe display text, source refs, `event_refs` |
| `human_approvals` | Human approval/rejection decisions for physical-action proposals | `approval_id`, `plant_id`, status, proposal/source refs, decision provenance, `event_refs` |
| `human_reviews` | Manual review decisions for data/labels when needed by dataset governance | `review_id`, subject ref, reviewer role/status, evidence refs, `event_refs` |
| `dataset_items` | Dataset lifecycle metadata without a full registry | subject ref, status, split, curator decision, confirmation source, evidence refs, `can_train_on`, provenance refs |
| `sync_state` | Local-only sync/storage prompt state | scope ref, `local_only` status, local bytes/prompt fields, `event_refs` |

Implementation tasks may split or defer non-blocking columns inside these table boundaries, but they must not remove the ability to store the mutable fields required by REQ-005, REQ-011, and REQ-012.

### Runtime Authority Reads

- Application services must read current plant state, photo status, task status, Safety Gate decision status/expiry, approval status, review status, dataset status, `can_train_on`, sync status, and future `sensor_window_ref` from PostgreSQL.
- `timeline.jsonl` may be read for audit, export, debugging, and evidence trails only.
- Photo manifests may be read as immutable artifacts only. They must not be used to answer current mutable status questions.
- If PostgreSQL conflicts with `timeline.jsonl`, treat it as an integrity issue and report it through verification or a later repair task. Do not silently rebuild mutable state from the timeline during normal runtime.

### Timeline File Location

- The default MVP timeline path is `data/plants/tomato_001/timeline.jsonl`.
- The path may be configurable in backend settings for tests and local environments.
- Timeline files must stay outside PostgreSQL and must use newline-delimited JSON with one valid JSON object per line.

### Timeline Append Semantics

- Timeline writes go through a single backend event/audit adapter.
- Existing timeline lines must never be edited, deleted, reordered, or rewritten to represent current state.
- Corrections and compensations are represented as new events.
- A state-changing workflow must not report success unless the PostgreSQL write and required timeline append both succeeded.
- For MVP simplicity, timeline append is synchronous in the request/workflow path. A generic async event outbox is out of FT-003 scope unless a later task proves synchronous append is insufficient.
- Workflows should generate event IDs before persistence, store those IDs in runtime `event_refs`, append the validated timeline event, and then complete the workflow. Any detected mismatch between persisted refs and file events is a data-integrity failure.

### Timeline Event ID And Validation

- `event_id` is an opaque globally unique string. Implementations should use a stable prefix such as `evt_` for domain timeline events and must not encode mutable state in the ID.
- All timeline events must validate against the global envelope from [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md).
- Pydantic or equivalent backend schemas must validate timeline events before append.
- `created_at` must be timezone-aware.
- `payload` must include stable refs for the domain object affected by the event whenever an object exists.
- Plant-bound events must include `payload.plant_id`.
- `event_type=user_photo` must include at least `payload.plant_id`, `payload.photo_id`, and `payload.photo_type`.

### Feature-Local Payload Minimums

FT-003 refines only common identifier requirements. Domain-specific fields can be extended by the owning feature-local specs.

| Event type | Minimum payload identifiers |
|---|---|
| `daily_observation` | `plant_id`, `observation_id` |
| `manual_measurement` | `plant_id`, `measurement_id` |
| `user_photo` | `plant_id`, `photo_id`, `photo_type` |
| `task_created` / `task_updated` | `plant_id`, `task_id` |
| `human_approval` / `human_rejection` | `plant_id`, `approval_id`, proposal/source ref |
| `agent_conclusion` / clarification / team signal | source refs to the relevant plant/photo/observation/task/approval when they influenced state or tasks |
| `safety_block` | `plant_id` when plant-bound, blocked proposal/source ref |
| `sync_event` | sync scope ref and sync status; MVP status remains `local_only` |
| `system_event` | machine-readable reason/code and relevant refs if it reports an integrity or recovery condition |

### API Surface

FT-003 defines the backend state/audit foundation; most write APIs are owned by feature workflows such as FT-001, FT-002, FT-008, FT-009, and FT-014.

Minimum FT-003-owned API/read surface:

- `GET /api/plants/{plant_id}/state` returns the current read-model state summary from PostgreSQL only.
- `GET /api/plants/{plant_id}/timeline` returns a paginated audit/export view from `timeline.jsonl`; it must be read-only and must not be used by the frontend as current mutable state.
- `GET /api/runtime/health` may expose local runtime readiness for PostgreSQL and timeline append path checks without leaking secrets or local absolute paths.

All API errors must use the shared structured error envelope from [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md).

## Verification Targets

Required before FT-003 can be marked implemented:

- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- Migration test or equivalent setup check proving required table boundaries exist.
- Schema tests for timeline envelope validation, timezone-aware timestamps, allowed event types, and `user_photo.payload.plant_id`.
- Integration test proving current mutable state reads come from PostgreSQL, not `timeline.jsonl` or photo manifests.
- Integration test proving `safety_decision:<safety_decision_id>` refs resolve to PostgreSQL/read-model `safety_decisions` rows for display, task, pending approval, and action unlock flows.
- Integration test proving a successful state-changing workflow writes PostgreSQL state and a corresponding timeline event ref.
- Append-only test proving existing timeline lines are not mutated by updates/corrections.
- Negative test for malformed timeline payloads and missing required identifiers.
- Anti-cheat check proving timeline import/export is not used as normal runtime authority.

## Gaps And Non-Goals

- No FT-003 blocker remains for `/prd-to-tasks FT-003`.
- Exact endpoint response fields, ORM model names, Alembic revision names, and test fixture shapes belong to implementation tasks.
- Full event sourcing, async event outbox, server sync lifecycle, InfluxDB integration, multi-plant/farm hierarchy, and full dataset registry are out of FT-003 MVP scope.
