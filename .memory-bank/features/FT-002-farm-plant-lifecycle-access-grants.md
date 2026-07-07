---
description: FT-002 Farm Plant Lifecycle And Access Grants.
status: draft
type: feature
feature_id: FT-002
epic: EP-001
lifecycle: planned
last_updated: 2026-07-06
clarification_status: complete
last_clarified: 2026-07-06
clarification_questions: 12
spec_design_status: complete
spec_design_links:
  - .memory-bank/domains/farm/farm-plant-access-storage.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/domains/admin/admin-audit.md
  - .memory-bank/contracts/farm/plant-management-http.md
  - .memory-bank/testing/farm/plant-lifecycle-and-access.md
  - .memory-bank/states/safety-action-lifecycle.md
  - .memory-bank/states/companion-governance.md
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/states/lifecycle-map.md
---
# FT-002 Farm Plant Lifecycle And Access Grants

## Use Cases

- Boss uses the single local Farm workspace created by idempotent local bootstrap.
- The Farm uses UUID primary identity, immutable `farm_key="local_farm"`, and
  a Boss-editable `display_name`.
- Bootstrap creates `tomato_001` when it is absent and reuses existing canonical
  Farm/Plant records without duplication or overwrite.
- Boss or an Engineer with an active grant may change an active Plant
  `display_name`; stable `plant_key` values are never renamed.
- Active Boss or Engineer creates additional Plants inside the local Farm by
  providing an immutable `plant_key` and initial `display_name`.
- An Engineer creator receives an active PlantAccessGrant in the same
  transaction and can immediately read and operate the new Plant.
- Boss archives or restores a Plant.
- Boss grants or revokes per-Plant access and optionally grants `plant_approve_actions`.
- Boss may reactivate a revoked PlantAccessGrant without creating a new grant
  identity.
- Boss may manage PlantAccessGrant records while the Plant is archived; the
  stored changes remain non-operative until restore.

## Acceptance Criteria

- MVP supports exactly one local Farm workspace.
- The canonical Farm has UUID primary identity and immutable
  `farm_key="local_farm"`; only Boss may update its `display_name`.
- Multiple Plants are supported; `tomato_001` is the initial Plant.
- Local bootstrap idempotently creates the canonical Farm and `tomato_001` only
  when absent; repeated runs preserve existing records and create no duplicates.
- Bootstrap fails closed without mutation when multiple Farm records or
  conflicting canonical keys are detected.
- Every Plant has UUID primary identity plus an immutable `plant_key` unique
  within the Farm and a mutable `display_name`; the initial key remains
  `tomato_001` permanently.
- Active Boss or Engineer supplies `plant_key` at Plant creation. Backend
  accepts only lowercase keys matching `^[a-z0-9]+(?:_[a-z0-9]+)*$` and
  enforces uniqueness within the Farm.
- Engineer creation atomically commits the active Plant, an active creator
  PlantAccessGrant with `plant_approve_actions=false`, and the required
  `plant_created`/`plant_access_granted` audit records. Any failure persists
  none of them.
- The creator grant gives the Engineer immediate read and operate authority for
  the new active Plant through normal ActorContext resolution.
- Boss and an Engineer with an active grant may update `display_name` for an
  active Plant. Consultant has no rename authority.
- Engineer creation does not authorize Plant archive/restore or
  PlantAccessGrant management; those remain Boss-only.
- Plant removal is archive/restore only; no hard delete in MVP.
- Archived Plants disappear from normal operations but remain retained for authorized history/audit/export access.
- Archiving a Plant preserves its grants unchanged; restoring it makes every
  still-active grant effective again.
- Boss may archive a Plant with unfinished tasks, approvals, or proposals.
  Those records remain retained but become non-operative while archived;
  restore never bypasses current authorization, freshness, or Safety Gate
  checks.
- PlantAccessGrant controls Plant visibility and work authorization.
- At most one PlantAccessGrant exists for each `(membership_id, plant_id)`
  pair. Re-granting access reactivates the same stable `grant_id`, applies the
  requested `plant_approve_actions` value, and writes an audit record.
- Archived Plant does not block Boss grant/revoke/reactivate/approval-flag
  mutations, but none of those mutations grants operational access before
  restore.

## Edge Cases & Failure Modes

- Unauthorized actors cannot see, mutate, archive, restore, or access retained history for unauthorized Plants.
- Archived Plant cannot be selected for normal daily operations.
- Archive temporarily blocks access without revoking grants; restore must not
  reactivate grants that were explicitly revoked while the Plant was archived.
- Archive must not delete, complete, cancel, or execute unfinished workflow
  records. Archived Plant state blocks their operational transitions; after
  restore each transition is revalidated against current guards.
- Revoked PlantAccessGrant removes operational visibility and context-builder access.
- Duplicate grants for the same membership/Plant pair are rejected; revoke and
  reactivate transitions preserve the original `grant_id`.
- Grant mutations on archived Plant are audited and must not make the Plant
  selectable or operational.
- `plant_approve_actions` is the only MVP per-Plant permission override.
- Repeated bootstrap must not duplicate or overwrite the canonical Farm or
  `tomato_001`.
- Multiple Farm records or conflicting canonical keys produce one safe,
  actionable diagnostic error and require manual repair; bootstrap must not
  select, merge, or delete records automatically.
- Attempts to change `farm_key` are rejected.
- Attempts to change `plant_key`, including `tomato_001`, are rejected; only
  `display_name` is user-editable.
- Invalid or duplicate `plant_key` values fail without creating a Plant.
- Archived Plant, Consultant, and an Engineer with a missing or revoked grant
  cannot update `display_name`.
- Consultant, disabled membership, or any Engineer create failure writes no
  Plant, creator grant, or success audit.

## Verification Targets

- Unit: Plant lifecycle transitions, create/rename role policy, grant
  uniqueness, stable grant identity, revoke/reactivate policy, and archived
  grant-management behavior.
- Integration: authorized vs unauthorized Plant list/context builder, atomic
  Engineer creator grant/audit, rollback, and grant preservation across
  archive/restore; later task/approval/governance integrations must prove
  archived workflows are retained but non-operative.
- E2E: Engineer creates and immediately selects a Plant, cannot archive/restore
  it or manage grants; Boss archives/restores it and the same active creator
  grant becomes non-operative then operative again.

## Behavior specs

- `.memory-bank/behavior-specs/FT-002-BHV-001-idempotent-canonical-bootstrap.behavior.json`
- `.memory-bank/behavior-specs/FT-002-BHV-002-engineer-create-immediate-access.behavior.json`
- `.memory-bank/behavior-specs/FT-002-BHV-003-archive-grant-restore.behavior.json`

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): module boundaries and runtime authority.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): Plant and PlantAccessGrant ownership.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): route authorization and fail-closed behavior.
- [.memory-bank/states/safety-action-lifecycle.md](../states/safety-action-lifecycle.md): archived-Plant guard for approvals, tasks, follow-up, and outcomes.
- [.memory-bank/states/companion-governance.md](../states/companion-governance.md): archived-Plant guard for proposals, decisions, and workflow effects.

## Specification Composition

- [Farm/Plant/access storage](../domains/farm/farm-plant-access-storage.md)
  defines identity/status relationships and Engineer-create atomicity.
- [Plant/access lifecycle](../states/plants/plant-and-access-lifecycle.md)
  defines active/archived, active/revoked, create authority, and grant
  preservation effects.
- [ActorContext](../contracts/access/actor-context.md) defines concrete Plant
  permission resolution and fail-closed output.
- [Admin audit](../domains/admin/admin-audit.md) defines the shared exact audit
  schema, taxonomy, redaction, and same-transaction requirements.
- [Plant management HTTP](../contracts/farm/plant-management-http.md) defines
  concrete Farm/Plant/access routes, payloads, authorization, and errors.
- [Plant lifecycle and access verification](../testing/farm/plant-lifecycle-and-access.md)
  defines migration, bootstrap, service, API, and integrated evidence.
- [Safety Action Lifecycle](../states/safety-action-lifecycle.md) and
  [Companion Governance](../states/companion-governance.md) compose the shared
  archive guard for already-open dependent records.

Retained-history payloads/services and downstream task, approval, agent, and
governance schemas remain with their owning features. FT-002 supplies the
shared archive guard and must not create placeholder implementations for them.

## SDD Design Gate

- Global/shared status: ready. Architecture Spine `AD-007` and the linked
  lifecycle specs define the archived-Plant operational guard.
- Feature-local status: complete. Exact persistence/bootstrap, lifecycle,
  audit, HTTP/error, ActorContext adapter, and verification contracts are
  linked above. Retained-history contents are explicitly not part of FT-002.

## Non-Goals

- Hard delete, multi-Farm tenancy, or a general ACL engine.
- Plant operation forms, daily check-ins, photo upload, or detailed Plant
  history rendering beyond access/lifecycle hooks.
- Agent output generation, MessageEnvelope/UI Feed projection, Safety Gate
  policy, or physical-action task execution.

## Implementation

- [Implementation plan](../tasks/plans/IMPL-FT-002.md): ordered task queue,
  dependencies, verification strategy, and UAT.

## Clarifications

### Session 2026-07-06

- Q: How should the initial Farm and `tomato_001` be created? -> A: An
  idempotent local bootstrap creates missing canonical records; repeated runs
  reuse existing records without duplication or overwrite.
- Q: How should bootstrap react to multiple Farm records or conflicting
  canonical keys? -> A: Fail closed without mutation, return a safe actionable
  diagnostic error, and require manual repair.
- Q: What identity contract should Plant use? -> A: UUID is the primary
  identity; `plant_key` is immutable and unique within the Farm, `tomato_001`
  is never renamed, and users may change only `display_name`.
- Q: How should immutable `plant_key` be assigned to new Plants? -> A: The
  authorized creator supplies it at creation; backend validates the lowercase
  `^[a-z0-9]+(?:_[a-z0-9]+)*$` format and Farm-scoped uniqueness.
- Q: What should happen to active PlantAccessGrant records during
  archive/restore? -> A: Preserve them unchanged; archive temporarily blocks
  access and restore makes previously active, non-revoked grants effective
  again.
- Q: Who besides Boss may create a Plant, and which management abilities remain
  Boss-only? -> A: An active Engineer may create a Plant; archive/restore and
  grant management remain Boss-only.
- Q: What access does an Engineer receive to a Plant they create? -> A: The
  creation transaction atomically creates an active creator PlantAccessGrant;
  the Engineer can immediately read and operate the Plant, while
  `plant_approve_actions` starts as `false`.
- Q: How should access be granted again after revoke? -> A: Keep one grant per
  `(membership_id, plant_id)` pair and reactivate the same stable `grant_id`;
  Boss sets the requested `plant_approve_actions` value and the transition is
  audited.
- Q: Who may change Plant `display_name`? -> A: Boss and an Engineer with an
  active grant may rename an active Plant; Consultant, archived Plant, and a
  missing or revoked grant do not permit it.
- Q: May a Plant with unfinished tasks, approvals, or proposals be archived?
  -> A: Yes. Preserve the records without automatic completion, cancellation,
  deletion, or execution; archived state makes them non-operative, and restore
  requires all current authorization, freshness, and Safety Gate checks again.
- Q: May Boss manage grants while a Plant is archived? -> A: Yes. Grant,
  revoke, reactivate, and `plant_approve_actions` changes are stored and
  audited, but remain non-operative until restore.
- Q: What identity contract should the single Farm use? -> A: UUID is the
  primary identity, `farm_key="local_farm"` is immutable, and Boss may change
  only the Farm `display_name`.
