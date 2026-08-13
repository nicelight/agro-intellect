---
description: Router for active canonical domain, persistence, migration, and internal data specifications.
status: active
last_updated: 2026-08-12
source_of_truth:
  - .memory-bank/spec-index.md
  - .memory-bank/spec-backbone.md
---
# Domains Index

## Global domain specs

- [Core Domain](core-domain.md): PRD-level vocabulary and rules.
- [Runtime Data Model](runtime-data-model.md): runtime authority and shared identity.
- [Foundation Data Substrate](foundation-data-substrate.md): DB/session/Alembic/runtime roots.
- [Plant Operations](plant-operations.md): check-in, observation, manual pH/EC, and freshness persistence.
- [Photo Artifacts](photo-artifacts.md): local artifact authority, catalog,
  layout, capture manifests, and authoritative Farm photo-storage pressure.
- [Plant History](plant-history.md): Plant card/history projections, retained-history access, and timeline-ref authority boundaries.
- [Agent Chat And UI Feed Storage](agent-chat-ui-feed-storage.md): Bus/UI
  PostgreSQL authority, atomic publication, lazy active-Feed introduction
  materialization, and data-preserving batch-table removal.
- [Plant State Observations](plant-state-observations.md): visual/state
  observations, assessments, conflicts, and explicit human promotion.
- [Safety Action Routing](safety-action-routing.md): immutable classification,
  physical-action Safety decision, approval-input evidence, and pending
  proposal persistence.
- [Task, Approval, And Outcome Data](task-approval-outcomes.md): PostgreSQL
  authority, transactions, idempotency, automatic follow-up, and audit refs.
- [Companion Governance Data](companion-governance.md): IssueStack,
  HumanAttentionNeeded, proposals, DecisionRecords, atomic effects, and
  projections.
- [Dataset Governance Data](dataset-governance.md): Dataset Candidate
  persistence, evidence-flow creation seam, transition transactions, and
  derived trainability.

## Subject data specs

- [Account And FarmMembership](identity/account-membership.md): local identity and membership persistence.
- [Session Storage](auth/session-storage.md): digest-only LocalSession persistence.
- [Farm Plant And Access Storage](farm/farm-plant-access-storage.md): exact Farm/Plant/grant persistence, migration, bootstrap, and transaction rules.
- [Admin Audit](admin/admin-audit.md): durable audited mutation records.

## Routing

Use `domains/` for internal models, storage, migrations, retention, and runtime
data rules. Payload compatibility belongs in `contracts/`; transitions belong
in `states/`. Discover existing canonical paths before creating a spec.
