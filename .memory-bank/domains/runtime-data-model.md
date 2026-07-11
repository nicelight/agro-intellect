---
description: Global runtime data authority model for MVP v2.
status: active
type: domain
last_updated: 2026-07-10
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/domains/core-domain.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/domains/foundation-data-substrate.md
  - .memory-bank/domains/photo-artifacts.md
  - .memory-bank/contracts/timeline-event.md
  - .memory-bank/states/plant-state-trust.md
  - .memory-bank/states/safety-action-lifecycle.md
  - .memory-bank/states/companion-governance.md
  - .memory-bank/states/dataset-governance.md
---
# Runtime Data Model

## Scope

This document defines global runtime authority and entity responsibility for MVP v2.
It is not a database schema, migration plan, or field catalog. Concrete tables,
columns, indexes, and migrations belong to the applicable canonical subject
specs and task-scoped implementation handoffs.

## Scope Boundaries

- Defines: global runtime authority layers, shared entity relationships, cross-feature
  relational identifier compatibility, storage authority separation, and
  feature-local data-detail routing.
- Out of scope: exact table schemas, migrations, endpoint payloads, concrete
  event payloads, or feature-specific state machines.
- Related specs:
  - [.memory-bank/domains/foundation-data-substrate.md](foundation-data-substrate.md):
    defines FT-000 DB/session/Alembic/runtime-root substrate.
  - [.memory-bank/domains/photo-artifacts.md](photo-artifacts.md): defines local
    photo artifact authority and cross-feature refs.
  - [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md):
    defines append-only audit/export events.
  - [.memory-bank/states/index.md](../states/index.md): routes active
    cross-feature lifecycle/state specs.
  - [.memory-bank/domains/identity/account-membership.md](identity/account-membership.md):
    defines exact Account and FarmMembership columns/constraints.
  - [.memory-bank/domains/auth/session-storage.md](auth/session-storage.md):
    defines exact LocalSession persistence.
  - [.memory-bank/domains/farm/farm-plant-access-storage.md](farm/farm-plant-access-storage.md):
    defines Farm, Plant, PlantAccessGrant, and final Farm FK migration.

## Brownfield Baseline

Verified FT-000 code/evidence currently proves the shared backend app factory,
settings, database/session helper, Alembic command path, local bootstrap,
runtime-root settings, `/health`, `/ready`, and redaction baseline. The concrete
substrate is owned by
[.memory-bank/domains/foundation-data-substrate.md](foundation-data-substrate.md).
It does not implement product Account, FarmMembership, Plant, task, photo,
agent, Safety Gate, governance, or UI projection schemas.

## Authority Layers

| Layer | Authority | Examples |
|---|---|---|
| PostgreSQL/read model | Mutable operational state and authorization state. | Account, Farm, FarmMembership, Plant, PlantAccessGrant, check-in, measurement, task, approval, outcome, governance record, dataset fields, photo catalog. |
| Local filesystem | Binary/artifact identity only. | Photo original, derived file, adjacent manifest. |
| `timeline.jsonl` | Append-only audit/export trace only. | User photo event, check-in event, agent publication ref, task/outcome ref, admin audit export ref. |
| Agent Chat Bus | Agent-consumable working events only. | Validated event refs, MessageEnvelope refs, approved governance summary facts. |
| UI Feed | Human presentation only. | Cards, prompts, timeline views, spoiler notes, storage warnings. |

## Shared Entities

- `Account`: local user identity for session, attribution, and authorization.
- `Farm`: the single local MVP workspace.
- `FarmMembership`: Account-to-Farm relationship with role preset and membership status.
- `ActorContext`: request/context boundary containing Account, Farm, role/membership, Plant permissions, and session/auth provenance.
- `Plant`: Farm-managed crop unit; `tomato_001` is the initial Plant.
- `PlantAccessGrant`: per-Plant visibility/work authorization and optional `plant_approve_actions`.
- `AdminAuditRecord`: durable account, role, membership, Plant lifecycle, and access-change audit.
- `PhotoCatalogItem`: accepted photo metadata and artifact refs.
- `TimelineEvent`: append-only audit/export event.
- `Task`, `Approval`, `Outcome`: operational loop records.
- `IssueStack`, `CompanionProposal`, `CompanionConclusion`, `HumanAttentionNeeded`, `DecisionRecord`: Plant-scoped governance records.
- Dataset governance fields: lifecycle status, evidence refs, confirmation source, split, and `can_train_on`.

Detailed state authority for Plant trust, Safety action lifecycle, Companion
governance, and dataset trainability lives in the active state specs under
[.memory-bank/states/](../states/index.md). Feature specs may refine those
state machines but must not contradict the shared canonical spec.

## Cross-Feature Relational Identity Contract

Shape:

- Product entity identifiers and matching FK columns use PostgreSQL native
  `uuid`, mapped as Python `uuid.UUID` through SQLAlchemy
  `Uuid(as_uuid=True)`.
- `account_id`, `membership_id`, `session_id`, and `farm_id` use this same
  representation. FT-002 `plant_id` and `grant_id` follow it as well.
- New identifiers are application-generated with `uuid.uuid4`; the schema does
  not require a PostgreSQL UUID extension or integer sequence.

Rules:

- A FK column must use exactly the same UUID representation as its referenced
  PK. String, integer, mixed UUID/text, and feature-local alternate ID schemes
  are forbidden for these relational identities.
- Human-readable keys such as `farm_key` and `plant_key` are alternate lookup
  keys, never substitutes for UUID identity.
- Authority records use disable/archive/revoke lifecycle semantics. Relational
  FKs between Account/Farm/Membership/Session/Plant/Grant records must use
  `ON DELETE RESTRICT` (or equivalent non-cascading enforcement); cascading
  deletion of authority/history is forbidden.
- Canonical subject specs remain the single sources for exact columns,
  nullability, indexes, FK timing, and migration order.

Edge cases/errors:

- Malformed external UUID text is rejected at request/schema validation before
  repository access.
- A migration that changes one side of an existing UUID relation to text or
  integer is incompatible and must stop.
- A cross-feature relation may be introduced in a later scoped migration only
  when earlier work cannot create the referenced authority without crossing
  its boundary; applicable canonical specs must define the temporary
  invariant and final FK migration explicitly.

Verification target:

- Migration/model tests inspect native UUID PK/FK types and prove Python values
  round-trip as `uuid.UUID`.
- Contract tests prove authority FKs reject deletes instead of cascading.
- Cross-feature migration tests prove deferred references are closed by the
  scoped migration before product write paths are enabled.

## Runtime Invariants

- Every Farm/Plant mutable record is scoped to the single local Farm and, when relevant, Plant.
- Engineer Plant creation commits the new Plant, active creator
  PlantAccessGrant (`plant_approve_actions=false`), and required audit records
  in one PostgreSQL transaction; any failure rolls back the full write set.
- Every protected product read, mutation, and context-builder path has
  ActorContext before business logic. Service health/readiness endpoints and
  explicitly public auth endpoints are not runtime authority and must not expose
  Farm/Plant data.
- Plant archive removes the Plant from normal operations but does not delete history, photos, tasks, outcomes, timeline, or admin audit.
- Plant archive/restore changes only Plant status at this boundary and preserves
  PlantAccessGrant identities, statuses, and permission flags unchanged.
- Plant archive preserves dependent operational/governance record rows and
  states but globally denies their state-advancing commands. Restore changes no
  dependent record and every later transition revalidates current Plant,
  authorization, record-version, freshness, safety, and governance guards.
- Photo files/manifests can be referenced by runtime records but cannot override runtime state.
- Timeline events can reference runtime records but cannot become mutable state authority.
- Agent output can create downstream publishable events or tasks only after
  project-owned adapter validation, strict safety classification, current
  authorization, and the applicable Bus/UI/task/Safety boundary.
- DecisionRecord can create governance/workflow direction only inside backend rules.
- `can_train_on` is false unless dataset governance rules explicitly allow a later transition.

## Subject Detail Routing

- FT-001..FT-003 compose registered identity/session/access/admin subject specs.
- FT-004..FT-006 compose canonical check-in, measurement, photo catalog,
  timeline, and Plant-history specs.
- FT-007..FT-010 must compose agent I/O and Plant-trust specs.
- FT-011..FT-012 must compose Safety Gate, approval, task, and outcome specs.
- FT-013..FT-016 must compose governance, dataset, local-security, and UI
  subject specs as applicable.

Before any T2/T3 task is created, `/prd-to-tasks` performs registry/folder
discovery, links the relevant shared/canonical specs, and writes any missing
concrete shape, rules, errors, and verification into exactly one subject path.
