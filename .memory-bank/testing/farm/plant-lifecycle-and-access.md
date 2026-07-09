---
description: Cross-contract verification for Farm bootstrap, Plant lifecycle, grants, ActorContext, audit, migration, and HTTP.
status: active
type: testing_spec
last_updated: 2026-07-08
source_of_truth:
  - .memory-bank/domains/farm/farm-plant-access-storage.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
  - .memory-bank/contracts/farm/plant-management-http.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/domains/admin/admin-audit.md
---
# Plant Lifecycle And Access Verification

## Scope

Defines the minimum deterministic and PostgreSQL-backed evidence that FT-002
must provide without claiming FT-003 admin UI or downstream Plant-operation,
history, task, approval, agent, Safety Gate, or Companion implementations.

## Coverage matrix

| Area | Minimum evidence |
|---|---|
| Schema/migration | PostgreSQL model/migration inspection and upgrade/reconciliation tests |
| Canonical bootstrap | command/service integration for create, reuse, partial, conflict, and redaction paths |
| Farm/Plant services | role policy, immutable keys, rename, lifecycle, row-lock/current-state checks, audit atomicity |
| Grant services | unique stable identity, create/reactivate/update/revoke/no-op, archived administration, audit atomicity |
| Permission adapter | persisted Farm/Plant/grant snapshots through the existing ActorContext resolver |
| HTTP | exact route/body/response/error/OpenAPI contract and backend authorization |
| Integrated flow | Engineer create/immediate select plus Boss archive/grant/restore behavior |

## Required checks

### Persistence and migration

- Native UUID PK/FK parity, restrictive FKs, status/key/display checks, exact
  unique/list indexes, JSON audit objects, actor-shape checks, and timestamps.
- `farm_memberships.farm_id` gains the final restrictive Farm FK without
  changing valid existing UUIDs.
- Zero legacy Farm IDs leaves runtime bootstrap in charge; one creates the
  canonical Farm with that UUID; multiple distinct values fail before
  committed mutation.
- Guarded downgrade refuses to cascade, orphan, or discard authority/history.
- Product behavior claiming PostgreSQL constraints runs against PostgreSQL;
  SQLite may cover only portable service logic and must not be reported as
  PostgreSQL evidence.

### Bootstrap

- Empty DB creates one Farm, active `tomato_001`, and exactly the applicable
  safe system-bootstrap audits.
- Canonical Farm without initial Plant creates only the missing Plant/audit.
- Repeated runs preserve IDs, names, status, timestamps, grants, and audit
  count. Archived `tomato_001` remains archived.
- Multiple/conflicting Farm/key/membership relations fail with an actionable
  redacted diagnostic and no mutation.

### Domain policy and transactions

- Active Boss/Engineer create; Consultant/disabled deny before persistence.
- Engineer create commits Plant, creator grant approval false, and two audits
  atomically; every injected failure leaves all four absent.
- Boss create writes no synthetic grant. Duplicate/invalid key rolls back.
- Plant-create failure injection proves a prechecked or positively identified
  `uq_plants_farm_plant_key` race maps to `PLANT_KEY_CONFLICT`, while an
  unrelated DB/audit/flush/commit failure maps to
  `PLANT_PERSISTENCE_FAILED`; neither path persists Plant, grant, or success
  audit rows.
- Boss or granted Engineer can rename active Plant; keys remain immutable;
  Consultant, revoked/missing grant, and archived Plant fail unchanged.
- Only Boss archives/restores and manages grants. Archive/restore preserves
  every grant ID, status, and approval flag.
- Grant create/reactivate preserves one ID; flag updates and revoke follow the
  exact audit taxonomy; no-op retries add no audit.
- Consultant approval flag true, Boss target grant, wrong-Farm target, inactive
  target grant/reactivation, and concurrent stale state fail closed.
- Grant administration while archived changes stored grant state but cannot
  produce normal read/operate permission before restore.

### ActorContext and HTTP

- Persisted snapshot adapter replaces the default deny-only application
  provider while preserving fail-closed behavior on repository errors.
- Boss sees all active Plants. Engineer/Consultant see only active granted
  Plants; revoked, missing, wrong-Farm, and archived normal paths are filtered.
- Engineer immediately resolves the creator grant after successful create and
  still cannot archive/restore or manage access.
- Every route resolves ActorContext before business logic and matches the
  concrete status/error/OpenAPI contract. Unknown, unauthorized, and archived
  normal Plant access does not leak existence.
- Responses, diagnostics, audit, and evidence contain no password, hash,
  session/token, cookie/header, `.env`, DB credential, or raw SQL exception.
- The HTTP adapter never overrides generic persistence failure with a
  route-selected business conflict. Tests assert safe status/code/body for
  both key-conflict and generic persistence paths and reject leaked exception
  or credential fragments.

## Behavior-spec traceability

- `FT-002-BHV-001`: bootstrap idempotency and fail-closed conflict.
- `FT-002-BHV-002`: atomic Engineer creation and immediate permission.
- `FT-002-BHV-003`: archive/grant mutation/restore with stable identity and no
  automatic operational access while archived.
- `FT-002-BHV-004`: named Plant-key uniqueness race remains distinct from
  unrelated rollback-safe persistence failure and both paths stay redacted.

## Deferred cross-feature checks

FT-002 proves the shared archived-Plant guard and changes no downstream rows.
Once the owning schemas exist, FT-006/007/008/011/012/013 integration must
archive a Plant with open history/task/approval/follow-up/agent/governance
records and prove no transition/publication while archived plus full current-
guard revalidation after restore. FT-002 must not create placeholder downstream
tables or fake those feature outcomes.

## Quality gates

- `.venv/bin/python -m pytest tests/backend/access_admin tests/backend/api`
- `.venv/bin/python -m pytest tests`
- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- `git diff --check`

Task-specific `/verify`, `/red-verify`, checkpoint, and sync evidence is
risk-based under the active tier policy; binding schema, authorization,
transaction, no-leak, and archive contracts cannot be waived by process choice.

## Related specs

- [.memory-bank/testing/strategy.md](../strategy.md)
- [.memory-bank/testing/auth/session-and-access.md](../auth/session-and-access.md)
