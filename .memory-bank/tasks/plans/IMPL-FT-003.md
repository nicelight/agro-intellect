---
description: Implementation plan for FT-003 Boss Admin Surface and Admin Audit.
status: active
type: implementation_plan
feature_id: FT-003
last_updated: 2026-07-09
source_of_truth:
  - .memory-bank/features/FT-003-boss-admin-surface-admin-audit.md
  - .memory-bank/contracts/admin/boss-admin-http.md
  - .memory-bank/runbooks/first-boss-local-bootstrap.md
  - .memory-bank/testing/admin/boss-admin-and-audit.md
---
# IMPL FT-003 Boss Admin Surface And Admin Audit

## Goal

Implement the backend Boss administration boundary for local personnel,
first-Boss setup, direct Account creation, role changes, Plant admin
projection, durable audit reads, and integrated evidence.

## Scope

- Add one-shot first-Boss local bootstrap command.
- Add admin service/repository behavior for Account creation, Account disable,
  membership role changes, last-active-Boss protection, personnel listing, Plant
  projection, and audit listing.
- Expose Boss-only `/api/admin/*` routes with safe response shapes, stable
  errors, and OpenAPI coverage.
- Reuse FT-002 Plant lifecycle/access routes and semantics for actual Plant
  mutations; do not redefine them.
- Prove Boss creates Engineer, Engineer logs in, Boss grants Plant access, and
  audit remains safe.

## Non-goals

- PWA/admin UI components; FT-016 owns Web App/PWA implementation.
- Hosted identity, email delivery, password recovery, OAuth, enterprise
  identity, SaaS tenancy, or multi-Farm support.
- New Plant lifecycle/access semantics beyond the existing FT-002 contract.
- Agent Bus, UI Feed, timeline/export, dataset, Safety Gate, or Plant
  operations implementation.

## Constitution Check

- Spec Before Code: queue derives from FT-003 feature composition, PRD/RTM,
  verified FT-001/FT-002 evidence, and canonical subject specs.
- KISS/low maintenance: use the existing Access & Admin package and fixed role
  presets; no generic ACL or extra identity subsystem.
- Safety/authority: PostgreSQL/read model remains authority; admin UI text is
  presentation only; `plant_approve_actions` never bypasses Safety Gate.
- Security: tasks are T3 because they touch passwords, local identity, admin
  authorization, and durable audit.
- Blockers: none.

## Source Artifacts

- `.memory-bank/features/FT-003-boss-admin-surface-admin-audit.md`
- `.memory-bank/behavior-specs/FT-003-BHV-001-first-boss-bootstrap-one-shot.behavior.json`
- `.memory-bank/behavior-specs/FT-003-BHV-002-boss-creates-engineer-atomic-audit.behavior.json`
- `.memory-bank/behavior-specs/FT-003-BHV-003-admin-denial-last-boss-guard.behavior.json`
- `.memory-bank/requirements.md`
- `.memory-bank/epics/EP-001-local-farm-access-admin.md`

## Direct Canonical Design Links

- `.memory-bank/domains/identity/account-membership.md`
- `.memory-bank/contracts/auth/session-security.md`
- `.memory-bank/states/auth/session-lifecycle.md`
- `.memory-bank/contracts/auth/session-http.md`
- `.memory-bank/contracts/access/actor-context.md`
- `.memory-bank/domains/admin/admin-audit.md`
- `.memory-bank/contracts/admin/boss-admin-http.md`
- `.memory-bank/contracts/farm/plant-management-http.md`
- `.memory-bank/domains/farm/farm-plant-access-storage.md`
- `.memory-bank/states/plants/plant-and-access-lifecycle.md`
- `.memory-bank/runbooks/first-boss-local-bootstrap.md`
- `.memory-bank/testing/admin/boss-admin-and-audit.md`

## Dependencies

- `TASK-004-T2-FT-000-W0` is the required completed Foundation gate.
- Completed FT-001 and FT-002 work is consumed through direct dependency on
  `TASK-015-T3-FT-002-W4`.
- Existing app factory, DatabaseHandle, Access & Admin metadata, session
  security, ActorContext dependencies, Plant snapshot provider, FarmService,
  and Plant API are brownfield constraints, not work to recreate.

## Ordered Implementation Strategy

### W1 - First-Boss Bootstrap And Admin Service

`TASK-016-T3-FT-003-W1` implements the first-Boss CLI and shared admin
identity/audit service using existing Account, FarmMembership, and
AdminAuditRecord persistence.

### W2 - Boss Admin HTTP

`TASK-017-T3-FT-003-W2` adds FastAPI schemas/routes/error mapping for
`/api/admin/*`, mounts the router, and verifies OpenAPI, no-store, safe
responses, filters, non-Boss denial, and error classification.

### W3 - Integrated Evidence And Durable Sync

`TASK-018-T3-FT-003-W3` runs focused/full tests and MB gates, traces behavior
specs, verifies Boss->Engineer->grant->audit flow, and synchronizes durable
feature/RTM docs without claiming FT-016 UI or downstream product features.

## Task Queue

| Task | Tier | Outcome |
|---|---|---|
| `TASK-016-T3-FT-003-W1` | T3 | First-Boss bootstrap plus admin identity/audit service |
| `TASK-017-T3-FT-003-W2` | T3 | Boss admin HTTP contract implementation |
| `TASK-018-T3-FT-003-W3` | T3 | Integrated FT-003 evidence and durable docs sync |

## Dependency Order

```text
TASK-004-T2-FT-000-W0
  -> TASK-005..011 (completed FT-001 chain)
  -> TASK-012..015 (completed FT-002 chain)
  -> TASK-016-T3-FT-003-W1
  -> TASK-017-T3-FT-003-W2
  -> TASK-018-T3-FT-003-W3
```

## Expected Touched Areas

- `backend/app/access_admin/`
- `backend/app/api/`
- `backend/app/main.py`
- `scripts/bootstrap-first-boss-local.sh`
- `tests/backend/access_admin/`
- `tests/backend/api/`
- FT-003 protocol/evidence and Memory Bank docs during execution.

## Constraints And Invariants

- Preserve verified Foundation, FT-001, and FT-002 behavior.
- Do not accept passwords through first-Boss command argv/env or return
  passwords/hashes from admin APIs.
- Every successful admin mutation represented by the Admin Audit taxonomy writes
  exactly one same-transaction audit record; failed and no-op commands write
  none.
- Last active Boss cannot be disabled or demoted.
- Admin routes require active Boss ActorContext before business logic.
- Plant/access administration composes existing FT-002 Plant HTTP semantics and
  audit behavior.

## Verification Strategy

- Unit/integration tests for first-Boss bootstrap, admin identity service,
  last-Boss guard, duplicate-login handling, rollback, redaction, and audit.
- API/OpenAPI tests for admin routes, filters, safe response fields, no-store
  responses, non-Boss denial, cursor validation, and stable error mapping.
- Integrated flow tests for first Boss login, Boss creates Engineer, Engineer
  login, Boss grants `tomato_001` access through canonical Plant API, and audit
  safe entries.
- Feature-level `/red-verify --feature FT-003` is recommended after all FT-003
  tasks close because admin/security semantic drift risk is material.

## Quality Gates

- `.venv/bin/python -m pytest tests/backend/access_admin tests/backend/api -k "ft001 or ft002 or ft003"`
- `.venv/bin/python -m pytest tests`
- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- `git diff --check`

## UAT

1. Run migrations, `bash scripts/bootstrap-farm-local.sh`, and
   `bash scripts/bootstrap-first-boss-local.sh --login-name boss --display-name Boss`.
2. Confirm a second first-Boss bootstrap refuses without mutation.
3. Boss logs in through `/api/session/login`.
4. Boss creates Engineer through `/api/admin/accounts`; response and audit omit
   password material.
5. Engineer logs in.
6. Boss grants Engineer access to `tomato_001` with the existing Plant API.
7. Boss lists personnel, Plants, and audit; Engineer cannot access
   `/api/admin/*`; the last active Boss cannot be disabled or demoted.
