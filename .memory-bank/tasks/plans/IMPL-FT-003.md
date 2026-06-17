---
description: Implementation plan for FT-003 Boss Admin Surface And Admin Audit.
status: active
owner: planning
type: implementation-plan
last_updated: 2026-06-14
source_of_truth:
  - .memory-bank/features/FT-003-boss-admin-surface-admin-audit.md
  - .memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md
  - .memory-bank/tasks/index.json
---
# IMPL-FT-003 Boss Admin Surface And Admin Audit

## Goals

- Implement Boss admin workflows for local invite/account, role, Plant/access administration, and minimal audit view.
- Persist LocalInviteCredential and AdminAuditRecord in PostgreSQL/read model.
- Keep admin UI notices and audit display text out of agent context.

## Source Artifacts

- [FT-003 feature](../../features/FT-003-boss-admin-surface-admin-audit.md)
- [FT-003 feature SDD](../../tech-specs/FT-003-boss-admin-surface-admin-audit.md)
- [EP-001](../../epics/EP-001-local-farm-access-admin.md)
- [Requirements](../../requirements.md): REQ-003, REQ-005, REQ-021, REQ-022.

## Normative Inputs

- [System Architecture](../../architecture/system-architecture.md)
- [Runtime Data Model](../../domains/runtime-data-model.md)
- [API Guidelines](../../contracts/api-guidelines.md)
- [FT-001 feature SDD](../../tech-specs/FT-001-local-accounts-sessions-actor-context.md)
- [FT-002 feature SDD](../../tech-specs/FT-002-farm-plant-lifecycle-access-grants.md)
- [Invariants](../../invariants.md)
- [Tier Policy](../../workflows/tier-policy.md)

## Constitution Check

- Relevant principles: local-only MVP scope, no SaaS/hosted recovery/email delivery, backend authorization, secret redaction, durable Memory Bank sync.
- No conflict found. Invite/session/admin audit work is T3 because credentials, secrets, authorization, and durable audit are involved; admin UI is T2 and depends on backend authority.

## Steps

1. Add DB-backed LocalInviteCredential and AdminAuditRecord persistence.
2. Implement Boss-only local invite/account/disable/role APIs and public local invite activation boundary that calls FT-001's credential/session primitive.
3. Wire Boss Plant/access admin wrappers and AdminAuditRecord writes for FT-002 mutations.
4. Build minimal first-demo Boss admin UI for personnel, invites, roles, Plant list/access, and audit list.
5. Add unit, integration, e2e, and anti-context-leak verification.

## Expected Touched Files

- `backend/app/access_admin/**`
- `backend/app/api/admin/**`
- `backend/app/api/local_invites/**`
- `backend/migrations/**`
- `frontend/**`
- `tests/backend/**`
- `tests/e2e/**`
- `.memory-bank/**` docs touched by Docs First sync.

## Tests

- Unit: Boss-only admin policy, invite status transitions, last-active-Boss guard, secret redaction.
- Integration: audited mutation writes exactly one durable AdminAuditRecord in the same transaction after success.
- Integration: local invite activation uses constrained activation ActorContext, FT-001 session issuing, Set-Cookie, and no normal access before activation.
- Integration: admin notices/audit display text excluded from agent context fixtures.
- E2E: Boss creates Engineer, assigns role, grants `tomato_001`, toggles `plant_approve_actions`, and sees audit entry.

## Quality Gates

- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- `git diff --check`
- Runtime backend/frontend/e2e gates introduced by TASK-001 and admin UI tasks.

## UAT Steps

- Boss creates a local Engineer invite and sees the activation secret once.
- Engineer activates locally and receives a normal FT-001 session.
- Boss grants and revokes `tomato_001` access and sees safe audit rows.
- Non-Boss actors cannot access admin reads/mutations.

## Task Records

- [TASK-011](../TASK-011.task.json)
- [TASK-012](../TASK-012.task.json)
- [TASK-013](../TASK-013.task.json)
- [TASK-014](../TASK-014.task.json)
- [TASK-015](../TASK-015.task.json)
