---
description: Verification contract for Boss direct Account creation, admin policy, audit, and first-demo provisioning.
status: active
type: testing_spec
last_updated: 2026-07-09
source_of_truth:
  - .memory-bank/contracts/admin/boss-admin-http.md
  - .memory-bank/contracts/auth/session-security.md
  - .memory-bank/domains/admin/admin-audit.md
  - .memory-bank/runbooks/first-boss-local-bootstrap.md
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
- First-Boss one-shot CLI reads password only through `getpass`, requires the
  canonical Farm, refuses when an active Boss already exists, creates no
  session, and writes exactly one `account_created` system-bootstrap audit.
- Admin HTTP contract tests cover exact response shapes, filters, no-store
  responses, OpenAPI, documented error statuses, audit cursor behavior, and
  duplicate-login versus generic persistence failure classification.
- E2E: first Boss bootstrap creates the initial Boss; Boss logs in; Boss
  directly creates Engineer; Engineer logs in; Boss assigns `tomato_001`
  access/toggle through the canonical Plant API; audit shows safe entries.
- Behavior examples:
  - `FT-003-BHV-001`: first Boss one-shot bootstrap.
  - `FT-003-BHV-002`: Boss-created Engineer Account and audit.
  - `FT-003-BHV-003`: non-Boss denial and last-Boss guard.

## Quality gates

- `.venv/bin/python -m pytest tests`
- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- `git diff --check`

## Related specs

- [.memory-bank/testing/strategy.md](../strategy.md)
- [.memory-bank/testing/auth/session-and-access.md](../auth/session-and-access.md)
- [.memory-bank/testing/farm/plant-lifecycle-and-access.md](../farm/plant-lifecycle-and-access.md)
