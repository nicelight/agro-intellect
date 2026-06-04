---
description: Analysis artifact index.
status: active
---
# Analysis Index

## Current State

- The project has moved into MVP v2 migration planning.
- The previous MVP v1 spec-layer is archived under [.memory-bank/archive/mvp-v1/](../archive/mvp-v1/).
- Active MVP v2 PRD exists at [.memory-bank/prd.md](../prd.md) with `clarification_status: complete`.
- Active MVP v2 requirements, epics, and features now exist as `/prd` output.
- Global architecture backbone exists and `/spec-design` is complete; feature-local SDD specs remain routed through `/spec-improve FT-<NNN>`.
- Active MVP v2 Product Brief exists at [.memory-bank/analysis/product-brief.md](product-brief.md) with `Decision: proceed`.
- [.memory-bank/constitution.md](../constitution.md) has been amended to allow a bounded local-first Farm workspace with local Accounts, role-scoped access, multiple Plants, and Companion governance after PRD/spec promotion.
- [.memory-bank/glossary.md](../glossary.md) remains active and has been updated with MVP v2 vocabulary.

## Active Artifact Links

- [project_dossier_v2.md](../../project_dossier_v2.md): upstream MVP v2 product and architecture dossier context.
- [.memory-bank/prd.md](../prd.md): clarified MVP v2 PRD; current source of truth for downstream `/spec-init` and `/prd`.
- [.memory-bank/requirements.md](../requirements.md): MVP v2 REQ list and RTM created by `/prd`.
- [.memory-bank/epics/index.md](../epics/index.md): MVP v2 epic router created by `/prd`.
- [.memory-bank/features/index.md](../features/index.md): MVP v2 feature router created by `/prd`.
- [.memory-bank/analysis/product-brief.md](product-brief.md): Product Brief input contract, now clarified by the active PRD.
- [.memory-bank/analysis/companion-issue-stack-decision-governance.md](companion-issue-stack-decision-governance.md): draft analysis for Companion-driven `IssueStack`, `CompanionProposal`, and human `DecisionRecord` governance.
- [.memory-bank/analysis/accounts-farm-access-admin-analysis.md](accounts-farm-access-admin-analysis.md): draft analysis for Accounts, Farm access, Boss admin, personnel, Plants, and per-Plant access control.
- [.memory-bank/analysis/mvp-scope-expansion-integration-plan.md](mvp-scope-expansion-integration-plan.md): MVP v2 feature-scope input for Companion governance and local Farm/Admin accounts.
- [.memory-bank/constitution.md](../constitution.md): amended top governing policy for MVP v2 direction.
- [.memory-bank/invariants.md](../invariants.md): active cross-cutting guardrails.
- [.memory-bank/glossary.md](../glossary.md): active vocabulary.
- [.memory-bank/spec-index.md](../spec-index.md): MVP v2 migration route map.
- [.memory-bank/spec-backbone.md](../spec-backbone.md): global backbone status and handoff to `/spec-improve`.
- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): global MVP v2 architecture backbone.

## Archived MVP v1 Inputs

- [.memory-bank/archive/mvp-v1/analysis/product-brief.md](../archive/mvp-v1/analysis/product-brief.md): archived MVP v1 Product Brief.
- [.memory-bank/archive/mvp-v1/analysis/brainstorming/BR-001.md](../archive/mvp-v1/analysis/brainstorming/BR-001.md): archived MVP v1 brainstorming report.
- [.memory-bank/archive/mvp-v1/prd.md](../archive/mvp-v1/prd.md): archived MVP v1 PRD.
- [.memory-bank/archive/mvp-v1/product.md](../archive/mvp-v1/product.md): archived MVP v1 product summary.
- [.memory-bank/archive/mvp-v1/requirements.md](../archive/mvp-v1/requirements.md): archived MVP v1 requirements and RTM.
- [.memory-bank/archive/mvp-v1/spec-index.md](../archive/mvp-v1/spec-index.md): archived MVP v1 SDD route map.

## Recommended Next Step

After explicit user instruction, continue from the completed `/prd` decomposition:

```text
/spec-improve FT-<NNN> -> /prd-to-tasks FT-<NNN>
```

## Closed PRD Clarifications

- Loopback is the first-demo default; LAN is optional only when explicitly enabled with auth/session/CORS controls.
- MVP uses Boss/Engineer/Consultant role presets plus PlantAccessGrant; the only MVP permission override is `plant_approve_actions`.
- Boss may approve Safety Gate physical-action proposals; Engineer may approve only with per-Plant `plant_approve_actions`; Consultant never approves.
- Consultant is read/comment/advice only and does not create domain task/recommendation records or approvals.
- Plant removal is archive/restore only; no hard delete in MVP.
- `IssueStack` is Plant-scoped in MVP.
- `DecisionRecord` may route Plant-scoped workflow and safe check/measurement/follow-up task requests, but cannot mutate Plant state or unlock physical actions.
- A new CompanionProposal for the same Plant issue supersedes the previous pending proposal; no parallel proposals.
- Agent-consumable governance summary is compact typed facts from a valid DecisionRecord only.
- MVP runtime/demo agents must be real LLM/model-backed flows over actual scoped Plant data; fake/mock/stub outputs are not acceptable as the MVP runtime path.
