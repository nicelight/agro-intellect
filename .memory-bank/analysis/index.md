---
description: Analysis artifact index.
status: active
---
# Analysis Index

## Current State

- Upstream context for this analysis pass: [project_dossier.md](../../project_dossier.md).
- `project_dossier.md` defines the project as a greenfield AI-first training ground for an agentic agro-monitoring MVP around one hydroponic tomato.
- [.memory-bank/prd.md](../prd.md) exists and has `clarification_status: complete`.
- `.memory-bank/analysis/product-brief.md` exists with `Decision: proceed`.
- EP-001 through EP-004 exist under [.memory-bank/epics/](../epics/).
- FT-001 through FT-014 exist under [.memory-bank/features/](../features/).
- [.memory-bank/product.md](../product.md) and [.memory-bank/requirements.md](../requirements.md) are PRD-derived L1 artifacts, not skeleton placeholders.
- [.memory-bank/constitution.md](../constitution.md) has `project_principles: ratified`.
- [.memory-bank/spec-index.md](../spec-index.md) routes the current decomposition handoff state: global `/spec-design` backbone and all feature-local `/spec-improve` gates are complete for the current PRD feature set.
- No application codebase signals were found in the repository root during routing inspection.
- New user direction on 2026-06-01: Accounts/Farm/Boss Admin and Companion governance should enter MVP scope together; this requires a Constitution amendment before PRD/spec promotion.

## Artifact Links

- [project_dossier.md](../../project_dossier.md): upstream product and architecture dossier context.
- [.memory-bank/analysis/brainstorming/BR-001.md](brainstorming/BR-001.md): brainstorming report derived from `project_dossier.md`.
- [.memory-bank/analysis/product-brief.md](product-brief.md): Product Brief input contract for `/constitution` and `/write-prd`.
- [.memory-bank/analysis/companion-issue-stack-decision-governance.md](companion-issue-stack-decision-governance.md): exploratory architecture note for Companion-driven `IssueStack`, `CompanionProposal`, and human `DecisionRecord` governance.
- [.memory-bank/analysis/accounts-farm-access-admin-analysis.md](accounts-farm-access-admin-analysis.md): exploratory product analysis for future accounts, boss admin, personnel, Plants, and per-Plant access control.
- [.memory-bank/analysis/mvp-scope-expansion-integration-plan.md](mvp-scope-expansion-integration-plan.md): pre-PRD integration plan for bringing Companion governance and local Farm/Admin accounts into MVP scope.
- [.memory-bank/prd.md](../prd.md): clarified Product Requirements Document.
- [.memory-bank/constitution.md](../constitution.md): ratified top governing policy for project-specific principles.
- [.memory-bank/spec-index.md](../spec-index.md): SDD route map for the current completed design-gate state and `/prd-to-tasks` routing.
- [.memory-bank/product.md](../product.md): PRD-derived product summary and constraints.
- [.memory-bank/requirements.md](../requirements.md): PRD-derived REQ list and RTM.
- [.memory-bank/epics/index.md](../epics/index.md): EP-001..EP-004 router.
- [.memory-bank/features/index.md](../features/index.md): FT-001..FT-014 router.

## Brainstorming

- Latest report: [.memory-bank/analysis/brainstorming/BR-001.md](brainstorming/BR-001.md).
- Upstream context: [project_dossier.md](../../project_dossier.md).
- Historical next step at creation time: `/brief`.

## Product Brief

- Status: draft.
- Decision: proceed.
- Source artifacts: [project_dossier.md](../../project_dossier.md), [.memory-bank/analysis/brainstorming/BR-001.md](brainstorming/BR-001.md).
- Brief: [.memory-bank/analysis/product-brief.md](product-brief.md).

## Exploratory Architecture Notes

- [.memory-bank/analysis/companion-issue-stack-decision-governance.md](companion-issue-stack-decision-governance.md): draft analysis for transparent Companion discussion coordination, explicit `IssueStack`, human-only `DecisionRecord` authority, and future promotion into architecture/contracts/states/feature specs if accepted.
- [.memory-bank/analysis/accounts-farm-access-admin-analysis.md](accounts-farm-access-admin-analysis.md): draft analysis for account registration, Boss admin surface, personnel roles, Plant creation/archive, and per-Plant access grants; user direction now targets promotion into MVP after Constitution/PRD updates.

## MVP Scope Expansion Planning

- [.memory-bank/analysis/mvp-scope-expansion-integration-plan.md](mvp-scope-expansion-integration-plan.md): records the non-binding plan to amend the MVP into a bounded local-first Farm workspace with Accounts/Boss Admin and Companion governance, then promote through `/constitution`, `/write-prd`, `/prd`, `/spec-design`, and `/spec-improve`.

## Recommended Next Step

Run `/constitution` first to amend MVP governing constraints for bounded local-first Accounts/Farm/Boss Admin. Then run `/write-prd` with combined delta sources:

- [.memory-bank/analysis/companion-issue-stack-decision-governance.md](companion-issue-stack-decision-governance.md)
- [.memory-bank/analysis/accounts-farm-access-admin-analysis.md](accounts-farm-access-admin-analysis.md)
- [.memory-bank/analysis/mvp-scope-expansion-integration-plan.md](mvp-scope-expansion-integration-plan.md)

## Open Routing Questions

- Constitution amendment scope for bounded local-first multi-account Farm MVP.
- PRD decisions for deployment model, one-Farm vs multi-Farm, role permissions, Plant lifecycle, `IssueStack` scope, `DecisionRecord` authority, and `tomato_001` migration.
