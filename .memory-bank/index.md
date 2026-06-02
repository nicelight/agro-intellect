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
Archived docs are historical reference only. The active MVP v2 PRD now promotes the
first product decisions back into the active Memory Bank; downstream requirements,
features, and SDD backbone still need the normal workflow.

## Active Governance And Routing

- [.memory-bank/constitution.md](constitution.md): Project Constitution — top governing policy for agents.
- [.memory-bank/prd.md](prd.md): clarified MVP v2 PRD with `clarification_status: complete`.
- [.memory-bank/mbb/index.md](mbb/index.md): Memory Bank Bible rules.
- [.memory-bank/invariants.md](invariants.md): current cross-cutting MUST/NEVER guardrails.
- [.memory-bank/glossary.md](glossary.md): active shared vocabulary for MVP v2 migration.
- [.memory-bank/spec-index.md](spec-index.md): active MVP v2 migration route map.
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
/spec-init
-> /prd
-> /spec-design
-> /spec-improve FT-<NNN>
-> /prd-to-tasks FT-<NNN>
```

Do not run `/prd-to-tasks` from archived MVP v1 features.

## Operational Roots

- [.memory-bank/tasks/index.json](tasks/index.json): authoritative JSON task record index.
- [.memory-bank/schemas/task.schema.json](schemas/task.schema.json): JSON schema for task records.
- [.memory-bank/workflows/index.md](workflows/index.md): workflow policies and execution-loop router.
- [.memory-bank/skills/index.md](skills/index.md): skill registry.
