---
description: Global runtime data authority model for MVP v2.
status: active
owner: architecture
type: domain
last_updated: 2026-06-14
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/domains/core-domain.md
  - .memory-bank/architecture/system-architecture.md
---
# Runtime Data Model

## Scope

This document defines global runtime authority and entity ownership for MVP v2. It is not a database schema, migration plan, or field catalog. Concrete tables, columns, indexes, and migrations belong to feature-local `/spec-improve` and task decomposition.

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

## Runtime Invariants

- Every Farm/Plant mutable record is scoped to the single local Farm and, when relevant, Plant.
- Every read/mutation/context-builder path has ActorContext before business logic.
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
