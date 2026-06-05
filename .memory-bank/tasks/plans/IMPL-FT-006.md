---
description: Implementation plan for FT-006 Runtime Plant State, History, And Timeline Audit.
status: active
---
# IMPL-FT-006 Runtime Plant State, History, And Timeline Audit

## Goals

- Implement mutable Plant runtime state and history projections backed by
  PostgreSQL/read model authority.
- Keep `timeline.jsonl` append-only audit/export only and link runtime records to
  timeline/photo/task/approval/outcome refs without delegating authority to artifacts.
- Provide authorized Plant card/history and archived history access with redaction and
  integrity checks.

## Constitution Check

- Aligns with Spec Before Code, data authority separation, local-first/private scope,
  bounded agent autonomy, and risk-based DoD.
- No conflict found with the Constitution.
- Tier policy: runtime state data authority is T2; authorized history, timeline/export,
  redaction, UI, and integrity slices are T3.
- KISS boundary: simple read-model projections and append-only JSONL refs; no full
  export packaging, timeline replay authority, sensor runtime, or agent reasoning.

## Source Artifacts

- .memory-bank/features/FT-006-runtime-plant-state-history-and-timeline-audit.md
- .memory-bank/tech-specs/FT-006-runtime-plant-state-history-and-timeline-audit.md
- .memory-bank/epics/EP-002-plant-evidence-and-runtime-authority.md
- .memory-bank/requirements.md
- .tasks/SPEC-IMPROVE-REVIEW/final-report.md

## Normative Inputs

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
- .memory-bank/testing/index.md

## Constraints

- PostgreSQL/read model is mutable runtime authority for Plant state and history
  projections.
- `timeline.jsonl`, photo manifests/files, UI Feed cards, admin UI notices, raw chat,
  raw provider output, and raw agent memory are not mutable runtime authority.
- Timeline append happens after the authoritative source record exists or in the same
  logical command boundary.
- Unauthorized, stale, missing, conflicting, or untrusted evidence maps to explicit
  labels, not silent confirmation.

## Invariants

- History reads resolve ActorContext, Farm, Plant, PlantAccessGrant, and archive state.
- Existing timeline lines are never edited, deleted, reordered, or rewritten to express
  current state.
- Timeline replay/import cannot overwrite PostgreSQL/read-model state.
- Secrets/auth material and raw UI/model/chat content are excluded from timeline,
  history summaries, exports, Bus, UI Feed, screenshots, and agent context.

## Steps

1. Build PlantStateSnapshot projection foundation and evidence-ref update rules.
2. Add authorized Plant card/current-state and history query services.
3. Add append-only TimelineEvent writer, event taxonomy, and idempotency handling.
4. Wire runtime/timeline refs to CheckIn/photo/admin source records and integrity
   checks.
5. Build Plant history/card UI and archived history flow.
6. Add runtime/timeline regression suite and OpenAPI contract coverage.

## Expected Touched Files

- backend/app/runtime_state/*
- backend/app/plant_operations/*
- backend/app/timeline/*
- backend/app/access/*
- backend/app/publication/*
- backend/app/db/migrations/*
- backend/app/api/*
- frontend/src/*
- backend/tests/runtime_state/*
- backend/tests/integration/*
- backend/tests/security/*
- frontend/tests/*
- .memory-bank/changelog.md

## Tests

- Unit: PlantStateSnapshot status/freshness mapping, timeline event validation,
  idempotency, redaction helpers, and duplicate/out-of-order detection.
- Integration: authorized Plant card/history reads, archived history access, revoked
  grant filtering, runtime state updates from persisted evidence refs, and timeline
  append after source records.
- Contract: generated OpenAPI validation and Bus/timeline ref shape checks where
  publication refs are exposed.
- UI/e2e: authorized Plant card/history and archived history smoke once UI exists.
- Security/context: timeline replay, UI markdown, raw chat, raw provider output, and
  secrets cannot become Plant facts or agent context.

## Quality Gates

- pytest backend/tests/runtime_state backend/tests/integration backend/tests/security
- Frontend/UI smoke or e2e evidence under the task report when a frontend test runner exists; otherwise record the missing-runner reason in /verify
- generated OpenAPI validation after implementation schemas exist
- node scripts/mb-lint.mjs
- node scripts/mb-doctor.mjs
- /verify and /red-verify for T2/T3 closure
- T3 human checkpoint and rollback/recovery note for authorized history/timeline/UI
  slices

## UAT Steps

- Authorized Boss/Engineer views Plant card/history for `tomato_001` from runtime
  state, not timeline replay.
- Unauthorized or revoked actor cannot read Plant history or audit refs.
- Archived Plant history remains retained and authorized while normal operations stay
  blocked.
- Timeline export refs are append-only and redacted.

## Task Slice

- TASK-035: PlantStateSnapshot projection foundation and evidence-ref update rules.
- TASK-036: Authorized Plant card/current state and history query services.
- TASK-037: Append-only TimelineEvent writer, taxonomy, and idempotency rules.
- TASK-038: Runtime/timeline source-ref integration and integrity checks.
- TASK-039: Plant history/card UI and archived history flow.
- TASK-040: Runtime/timeline regression suite and OpenAPI contract coverage.
