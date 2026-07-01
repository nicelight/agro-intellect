---
description: Minimal Farm, Plant, and PlantAccessGrant identity relationships required by the FT-001 permission seam.
status: active
type: data_spec
last_updated: 2026-06-30
source_of_truth:
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/domains/identity/account-membership.md
---
# Farm Plant And Access Storage

## Scope

Defines only the identity, status, and relationship assumptions needed for the
FT-001 `PlantPermissionContext` interface. PostgreSQL remains future FT-002
runtime authority, but exact tables and migrations are not designed here.

## Out of scope

Exact columns/types/indexes/FKs, migration order, single-Farm reconciliation,
`tomato_001` seed mechanics, repositories, mutations, audit writes, and HTTP.

## Shape

- `Farm` has stable `farm_id` identity.
- `Plant` has stable `plant_id`, belongs to one Farm, and exposes
  `status: active|archived` to the permission resolver.
- `PlantAccessGrant` has stable `grant_id`, relates one FarmMembership to one
  Plant in the same Farm, exposes `status: active|revoked`, and carries only
  the MVP override `plant_approve_actions`.

## Constraints

- Grant Farm identity must match both Plant and membership Farm identity.
- Boss permission derives from role and Farm scope, not a synthetic grant.
- Engineer/Consultant permission derives only from an active matching grant.
- Missing/revoked/mismatched relationships resolve denied; they do not leak
  Plant existence.
- No generic ACL or additional per-Plant override is implied.

## Verification

- Resolver fixture/adapter tests cover stable IDs, Farm matching, active versus
  revoked grant, active versus archived Plant, and missing relations.
- No migration, repository, seed, or mutation verification is required until
  full `/prd-to-tasks FT-002` design.

## Related specs

- [.memory-bank/domains/identity/account-membership.md](../identity/account-membership.md)
- [.memory-bank/states/plants/plant-and-access-lifecycle.md](../../states/plants/plant-and-access-lifecycle.md)
- [.memory-bank/contracts/access/actor-context.md](../../contracts/access/actor-context.md)
