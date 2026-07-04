---
description: Verification contract for Boss direct Account creation, admin policy, audit, and first-demo provisioning.
status: active
type: testing_spec
last_updated: 2026-07-04
source_of_truth:
  - .memory-bank/contracts/admin/boss-admin-http.md
  - .memory-bank/contracts/auth/session-security.md
  - .memory-bank/domains/admin/admin-audit.md
---
# Boss Admin And Audit Verification

## Scope

Defines minimum policy, lifecycle, security, transaction, isolation, and E2E
evidence for the Boss admin boundary.

## Required checks

- Boss-only admin reads/mutations; Engineer/Consultant denial.
- Direct Account creation validates normalized login/role/Farm, hashes the
  initial password with Argon2id, and creates active Account plus active
  FarmMembership in one transaction.
- Create responses, logs, audit, timeline, Bus/UI, screenshots, exports, and
  agent context exclude plaintext password and `password_hash`.
- Last-active-Boss disable/demotion guard.
- Exactly one AdminAuditRecord in the same transaction for each successful
  audited mutation and none on failed validation/auth/persistence.
- Safe before/after summaries and full secret exclusion.
- Plant/access changes update ActorContext resolution without redefining Plant
  semantics.
- Admin UI notices and audit display text are absent from agent context.
- E2E: Boss directly creates Engineer, Engineer logs in, Boss assigns
  `tomato_001` access/toggle, and audit shows safe entries.
- Bootstrap contract tests are deferred until FT-002/FT-003 define the exact
  one-shot local CLI and single-Farm sequencing.

## Quality gates

- `.venv/bin/python -m pytest tests`
- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- `git diff --check`

## Related specs

- [.memory-bank/testing/strategy.md](../strategy.md)
- [.memory-bank/testing/auth/session-and-access.md](../auth/session-and-access.md)
