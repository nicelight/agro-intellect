---
description: Feature-local SDD tech spec for FT-006 runtime Plant state, history projections, and timeline audit/export separation.
status: active
feature_id: FT-006
owner: spec-improve
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/features/FT-006-runtime-plant-state-history-and-timeline-audit.md
  - .memory-bank/requirements.md
  - .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
  - .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
  - .memory-bank/tech-specs/FT-004-authorized-plant-selector-and-daily-check-in.md
  - .memory-bank/tech-specs/FT-005-photo-intake-catalog-and-capture-manifests.md
  - .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/states/core-lifecycles.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/agent-chat-bus.md
---
# FT-006 Runtime Plant State, History, And Timeline Audit Tech Spec

## Purpose

Define the minimum feature-local design needed before task decomposition for mutable
Plant runtime state, authorized Plant card/history projections, append-only timeline
audit/export refs, and the rule that timeline/photo/UI artifacts never replace
PostgreSQL/read-model authority.

This spec refines the global backbone and depends on FT-001 ActorContext, FT-002 Plant
lifecycle/access, FT-004 check-in evidence, FT-005 photo refs, and FT-017 redaction.

## Scope

In scope:

- runtime Plant state snapshots and history projections;
- state evidence refs from observations, measurements, photos, tasks, approvals,
  outcomes, timeline events, and validated agent messages when later features allow;
- trust labels for current Plant state values;
- authorized Plant card/history and archive-history access;
- append-only `TimelineEvent` taxonomy and refs for audit/export;
- integrity checks proving timeline replay cannot overwrite mutable state.

Out of scope:

- photo file/catalog/manifest internals owned by FT-005;
- AgentHarness runtime/output generation owned by FT-007, FT-009, and FT-010;
- Plant State Agent/advisor trust-promotion rules owned by FT-011;
- Safety Gate decisions, approval records, action tasks, and outcomes owned by later
  Safety & Task Loop features;
- full export packaging or server sync.

## Data Ownership

PostgreSQL/read model is mutable authority for:

- current `Plant` lifecycle state;
- current `PlantStateSnapshot` / read-model projection;
- `PlantHistoryEntry` projection rows or queryable history refs;
- CheckIn, Observation, ManualMeasurement, PhotoCatalogItem refs, Task, Approval,
  Outcome, SafetyGateDecision refs, and MessageEnvelope refs when the owning feature
  creates them;
- the refs that tie runtime records to timeline events and local artifacts.

`timeline.jsonl`, photo manifests, local photo files, UI Feed cards, admin UI notices,
raw chat, raw provider output, and raw agent memory are not mutable runtime authority.

## Runtime State Shape

Minimum `PlantStateSnapshot` semantics:

```yaml
state_snapshot_id: string
farm_id: string
plant_id: string
snapshot_version: integer
state_values:
  - key: string
    value: object | string | number | null
    status: confirmed_updated | confirmed_unchanged | assumed_unchanged | probable | unknown | conflict
    freshness_label: fresh | stale | unknown | not_applicable
    source_refs: []
    evidence_refs: []
    updated_by_actor_ref: string | null
    updated_by_agent_ref: string | null
    reviewed_by_actor_ref: string | null
    updated_at: datetime
timeline_refs: []
redaction_status: redacted | no_sensitive_fields
```

Rules:

- human-entered observations and measurements may update runtime projections only after
  backend validation and ActorContext/PlantAccessGrant checks;
- agent hypotheses may create `probable`, `unknown`, or `conflict` values, but cannot
  create `confirmed_updated` or `confirmed_unchanged` without the owning FT-011 rules
  and human review or follow-up evidence;
- missing, stale, conflicting, unauthorized, or untrusted evidence must produce explicit
  `unknown`, `probable`, or `conflict` state instead of silent confirmation;
- photo refs and timeline refs may be evidence refs only; they do not compute authority
  by themselves.

## History Projection

Minimum `PlantHistoryEntry` semantics:

```yaml
history_entry_id: string
farm_id: string
plant_id: string
entry_type: checkin | observation | measurement | photo | state_change | task | approval | outcome | safety | agent_message | admin | governance
occurred_at: datetime
actor_ref: string | null
agent_ref: string | null
summary: object
source_refs: []
timeline_refs: []
visibility_scope:
  farm_id: string
  plant_id: string
redaction_status: redacted | no_sensitive_fields
```

Projection rules:

- history reads resolve ActorContext and PlantAccessGrant before returning entries;
- normal operational views exclude archived Plants, but authorized history/audit/export
  views may include retained archived Plant entries;
- revoked PlantAccessGrant blocks future normal retrieval for that actor without
  deleting retained history/audit/evidence;
- summary fields are bounded and redacted; raw UI markdown, raw chat, hidden reasoning,
  secrets, or auth material are excluded;
- entries reference source records and timeline events instead of copying bulky blobs.

## Timeline Event Taxonomy

`TimelineEvent` is append-only audit/export. Minimum semantics:

```yaml
event_id: string
schema_version: string
created_at: datetime
event_type: string
farm_id: string
plant_id: string | null
actor_ref: string | null
agent_ref: string | null
source_ref: string
source_refs: []
payload_summary: object
redaction_status: redacted | no_sensitive_fields
```

Allowed FT-006 event families:

- access/admin refs: `plant_created`, `plant_archived`, `plant_restored`,
  `plant_access_changed`, `admin_audit_recorded`;
- check-in refs: `checkin_started`, `observation_recorded`,
  `manual_measurement_recorded`, `manual_measurement_no_data`,
  `manual_measurement_superseded`, `photo_ref_attached`, `checkin_completed`,
  `checkin_aborted`;
- runtime refs: `plant_state_snapshot_updated`, `plant_state_conflict_marked`;
- publication refs: `message_envelope_published`, `bus_event_published`,
  `agent_silent_decision_recorded`;
- safety/task refs: `safety_gate_recorded`, `approval_requested`,
  `approval_decided`, `task_created`, `task_status_changed`, `outcome_recorded`;
- governance/dataset refs: compact refs only when the owning later feature creates
  valid records.

Task decomposition may narrow which events are implemented in each slice, but must not
invent timeline replay as current state authority.

## Append And Integrity Rules

- Timeline append happens only after the authoritative source record exists or in the
  same logical command boundary as the source mutation.
- Successful state-changing workflows that require audit refs must not report success
  with a misleading missing timeline ref. They should fail the command or record a
  bounded integrity error for recovery.
- Existing timeline lines are never edited, deleted, reordered, or rewritten to express
  current state.
- Timeline import/replay is allowed only for audit/export/debug/integrity checks, never
  for normal runtime-state mutation.
- Out-of-order or duplicate events are detected by `event_id`, `source_ref`, or
  feature-level idempotency keys and cannot overwrite PostgreSQL/read-model state.
- Timeline payloads are redacted before append and exclude secrets/auth material,
  UI markdown, raw chat, hidden reasoning, and raw provider output.

## API Surface To Refine In Tasks

Task decomposition may define exact endpoint and schema details for:

- read Plant card runtime summary;
- read authorized Plant history with pagination/filtering;
- read archived Plant history for authorized history/admin views;
- append/query timeline audit/export events through backend-only services;
- resolve timeline/source refs for authorized detail views;
- runtime integrity check for missing/mismatched refs.

Generated OpenAPI comes from implementation schemas later.

## Verification Targets

Required tests before FT-006 can be considered implemented:

- Plant card/current state reads from PostgreSQL/read model, not timeline/photo/UI
  artifacts;
- timeline replay/import cannot overwrite runtime state;
- successful audited mutations persist authoritative state plus required timeline refs
  or fail without misleading success;
- existing timeline lines are append-only and are not rewritten;
- history reads are ActorContext, Farm, Plant, PlantAccessGrant, and archive-state
  scoped;
- archived Plant history remains retained and authorized while normal operations stay
  blocked;
- missing/stale/conflicting evidence maps to explicit state labels, not confirmation;
- UI Feed/admin markdown/raw chat/raw provider output cannot become Plant facts;
- secrets/auth material is redacted from timeline, history summaries, exports, Bus,
  UI Feed, screenshots, and agent context.

## Open Questions

No blocker for `/prd-to-tasks FT-006`. Exact endpoint names, pagination defaults,
timeline storage path, idempotency key shape, and first-slice event subset can be
chosen during task decomposition as long as runtime authority, authorization,
append-only audit, and redaction constraints hold.
