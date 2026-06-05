---
description: Implementation plan for FT-003 Boss Admin Surface And Admin Audit.
status: active
---
# IMPL-FT-003 Boss Admin Surface And Admin Audit

## Goals

- Implement Boss-only admin command boundaries for personnel, local account add/invite,
  role/status changes, Plant lifecycle entrypoints, and PlantAccessGrant management.
- Create durable, actor-attributed, redacted `AdminAuditRecord` entries for every
  successful admin mutation.
- Provide a minimal Boss Admin Surface and audit view without treating UI rows,
  markdown, or notices as authority or agent context.

## Constitution Check

- Aligns with Spec Before Code, schema-backed tasks, risk-based DoD, local-first scope,
  and low-maintenance MVP boundaries.
- No conflict found with the Constitution.
- Tier policy: all slices are T3 because they affect privileged admin, identity/access,
  authorization, audit, and redaction.
- KISS boundary: local-only admin; no email delivery, hosted account recovery,
  enterprise identity, SaaS tenancy, billing, or broad permission matrix.

## Source Artifacts

- .memory-bank/features/FT-003-boss-admin-surface-and-admin-audit.md
- .memory-bank/tech-specs/FT-003-boss-admin-surface-and-admin-audit.md
- .memory-bank/epics/EP-001-local-farm-access-and-admin.md
- .memory-bank/requirements.md
- .tasks/SPEC-IMPROVE-REVIEW/final-report.md

## Normative Inputs

- .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
- .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
- .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
- .memory-bank/architecture/system-architecture.md
- .memory-bank/domains/runtime-data-model.md
- .memory-bank/states/core-lifecycles.md
- .memory-bank/contracts/api-guidelines.md
- .memory-bank/testing/index.md
- agents-best-practices: privileged admin and identity/access changes require narrow,
  typed, schema-validated, permissioned, audited action boundaries with redacted
  evidence refs.

## Constraints

- PostgreSQL/read model owns Accounts, FarmMembership, Plant lifecycle,
  PlantAccessGrant, and AdminAuditRecord.
- Admin mutations require resolved ActorContext and active Boss role.
- Admin UI rows, notices, markdown, timeline refs, logs, and exports are not authority.
- Raw credentials, temporary credential material, session IDs, tokens, `.env` values,
  hidden reasoning, raw chat, and UI markdown are excluded from admin audit and agent
  context.
- Admin authority never bypasses Safety Gate or physical-action approval rules.

## Invariants

- Backend authorization is authority; frontend visibility is presentation only.
- Every successful admin mutation creates a durable `AdminAuditRecord`.
- Failed mutations do not create misleading successful audit records.
- Role presets remain `boss`, `engineer`, and `consultant`; `plant_approve_actions`
  remains the only MVP per-permission override.

## Steps

1. Define Boss-only admin API command schemas and safe error envelopes.
2. Implement durable `AdminAuditRecord` persistence and redacted audit writer.
3. Implement personnel/local account add/invite and membership role/status workflows.
4. Wire Plant create/archive/restore through FT-002 lifecycle services with audit.
5. Wire PlantAccessGrant grant/revoke/update through FT-002 policy with audit.
6. Add minimal Boss Admin UI, audit view, generated OpenAPI validation, and
   authorization/redaction regression coverage.

## Expected Touched Files

- backend/app/admin/*
- backend/app/access/*
- backend/app/plants/*
- backend/app/db/migrations/*
- backend/app/api/*
- frontend/src/*
- backend/tests/admin/*
- backend/tests/integration/*
- frontend/tests/*
- .memory-bank/changelog.md

## Tests

- Unit: admin command schemas, audit payload redaction, action type enum, summary
  shaping.
- Integration: non-Boss denial, local add/invite, role/status change, Plant lifecycle
  admin commands, PlantAccessGrant changes, audit retention after archive.
- Contract: generated OpenAPI validation after backend schemas exist.
- UI/e2e: Boss sees/administers personnel, Plants, grants, and audit; non-Boss cannot
  use admin mutation paths.
- Security: no secrets/auth material/UI markdown/raw chat in audit, logs, exports, Bus,
  UI Feed, screenshots, or agent context.

## Quality Gates

- pytest backend/tests/admin backend/tests/integration
- Frontend/UI smoke or e2e evidence under the task report when a frontend test runner exists; otherwise record the missing-runner reason in /verify
- generated OpenAPI validation after implementation schemas exist
- node scripts/mb-lint.mjs
- node scripts/mb-doctor.mjs
- /verify and /red-verify before T3 closure
- T3 human checkpoint and rollback/recovery note before closure

## UAT Steps

- Boss adds a local Engineer, changes role/status, grants access to `tomato_001`, and
  sees durable audit entries.
- Engineer/non-Boss cannot perform admin mutations through API or UI.
- Boss archives/restores a Plant and the admin audit remains retained.
- Admin audit and UI never reveal raw auth/session/secret material.

## Task Slice

- TASK-017: Boss-only admin API command boundary and schemas.
- TASK-018: AdminAuditRecord persistence and redacted audit writer.
- TASK-019: Personnel/local account add/invite and membership role/status workflows.
- TASK-020: Plant lifecycle admin entrypoints and audit integration.
- TASK-021: PlantAccessGrant admin management and audit integration.
- TASK-022: Boss Admin UI, audit view, integration, and OpenAPI coverage.

