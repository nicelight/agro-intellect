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
- [.memory-bank/spec-index.md](../spec-index.md) routes the post-`/prd` state and records that global `/spec-design` has not produced the backbone yet.
- No application codebase signals were found in the repository root during routing inspection.

## Artifact Links

- [project_dossier.md](../../project_dossier.md): upstream product and architecture dossier context.
- [.memory-bank/analysis/brainstorming/BR-001.md](brainstorming/BR-001.md): brainstorming report derived from `project_dossier.md`.
- [.memory-bank/analysis/product-brief.md](product-brief.md): Product Brief input contract for `/constitution` and `/write-prd`.
- [.memory-bank/prd.md](../prd.md): clarified Product Requirements Document.
- [.memory-bank/constitution.md](../constitution.md): ratified top governing policy for project-specific principles.
- [.memory-bank/spec-index.md](../spec-index.md): SDD route map for the current post-`/prd`, pre-`/spec-design` state.
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

## Recommended Next Step

Next route: `/spec-design -> /spec-improve FT-<NNN> -> /prd-to-tasks FT-<NNN>`.

## Open Routing Questions

- None blocking for `/spec-design` from the analysis layer.
