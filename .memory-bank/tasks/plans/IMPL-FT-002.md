---
description: Implementation plan for FT-002 Farm, Plant lifecycle, access grants, bootstrap, audit, and HTTP.
status: active
last_updated: 2026-07-06
source_of_truth:
  - .memory-bank/features/FT-002-farm-plant-lifecycle-access-grants.md
  - .memory-bank/domains/farm/farm-plant-access-storage.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
  - .memory-bank/contracts/farm/plant-management-http.md
  - .memory-bank/testing/farm/plant-lifecycle-and-access.md
---
# IMPL FT-002 Farm Plant Lifecycle And Access Grants

## Goal

Turn the verified FT-001 permission seam into a persisted single-Farm Plant
authority: exact schema and bootstrap, transactionally audited lifecycle/grant
services, protected HTTP, and integrated evidence.

## Scope

- Create exact Farm, Plant, PlantAccessGrant, and AdminAuditRecord persistence.
- Close the deferred `FarmMembership.farm_id` FK without losing valid FT-001
  identity data.
- Add fail-closed idempotent canonical `local_farm`/`tomato_001` bootstrap.
- Implement create/rename/archive/restore and stable grant
  create/reactivate/update/revoke behavior.
- Bind the persisted snapshot provider to FT-001 ActorContext resolution.
- Expose and verify the concrete Farm/Plant/access HTTP contract.

## Non-goals

- FT-003 personnel/admin UI, Account creation, first-Boss CLI, or admin list UI.
- Retained-history payloads, check-ins, photos, timeline events, tasks,
  approvals, agent publication, Companion workflows, or PWA components.
- Hard delete, multi-Farm tenancy, generic ACL, event bus, microservice, or a
  second DB/session/migration path.

## Constitution Check

- Spec Before Code: the queue is derived from the clarified feature, RTM,
  verified brownfield baseline, and direct canonical specs.
- KISS/low maintenance: extend Access & Admin and the existing Foundation
  substrate; use four cohesive tasks and fixed role/grant semantics.
- Safety and authority: PostgreSQL remains mutable authority; archived Plant
  fails closed; `can_approve_actions` never becomes Safety Gate clearance.
- Bounded scope: no SaaS, multi-Farm, automated actuation, or downstream
  placeholder implementation is introduced.
- Blockers: none.

## Source Artifacts

- `.memory-bank/features/FT-002-farm-plant-lifecycle-access-grants.md`
- `.memory-bank/behavior-specs/FT-002-BHV-001-idempotent-canonical-bootstrap.behavior.json`
- `.memory-bank/behavior-specs/FT-002-BHV-002-engineer-create-immediate-access.behavior.json`
- `.memory-bank/behavior-specs/FT-002-BHV-003-archive-grant-restore.behavior.json`
- `.memory-bank/requirements.md`
- `.memory-bank/epics/EP-001-local-farm-access-admin.md`

## Direct canonical design links

- `.memory-bank/domains/farm/farm-plant-access-storage.md`
- `.memory-bank/states/plants/plant-and-access-lifecycle.md`
- `.memory-bank/contracts/access/actor-context.md`
- `.memory-bank/domains/admin/admin-audit.md`
- `.memory-bank/contracts/farm/plant-management-http.md`
- `.memory-bank/testing/farm/plant-lifecycle-and-access.md`
- `.memory-bank/states/safety-action-lifecycle.md`
- `.memory-bank/states/companion-governance.md`

## Dependencies

- `TASK-004-T2-FT-000-W0` is the required completed Foundation gate.
- `TASK-005..011` are completed FT-001 work. The queue uses completed
  `TASK-011-T3-FT-001-W3` as its direct prerequisite; that edge carries the
  full FT-001 chain and Foundation dependency transitively.
- The existing app factory, DatabaseHandle, Alembic runner, Access & Admin
  metadata, ActorContext, permission DTO/resolver, protected dependencies,
  auth errors, and tests are brownfield constraints, not work to recreate.

## Ordered implementation strategy

### W1 - Authority schema and canonical bootstrap

`TASK-012-T3-FT-002-W1` extends the existing Access & Admin metadata, creates
the FT-002 Alembic revision, closes the deferred Farm FK, implements the
canonical bootstrap service/script, and verifies PostgreSQL/reconciliation,
idempotency, audit, rollback, and redaction.

### W2 - Lifecycle, grants, and persisted permission adapter

`TASK-013-T3-FT-002-W2` implements repositories/services for Farm display,
Plant create/rename/archive/restore, grant management, same-transaction audit,
row-lock/current-state guards, and the fail-closed persisted snapshot provider.

### W3 - Protected HTTP

`TASK-014-T3-FT-002-W3` adds FastAPI schemas/routes/error mapping, composes
ActorContext and lifecycle/access operation kinds, mounts the persisted
provider, verifies generated OpenAPI, and proves backend-only authorization.

### W4 - Integrated evidence and durable sync

`TASK-015-T3-FT-002-W4` runs focused/full tests and MB gates, verifies all
three behavior specs and Foundation/FT-001 regression, and synchronizes the
feature, epic, RTM, changelog, and routing docs without claiming FT-003 or
downstream feature completion.

## Task queue

| Task | Tier | Outcome |
|---|---|---|
| `TASK-012-T3-FT-002-W1` | T3 | Exact schema, final Farm FK, audit authority, and idempotent canonical bootstrap |
| `TASK-013-T3-FT-002-W2` | T3 | Audited lifecycle/grant services and persisted permission adapter |
| `TASK-014-T3-FT-002-W3` | T3 | Concrete protected Farm/Plant/access API and stable no-leak errors |
| `TASK-015-T3-FT-002-W4` | T3 | Integrated FT-002 evidence and durable planning/lifecycle sync |

## Dependency order

```text
TASK-004-T2-FT-000-W0
  -> TASK-005..011 (completed FT-001 chain)
  -> TASK-012-T3-FT-002-W1
  -> TASK-013-T3-FT-002-W2
  -> TASK-014-T3-FT-002-W3
  -> TASK-015-T3-FT-002-W4
```

## Expected touched areas

- `backend/app/access_admin/`
- `backend/app/api/`
- `backend/app/main.py`
- `backend/migrations/versions/`
- `scripts/bootstrap-farm-local.sh`
- `tests/backend/access_admin/`
- `tests/backend/api/`
- FT-002 protocol/evidence and boundary Memory Bank docs during execution.

## Constraints and invariants

- Preserve verified Foundation and FT-001 runtime behavior; extend rather than
  replace their app/database/auth/permission paths.
- Keys are immutable; display names are the only Farm/Plant rename fields.
- No actual mutation succeeds without its exact same-transaction audit; no
  failed or no-op command writes a misleading audit.
- Engineer create is all-or-nothing and grants no lifecycle/access management.
- Archive mutates only Plant status; grant administration may occur but remains
  non-operative until restore. Downstream records are not invented or mutated.
- Authorization and current Plant status are rechecked inside the write
  transaction; stale UI/ActorContext snapshots do not authorize writes.

## Verification strategy

- Each implementation task carries focused unit/integration/PostgreSQL tests
  for its own outcome and preserves the complete existing suite.
- Real PostgreSQL evidence is required for native UUID, regex/check, FK,
  migration reconciliation, transaction, and downgrade claims. Any unavailable
  environment path must be reported explicitly, not replaced by SQLite claims.
- API contract checks cover status/body/OpenAPI, ActorContext-before-business,
  no-leak errors, list filtering, archived exceptions, and secret redaction.
- Integrated evidence traces `REQ-001`, `REQ-003`, `REQ-004`, `REQ-006`, and
  the FT-002-owned portion of `REQ-007` without closing cross-feature portions.

## Quality gates

- `.venv/bin/python -m pytest tests/backend/access_admin tests/backend/api`
- `.venv/bin/python -m pytest tests`
- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- `git diff --check`

## UAT

1. Run migration and `bash scripts/bootstrap-farm-local.sh` twice; observe one
   canonical Farm/Plant and no second-run changes.
2. Active Engineer creates `lettuce_001`, immediately lists/reads it, can
   rename it, and cannot archive/restore or manage grants.
3. Boss creates a Plant, archives/restores it, and sees grant identity/status/
   approval values preserved.
4. Boss revokes/reactivates and changes an Engineer grant while archived; the
   Engineer cannot operate before restore and regains only current grant-based
   authority afterward.
5. Consultant remains read/comment only; approval flag true is rejected.
6. Unknown/unauthorized/archived normal Plant requests share the safe no-leak
   result; audit contains safe exact state-change records and no auth material.

## Next workflow step

Run `/review-tasks-plan FT-002`, then use conditional `/mb-doctor` before task
execution because this is a complex T3 migration/authorization queue.
