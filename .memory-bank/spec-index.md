---
description: MVP v2 SDD Design Specs Index and migration route map.
status: active
owner: architecture
last_updated: 2026-06-02
source_of_truth:
  - .memory-bank/constitution.md
  - .memory-bank/prd.md
  - .memory-bank/invariants.md
  - .memory-bank/glossary.md
  - project_dossier_v2.md
  - .memory-bank/analysis/mvp-scope-expansion-integration-plan.md
---
# SDD Design Specs Index

## Purpose

This file is the active route map during MVP v2 migration.

The MVP v1 spec-layer has been archived under
[.memory-bank/archive/mvp-v1/](archive/mvp-v1/). Archived MVP v1 specs are historical
reference only and must not be treated as current source of truth for task decomposition.

## Active Backbone Status

- Status: `blocked`.
- Reason: MVP v2 PRD is complete, but `/spec-init`, `/prd`, and global SDD backbone have not been produced yet.
- Next required command: `/spec-init` after explicit user instruction.
- Downstream gate: `/prd-to-tasks` is blocked until `/spec-init`, `/prd`,
  `/spec-design`, and feature-level `/spec-improve` complete for MVP v2 features.

## Active Source Inputs

- [.memory-bank/constitution.md](constitution.md): governing policy, amended for bounded local-first Farm workspace and Companion governance.
- [.memory-bank/prd.md](prd.md): clarified MVP v2 PRD with `clarification_status: complete`.
- [.memory-bank/invariants.md](invariants.md): active cross-cutting guardrails.
- [.memory-bank/glossary.md](glossary.md): active vocabulary.
- [project_dossier_v2.md](../project_dossier_v2.md): upstream MVP v2 dossier.
- [.memory-bank/analysis/product-brief.md](analysis/product-brief.md): PRD input brief, now clarified by the active PRD.
- [.memory-bank/analysis/mvp-scope-expansion-integration-plan.md](analysis/mvp-scope-expansion-integration-plan.md): MVP v2 feature-scope input.
- [.memory-bank/analysis/accounts-farm-access-admin-analysis.md](analysis/accounts-farm-access-admin-analysis.md): Accounts/Farm/Admin analysis input.
- [.memory-bank/analysis/companion-issue-stack-decision-governance.md](analysis/companion-issue-stack-decision-governance.md): Companion governance analysis input.

## Archived MVP v1 References

- [.memory-bank/archive/mvp-v1/index.md](archive/mvp-v1/index.md): archived MVP v1 router.
- [.memory-bank/archive/mvp-v1/prd.md](archive/mvp-v1/prd.md): archived MVP v1 PRD.
- [.memory-bank/archive/mvp-v1/spec-index.md](archive/mvp-v1/spec-index.md): archived MVP v1 SDD route map.
- [.memory-bank/archive/mvp-v1/features/index.md](archive/mvp-v1/features/index.md): archived MVP v1 features.
- [.memory-bank/archive/mvp-v1/tech-specs/index.md](archive/mvp-v1/tech-specs/index.md): archived MVP v1 feature-local tech specs.

## Not Yet Active

The following active MVP v2 docs do not exist yet and must be created through the normal workflow:

- `.memory-bank/product.md`
- `.memory-bank/requirements.md`
- `.memory-bank/epics/EP-*.md`
- `.memory-bank/features/FT-*.md`
- `.memory-bank/architecture/system-architecture.md`
- `.memory-bank/domains/*.md`
- `.memory-bank/contracts/*.md`
- `.memory-bank/states/*.md`
- `.memory-bank/runbooks/*.md`
- `.memory-bank/tech-specs/FT-*.md`

## Expected Workflow

```text
/spec-init
-> /prd
-> /spec-design
-> /spec-improve FT-<NNN>
-> /prd-to-tasks FT-<NNN>
```

## Migration Guardrails

- Do not resurrect archived MVP v1 feature completion statuses into MVP v2.
- Do not mark MVP v2 feature specs complete until `/spec-improve` has run against the new PRD/backbone.
- Keep `DecisionRecord` governance separate from Safety Gate physical-action approval.
- Keep local Farm/Admin account scope bounded until PRD/specs explicitly widen it.
- Keep production SaaS, hosted/cloud sync as an MVP requirement, billing, enterprise identity,
  automated actuation, and broad farm-management scope out of MVP v2 unless a later product stage amends the project.
