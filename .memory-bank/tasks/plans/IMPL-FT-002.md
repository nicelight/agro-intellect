---
description: Implementation plan for FT-002 Farm Plant Lifecycle And Access Grants.
status: active
owner: planning
type: implementation-plan
last_updated: 2026-06-14
source_of_truth:
  - .memory-bank/features/FT-002-farm-plant-lifecycle-access-grants.md
  - .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md
  - .memory-bank/tasks/index.json
---
# IMPL-FT-002 Farm Plant Lifecycle And Access Grants

## Goals

- Implement the single local Farm seed, `tomato_001` seed, Plant lifecycle, and PlantAccessGrant storage.
- Provide the PlantPermissionContext resolver used by FT-001 ActorContext.
- Preserve archived Plant history authorization while excluding archived Plants from normal operations.

## Source Artifacts

- [FT-002 feature](../../features/FT-002-farm-plant-lifecycle-access-grants.md)
- [FT-002 feature SDD](../../tech-specs/FT-002-farm-plant-lifecycle-access-grants.md)
- [EP-001](../../epics/EP-001-local-farm-access-admin.md)
- [Requirements](../../requirements.md): REQ-001, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008.

## Normative Inputs

- [System Architecture](../../architecture/system-architecture.md)
- [Runtime Data Model](../../domains/runtime-data-model.md)
- [API Guidelines](../../contracts/api-guidelines.md)
- [Agent Chat Bus](../../contracts/agent-chat-bus.md)
- [FT-001 feature SDD](../../tech-specs/FT-001-local-accounts-sessions-actor-context.md)
- [FT-003 feature SDD](../../tech-specs/FT-003-boss-admin-surface-admin-audit.md)
- [Tier Policy](../../workflows/tier-policy.md)

## Constitution Check

- Relevant principles: local-first bounded Farm workspace, backend authorization, PostgreSQL/read-model authority, no broad farm-management scope, schema-backed task execution.
- No conflict found. Data/API/state tasks are T2; grant resolver/authz behavior is T3 because Plant visibility and approval authority are security-sensitive.

## Steps

1. Add DB-backed Farm, Plant, and PlantAccessGrant records with single-Farm and seed constraints.
2. Implement Plant list/create/read/archive/restore/retained-history routes and services.
3. Implement PlantAccessGrant grant/update/revoke routes and PlantPermissionContext resolver integration.
4. Integrate successful Plant and grant mutations with FT-003 AdminAuditRecord writer.
5. Add unit, integration, and e2e verification for Plant lifecycle, authorization, archive/restore, retained history, and revoked grants.

## Expected Touched Files

- `backend/app/access_admin/**`
- `backend/app/plants/**`
- `backend/migrations/**`
- `tests/backend/**`
- `.memory-bank/**` docs touched by Docs First sync.

## Tests

- Unit: Plant lifecycle transitions, grant/update/revoke rules, duplicate active grants, single-Farm and plant key constraints.
- Integration: Plant list/context builder filters by Boss, Engineer, Consultant, archived Plant, missing grant, and revoked grant.
- Integration: successful create/archive/restore/grant/update/revoke writes exactly one safe AdminAuditRecord after FT-003 audit writer exists.
- E2E: Boss grants Engineer access to `tomato_001`; archive removes it from normal operations; restore returns it.

## Quality Gates

- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- `git diff --check`
- Runtime backend unit/integration/e2e gates introduced by TASK-001.

## UAT Steps

- Boss sees all Farm Plants and can create/archive/restore.
- Engineer sees only active granted Plants and loses visibility after revoke.
- Archived Plant is absent from normal selector but available through explicit retained-history authorization.
- Unauthorized Plant errors do not reveal Plant existence.

## Task Records

- [TASK-006](../TASK-006.task.json)
- [TASK-007](../TASK-007.task.json)
- [TASK-008](../TASK-008.task.json)
- [TASK-009](../TASK-009.task.json)
- [TASK-010](../TASK-010.task.json)
