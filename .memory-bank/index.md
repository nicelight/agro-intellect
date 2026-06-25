---
description: Главная карта знаний проекта (table of contents) для агентов.
status: active
---
# Memory Bank Index

## Current State

The active Memory Bank is in MVP v2 post-PRD-decomposition,
post-global-SDD-backbone, and post-Foundation state. Generated first-wave
product task artifacts have been intentionally removed. The compact `FT-000`
Foundation task queue is complete and verified.

The MVP v1 spec-layer has been hard-archived under
[.memory-bank/archive/mvp-v1/](archive/mvp-v1/): historical PRD, requirements,
epics, features, SDD specs, contracts, states, domains, runbooks, and testing docs.

Active agents must not use archived MVP v1 specs as current source of truth.
Archived docs are historical reference only. The active MVP v2 PRD now promotes the
first product decisions back into the active Memory Bank. Active MVP v2 product,
requirements, epics, and features exist as draft L1-L3 artifacts. The global SDD
architecture backbone is complete. Feature-level `/spec-improve` is complete for
FT-001, FT-002, and FT-003; their current normative feature designs are
registered in [.memory-bank/spec-index.md](spec-index.md). The active task index
contains `FT-000` foundation tasks only, and `TASK-000-T1-FT-000-W0` through
`TASK-004-T2-FT-000-W0` are `done`. `REQ-000` and `FT-000` are verified by the
final Foundation gate and W0 semantic red-verification.
Other features still require feature-level `/spec-improve FT-<NNN>` before any
future implementation planning.

## Active Governance And Routing

- [.memory-bank/constitution.md](constitution.md): Project Constitution — top governing policy for agents.
- [.memory-bank/product.md](product.md): active L1 product summary for MVP v2.
- [.memory-bank/prd.md](prd.md): clarified MVP v2 PRD with `clarification_status: complete`.
- [.memory-bank/requirements.md](requirements.md): active MVP v2 REQ list and RTM.
- [.memory-bank/epics/index.md](epics/index.md): active MVP v2 epic router.
- [.memory-bank/features/index.md](features/index.md): active MVP v2 feature router.
- [.memory-bank/mbb/index.md](mbb/index.md): Memory Bank Bible rules.
- [.memory-bank/invariants.md](invariants.md): current cross-cutting MUST/NEVER guardrails.
- [.memory-bank/glossary.md](glossary.md): active shared vocabulary for MVP v2 migration.
- [.memory-bank/spec-index.md](spec-index.md): active MVP v2 migration route map.
- [.memory-bank/spec-backbone.md](spec-backbone.md): pre-PRD spec framing status, global backbone status, and /spec-improve handoff.
- [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md): global MVP v2 architecture backbone.
- [.memory-bank/foundation.md](foundation.md): required compact Foundation Dev Path and Feature Pressure Map before product tasking.
- [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md): global runtime authority and data ownership model.
- [.memory-bank/contracts/index.md](contracts/index.md): active contract router.
- [.memory-bank/contracts/api-guidelines.md](contracts/api-guidelines.md): HTTP/API, ActorContext, authz, error, upload, CORS, and OpenAPI-generation guardrails.
- [.memory-bank/contracts/agent-chat-bus.md](contracts/agent-chat-bus.md): agent-consumable event boundary and context hygiene.
- [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md): structured agent-output boundary.
- [.memory-bank/user-scenarios.md](user-scenarios.md): active pre-PRD user scenarios and decomposition implications.
- [.memory-bank/domains/core-domain.md](domains/core-domain.md): active pre-PRD core domain framing.
- [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md): active preliminary boundary hints for decomposition.
- [.memory-bank/states/lifecycle-map.md](states/lifecycle-map.md): active lifecycle hints for decomposition.
- [.memory-bank/testing/index.md](testing/index.md): testing and verification router for the post-PRD decomposition stage.
- [.memory-bank/changelog.md](changelog.md): Memory Bank changelog.

## Active Analysis Inputs

- [.memory-bank/analysis/index.md](analysis/index.md): analysis router and current next-step record.
- [.memory-bank/analysis/mvp-scope-expansion-integration-plan.md](analysis/mvp-scope-expansion-integration-plan.md): MVP v2 feature-scope input.
- [.memory-bank/analysis/accounts-farm-access-admin-analysis.md](analysis/accounts-farm-access-admin-analysis.md): draft analysis for Accounts, Farm access, Boss admin, personnel, Plants, and per-Plant access.
- [.memory-bank/analysis/companion-issue-stack-decision-governance.md](analysis/companion-issue-stack-decision-governance.md): draft analysis for Companion `IssueStack`, proposals, and `DecisionRecord` governance.

## Archived MVP v1

- [.memory-bank/archive/mvp-v1/index.md](archive/mvp-v1/index.md): archived MVP v1 router.
- [.memory-bank/archive/mvp-v1/prd.md](archive/mvp-v1/prd.md): archived MVP v1 PRD.
- [.memory-bank/archive/mvp-v1/spec-index.md](archive/mvp-v1/spec-index.md): archived MVP v1 SDD Design Specs Index.
- [.memory-bank/archive/mvp-v1/features/index.md](archive/mvp-v1/features/index.md): archived FT-001..FT-014 feature router.
- [.memory-bank/archive/mvp-v1/tech-specs/index.md](archive/mvp-v1/tech-specs/index.md): archived FT-001..FT-014 tech-spec router.
- [.memory-bank/archive/mvp-v1/root/index.md](archive/mvp-v1/root/index.md): archived root-level MVP v1 planning and diagram artifacts.

## Workflow

Next route:

```text
/prd-to-tasks FT-001
then /review-tasks-plan FT-001 before implementation
```

Foundation no longer blocks product tasking. FT-001, FT-002, and FT-003 already
have current normative feature designs and may be decomposed with `/prd-to-tasks`
one feature at a time, followed by `/review-tasks-plan FT-<NNN>` before
implementation. For features outside FT-001..FT-003, run `/spec-improve
FT-<NNN>` before task decomposition. Do not use archived MVP v1 features as
current source of truth.

## Operational Roots

- [.memory-bank/tasks/index.json](tasks/index.json): authoritative JSON task record index.
- [.memory-bank/schemas/task.schema.json](schemas/task.schema.json): JSON schema for task records.
- [.memory-bank/workflows/index.md](workflows/index.md): workflow policies and execution-loop router.
- [.memory-bank/skills/index.md](skills/index.md): skill registry.
