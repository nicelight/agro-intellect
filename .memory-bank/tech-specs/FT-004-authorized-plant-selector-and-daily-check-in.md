---
description: Feature-local SDD tech spec for FT-004 authorized Plant selector and daily check-in workflow.
status: active
feature_id: FT-004
owner: spec-improve
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/features/FT-004-authorized-plant-selector-and-daily-check-in.md
  - .memory-bank/requirements.md
  - .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
  - .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
  - .memory-bank/tech-specs/FT-005-photo-intake-catalog-and-capture-manifests.md
  - .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/states/core-lifecycles.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/agent-chat-bus.md
---
# FT-004 Authorized Plant Selector And Daily Check-In Tech Spec

## Purpose

Define the minimum feature-local design needed before task decomposition for authorized
Plant selection, daily check-in records, observations, manual pH/EC entry, Plant
card/history entry points, task/approval/follow-up entry points, and backend-controlled
agent-publication triggers.

This spec uses FT-001 ActorContext, FT-002 PlantAccessGrant/Plant lifecycle, FT-005
photo intake, FT-017 redaction, and the global Bus/API/testing contracts as normative
inputs.

## Scope

In scope:

- authorized active Plant selector for Boss and granted users;
- start/complete/abort daily CheckIn for active Plants;
- human-entered observation records;
- manual pH/EC measurement entry with explicit provenance and no-data states;
- photo-upload entry point that delegates accepted artifact handling to FT-005;
- Plant card/history, tasks, approvals, and follow-up navigation/refs;
- allowed backend publication of validated check-in evidence refs to Agent Chat Bus.

Out of scope:

- photo file/catalog/manifest internals owned by FT-005;
- mutable Plant state/history/timeline read-model details owned by FT-006;
- Safety Gate decision logic, approval records, action_task unlock, and follow-up
  outcome state owned by later Safety & Task Loop features;
- product-agent reasoning or MessageEnvelope generation.

## Authority And Selector Rules

PostgreSQL/read model is authority for authorized Plant lists, CheckIn, observations,
manual measurements, and current operational refs. UI selector state is not authority.

Selector rules:

- resolve ActorContext before listing Plants;
- include only `active` Plants for normal operation;
- Boss may see active Plants in the single Farm through role authority;
- Engineer and Consultant require granted PlantAccessGrant visibility;
- Consultant access is read/comment/advisory only and cannot start operational
  mutations unless a later active spec explicitly changes the Consultant boundary;
- revoked grants, archived Plants, disabled memberships, or invalid sessions fail
  closed;
- do not leak unauthorized Plant existence through selector, errors, or counts.

## CheckIn Lifecycle

Minimum CheckIn semantics:

```yaml
checkin_id: string
farm_id: string
plant_id: string
actor_ref: string
status: started | completed | aborted
started_at: datetime
completed_at: datetime | null
aborted_at: datetime | null
observation_refs: []
manual_measurement_refs: []
photo_refs: []
task_refs: []
approval_refs: []
follow_up_refs: []
timeline_refs: []
redaction_status: redacted | no_sensitive_fields
```

Rules:

- CheckIn start requires an authorized active Plant;
- only one open CheckIn per actor/Plant/day-like operational window should be allowed
  unless task decomposition records a simpler explicit duplicate policy;
- completing a CheckIn requires at least one accepted evidence ref or an explicit
  no-data/empty-check reason;
- aborting preserves safe audit refs and does not publish successful evidence events;
- archived Plants cannot start normal CheckIns;
- CheckIn refs are actor/Farm/Plant scoped and retained for authorized history.

## Observations And Manual Measurements

Observation records are human-entered data and must be treated as untrusted data when
later assembled into agent context. They become usable evidence only through backend
validation, source refs, trust labels, and redaction.

Minimum observation semantics:

```yaml
observation_id: string
checkin_id: string
farm_id: string
plant_id: string
actor_ref: string
body: string
created_at: datetime
trust_label: untrusted_data
source_ref: string
```

Minimum manual measurement semantics:

```yaml
measurement_id: string
checkin_id: string
farm_id: string
plant_id: string
actor_ref: string
kind: ph | ec
value: number | null
unit: pH | mS_cm
provenance: manual
recorded_at: datetime
data_state: recorded | no_data | invalidated | superseded
freshness_label: fresh | stale | unknown
source_ref: string
```

Rules:

- missing pH/EC is explicit as `data_state=no_data` or absent with an explicit
  missing-data projection for downstream advisor/safety behavior;
- measurement correction/supersede may be decomposed as a later task but must preserve
  the prior source ref;
- pH/EC freshness labels are handoff metadata and never sufficient by themselves for
  physical-action approval.

## Agent Publication Trigger Rules

Check-in evidence can become agent-consumable only through backend/domain adapters and
the Agent Chat Bus contract. Allowed FT-004 publication families:

- `checkin_started` as a low-detail operational ref when useful for workflow;
- `observation_recorded` after observation persistence and redaction;
- `manual_measurement_recorded` after measurement persistence and freshness labeling;
- `photo_ref_attached` after FT-005 accepts a photo and returns catalog/manifest refs;
- `checkin_completed` after CheckIn completion.

Publication rules:

- publish refs after persistence, not before authority exists;
- include ActorContext/Farm/Plant scope, source refs, trust/freshness labels, and
  redaction status;
- do not publish UI Feed text, admin UI notices, raw chat, hidden reasoning, auth
  material, or unauthorized Plant data;
- malformed or duplicate publication attempts must be rejected or idempotently ignored;
- timeline refs may be included as audit/export refs but cannot be replayed as current
  authority.

## API Surface To Refine In Tasks

Task decomposition may define exact endpoint and schema details for:

- authorized active Plant selector;
- start CheckIn;
- add observation;
- add manual pH/EC or mark no-data;
- attach accepted photo ref from FT-005;
- complete or abort CheckIn;
- read Plant card/history entry data through authorized refs;
- read task/approval/follow-up entry points by authorized Plant.

Generated OpenAPI comes from implementation schemas later.

## Verification Targets

Required tests before FT-004 can be considered implemented:

- selector excludes unauthorized and archived Plants;
- backend rejects CheckIn start/mutation for missing/revoked PlantAccessGrant, archived
  Plant, disabled membership, invalid session, and Consultant operational mutation;
- Boss and authorized Engineer can complete the first `tomato_001` flow;
- CheckIn, observation, measurement, and refs are actor/Farm/Plant scoped;
- missing pH/EC is represented explicitly for downstream advisor/safety behavior;
- photo upload entry point cannot bypass FT-005 validation/acceptance;
- Bus publication occurs only after persistence and contains refs, trust/freshness
  labels, and redaction status;
- UI Feed/admin text/raw chat/secrets cannot enter Bus or agent context through the
  check-in flow;
- timeline/photo artifacts cannot overwrite runtime authority.

## Open Questions

No blocker for `/prd-to-tasks FT-004`. Exact day/window duplicate policy, form layout,
route names, and Plant card/history composition can be decided during task decomposition
as long as ActorContext, PlantAccessGrant, persistence-before-publication, and
redaction boundaries hold.
