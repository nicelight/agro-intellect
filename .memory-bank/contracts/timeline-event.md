---
description: Global timeline audit/export event contract for MVP v2.
status: active
type: contract
last_updated: 2026-07-10
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/domains/runtime-data-model.md
---
# Timeline Event

## Scope

`timeline.jsonl` is the append-only audit/export trace for significant local
Farm/Plant events. It is not mutable runtime authority, not Agent Chat Bus, not
UI Feed, and not a state rebuild source.

The verified FT-000 executable baseline provides a local timeline root setting.
This contract owns the minimum append writer seam and active event registry
needed by current emitters. Subject specs own their payload summaries and
runtime mutation rules. Timeline history UI, pagination, file rotation, and
export packaging remain outside this contract.

## Contract Scope

- Defines: global timeline authority boundary, minimum event identity, reference
  shape, append writer seam, active event registry, redaction rules, replay
  limits, and verification requirements.
- Out of scope: complete future event taxonomy, all payload fields, JSONL
  rotation, export UI, history projection endpoint schemas, or DB table schemas.
- Related specs:
  - [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md):
    defines mutable runtime authority and shared entity relationships.
  - [.memory-bank/contracts/ui-feed.md](ui-feed.md): defines human-facing
    projection rules.
  - [.memory-bank/domains/photo-artifacts.md](../domains/photo-artifacts.md):
    defines local photo artifact authority.

## Event Shape

Feature-local specs may add event-specific fields, but every timeline event
must carry:

- `timeline_event_id`
- `created_at`
- `farm_id`
- `plant_id` when Plant-scoped
- `actor_ref` or `source_ref`
- `event_type`
- `source_type`
- `source_id`
- `source_refs`
- `payload_summary`
- `redaction_status`

`payload_summary` is an audit/export summary. It must not carry auth material,
raw provider payloads, hidden reasoning, raw proposal text, or full binary data.

`event_refs` stored by runtime rows use this minimum shape:

- `timeline_event_id`: UUID string.
- `timeline_ref`: stable relative ref in the form
  `timeline.jsonl#<timeline_event_id>`.
- `event_type`: the emitted event type.
- `created_at`: the event creation timestamp.

## Active Event Registry

The following event types are registered for the current taskable features:

| Event type | Producer | `source_type` | `source_id` | Payload summary owner |
|---|---|---|---|---|
| `daily_checkin_recorded` | Plant operations service | `daily_checkin` | `check_in_id` | `.memory-bank/domains/plant-operations.md` |
| `manual_measurement_recorded` | Plant operations service | `manual_measurement` | `measurement_id` | `.memory-bank/domains/plant-operations.md` |
| `photo_accepted` | Photo intake service | `photo_catalog_item` | `photo_id` | `.memory-bank/domains/photo-artifacts.md` |

New event types require the emitting feature's subject spec to define producer,
source identity, payload summary, redaction, failure behavior, and verification
before task creation.

## Append Writer Seam

The implementation exposes one backend-owned append helper for current feature
emitters. The helper:

- resolves `LOCAL_TIMELINE_ROOT` from application settings;
- creates or opens the MVP `timeline.jsonl` file under that root;
- validates the minimum event shape and registered `event_type`;
- writes one UTF-8 JSON object per line and returns the minimum `event_refs`
  shape above;
- rejects or redacts forbidden payload content before writing;
- never reads timeline events to compute mutable runtime state.

Feature services generate runtime ids before append, call the helper inside
their service boundary, persist returned `event_refs` on the owning runtime
row, and return success only after runtime persistence and timeline append have
both succeeded. For FT-004 and FT-005, append failure is fail-safe: the service
returns the documented `TIMELINE_APPEND_FAILED` error and must not report a
successful check-in, measurement, or accepted photo. Any task that adds a new
filesystem artifact must also clean up files it created for the failed attempt.

## Rules

- Runtime state remains in PostgreSQL/read model; timeline events only reference
  runtime records and artifact refs.
- Timeline replay must not rehydrate mutable runtime state.
- Timeline events cannot publish directly to Agent Chat Bus.
- Timeline events cannot make UI Feed content, raw chat, or raw model output
  agent-consumable.
- Timeline events that reference physical-action wording must reference the
  relevant Safety Gate/task records instead of becoming action authority.
- Timeline events that reference DecisionRecord must preserve
  `safety_gate_authority=not_granted` when governance summary is involved.
- Timeline events that reference dataset candidates cannot set or imply
  `can_train_on=true`.
- Feature success responses must not claim audit/export evidence when the
  append helper failed.

## Edge Cases And Errors

- If runtime persistence would succeed but timeline append fails, the current
  FT-004 and FT-005 operations fail and roll back/clean up task-owned runtime
  changes instead of claiming success.
- If timeline append succeeds but the runtime commit fails, the API must return
  the owning persistence error and the event remains non-authoritative audit
  noise; replay still cannot create or repair runtime state.
- If a timeline payload would include secrets or auth material, redact or block
  the event before writing.
- If event ordering matters for a feature, the feature-level spec must define
  the stricter ordering/idempotency rule before task creation.

## Verification

Tests must prove:

- Timeline events reference authoritative runtime/artifact records rather than
  replacing them.
- Timeline replay cannot mutate runtime state or Agent Chat Bus context.
- Secret/auth material is redacted from event payloads.
- Unauthorized Plant timeline/history reads fail closed.
- Feature-specific audit writes are transactionally consistent with their
  owning runtime mutation policy.
