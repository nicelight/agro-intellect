---
description: Implementation plan for FT-001 Local Accounts Sessions And ActorContext.
status: active
type: implementation_plan
feature_id: FT-001
last_updated: 2026-07-01
source_of_truth:
  - .memory-bank/features/FT-001-local-accounts-sessions-actor-context.md
  - .memory-bank/testing/auth/session-and-access.md
  - .memory-bank/spec-backbone.md
  - .memory-bank/foundation.md
  - .memory-bank/architecture/foundation-runtime-substrate.md
  - .memory-bank/domains/foundation-data-substrate.md
  - .memory-bank/contracts/evidence-redaction.md
  - .memory-bank/testing/index.md
  - .memory-bank/workflows/tier-policy.md
---
# IMPL-FT-001 Local Accounts Sessions And ActorContext

## Objective

Implement the local identity, session, role-policy, and ActorContext boundary
needed by later Farm/Plant, admin, and agent-context features.

## Constitution Check

- Spec Before Code: tasks are derived from the FT-001 feature composition,
  requirements, Foundation, and global backbone specs.
- KISS / low maintenance: use a local modular monolith, fixed role presets, and
  no general ACL engine beyond `plant_approve_actions`.
- Risk-based DoD: all tasks are T3 because they touch auth, sessions,
  authorization, secrets, or security-sensitive route behavior.
- No conflicts found with the Constitution.

## Source Artifacts

- `.memory-bank/features/FT-001-local-accounts-sessions-actor-context.md`
- `.memory-bank/behavior-specs/FT-001-BHV-001-login-success.behavior.json`
- `.memory-bank/behavior-specs/FT-001-BHV-002-login-no-leak-failure.behavior.json`
- `.memory-bank/behavior-specs/FT-001-BHV-003-actor-context-permission-filtering.behavior.json`

## Spec Design Links

- `.memory-bank/domains/identity/account-membership.md`
- `.memory-bank/domains/auth/session-storage.md`
- `.memory-bank/contracts/auth/session-security.md`
- `.memory-bank/states/auth/session-lifecycle.md`
- `.memory-bank/contracts/auth/session-http.md`
- `.memory-bank/contracts/access/actor-context.md`
- `.memory-bank/testing/auth/session-and-access.md`

## Normative Inputs

- `.memory-bank/spec-backbone.md`
- `.memory-bank/foundation.md`
- `.memory-bank/architecture/system-architecture.md`
- `.memory-bank/architecture/foundation-runtime-substrate.md`
- `.memory-bank/domains/runtime-data-model.md`
- `.memory-bank/domains/foundation-data-substrate.md`
- `.memory-bank/contracts/api-guidelines.md`
- `.memory-bank/contracts/evidence-redaction.md`
- `.memory-bank/contracts/agent-chat-bus.md`
- `.memory-bank/contracts/message-envelope.md`
- `.memory-bank/contracts/ui-feed.md`
- `.memory-bank/contracts/boundary-map.md`
- `.memory-bank/invariants.md`
- `.memory-bank/domains/farm/farm-plant-access-storage.md`
- `.memory-bank/states/plants/plant-and-access-lifecycle.md`
- `.memory-bank/domains/admin/admin-audit.md`
- `.memory-bank/testing/index.md`
- `.memory-bank/testing/foundation-test-harness.md`
- `.memory-bank/workflows/tier-policy.md`

## Refresh Note

On 2026-06-30 the queue migrated to the framework single-card handoff and
subject-based SDD model. Task IDs, tiers, waves, dependencies, statuses,
outcomes, gates, evidence, and scope are unchanged. Persisted packets were
removed after their success checks were confirmed in task cards. Each task now
links only its applicable canonical specs.

On 2026-07-01 the queue was reconciled to the KISS direct-Account decision and
the bounded FT-002 permission dependency. Invite/activation state and the
session activation primitive were removed; Account/Membership states are now
`active|disabled`, `password_hash` is required, and LocalSession uses only
`local_password`. No task identity, tier, wave, dependency, lifecycle status,
or independent outcome changed.

A follow-up `/prd-to-tasks FT-001` link audit on 2026-07-01 confirmed that no
new spec is required. It linked the existing cross-contract verification spec
directly to every applicable implementation card and linked session lifecycle
plus session HTTP directly to the protected-dependency task. Task topology and
lifecycle state remain unchanged.

Later on 2026-07-01, `TASK-005` passed implementation, functional verification,
and adversarial semantic verification. The explicit manual owner recorded the
required TASK-005-specific closure markers and closed the task. An
owner-requested early Memory Bank sync plus strict doctor gate passed; the
separate manual readiness decision promoted `TASK-006` to `ready`. This early
sync does not replace the final W1 boundary sync after `TASK-006` closes.

## Constraints

- Preserve verified FT-000 app factory, settings, database/session, migration,
  readiness, runtime-root, and redaction anchors; if implementation contradicts
  the brownfield baseline, stop and route to design repair.
- Store only server-side session token hashes; never persist raw session tokens.
- Use `argon2-cffi` Argon2id for password hashing with the FT-001 parameter
  contract, generate at least 256-bit opaque session tokens, persist only
  SHA-256 `token_hash`, and verify token digests with constant-time comparison.
- Use HTTP-only same-site `agro_intellect_session` cookie transport by default
  for browser/PWA sessions with `SameSite=Lax`, `Path=/`, TTL aligned to
  `LocalSession.expires_at`, and `Secure` required outside explicit loopback
  HTTP.
- Every protected product route and context-builder path must resolve
  ActorContext before business logic. Service endpoints `/health` and `/ready`,
  plus explicitly public auth endpoints such as login, are
  exceptions and must not expose Farm/Plant data or auth material.
- Product code must extend the verified Foundation app/database substrate
  instead of inventing a parallel app factory, DB/session, migration, local
  runtime-root, or redaction path.
- Authorization failures must fail closed and avoid leaking unauthorized Plant
  existence.
- ActorContext defines the permission interface and bounded resolver semantics;
  Plant/access persistence, mutations, retained-history workflows, and Plant
  HTTP behavior stay outside these task write scopes and await full FT-002 SDD.
- Do not implement FT-002 Plant lifecycle/PlantAccessGrant persistence or
  mutation rules, FT-003 direct Account creation/first-Boss bootstrap/admin
  surfaces, or AdminAuditRecord persistence.
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
- Passwords, session tokens, token hashes, cookies, bearer
  tokens, and auth headers never enter logs, audit/export, Bus, UI Feed,
  screenshots, exports, or agent context.
- Generated task assumptions remain below Constitution, explicit user
  decisions, verified code/evidence, and active SDD specs.

## Task Queue

| Task | Tier | Status | Purpose |
|---|---|---|---|
| `TASK-005-T3-FT-001-W1` | T3 | done | Add Account, FarmMembership, and LocalSession schema/migration baseline. |
| `TASK-006-T3-FT-001-W1` | T3 | ready | Implement Argon2id password/session-token security primitives. |
| `TASK-007-T3-FT-001-W2` | T3 | planned | Implement session lifecycle repositories and credential service using the security primitive contract. |
| `TASK-008-T3-FT-001-W2` | T3 | planned | Implement ActorContext, role policy, and PlantPermissionContext interface envelope. |
| `TASK-009-T3-FT-001-W2` | T3 | planned | Implement login/logout/me API routes, exact session cookie behavior, and no-leak error contract. |
| `TASK-010-T3-FT-001-W3` | T3 | planned | Implement protected-route and context-builder authz seams with canonical PlantPermissionContext filtering. |
| `TASK-011-T3-FT-001-W3` | T3 | planned | Run FT-001 security/cookie/permission integration gate and docs sync. |

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
- `pyproject.toml`
- `backend/migrations/versions/`
- `tests/backend/access_admin/`
- `tests/backend/api/`
- FT-001 task/protocol/evidence docs during execution.

## Verification Strategy

- Unit tests for schema constraints, session lifecycle, Argon2id
  token/password hashing, SHA-256 `token_hash` persistence, constant-time token
  verification, role policy, ActorContext, PlantPermissionContext, and no-leak
  error mapping.
- Integration tests for login/logout/me, protected-route ActorContext
  resolution, exact `agro_intellect_session` cookie attributes, logout
  clear-cookie behavior, disabled fail-closed behavior, canonical
  PlantPermissionContext compatibility, denial filtering, and context-builder
  auth material exclusion.
- Contract checks that FT-001 feature code preserves Foundation `/health` and
  `/ready`, uses the Foundation DB/session/Alembic substrate, and applies
  evidence-redaction rules to auth/session material.
- T3 task closure requires full protocol, complete indexed task card,
  `/verify PASS`, per-task `/red-verify semantic-pass`,
  `HUMAN_CHECKPOINT: done`, and explicit owner closure. Full `/mb-sync` runs at
  the end of the current wave unless an explicit early-sync condition applies.
- Feature completion later requires feature-level `/red-verify --feature FT-001`
  after all FT-001 tasks are done.

## Quality Gates

- `python -m pytest tests/backend/access_admin tests/backend/api`
- `.venv/bin/python -m pytest tests`
- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- `git diff --check`

## UAT Steps

1. Boss local account logs in and receives a safe session summary plus
   HTTP-only same-site `agro_intellect_session` cookie.
2. Invalid login returns `AUTH_CREDENTIAL_INVALID` without revealing whether the
   account exists.
3. Logout clears/revokes the current session and is idempotent for invalid or
   missing sessions.
4. `/api/session/me` returns only safe account, Farm, membership, role, and
   session expiry summary.
5. Consultant ActorContext cannot operate, create domain tasks, approve
   physical actions, or leak auth material into context-builder output.
6. Plant-scoped context-builder seams filter denied Plant contexts before
   Bus/model context and stay compatible with the bounded FT-002 permission
   fields.

Engineer/Consultant grant and direct-Account-creation E2E remains deferred until
FT-002/FT-003 have completed SDD and runnable task queues.
