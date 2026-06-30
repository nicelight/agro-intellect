---
description: Global runtime data authority model for MVP v2.
status: active
owner: architecture
type: domain
last_updated: 2026-06-29
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

This document defines global runtime authority and entity ownership for MVP v2.
It is not a database schema, migration plan, or field catalog. Concrete tables,
columns, indexes, and migrations belong to feature-level SDD design inside
`/prd-to-tasks FT-<NNN>` and the resulting task decomposition. Standalone
`/spec-improve FT-<NNN>` is reserved for repair or advanced refresh without task
generation.

## Ownership

- Owns: global runtime authority layers, shared entity ownership, cross-feature
  relational identifier compatibility, storage authority separation, and
  feature-local data-detail routing.
- Does not own: exact table schemas, migrations, endpoint payloads, concrete
  event payloads, or feature-specific state machines.
- Related specs:
  - [.memory-bank/domains/foundation-data-substrate.md](foundation-data-substrate.md):
    owns FT-000 DB/session/Alembic/runtime-root substrate.
  - [.memory-bank/domains/photo-artifacts.md](photo-artifacts.md): owns local
    photo artifact authority and cross-feature refs.
  - [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md):
    owns append-only audit/export events.
  - [.memory-bank/states/index.md](../states/index.md): routes active
    cross-feature lifecycle/state specs.
  - [.memory-bank/domains/local-identity-session-data.md](local-identity-session-data.md):
    owns exact Account, FarmMembership, and LocalSession columns/constraints.
  - [.memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md](../tech-specs/FT-002-farm-plant-lifecycle-access-grants.md):
    owns exact Farm, Plant, PlantAccessGrant, and deferred Farm FK migration.

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
state machines but must not contradict the shared owner.

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
- Feature specs remain the single owners for exact columns, nullability,
  indexes, FK timing, and migration order.

Edge cases/errors:

- Malformed external UUID text is rejected at request/schema validation before
  repository access.
- A migration that changes one side of an existing UUID relation to text or
  integer is incompatible and must stop.
- A cross-feature relation may be introduced in a later owning migration only
  when the earlier feature cannot create the referenced authority without
  violating ownership; the owning feature specs must define the temporary
  invariant and final FK migration explicitly.

Verification target:

- Migration/model tests inspect native UUID PK/FK types and prove Python values
  round-trip as `uuid.UUID`.
- Contract tests prove authority FKs reject deletes instead of cascading.
- Cross-feature migration tests prove deferred references are closed by the
  owning feature before its product write paths are enabled.

## Runtime Invariants

- Every Farm/Plant mutable record is scoped to the single local Farm and, when relevant, Plant.
- Every protected product read, mutation, and context-builder path has
  ActorContext before business logic. Service health/readiness endpoints and
  explicitly public auth endpoints are not runtime authority and must not expose
  Farm/Plant data.
- Plant archive removes the Plant from normal operations but does not delete history, photos, tasks, outcomes, timeline, or admin audit.
- Photo files/manifests can be referenced by runtime records but cannot override runtime state.
- Timeline events can reference runtime records but cannot become mutable state authority.
- Agent output can create publishable events/tasks only through project-owned adapters and safety/task boundaries.
- DecisionRecord can create governance/workflow direction only inside backend rules.
- `can_train_on` is false unless dataset governance rules explicitly allow a later transition.

## Feature-Local Detail Routing

- FT-001..FT-003 own exact Account/FarmMembership/ActorContext/admin data details.
- FT-004..FT-006 own check-in, measurement, photo catalog, timeline, and Plant history details.
- FT-007..FT-010 own agent output refs and Plant state trust details.
- FT-011..FT-012 own Safety Gate, approval, task, and outcome state details.
- FT-013 owns Companion governance state details.
- FT-014 owns dataset lifecycle and trainability transition details.
- FT-015 owns local security/storage fields.
- FT-016 owns UI projections and first-demo data dependencies.

Before any T2/T3 task record is created for these areas, the feature-level SDD
design must link the relevant shared owner and add concrete feature-local
`shape`, `rules`, `edge cases/errors`, and `verification target` blocks where
the shared owner intentionally routes detail to the feature.
