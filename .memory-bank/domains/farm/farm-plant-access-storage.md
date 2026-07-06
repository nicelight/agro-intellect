---
description: Farm, Plant, and PlantAccessGrant identity relationships plus the FT-002 Engineer-create atomicity contract.
status: active
type: data_spec
last_updated: 2026-07-06
source_of_truth:
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/domains/identity/account-membership.md
---
# Farm Plant And Access Storage

## Scope

Defines the identity, status, and relationship assumptions needed for the
FT-001 `PlantPermissionContext` interface and the FT-002 atomic relationship
created when an Engineer creates a Plant. PostgreSQL remains FT-002 runtime
authority, but exact tables and migrations are not designed here.

## Out of scope

Exact columns/types/indexes/FKs, migration order, single-Farm reconciliation,
`tomato_001` bootstrap implementation, repositories, general mutation/API
shapes, and HTTP.

## Shape

- `Farm` has stable `farm_id` identity.
- `Plant` has stable `plant_id`, belongs to one Farm, and exposes
  `status: active|archived` to the permission resolver.
- `PlantAccessGrant` has stable `grant_id`, relates one FarmMembership to one
  Plant in the same Farm, exposes `status: active|revoked`, and carries only
  the MVP override `plant_approve_actions`.
- An Engineer-created Plant has an active PlantAccessGrant for the creator's
  active FarmMembership with `plant_approve_actions=false`; normal
  ActorContext resolution gives immediate read/operate authority.

## Constraints

- Grant Farm identity must match both Plant and membership Farm identity.
- Boss permission derives from role and Farm scope, not a synthetic grant.
- Engineer/Consultant permission derives only from an active matching grant.
- Active Boss and Engineer memberships may create Plants. Consultant and
  disabled memberships may not.
- Engineer creation atomically writes the Plant, creator grant, one
  `plant_created` AdminAuditRecord, and one `plant_access_granted`
  AdminAuditRecord. A failure in validation, authorization, persistence, grant,
  or audit rolls back the entire write set.
- Boss creation writes no synthetic grant and follows the existing same-
  transaction `plant_created` audit rule.
- Creator grant establishment does not confer archive/restore or access-
  management authority; those remain Boss-only.
- Plant archive/restore mutates only `Plant.status`; it does not mutate grant
  identity or status. Existing active grants regain effect after restore and
  revoked grants remain revoked.
- Missing/revoked/mismatched relationships resolve denied; they do not leak
  Plant existence.
- No generic ACL or additional per-Plant override is implied.

## Verification

- Resolver fixture/adapter tests cover stable IDs, Farm matching, active versus
  revoked grant, active versus archived Plant, and missing relations.
- Transaction tests for FT-002 must prove Engineer create success is
  immediately resolvable through the creator grant and every injected failure
  leaves no Plant, grant, or misleading audit record.
- Lifecycle persistence tests prove archive/restore preserves grant IDs,
  statuses, and approval flags unchanged.
- No migration, repository, bootstrap, or HTTP shape is defined until full
  `/prd-to-tasks FT-002` design.

## Related specs

- [.memory-bank/domains/identity/account-membership.md](../identity/account-membership.md)
- [.memory-bank/states/plants/plant-and-access-lifecycle.md](../../states/plants/plant-and-access-lifecycle.md)
- [.memory-bank/contracts/access/actor-context.md](../../contracts/access/actor-context.md)
