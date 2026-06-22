---
description: Лог изменений Memory Bank.
status: active
---
# Changelog

## [2026-06-22] Generated task artifacts removed after rollback
- Reset the active task queue to an empty [.memory-bank/tasks/index.json](tasks/index.json).
- Removed generated first-wave task records and implementation plans for FT-001, FT-002, and FT-003.
- Removed local ignored `.tasks/` task evidence/review artifacts and task/feature protocol state tied to old task generation.
- Updated active routing docs so the Memory Bank no longer points to `/execute TASK-001` or stale `TASK-*` records.
- Kept PRD, product, requirements, epics, features, global SDD backbone, and FT-001..FT-003 feature-local specs.

## [2026-06-17] Task registry cleanup
- Removed the obsolete standalone foundation task from the active task registry and project navigation.
- Kept the executable backend scaffold as part of the active TASK-001 implementation evidence.
- Updated current routing and verification notes so Memory Bank doctor no longer trips on the retired foundation task shape.

## [2026-06-17] TASK-001 DB/test scaffold implemented
- Extended the backend baseline with a minimal database settings primitive, a SQLAlchemy-backed engine/session/test harness, and a migration entrypoint package under `backend/migrations`.
- Added backend fixtures/tests that prove the app imports, can be created with an explicit test database handle, and can open a clean rollback-safe test session boundary.
- Updated `.env.example`, `pyproject.toml`, and the `backend/app` package exports to surface the new reusable scaffold without implementing FT-001 auth/session behavior.
- Captured T2 protocol notes and evidence under `.protocols/TASK-001/` and `.tasks/TASK-001/evidence/`.

## [2026-06-16] First-wave task artifacts verified
- Verified generated `/prd-to-tasks` artifacts for FT-001, FT-002, and FT-003: implementation plans, TASK-001..TASK-015 records, task index, dependencies, tiers, SDD links, requirement coverage, and T3 closure evidence requirements.
- Added verification evidence at `.tasks/TASK-ARTIFACT-VERIFY/FT-001-003-task-artifacts-verification.md`.
- Fixed stale per-feature routing text that still pointed to `/prd-to-tasks` after task generation.
- Updated Memory Bank routing so the next route is `/execute TASK-001`.
- No application code was implemented.

## [2026-06-14] /prd-to-tasks first wave completed
- Created feature protocols for FT-001, FT-002, and FT-003 under `.protocols/FT-001/`, `.protocols/FT-002/`, and `.protocols/FT-003/`.
- Added implementation plans `.memory-bank/tasks/plans/IMPL-FT-001.md`, `.memory-bank/tasks/plans/IMPL-FT-002.md`, and `.memory-bank/tasks/plans/IMPL-FT-003.md`.
- Created schema-backed TASK-001..TASK-015 records for FT-001..FT-003 and indexed them in `.memory-bank/tasks/index.json`.
- Marked only TASK-001 `ready`; dependent tasks remain `planned` with explicit dependencies.
- Updated Memory Bank routing in `.memory-bank/index.md`, `.memory-bank/features/index.md`, `.memory-bank/analysis/index.md`, and `.memory-bank/epics/EP-001-local-farm-access-admin.md`.
- Did not implement application code or create task records for FT-004..FT-016.

## [2026-06-14] /spec-improve first wave integrated
- Registered active/current normative `feature_design` specs for FT-001, FT-002, and FT-003 in `.memory-bank/spec-index.md`.
- Updated shared navigation for EP-001, features, analysis, and main Memory Bank routing to show first-wave `/spec-improve` completion.
- Recorded that TASK records and task decomposition have not been created yet; next route is `/prd-to-tasks FT-001`, `/prd-to-tasks FT-002`, and `/prd-to-tasks FT-003`.
- Did not edit feature docs, feature-local tech specs, TASK records, implementation plans, generated OpenAPI, DB migrations, or code.

## [2026-06-14] /spec-design global backbone completed
- Added global architecture backbone at `.memory-bank/architecture/system-architecture.md` with local modular monolith, source-of-truth hierarchy, module boundaries, data flow, storage, API/contract, security/safety, testing, deployment, risks, and open-question routing.
- Added `.memory-bank/domains/runtime-data-model.md` for runtime authority layers and shared entity ownership.
- Added active contract router and global contracts: `.memory-bank/contracts/index.md`, `.memory-bank/contracts/api-guidelines.md`, `.memory-bank/contracts/agent-chat-bus.md`, and `.memory-bank/contracts/message-envelope.md`.
- Updated `.memory-bank/spec-backbone.md` to `Global Backbone Status: complete`, `Mode: standard_ai_first`, `Architecture artifact strategy: single-file`, with all required backbone matrix areas authoritative.
- Updated `.memory-bank/spec-index.md`, feature SDD gate notes, epic open-question routing, testing router, Memory Bank index, and analysis router for the post-`/spec-design` state.
- Did not create TASK records, implementation plans, generated OpenAPI, DB migrations, or feature-local tech specs.

## [2026-06-14] /prd MVP v2 decomposition completed
- Filled active `.memory-bank/product.md` from the clarified MVP v2 PRD.
- Rebuilt `.memory-bank/requirements.md` with REQ-001..REQ-022 and an MVP v2 traceability matrix.
- Added active MVP v2 L2/L3 decomposition: 6 epics under `.memory-bank/epics/` and 16 features under `.memory-bank/features/`.
- Added feature SDD Design Gate notes that require global `/spec-design`, then per-feature `/spec-improve FT-<NNN>`, before `/prd-to-tasks FT-<NNN>`.
- Updated `.memory-bank/testing/index.md`, `.memory-bank/index.md`, `.memory-bank/analysis/index.md`, `.memory-bank/spec-backbone.md`, and `.protocols/PRD-BOOTSTRAP/` routing for the post-`/prd` state.
- Did not create TASK records, implementation plans, global architecture specs, or feature-local tech specs.

## [2026-06-03] /spec-init pre-PRD framing completed
- Marked `.memory-bank/spec-backbone.md` `Pre-PRD Spec Status` as `ready_for_prd`.
- Added active pre-PRD framing artifacts for MVP v2: `.memory-bank/user-scenarios.md`, `.memory-bank/domains/core-domain.md`, `.memory-bank/contracts/boundary-map.md`, and `.memory-bank/states/lifecycle-map.md`.
- Updated `.memory-bank/spec-index.md` as a pure registry and `.memory-bank/index.md` routing so the next command is `/prd`.
- Kept architecture contracts, state machines, schemas, routes, and verification strategy routed to `/spec-design` after `/prd`.

## [2026-06-02] MVP v2 PRD completed and source docs synced
- Created clarified MVP v2 PRD at `.memory-bank/prd.md` with `clarification_status: complete` and Constitution gate passed.
- Synchronized Product Brief, dossier, glossary, invariants, analysis router, spec-index, and Memory Bank index with PRD decisions.
- Fixed MVP runtime/demo boundary: product-agent flows must use real LLM/model-backed agents over actual scoped Plant data; fake/mock/stub outputs are test-only and do not satisfy MVP runtime acceptance.
- Updated routing so the next possible workflow step is `/spec-init` after explicit user instruction; `/prd-to-tasks` remains blocked until `/spec-init`, `/prd`, `/spec-design`, and feature-level `/spec-improve` complete.

## [2026-06-01] MVP v1 spec-layer archived for MVP v2 migration
- Hard-archived the MVP v1 PRD, requirements, epics, features, SDD backbone, contracts, states, domains, runbooks, tech specs, testing docs, and v1 analysis inputs under `.memory-bank/archive/mvp-v1/`.
- Archived old root-level MVP v1 planning/onboarding artifacts `epic_list.md`, `features_list.md`, and `schemas_mermaid.md` under `.memory-bank/archive/mvp-v1/root/`.
- Kept active governance and planning docs for MVP v2: Constitution, invariants, glossary, analysis inputs, migration plan, and routing stubs.
- Replaced active Memory Bank and SDD routing with MVP v2 migration stubs that block `/prd-to-tasks` until `/write-prd`, `/spec-init`, `/prd`, `/spec-design`, and feature-level `/spec-improve` are rerun.
- Updated the active glossary for Accounts/Farm/Admin and Companion governance vocabulary while keeping MVP v1 vocabulary available in the archive.

## [2026-06-01] P1-07 navigation drift fixed
- Updated current Memory Bank route text to point from completed SDD gates to `/prd-to-tasks FT-<NNN>` or `/prd-to-tasks --all`, subject to active review blockers/gates.
- Marked historical analysis as complete and aligned FT-014/FT-008 coordination wording with completed feature-local `/spec-improve` gates.
- Marked the old `SPEC_BACKBONE_NOT_READY` review-request warning as historical context for the earlier pre-backbone review phase.

## [2026-06-01] SafetyGateDecision authority clarified
- Defined `SafetyGateDecision` runtime authority as PostgreSQL/read-model `safety_decisions` records with canonical `safety_decision:<safety_decision_id>` refs.
- Updated runtime model, FT-003, FT-013, FT-014, FT-008, and FT-011 specs so timeline, Bus, UI Feed, tasks, and approvals may reference Safety Gate decisions but cannot replace their authority.
- Added verification targets for resolving Safety Gate decision refs through PostgreSQL/read-model records in display, task, pending approval, and action unlock flows.

## [2026-06-01] MessageEnvelope stable identity docs-sync
- Added backend-owned `message_id` and canonical `message:<message_id>` refs to the global MessageEnvelope contract and FT-012 lifecycle.
- Aligned FT-004 agent-originated Bus publication to carry `message_ref` instead of inline-only MessageEnvelope identity.
- Updated Vision, Advisor, Tasks, Dataset Governance, UI Feed, and PWA quote/detail refs to use the canonical message reference vocabulary.

## [2026-06-01] Issue 2 safety freshness policy closed
- Closed the review blocker for non-pH/EC physical-action freshness.
- Added MVP fresh context requirements for pump, light, and high-risk manual interventions in Safety Approval and FT-013.
- Tightened FT-014 approval unlock rules so physical-action approvals require expiry and validate non-pH/EC context freshness.

## [2026-06-01] RTM primary/supporting feature alignment
- Updated `.memory-bank/requirements.md` RTM to distinguish primary feature ownership from supporting/affected feature coverage.
- Added missing cross-feature traceability for FT-003 runtime authority/event-ref support and FT-008 task/approval handoff scope.
- Kept REQ rows intact while making cross-feature constraints visible for future `/prd-to-tasks`.

## [2026-06-01] FT-011 spec-improve completed
- Completed feature-level SDD design for FT-011 Minimal Web App/PWA Operator Surface.
- Added minimal route/view set, daily operator workflow, surface behavior, API dependency map, UI Feed presentation-only consumption, safety display checks, local auth/LAN behavior, PWA/offline boundaries, and UI/e2e verification targets.
- Updated FT-011, spec-index, tech-specs router, and Memory Bank routing to mark the feature design gate complete.

## [2026-06-01] FT-007 spec-improve completed
- Completed feature-level SDD design for FT-007 Hydroponics Advisor and Missing Data Policy.
- Added advisor input refs, missing/stale pH/EC policy, clarification-vs-task handoff, cautious recommendation wording, MessageEnvelope claim mapping, Safety Gate handoff, no-direct-action-task boundary, API/service surface, and verification targets.
- Updated FT-007, spec-index, tech-specs router, and Memory Bank routing to mark the feature design gate complete.

## [2026-06-01] FT-006 spec-improve completed
- Completed feature-level SDD design for FT-006 Vision Observation and Plant State Trust.
- Added Vision Observation report shape, observation-vs-diagnosis boundary, source/evidence refs, confidence/status mapping, plant-state promotion gates, contradiction handling, dataset handoff, API/service surface, and verification targets.
- Updated FT-006, spec-index, tech-specs router, and Memory Bank routing to mark the feature design gate complete.

## [2026-06-01] FT-008 spec-improve completed
- Completed feature-level SDD design for FT-008 Tasks, Approvals, and Follow-up Outcomes.
- Added task boundaries/statuses, creation sources, FT-014 unlock coordination, due/follow-up timing, outcome capture, event/audit refs, API/service surface, and verification targets.
- Updated FT-008, spec-index, tech-specs router, and Memory Bank routing to mark the feature design gate complete.

## [2026-06-01] FT-014 spec-improve completed
- Completed feature-level SDD design for FT-014 Human Approval and Action Unlock Semantics.
- Added pending approval representation, approval/rejection record lifecycle, stale/replay prevention, human-performed action unlock service, event/audit refs, API surface, and no-device-execution verification targets.
- Updated FT-014, spec-index, tech-specs router, and Memory Bank routing to mark the feature design gate complete.

## [2026-06-01] Invariants docs-sync
- Refactored `.memory-bank/invariants.md` into a short cross-cutting MUST/NEVER guardrail list.
- Replaced duplicated photo schema, timeline payload, pH/EC freshness/provenance, Bus mechanics, and dataset trainability details with pointers to owning domain, contract, state, runbook, and feature-local specs.
- Kept global guardrails for Spec Before Code, `tomato_001`, runtime authority, timeline audit, Agno/raw output boundary, UI Feed isolation, Safety Gate and human approval, local/private MVP sync, secret redaction, and MVP exclusions.

## [2026-05-31] FT-009 spec-improve finalized
- Added a feature-local SDD tech spec for FT-009 Dataset Governance and Trainability to complete the handoff surface.
- Clarified dataset item boundary, transition service, trainability recomputation, evidence refs, curator rules, API/service surface, and verification targets without creating a full dataset registry.
- Updated FT-009, spec-index, tech-specs router, and Memory Bank routing.

## [2026-05-31] FT-013 spec-improve completed
- Completed feature-level SDD design for FT-013 Safety Gate for Physical-Action Advice.
- Added deterministic Safety Gate policy, action taxonomy, pH/EC approval freshness, `SafetyGateDecision`, fail-closed outcomes, display checks, Bus/UI/task handoffs, and verification targets.
- Updated FT-013, spec-index, tech-specs router, and Memory Bank routing to mark the feature design gate complete.

## [2026-05-31] FT-005 spec-improve completed
- Completed feature-level SDD design for FT-005 UI Feed and Context Hygiene.
- Added UI Feed presentation storage, event payloads, controlled spoiler notes, context filtering, timeline/export snapshot rules, display safety, API surface, and verification targets.
- Updated FT-005, spec-index, tech-specs router, and Memory Bank routing to mark the feature design gate complete.

## [2026-05-31] FT-012 spec-improve completed
- Completed feature-level SDD design for FT-012 Agent Runtime Decisions and MessageEnvelope Output Contracts.
- Added runtime decision state machine, adapter boundary, `MessageEnvelope` schema, decision-to-event mapping, concise-output rules, `silent` audit, and safety/escalation boundary.
- Updated FT-012, spec-index, tech-specs router, and Memory Bank routing to mark the feature design gate complete.

## [2026-05-31] FT-004 spec-improve completed
- Completed feature-level SDD design for FT-004 Agent Chat Bus Event Stream and Publication Boundary.
- Added Bus working-stream persistence, envelope validation, event payload minimums, publication service, context filtering, influence levels, and anti-cheat verification targets.
- Updated FT-004, spec-index, tech-specs router, and Memory Bank routing to mark the feature design gate complete.

## [2026-05-31] FT-001 spec-improve completed
- Completed feature-level SDD design for FT-001 Daily Check-in, Observations, and Manual Measurements.
- Added observation/measurement fields, explicit no-data state, pH/EC units and provenance, computed freshness projection, API shape, timeline payloads, and verification targets.
- Updated FT-001, spec-index, and Memory Bank routing to mark the feature design gate complete.

## [2026-05-31] FT-002 spec-improve completed
- Completed feature-level SDD design for FT-002 Photo Intake, Catalog, and Capture Manifests.
- Added photo upload API, backend-generated `photo_id`, file path layout, initial capture manifest v1, publication sequence, `user_photo` timeline payload, and verification targets.
- Updated FT-002, spec-index, and Memory Bank routing to mark the feature design gate complete.

## [2026-05-31] FT-010 spec-improve completed
- Completed feature-level SDD design for FT-010 Local Security, Privacy, and Lazy Sync.
- Added LAN bearer-token auth, CORS allowlist, upload limits/MIME allowlist, safe path handling, secret redaction, privacy, `local_only`, and 200 MB prompt-only verification targets.
- Updated FT-010, spec-index, and Memory Bank routing to mark the feature design gate complete.

## [2026-05-31] FT-009 spec-improve completed
- Completed feature-level SDD design for FT-009 Dataset Governance and Trainability.
- Added dataset lifecycle transition matrix, actor/source rules, forbidden transitions, trainability side effects, transition audit refs, and verification targets.
- Updated FT-009 and spec-index routing to mark the feature design gate complete.

## [2026-05-31] Architecture docs consolidated
- Merged source-of-truth, module boundary, and Agno boundary architecture rules into `.memory-bank/architecture/system-architecture.md`.
- Removed split architecture docs and updated Memory Bank routing links to the consolidated architecture backbone.

## [2026-05-27] Constitution ratified
- Ratified project-specific Constitution from `/constitution` interview.
- Updated analysis routing to recommend `/write-prd`.
- Updated `/constitution` interview formatting instructions for `(adv)` markers.

## [2026-05-27] Initial setup
- Created Memory Bank skeleton
- Seeded core docs (product, requirements, testing, task registry)
