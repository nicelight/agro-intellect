---
description: Implementation plan for FT-001 Local Accounts Sessions And ActorContext.
status: active
type: implementation_plan
feature_id: FT-001
last_updated: 2026-06-25
source_of_truth:
  - .memory-bank/features/FT-001-local-accounts-sessions-actor-context.md
  - .memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md
  - .memory-bank/foundation.md
  - .memory-bank/workflows/tier-policy.md
---
# IMPL-FT-001 Local Accounts Sessions And ActorContext

## Objective

Implement the local identity, session, role-policy, and ActorContext boundary
needed by later Farm/Plant, admin, and agent-context features.

## Constitution Check

- Spec Before Code: tasks are derived from FT-001 feature doc, FT-001 tech spec,
  requirements, Foundation, and global backbone specs.
- KISS / low maintenance: use a local modular monolith, fixed role presets, and
  no general ACL engine beyond `plant_approve_actions`.
- Risk-based DoD: all tasks are T3 because they touch auth, sessions,
  authorization, secrets, or security-sensitive route behavior.
- No conflicts found with the Constitution.

## Source Artifacts

- `.memory-bank/features/FT-001-local-accounts-sessions-actor-context.md`
- `.memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md`
- `.memory-bank/behavior-specs/FT-001-BHV-001-login-success.behavior.json`
- `.memory-bank/behavior-specs/FT-001-BHV-002-login-no-leak-failure.behavior.json`
- `.memory-bank/behavior-specs/FT-001-BHV-003-actor-context-permission-filtering.behavior.json`

## Normative Inputs

- `.memory-bank/foundation.md`
- `.memory-bank/architecture/system-architecture.md`
- `.memory-bank/domains/runtime-data-model.md`
- `.memory-bank/contracts/api-guidelines.md`
- `.memory-bank/contracts/agent-chat-bus.md`
- `.memory-bank/contracts/message-envelope.md`
- `.memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md`
- `.memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md`
- `.memory-bank/testing/index.md`
- `.memory-bank/workflows/tier-policy.md`

## Constraints

- Store only server-side session token hashes; never persist raw session tokens.
- Use HTTP-only same-site cookie transport by default for browser/PWA sessions.
- Every non-health protected route and context-builder path must resolve
  ActorContext before business logic.
- Authorization failures must fail closed and avoid leaking unauthorized Plant
  existence.
- Do not implement FT-002 Plant lifecycle, FT-002 PlantAccessGrant mutation
  rules, FT-003 public invite activation route, FT-003 admin mutation surfaces,
  or AdminAuditRecord persistence except minimal interfaces needed by FT-001.
- Do not introduce OAuth, hosted recovery, email delivery, SaaS tenancy,
  multi-Farm membership, refresh tokens, device management, or a general ACL
  engine.

## Invariants

- PostgreSQL/read model owns mutable Account, FarmMembership, and LocalSession
  state.
- Frontend visibility is never an authorization substitute.
- Consultant remains advisory/read/comment only and cannot create domain tasks
  or approve physical actions.
- `can_approve_actions` is actor authority only and never Safety Gate clearance.
- Passwords, activation secrets, session tokens, token hashes, cookies, bearer
  tokens, and auth headers never enter logs, audit/export, Bus, UI Feed,
  screenshots, exports, or agent context.

## Task Queue

| Task | Tier | Status | Purpose |
|---|---|---|---|
| `TASK-005-T3-FT-001-W1` | T3 | ready | Add Account, FarmMembership, and LocalSession schema/migration baseline. |
| `TASK-006-T3-FT-001-W1` | T3 | planned | Implement password/session token security primitives. |
| `TASK-007-T3-FT-001-W2` | T3 | planned | Implement session lifecycle repositories and credential service. |
| `TASK-008-T3-FT-001-W2` | T3 | planned | Implement ActorContext, role policy, and PlantPermissionContext interface. |
| `TASK-009-T3-FT-001-W2` | T3 | planned | Implement login/logout/me API routes and no-leak error contract. |
| `TASK-010-T3-FT-001-W3` | T3 | planned | Implement protected-route and context-builder authz seams. |
| `TASK-011-T3-FT-001-W3` | T3 | planned | Run FT-001 integration gate and docs sync. |

## Dependency Order

```text
TASK-004-T2-FT-000-W0
  -> TASK-005-T3-FT-001-W1
  -> TASK-006-T3-FT-001-W1
  -> TASK-007-T3-FT-001-W2
  -> TASK-008-T3-FT-001-W2
  -> TASK-009-T3-FT-001-W2
  -> TASK-010-T3-FT-001-W3
  -> TASK-011-T3-FT-001-W3
```

## Expected Touched Areas

- `backend/app/access_admin/`
- `backend/app/api/`
- `backend/app/core/`
- `backend/app/main.py`
- `backend/migrations/versions/`
- `tests/backend/access_admin/`
- `tests/backend/api/`
- FT-001 task/protocol/evidence docs during execution.

## Verification Strategy

- Unit tests for schema constraints, session lifecycle, token/password hashing,
  role policy, ActorContext, PlantPermissionContext, and no-leak error mapping.
- Integration tests for login/logout/me, protected-route ActorContext
  resolution, disabled/pending fail-closed behavior, and context-builder auth
  material exclusion.
- T3 task closure requires full protocol, required packet, `/verify PASS`,
  per-task `/red-verify semantic-pass`, `HUMAN_CHECKPOINT: done`, and
  `ROLLBACK_RECOVERY_NOTE: present`.
- Feature completion later requires feature-level `/red-verify --feature FT-001`
  after all FT-001 tasks are done.

## Quality Gates

- `python -m pytest tests/backend/access_admin tests/backend/api`
- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- `git diff --check`

## UAT Steps

1. Boss local account logs in and receives a safe session summary plus
   HTTP-only same-site session cookie.
2. Invalid login returns `AUTH_CREDENTIAL_INVALID` without revealing whether the
   account exists.
3. Logout clears/revokes the current session and is idempotent for invalid or
   missing sessions.
4. `/api/session/me` returns only safe account, Farm, membership, role, and
   session expiry summary.
5. Consultant ActorContext cannot operate, create domain tasks, approve
   physical actions, or leak auth material into context-builder output.

