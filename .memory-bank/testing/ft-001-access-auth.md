---
description: FT-001 verification matrix for local identity, sessions, ActorContext, and authorization.
status: active
owner: quality
type: testing
feature_id: FT-001
last_updated: 2026-06-29
source_of_truth:
  - .memory-bank/features/FT-001-local-accounts-sessions-actor-context.md
  - .memory-bank/domains/local-identity-session-data.md
  - .memory-bank/contracts/local-session-security.md
  - .memory-bank/contracts/local-session-api.md
  - .memory-bank/contracts/actor-context.md
---
# FT-001 Access And Auth Verification

## Ownership

- Owns: FT-001 cross-contract verification coverage and task-to-evidence
  routing.
- Does not own: data/API/security/authorization behavior; those rules remain in
  their linked authoritative specs.
- Related specs:
  - [.memory-bank/domains/local-identity-session-data.md](../domains/local-identity-session-data.md)
  - [.memory-bank/contracts/local-session-security.md](../contracts/local-session-security.md)
  - [.memory-bank/contracts/local-session-api.md](../contracts/local-session-api.md)
  - [.memory-bank/contracts/actor-context.md](../contracts/actor-context.md)
  - [.memory-bank/testing/index.md](index.md): global risk-based testing policy.

## Coverage Matrix

| Area | Minimum evidence | Primary tasks |
|---|---|---|
| Relational identity/session schema | PostgreSQL model/migration integration tests | `TASK-005` |
| Credential and token primitives | deterministic unit tests plus redaction evidence | `TASK-006` |
| Session lifecycle services | unit/integration tests for activation, login, expiry, revocation, and disabled states | `TASK-007` |
| ActorContext and role policy | unit and component compatibility tests | `TASK-008` |
| Session HTTP API | API contract and cookie/bearer transport tests | `TASK-009` |
| Protected entrypoints/context builders | integration tests for authorization parity and no-leak behavior | `TASK-010` |
| Feature integration gate | full FT-001 suite, Memory Bank gates, and handoff evidence | `TASK-011` |

## Required Checks

- Relational schema tests cover UUID identity, `timestamptz`, nullability,
  named checks, normalized login uniqueness, non-cascading Account FKs, exact
  indexes, raw-token absence, and deferred Farm FK absence.
- Security unit tests cover Argon2id parameters, one-way password behavior,
  opaque token entropy, SHA-256 token hashing, constant-time comparison, and
  malformed-token failure.
- API contract tests cover stable auth error codes, generic login failure,
  session TTL/expiry/revocation, logout idempotence, cookie attributes, and
  optional bearer isolation.
- ActorContext tests cover fixed role policy and PlantPermissionContext
  interface compatibility with FT-002.
- Protected-route integration tests prove ActorContext is resolved before
  business logic.
- Context-builder integration tests prove authorization parity with
  user-facing reads and exclude auth material/unauthorized Plants from Agent
  Chat Bus context.
- `GET /api/session/me` returns a safe actor/session summary without secrets.
- E2E tests prove Engineer sees only granted Plants, Consultant remains
  read/comment/advice only, and pending activation cannot access Farm/Plant
  data before FT-003 activation succeeds.

## Quality Gates

- `.venv/bin/python -m pytest tests`
- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- `git diff --check`

T3 closure still follows `.memory-bank/workflows/tier-policy.md`; this document
does not replace task-specific `/verify` or `/red-verify` evidence.
