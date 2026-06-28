---
description: Главная карта знаний проекта (table of contents) для агентов.
status: active
---
# Memory Bank Index

## Current State

The active Memory Bank is in MVP v2 post-PRD-decomposition,
post-brownfield-global-SDD-backbone refresh, post-expanded shared SDD
contract/state refresh, post-Foundation state, and post-expanded
`/prd-to-tasks FT-001` refresh. Older
generated first-wave product task artifacts were removed during rollback; the
current FT-001 task queue was regenerated later, refreshed after the brownfield
global SDD backbone update, and refreshed again against the expanded
`/prd-to-tasks` concrete contract readiness protocol. The compact `FT-000`
Foundation task queue is complete and verified.

The MVP v1 spec-layer has been hard-archived under
[.memory-bank/archive/mvp-v1/](archive/mvp-v1/): historical PRD, requirements,
epics, features, SDD specs, contracts, states, domains, runbooks, and testing docs.

Active agents must not use archived MVP v1 specs as current source of truth.
Archived docs are historical reference only. The active MVP v2 PRD now promotes the
first product decisions back into the active Memory Bank. Active MVP v2 product,
requirements, epics, and features exist as draft L1-L3 artifacts. The global SDD
architecture backbone is complete, brownfield-refreshed against verified
FT-000 code/evidence, expanded with shared global SDD owners for UI Feed,
timeline audit/export, photo artifacts, Plant state trust, Safety action
lifecycle, Companion governance, and dataset governance, and refreshed through
`/foundation-to-tasks` substrate spec audit for runtime, smoke API,
DB/session/migration, test harness, runbook, and redaction evidence owners.
Feature-level
`/spec-improve` is complete for
FT-001, FT-002, and FT-003; their current normative feature designs are
registered in [.memory-bank/spec-index.md](spec-index.md). `/prd-to-tasks FT-001`
is complete and refreshed with [.memory-bank/tasks/plans/IMPL-FT-001.md](tasks/plans/IMPL-FT-001.md),
behavior specs, required packets, and active task records
`TASK-005-T3-FT-001-W1` through `TASK-011-T3-FT-001-W3`; the latest refresh
linked FT-001 task records and packets to the current Foundation runtime/data
substrate, evidence-redaction, and testing owners without creating new tasks.
A later `/spec-improve FT-001` repair on 2026-06-26 closed concrete security
primitive, cookie transport, and PlantPermissionContext ownership gaps in the
linked feature specs, and `/prd-to-tasks FT-001` refreshed `TASK-006` through
`TASK-011` plus their required packets against those contracts without creating
new tasks.
The active task index
also contains completed `FT-000` foundation tasks, and `TASK-000-T1-FT-000-W0`
through `TASK-004-T2-FT-000-W0` are `done`. `REQ-000` and `FT-000` are verified
by the final Foundation gate and W0 semantic red-verification.
The next FT-001 gate is `/review-tasks-plan FT-001` before task execution.
Other product features should enter `/prd-to-tasks FT-<NNN>` when selected; that
command owns feature-level SDD design before task slicing.

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
- [.memory-bank/spec-backbone.md](spec-backbone.md): pre-PRD spec framing status, global backbone status, and `/prd-to-tasks` / `/spec-improve` repair handoff.
- [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md): global MVP v2 architecture backbone.
- [.memory-bank/architecture/foundation-runtime-substrate.md](architecture/foundation-runtime-substrate.md): verified FT-000 backend runtime substrate.
- [.memory-bank/foundation.md](foundation.md): required compact Foundation Dev Path and Feature Pressure Map before product tasking.
- [.memory-bank/domains/index.md](domains/index.md): active domain/data spec router.
- [.memory-bank/domains/foundation-data-substrate.md](domains/foundation-data-substrate.md): FT-000 DB/session/Alembic/runtime-root substrate.
- [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md): global runtime authority and data ownership model.
- [.memory-bank/domains/photo-artifacts.md](domains/photo-artifacts.md): global local photo artifact authority and cross-feature refs.
- [.memory-bank/contracts/index.md](contracts/index.md): active contract router.
- [.memory-bank/contracts/api-guidelines.md](contracts/api-guidelines.md): HTTP/API, ActorContext, authz, error, upload, CORS, and OpenAPI-generation guardrails.
- [.memory-bank/contracts/foundation-smoke-api.md](contracts/foundation-smoke-api.md): substrate `/health` and `/ready` route contract.
- [.memory-bank/contracts/evidence-redaction.md](contracts/evidence-redaction.md): Foundation evidence/log redaction contract.
- [.memory-bank/contracts/agent-chat-bus.md](contracts/agent-chat-bus.md): agent-consumable event boundary and context hygiene.
- [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md): structured agent-output boundary.
- [.memory-bank/contracts/ui-feed.md](contracts/ui-feed.md): human-facing projection boundary.
- [.memory-bank/contracts/timeline-event.md](contracts/timeline-event.md): append-only audit/export event boundary.
- [.memory-bank/states/index.md](states/index.md): active state/lifecycle router.
- [.memory-bank/states/plant-state-trust.md](states/plant-state-trust.md): Plant trust and promotion boundary.
- [.memory-bank/states/safety-action-lifecycle.md](states/safety-action-lifecycle.md): Safety Gate/action approval lifecycle boundary.
- [.memory-bank/states/companion-governance.md](states/companion-governance.md): Companion proposal/DecisionRecord lifecycle boundary.
- [.memory-bank/states/dataset-governance.md](states/dataset-governance.md): dataset trainability and evidence lifecycle boundary.
- [.memory-bank/testing/foundation-test-harness.md](testing/foundation-test-harness.md): FT-000 test harness and evidence requirements.
- [.memory-bank/runbooks/foundation-local-runtime.md](runbooks/foundation-local-runtime.md): local Foundation bootstrap/start/smoke runbook.
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
/review-tasks-plan FT-001
then conditional /mb-doctor before tier-routed /execute TASK-005-T3-FT-001-W1
```

Foundation no longer blocks product tasking. The current FT-001 task records,
implementation plan, behavior specs, and packets are refreshed against the
2026-06-26 brownfield global SDD backbone, expanded shared SDD owners,
Foundation substrate owners, and the expanded `/prd-to-tasks` concrete contract
readiness protocol, repaired by `/spec-improve FT-001`, and refreshed again by
`/prd-to-tasks FT-001` for the existing task cards/packets. Run
`/review-tasks-plan FT-001`, followed by conditional `/mb-doctor` for T3/packet
readiness before executing
`TASK-005-T3-FT-001-W1`. FT-002 and FT-003 already have current normative
feature designs and may be decomposed later with
`/prd-to-tasks FT-<NNN>` one feature at a time. For features outside
FT-001..FT-003, `/prd-to-tasks` must first complete or block feature-level SDD
design before writing tasks. Use standalone `/spec-improve FT-<NNN>` only for
repair or advanced refresh without task generation. Do not use archived MVP v1
features as current source of truth.

## Operational Roots

- [.memory-bank/tasks/index.json](tasks/index.json): authoritative JSON task record index.
- [.memory-bank/schemas/task.schema.json](schemas/task.schema.json): JSON schema for task records.
- [.memory-bank/workflows/index.md](workflows/index.md): workflow policies and execution-loop router.
- [.memory-bank/skills/index.md](skills/index.md): skill registry.
