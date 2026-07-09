---
description: Exact Farm, Plant, and PlantAccessGrant persistence, migration, bootstrap, and transaction contract.
status: active
type: data_spec
last_updated: 2026-07-08
source_of_truth:
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/domains/identity/account-membership.md
  - .memory-bank/domains/admin/admin-audit.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
---
# Farm Plant And Access Storage

## Scope

Defines the exact PostgreSQL shape, migration/reconciliation order, canonical
local bootstrap, repository transaction rules, and persisted relationship used
by the FT-001 `PlantPermissionContext` interface.

## Out of scope

HTTP request/response payloads, UI/admin projections, retained-history payloads,
and downstream operational record schemas.

## Shape

All identifiers use PostgreSQL native `uuid`, SQLAlchemy `Uuid(as_uuid=True)`,
Python `uuid.UUID`, and application-generated `uuid.uuid4`.

- `farms`:
  - `farm_id`: primary key, non-null;
  - `farm_key`: `text`, non-null, immutable, unique, and DB-checked to equal
    exactly `local_farm`;
  - `display_name`: `text`, non-null and non-blank after trim;
  - `created_at`, `updated_at`: `timestamptz`, non-null, server default `now()`.
- `plants`:
  - `plant_id`: primary key, non-null;
  - `farm_id`: non-null FK to `farms.farm_id` with `ON DELETE RESTRICT`;
  - `plant_key`: `text`, non-null and immutable;
  - `display_name`: `text`, non-null and non-blank after trim;
  - `status`: `varchar(16)`, non-null, checked to `active|archived`;
  - `created_at`, `updated_at`: `timestamptz`, non-null, server default `now()`;
  - one unique B-tree lookup on `(farm_id, plant_key)` and one list lookup on
    `(farm_id, status)`.
- `plant_access_grants`:
  - `grant_id`: primary key, non-null;
  - `membership_id`: non-null FK to `farm_memberships.membership_id` with
    `ON DELETE RESTRICT`;
  - `plant_id`: non-null FK to `plants.plant_id` with `ON DELETE RESTRICT`;
  - `status`: `varchar(16)`, non-null, checked to `active|revoked`;
  - `plant_approve_actions`: boolean, non-null, default false;
  - `created_at`, `updated_at`: `timestamptz`, non-null, server default `now()`;
  - one unique B-tree lookup on `(membership_id, plant_id)` and one Plant list
    lookup on `(plant_id, status)`.

The persisted grant does not duplicate `farm_id`. The repository joins its
Plant and FarmMembership and validates that both belong to the ActorContext
Farm before mutation or snapshot construction. The single-Farm DB constraint
prevents cross-Farm rows in MVP; the service check remains fail-closed.

## Key and value rules

- `farm_key` is always `local_farm`; no API/service update accepts it.
- `plant_key` is canonical lowercase input matching
  `^[a-z0-9]+(?:_[a-z0-9]+)*$`. Application validation and a PostgreSQL DB
  check enforce the same expression.
- `display_name` is trimmed on write, preserves case, and must remain non-empty.
- Services update `updated_at`; no trigger, soft-delete flag, or generic
  versioning framework is introduced.
- There is no hard-delete product operation for Farm, Plant, or grant rows.

## Migration and reconciliation

The FT-002 migration uses the existing Foundation Alembic path and performs
this order in one PostgreSQL migration transaction:

1. Inspect distinct `farm_memberships.farm_id` values before committed writes.
2. More than one distinct value fails with a safe actionable diagnostic; no
   Farm ID is selected, merged, rewritten, or deleted.
3. Create the FT-002 tables and constraints. With one legacy membership Farm
   ID, insert canonical `local_farm` using that UUID and initial display name
   `Local Farm`; with zero IDs, leave Farm creation to runtime bootstrap.
4. Add `farm_memberships.farm_id -> farms.farm_id ON DELETE RESTRICT` and prove
   the native-UUID representation matches.
5. A migration-created Farm receives one `farm_created` system-bootstrap audit
   row after the audit table exists. No Plant or grant is created by migration.

The downgrade must not silently delete product authority data. If Farm, Plant,
grant, audit, or Farm-referencing membership rows exist, downgrade stops with
an actionable error instead of cascading or orphaning them.

## Canonical local bootstrap

The post-migration command is `bash scripts/bootstrap-farm-local.sh`, backed by
one application service using the normal Foundation DB/session path.

- With no Farm, one transaction creates `local_farm` (`display_name="Local
  Farm"`), creates active `tomato_001` (`display_name="Tomato 001"`), and
  writes `farm_created` plus `plant_created` system-bootstrap audit rows.
- With the canonical Farm but no `tomato_001`, it creates only the active Plant
  and its `plant_created` audit row.
- Existing canonical records are reused without changing IDs, display names,
  status, timestamps, grants, or audit history. An archived `tomato_001` is not
  restored by bootstrap.
- Multiple Farm rows, a non-canonical Farm key, an inconsistent membership Farm
  relation, or a conflicting `tomato_001` identity fails before mutation with
  one redacted actionable diagnostic. Bootstrap never selects, merges, renames,
  restores, or deletes conflicting records.
- Repeated successful runs are no-ops and add no duplicate audit rows.

## Constraints

- Grant membership and Plant must belong to the ActorContext Farm.
- Boss permission derives from role and Farm scope, not a synthetic grant.
- Engineer/Consultant permission derives only from an active matching grant.
- Active Boss and Engineer memberships may create Plants. Consultant and
  disabled memberships may not.
- Engineer creation atomically writes the Plant, creator grant, one
  `plant_created` AdminAuditRecord, and one `plant_access_granted`
  AdminAuditRecord. A failure in validation, authorization, persistence, grant,
  audit, flush, or commit rolls back the entire write set.
- Boss creation writes no synthetic grant and writes one same-transaction
  `plant_created` audit row.
- Creator grant establishment does not confer archive/restore or
  access-management authority; those remain Boss-only.
- Plant archive/restore mutates only `Plant.status`; it does not mutate grant
  identity, status, or approval flag.
- Every state-changing service locks the affected Plant and, when relevant,
  grant row before rechecking ActorContext, Plant status, membership status,
  role, and uniqueness in the same transaction as the write.
- Missing/revoked/mismatched relationships resolve denied; they do not leak
  Plant existence.
- No generic ACL or additional per-Plant override is implied.

## Service error classification

- The Farm service owns the persistence-to-domain classification needed by the
  HTTP adapter; the HTTP layer MUST NOT infer a uniqueness race from a generic
  `PERSISTENCE_FAILED` result.
- A duplicate Plant key discovered before insert, or a PostgreSQL uniqueness
  race positively identified by the named `uq_plants_farm_plant_key`
  constraint, produces the same explicit Plant-key conflict category after the
  transaction rolls back.
- Every other unexpected DB, flush, commit, audit, or unrecognized integrity
  exception rolls back and remains a generic persistence-failure category.
  It MUST NOT be reclassified as a business conflict from operation context
  alone.
- Domain errors expose no raw SQLAlchemy/driver exception, SQL text, DSN, or
  credential-bearing detail. The original exception may remain internal
  diagnostic context only where the project redaction boundary permits it.

## Verification

- PostgreSQL migration/model tests inspect native UUIDs, timestamps,
  nullability, checks, exact indexes, restrictive FKs, the final Membership FK,
  zero/one/multiple legacy Farm-ID paths, and guarded downgrade behavior.
- Bootstrap integration tests prove create, partial-create, repeated no-op,
  preserve-existing, archived-preservation, and fail-without-mutation paths.
- Resolver adapter tests cover stable IDs, Farm matching, active/revoked grant,
  active/archived Plant, missing relations, and no-leak failure.
- Transaction tests inject failures at Plant, grant, audit, flush, and commit
  boundaries and prove no partial authority or misleading success audit remains.
- Classification tests inject both the named Plant-key uniqueness race and an
  unrelated persistence failure, proving only the former becomes the explicit
  key-conflict category while both remain atomic and redacted.

## Related specs

- [.memory-bank/domains/identity/account-membership.md](../identity/account-membership.md)
- [.memory-bank/states/plants/plant-and-access-lifecycle.md](../../states/plants/plant-and-access-lifecycle.md)
- [.memory-bank/contracts/access/actor-context.md](../../contracts/access/actor-context.md)
- [.memory-bank/domains/admin/admin-audit.md](../admin/admin-audit.md)
- [.memory-bank/contracts/farm/plant-management-http.md](../../contracts/farm/plant-management-http.md)
