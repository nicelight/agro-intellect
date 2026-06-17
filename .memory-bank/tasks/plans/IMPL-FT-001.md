---
description: Implementation plan for FT-001 Local Accounts Sessions And ActorContext.
status: active
owner: planning
type: implementation-plan
last_updated: 2026-06-14
source_of_truth:
  - .memory-bank/features/FT-001-local-accounts-sessions-actor-context.md
  - .memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md
  - .memory-bank/tasks/index.json
---
# IMPL-FT-001 Local Accounts Sessions And ActorContext

## Goals

- Establish the local monolith foundation needed by first-wave implementation.
- Implement DB-backed Account, FarmMembership, LocalSession, local credential/session lifecycle, and ActorContext boundaries.
- Keep FT-002 Plant lifecycle/grant mutation and FT-003 public invite/admin routes in their owning feature tasks.

## Source Artifacts

- [FT-001 feature](../../features/FT-001-local-accounts-sessions-actor-context.md)
- [FT-001 feature SDD](../../tech-specs/FT-001-local-accounts-sessions-actor-context.md)
- [EP-001](../../epics/EP-001-local-farm-access-admin.md)
- [Requirements](../../requirements.md): REQ-002, REQ-003, REQ-004, REQ-022.

## Normative Inputs

- [System Architecture](../../architecture/system-architecture.md)
- [Runtime Data Model](../../domains/runtime-data-model.md)
- [API Guidelines](../../contracts/api-guidelines.md)
- [Agent Chat Bus](../../contracts/agent-chat-bus.md)
- [MessageEnvelope](../../contracts/message-envelope.md)
- [Invariants](../../invariants.md)
- [Tier Policy](../../workflows/tier-policy.md)

## Constitution Check

- Relevant principles: Spec Before Code, low-maintenance MVP scope, schema-backed task execution, risk-based Definition of Done, no legacy risk fields.
- No conflict found. Auth/session/ActorContext work is T3 where security/authz/secrets are involved; the skeleton bootstrap is T2 because it establishes runtime architecture and persistence/test boundaries.

## Steps

1. Bootstrap a minimal local modular monolith skeleton, DB migration/test harness, and docs pointers.
2. Add DB-backed Account, FarmMembership, and LocalSession persistence with indexes and server-side token hash storage.
3. Implement login/logout/me and the internal local credential activation/session primitive used by FT-003.
4. Implement ActorContext, role preset policy, PlantPermissionContext interface, and context-builder enforcement hooks.
5. Add verification for fail-closed auth, redaction, ActorContext propagation, and Consultant/Engineer permission semantics.

## Expected Touched Files

- `pyproject.toml`
- `backend/app/**`
- `backend/migrations/**`
- `tests/backend/**`
- `frontend/**` only for minimal shared app/test scaffolding if selected by TASK-001.
- `.memory-bank/**` docs touched by Docs First sync.

## Tests

- Unit: role policy, account/session lifecycle, session TTL/revocation/logout, no-leak auth errors, redaction.
- Integration: protected routes resolve ActorContext before business logic; context builders exclude auth material and unauthorized Plants.
- E2E: Engineer sees only assigned Plants after FT-002/FT-003 dependencies; Consultant remains read/comment/advice only.

## Quality Gates

- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- `git diff --check`
- Runtime gates created by TASK-001, expected to include backend unit/integration tests and any frontend checks introduced by the skeleton.

## UAT Steps

- Boss/Engineer login paths return safe session summaries without secrets.
- Missing/expired/revoked sessions fail closed.
- Consultant cannot create domain task/recommendation records or approve physical actions.
- ActorContext is visible in audit/service fixtures as safe account/membership/role refs, never auth material.

## Task Records

- [TASK-001](../TASK-001.task.json)
- [TASK-002](../TASK-002.task.json)
- [TASK-003](../TASK-003.task.json)
- [TASK-004](../TASK-004.task.json)
- [TASK-005](../TASK-005.task.json)
