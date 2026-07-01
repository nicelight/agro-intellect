---
description: Minimal Plant and PlantAccessGrant status effects required by the FT-001 permission resolver seam.
status: active
type: state_spec
last_updated: 2026-06-30
source_of_truth:
  - .memory-bank/domains/farm/farm-plant-access-storage.md
  - .memory-bank/contracts/access/actor-context.md
---
# Plant And Access Lifecycle

## Scope

Defines only the status vocabulary and permission effects needed for the
FT-002 -> FT-001 resolver dependency slice.

## Out of scope

Create/archive/restore and grant/update/revoke commands, retained-history
services, HTTP errors/routes, audit writes, persistence migrations, and seeds.

## Plant lifecycle

- `Plant.status`: `active | archived`.
- `active` permits normal operations only when ActorContext grants the
  requested capability.
- `archived` denies normal read, operate, domain-task creation, and action
  approval. A later explicit retained-history flow may allow authorized
  read/comment without restoring operational authority.
- Archive does not implicitly convert an active grant to revoked; the resolver
  combines Plant and grant status on every decision.

## PlantAccessGrant lifecycle

- `PlantAccessGrant.status`: `active | revoked`.
- Engineer and Consultant require an active grant for Plant scope.
- Missing or revoked grant resolves fail-closed with `source=denied`.
- The only MVP override is `plant_approve_actions`.
- Engineer action approval requires an active grant with the override and a
  separate Safety Gate pass; Consultant never receives approval authority.
- Boss does not require a grant and resolves with `source=boss_role`.

## Effects and failures

- Missing/unknown/unauthorized Plant and missing/revoked grant produce the same
  no-existence-leak denial at the FT-001 seam.
- Archived Plant always denies normal operate/task/action approval.
- Denied records are filtered before Bus/model context preparation.

## Verification

- Unit tests cover active/archived and active/revoked effects, missing grant,
  Boss bypass, Consultant restrictions, and action-approval derivation.
- Compatibility tests prove these effects map to the canonical
  `PlantPermissionContext` fields without implementing FT-002 persistence or
  mutation workflows.

## Related specs

- [.memory-bank/domains/farm/farm-plant-access-storage.md](../../domains/farm/farm-plant-access-storage.md)
- [.memory-bank/contracts/access/actor-context.md](../../contracts/access/actor-context.md)
