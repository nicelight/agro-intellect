---
description: Главная карта знаний проекта (table of contents) для агентов.
status: active
---
# Memory Bank Index

## Current State

Agro Intellect is in active MVP v2 post-PRD decomposition with a complete
global SDD backbone and a verified FT-000 executable Foundation.

FT-001 uses complete subject-based canonical specs. FT-002 currently exposes
only the bounded permission dependency slice required by FT-001; full FT-002
API/migration/task design remains deferred. FT-003 records the direct local
Account KISS direction while its full design/tasking remains deferred. The
FT-001 queue uses one authoritative indexed task card per task and direct
applicable SDD links.

FT-000 tasks `TASK-000` through `TASK-004` are done. FT-001 W1 is complete:
`TASK-005-T3-FT-001-W1` and `TASK-006-T3-FT-001-W1` are done after functional
verification, adversarial semantic verification, and explicit T3 owner
closure. The W1 boundary Memory Bank sync is complete. `TASK-007` through
`TASK-011` remain planned; TASK-007 is a legal promotion candidate pending a
separate owner decision.

MVP v1 is archived under [.memory-bank/archive/mvp-v1/](archive/mvp-v1/) and is
historical only.

## Governance and product

- [Constitution](constitution.md): top governing policy.
- [Product](product.md), [PRD](prd.md), [Requirements](requirements.md): active L1 requirements and RTM.
- [Epics](epics/index.md), [Features](features/index.md): active L2/L3 routers.
- [MBB](mbb/index.md): Memory Bank rules.
- [Invariants](invariants.md), [Glossary](glossary.md): shared guardrails and vocabulary.

## SDD routing

- [Spec Backbone](spec-backbone.md): readiness, area matrix, and handoffs.
- [Spec Index](spec-index.md): canonical subject-spec registry.
- [System Architecture](architecture/system-architecture.md): architecture and Architecture Spine.
- [Foundation](foundation.md): verified executable baseline.
- [Domains](domains/index.md), [Contracts](contracts/index.md), [States](states/index.md), [Testing](testing/index.md): subject routers.
- [User Scenarios](user-scenarios.md), [Core Domain](domains/core-domain.md), [Boundary Map](contracts/boundary-map.md), [Lifecycle Map](states/lifecycle-map.md): decomposition context.
- [Foundation Runtime Runbook](runbooks/foundation-local-runtime.md): local setup/start/smoke.
- [Changelog](changelog.md): durable change history.

## Active EP-001 compositions

- [FT-001](features/FT-001-local-accounts-sessions-actor-context.md): identity, sessions, ActorContext.
- [FT-002](features/FT-002-farm-plant-lifecycle-access-grants.md): Farm, Plant, access grants.
- [FT-003](features/FT-003-boss-admin-surface-admin-audit.md): Boss direct Account creation and audit direction.
- [FT-001 implementation plan](tasks/plans/IMPL-FT-001.md): active task sequence.

## Operational roots

- [Task Index](tasks/index.json): authoritative task-card registry.
- [Task Schema](schemas/task.schema.json): task record schema.
- [Workflows](workflows/index.md): execution policies.
- [Skills](skills/index.md): project skill registry.

## Next Route

```text
separate owner decision: promote TASK-007-T3-FT-001-W2
-> /execute TASK-007-T3-FT-001-W2
```
