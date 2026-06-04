---
description: Главная карта знаний проекта (table of contents) для агентов.
status: active
---
# Memory Bank Index

## Current State

The active Memory Bank is in MVP v2 migration.

The MVP v1 spec-layer has been hard-archived under
[.memory-bank/archive/mvp-v1/](archive/mvp-v1/): historical PRD, requirements,
epics, features, SDD specs, contracts, states, domains, runbooks, and testing docs.

Active agents must not use archived MVP v1 specs as current source of truth.
Archived docs are historical reference only. The active MVP v2 PRD has now been
decomposed into MVP v2 L1-L3 product, requirements, epics, and features. The global SDD
backbone has completed `/spec-design`; feature-level `/spec-improve FT-<NNN>` is still
required before task decomposition.

## Active Governance And Routing

- [.memory-bank/constitution.md](constitution.md): Project Constitution — top governing policy for agents.
- [.memory-bank/product.md](product.md): active MVP v2 product summary.
- [.memory-bank/prd.md](prd.md): clarified MVP v2 PRD with `clarification_status: complete`.
- [.memory-bank/requirements.md](requirements.md): active MVP v2 REQ list and RTM.
- [.memory-bank/epics/index.md](epics/index.md): active MVP v2 L2 epic router.
- [.memory-bank/features/index.md](features/index.md): active MVP v2 L3 feature router.
- [.memory-bank/mbb/index.md](mbb/index.md): Memory Bank Bible rules.
- [.memory-bank/invariants.md](invariants.md): current cross-cutting MUST/NEVER guardrails.
- [.memory-bank/glossary.md](glossary.md): active shared vocabulary for MVP v2 migration.
- [.memory-bank/spec-index.md](spec-index.md): active MVP v2 migration route map.
- [.memory-bank/spec-backbone.md](spec-backbone.md): pre-PRD spec framing status and /prd handoff.
- [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md): global MVP v2 system architecture backbone.
- [.memory-bank/user-scenarios.md](user-scenarios.md): active pre-PRD user scenarios and decomposition implications.
- [.memory-bank/domains/core-domain.md](domains/core-domain.md): active pre-PRD core domain framing.
- [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md): runtime authority, storage ownership, and shared entity groups.
- [.memory-bank/contracts/index.md](contracts/index.md): active MVP v2 contract router.
- [.memory-bank/contracts/api-guidelines.md](contracts/api-guidelines.md): frontend/backend API, auth, errors, uploads, CORS, and OpenAPI generation rules.
- [.memory-bank/contracts/agent-harness.md](contracts/agent-harness.md): shared AgentHarness and AgentProfile runtime contract.
- [.memory-bank/contracts/agent-chat-bus.md](contracts/agent-chat-bus.md): agent-consumable BusEventEnvelope contract.
- [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md): MessageEnvelope, runtime decision, and UI Feed projection contract.
- [.memory-bank/contracts/safety-gate.md](contracts/safety-gate.md): physical-action advice and Safety Gate approval contract.
- [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md): active preliminary boundary hints for decomposition.
- [.memory-bank/states/core-lifecycles.md](states/core-lifecycles.md): global lifecycle state guardrails for shared entities.
- [.memory-bank/states/lifecycle-map.md](states/lifecycle-map.md): active lifecycle hints for decomposition.
- [.memory-bank/testing/index.md](testing/index.md): testing and verification router for the migration stage.
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
/spec-improve FT-<NNN>
-> /prd-to-tasks FT-<NNN>
```

Do not run `/prd-to-tasks` from archived MVP v1 features.
Do not create TASK records from the PRD output until the relevant feature-level
`/spec-improve` gates are complete.

## Operational Roots

- [.memory-bank/tasks/index.json](tasks/index.json): authoritative JSON task record index.
- [.memory-bank/schemas/task.schema.json](schemas/task.schema.json): JSON schema for task records.
- [.memory-bank/workflows/index.md](workflows/index.md): workflow policies and execution-loop router.
- [.memory-bank/skills/index.md](skills/index.md): skill registry.
