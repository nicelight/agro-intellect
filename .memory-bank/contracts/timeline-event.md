---
description: Global timeline audit/export event contract for MVP v2.
status: active
owner: architecture
type: contract
last_updated: 2026-06-26
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

The verified FT-000 executable baseline provides a local timeline root setting
only. Concrete event taxonomy, file rotation, export packaging, and task-level
write implementation belong to feature-level SDD design, primarily
`/prd-to-tasks FT-005`, `/prd-to-tasks FT-006`, and features that emit audit
refs.

## Ownership

- Owns: global timeline authority boundary, minimum event identity, reference
  shape, redaction rules, replay limits, and verification requirements.
- Does not own: exact event taxonomy, all payload fields, JSONL rotation,
  export UI, history projection endpoint schemas, or DB table schemas.
- Related specs:
  - [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md):
    owns mutable runtime authority and shared entity ownership.
  - [.memory-bank/contracts/ui-feed.md](ui-feed.md): owns human-facing
    projection rules.
  - [.memory-bank/domains/photo-artifacts.md](../domains/photo-artifacts.md):
    owns local photo artifact authority.

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

## Edge Cases And Errors

- If runtime persistence succeeds but timeline append fails, the owning feature
  spec must define whether the operation fails, retries, or records a repair
  task. The global default is fail-safe: do not claim audit/export evidence
  exists when append failed.
- If timeline append succeeds but the runtime transaction fails, the owning
  feature must avoid committing a misleading success event.
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
