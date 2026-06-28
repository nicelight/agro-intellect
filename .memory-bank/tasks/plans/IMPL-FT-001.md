---
description: Implementation plan for FT-001 Local Accounts Sessions And ActorContext.
status: active
type: implementation_plan
feature_id: FT-001
last_updated: 2026-06-27
source_of_truth:
  - .memory-bank/features/FT-001-local-accounts-sessions-actor-context.md
  - .memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md
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

## Spec Design Links

- `.memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md`

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
- `.memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md`
- `.memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md`
- `.memory-bank/testing/index.md`
- `.memory-bank/testing/foundation-test-harness.md`
- `.memory-bank/workflows/tier-policy.md`

## Refresh Note

`/prd-to-tasks FT-001` was refreshed on 2026-06-26 after the brownfield global
SDD backbone update and again against the expanded `/prd-to-tasks` concrete
contract readiness protocol. A later `/spec-improve FT-001` repair closed
concrete security primitive, cookie/session transport, and PlantPermissionContext
ownership gaps. This `/prd-to-tasks FT-001` refresh updated the existing
`TASK-006` through `TASK-011` cards and their packets without creating new task
records. `TASK-005` remains unchanged because the repair did not add new
schema-level column length, nullability, index, or migration constraints beyond
the existing `password_hash` and unique `token_hash` storage contract.

A targeted 2026-06-27 `/prd-to-tasks FT-001` refresh updates only `TASK-005`
and its canonical packet after the KISS storage repair made those schema-level
decisions concrete: nullable unbounded-text `password_hash`, active-account
credential enforcement, one non-null 64-character `token_hash` column with a
single unique lookup index, no raw-token column, and PostgreSQL migration smoke.
The queue shape and `TASK-006` through `TASK-011` records/packets remain
unchanged.

A second targeted refresh on 2026-06-28 updates only `TASK-005` and its packet
for the completed relational contract: native UUID/UUIDv4 identity, exact
nullability and `timestamptz` defaults, string-domain DB checks, normalized
login uniqueness, non-cascading Account FKs, intentional initial Farm FK
absence with FT-002 closure ownership, and the exact index set. No queue or
later-task boundary changes.

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
  plus explicitly public auth endpoints such as login/bootstrap endpoints, are
  exceptions and must not expose Farm/Plant data or auth material.
- Product code must extend the verified Foundation app/database substrate
  instead of inventing a parallel app factory, DB/session, migration, local
  runtime-root, or redaction path.
- Authorization failures must fail closed and avoid leaking unauthorized Plant
  existence.
- FT-001 owns ActorContext and the PlantPermissionContext interface envelope;
  FT-002 owns concrete PlantPermissionContext resolver semantics,
  PlantAccessGrant lookup, archived/retained-history behavior, and Plant route
  denial code mapping.
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
- Generated task/packet assumptions remain below Constitution, explicit user
  decisions, verified code/evidence, and active SDD specs.

## Task Queue

| Task | Tier | Status | Purpose |
|---|---|---|---|
| `TASK-005-T3-FT-001-W1` | T3 | ready | Add Account, FarmMembership, and LocalSession schema/migration baseline. |
| `TASK-006-T3-FT-001-W1` | T3 | planned | Implement Argon2id password/session-token security primitives. |
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
  clear-cookie behavior, disabled/pending fail-closed behavior, canonical
  PlantPermissionContext compatibility, denial filtering, and context-builder
  auth material exclusion.
- Contract checks that FT-001 feature code preserves Foundation `/health` and
  `/ready`, uses the Foundation DB/session/Alembic substrate, and applies
  evidence-redaction rules to auth/session material.
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
   Bus/model context and stay compatible with FT-002 resolver output fields.
