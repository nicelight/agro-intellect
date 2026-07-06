---
description: Plant lifecycle operational guard, PlantAccessGrant status effects, and FT-002 creation authority.
status: active
type: state_spec
last_updated: 2026-07-06
source_of_truth:
  - .memory-bank/domains/farm/farm-plant-access-storage.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/invariants.md
  - .memory-bank/architecture/system-architecture.md
---
# Plant And Access Lifecycle

## Scope

Defines Plant/PlantAccessGrant status vocabulary, the global archived-Plant
operational guard, permission effects, and the bounded creation and
creator-grant transitions accepted for FT-002.

## Out of scope

General create/archive/restore and grant/update/revoke command payloads,
retained-history presentation, HTTP errors/routes, persistence migrations, and
bootstrap implementation. Shared archive/restore effects and Engineer-creation
role/atomicity are in scope below.

## Plant lifecycle

- `Plant.status`: `active | archived`.
- Active Boss and Engineer memberships may transition a new Plant into
  `active` through creation. Consultant and disabled memberships cannot.
- Engineer creation atomically transitions a new creator PlantAccessGrant into
  `active` with `plant_approve_actions=false`; if that transition or its audit
  writes fail, the Plant does not enter `active`.
- Creation grants no archive/restore authority. Only Boss may transition an
  existing Plant between `active` and `archived`.
- `active` permits normal operations only when ActorContext grants the
  requested capability.
- `archived` denies normal read, operate, domain-task creation, and action
  approval. A later explicit retained-history flow may allow authorized
  read/comment without restoring operational authority.
- Archive does not implicitly convert an active grant to revoked; the resolver
  combines Plant and grant status on every decision.
- Restore does not mutate grants either: a previously active grant becomes
  operative again, while a previously revoked grant remains revoked.

## Archived Plant operational guard

- Boss may archive a Plant even when Plant-scoped tasks, approvals, follow-ups,
  agent work, IssueStack items, or Companion proposals remain open.
- Archive changes only `Plant.status` at this shared boundary. It does not
  complete, cancel, delete, execute, reject, approve, or supersede dependent
  records.
- While archived, normal Plant reads and every new or existing state-advancing
  Plant-scoped command fail closed. This includes operational mutations, agent
  context/publication, task transitions, approval decisions, action-task
  unlock, follow-up/outcome writes, Companion proposal decisions, and
  DecisionRecord workflow effects.
- Explicit exceptions are Boss archive/restore and grant administration plus
  authorized retained-history read/comment paths. Grant changes made while
  archived are stored and audited but remain non-operative.
- Restore changes only `Plant.status`. It does not resume, replay, refresh,
  approve, reject, complete, cancel, or otherwise transition a dependent
  record.
- After restore, each attempted transition must revalidate current
  ActorContext/grant, record state and anti-replay version, evidence freshness,
  and every owning safety or governance guard.
- A state-advancing service must check `Plant.status=active` in the same
  transactional authorization boundary as its write; cached UI state or an
  earlier context snapshot is insufficient against concurrent archive.

## PlantAccessGrant lifecycle

- `PlantAccessGrant.status`: `active | revoked`.
- Engineer and Consultant require an active grant for Plant scope.
- The active Engineer creator grant is required for immediate post-create
  visibility/operations and follows the same lifecycle as any other grant.
- Missing or revoked grant resolves fail-closed with `source=denied`.
- The only MVP override is `plant_approve_actions`.
- Engineer action approval requires an active grant with the override and a
  separate Safety Gate pass; Consultant never receives approval authority.
- Boss does not require a grant and resolves with `source=boss_role`.

## Effects and failures

- Missing/unknown/unauthorized Plant and missing/revoked grant produce the same
  no-existence-leak denial at the FT-001 seam.
- Archived Plant always denies normal operate/task/action approval.
- Archive/restore changes only Plant status and never creates, activates,
  revokes, or replaces a PlantAccessGrant.
- Open dependent records remain unchanged on archive; all operational
  transitions fail closed until restore and current-guard revalidation.
- Denied records are filtered before Bus/model context preparation.

## Verification

- Unit tests cover active/archived and active/revoked effects, missing grant,
  Boss bypass, Consultant restrictions, and action-approval derivation.
- Policy/transaction tests cover Boss and Engineer create, Consultant/disabled
  denial, atomic Engineer creator grant, default approval flag false, and
  rollback of Plant/grant/audit writes on any failure.
- Lifecycle tests prove the same grant IDs/statuses survive archive/restore,
  active grants regain normal effect after restore, and revoked grants do not.
- Cross-feature contract tests prove open task/approval/proposal records are
  unchanged by archive, cannot advance while archived, do not auto-resume on
  restore, and can advance only after current guards pass.
- Compatibility tests prove these effects map to the canonical
  `PlantPermissionContext` fields without implementing FT-002 persistence or
  mutation workflows.

## Related specs

- [.memory-bank/domains/farm/farm-plant-access-storage.md](../../domains/farm/farm-plant-access-storage.md)
- [.memory-bank/contracts/access/actor-context.md](../../contracts/access/actor-context.md)
- [.memory-bank/states/safety-action-lifecycle.md](../safety-action-lifecycle.md)
- [.memory-bank/states/companion-governance.md](../companion-governance.md)
