---
description: Cross-contract verification for identity, sessions, ActorContext, and authorization.
status: active
type: testing_spec
last_updated: 2026-07-04
source_of_truth:
  - .memory-bank/domains/identity/account-membership.md
  - .memory-bank/domains/auth/session-storage.md
  - .memory-bank/contracts/auth/session-security.md
  - .memory-bank/states/auth/session-lifecycle.md
  - .memory-bank/contracts/auth/session-http.md
  - .memory-bank/contracts/access/actor-context.md
---
# Session And Access Verification

## Scope

Defines cross-contract minimum evidence for local identity, credential/session,
HTTP, ActorContext, Plant permission, and protected-context behavior.

## Coverage matrix

| Area | Minimum evidence |
|---|---|
| Identity/session storage | PostgreSQL model and migration integration tests |
| Credential/token primitives | deterministic unit tests plus redaction evidence |
| Session lifecycle | login/expiry/revocation/disabled-state tests |
| ActorContext and role policy | unit and resolver compatibility tests |
| Session HTTP | API contract and cookie/bearer tests |
| Protected seams/context builders | authorization parity and no-leak integration tests |
| Integrated FT-001 flow | complete FT-001 backend suite, behavior specs, MB gates, and handoff evidence |

## Required checks

- Storage: UUID, timestamps, nullability, checks, normalized login,
  non-cascading relations, exact indexes, raw-token absence, deferred Farm FK
  absence, and an explicit handoff to later FT-002 closure.
- Security: Argon2id parameters, one-way password verification, token entropy,
  SHA-256 digest-only storage, constant-time comparison, malformed-token
  failure, and redaction.
- Lifecycle/API: login, TTL/expiry/revocation, disabled states,
  generic login failure, stable errors, cookie attributes, logout idempotence,
  and bearer isolation when enabled.
- ActorContext: fixed role policy, complete PlantPermissionContext output,
  bounded active/archived permission effects, deferred retained-history
  workflow ownership, no-existence-leak denials, and resolver compatibility.
- Protected routes resolve ActorContext before business logic. Context builders
  have authorization parity and exclude auth material/unauthorized Plants.
- `/api/session/me` returns a safe scoped summary.
- Current FT-001 integration proves disabled identity denial and
  fail-closed PlantPermissionContext seams without requiring FT-002/FT-003
  persistence or UI.

## Deferred Cross-Feature E2E

After FT-002 and FT-003 receive their own completed SDD/task queues, E2E must
prove granted Engineer access, Consultant advisory-only behavior, and direct
Account creation followed by login with correctly scoped Farm/Plant access.
These checks do not
block FT-001 task execution because their required persistence/UI does not yet
exist.

## Quality gates

- `.venv/bin/python -m pytest tests`
- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- `git diff --check`

Task-specific `/verify` and `/red-verify` evidence remains recommended by tier
policy when it adds confidence; this spec does not make either check a closure
prerequisite.

## Related specs

- [.memory-bank/testing/strategy.md](../strategy.md)
