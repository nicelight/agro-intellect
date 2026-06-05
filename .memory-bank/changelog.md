---
description: Лог изменений Memory Bank.
status: active
---
# Changelog

## [2026-06-05] SDD consistency findings fixed
- Normalized Safety Gate publishable vocabulary to `cleared_for_approval`.
- Removed FT-016 dataset-specific `StructuredObservation.status=blocked` drift by
  routing policy blocks through the shared `denied` observation status with typed
  reasons.
- Clarified that FT-011 `silent` advisor decisions are trace/eval-only and create no
  publishable advisor output, MessageEnvelope, Bus event, or UI Feed projection.
- Expanded FT-017 redaction verification coverage to include security traces visible
  to agents and capture metadata.
- Activated PRD, epic, and feature document metadata while keeping implementation
  lifecycle fields as `planned`.
- Synchronized stale `/spec-improve` and `/prd-to-tasks` routing text now that
  TASK-001..TASK-099 exist.
- Added owning feature docs and requirements to task `source_artifacts` for consistent
  fresh-session traceability.

## [2026-06-05] MVP v2 requirements and feature routers activated
- Marked `.memory-bank/requirements.md` and `.memory-bank/features/index.md` as
  `status: active` to match their current role as active MVP v2 routing and
  source-of-truth documents for execution handoff.

## [2026-06-05] Final task review findings triaged
- Normalized schema-backed task records so `task.wave` uses `/prd-to-tasks` workflow
  slices only: `W1` foundation, `W2` core logic, and `W3` integration/polish.
- Added missing `/verify` handoff instructions for TASK-001..TASK-016 and explicit T3
  closure evidence markers to T3 task records.
- Replaced placeholder required eval/frontend gate commands in task records with
  concrete planned test gates or evidence-backed verification requirements.
- Added missing implementation-plan links to task `docs` fields where plans were only
  present as source artifacts.
- Strengthened FT-017/TASK-014 privacy handoff with browser write-protection checks for
  state-changing loopback/LAN requests.

## [2026-06-05] Wave 6 /prd-to-tasks completed
- Decomposed FT-014, FT-015, and FT-016 into implementation plans and schema-backed
  JSON task records.
- Created .memory-bank/tasks/plans/IMPL-FT-014.md, IMPL-FT-015.md, and
  IMPL-FT-016.md, and updated .memory-bank/tasks/plans/index.md routing.
- Created TASK-082..TASK-099 and updated .memory-bank/tasks/index.json.
- Created feature protocol plans and decision logs under .protocols/FT-014/,
  .protocols/FT-015/, and .protocols/FT-016/.
- Kept all Wave 6 tasks planned because Wave 1-5 dependencies are not done.
- Preserved FT-017 as already decomposed in Wave 1 and used it only as privacy,
  local_only, no-upload, and redaction dependency input for FT-016.

## [2026-06-05] Wave 5 /prd-to-tasks completed
- Decomposed FT-012 and FT-013 into implementation plans and schema-backed JSON task
  records.
- Created `.memory-bank/tasks/plans/IMPL-FT-012.md` and `IMPL-FT-013.md`, and updated
  `.memory-bank/tasks/plans/index.md` routing.
- Created TASK-070..TASK-081 and updated `.memory-bank/tasks/index.json`.
- Created feature protocol plans and decision logs under `.protocols/FT-012/` and
  `.protocols/FT-013/`.
- Kept all Wave 5 tasks `planned` because Wave 1-4 dependencies are not done.
- Applied `agents-best-practices` guidance to approval-gated risky actions, typed
  proposals, draft/commit separation, runtime permission decisions, structured
  observations, traces/evals, budgets, and no automated actuation.

## [2026-06-05] Wave 4 /prd-to-tasks completed
- Decomposed FT-008, FT-010, and FT-011 into implementation plans and schema-backed
  JSON task records.
- Created `.memory-bank/tasks/plans/IMPL-FT-008.md`, `IMPL-FT-010.md`, and
  `IMPL-FT-011.md`, and updated `.memory-bank/tasks/plans/index.md` routing.
- Created TASK-053..TASK-069 and updated `.memory-bank/tasks/index.json`.
- Created feature protocol plans and decision logs under `.protocols/FT-008/`,
  `.protocols/FT-010/`, and `.protocols/FT-011/`.
- Kept all Wave 4 tasks `planned` because Wave 1-3 dependencies are not done.
- Applied `agents-best-practices` guidance to permission-aware context and memory,
  provider/model runtime, prompt-cache-aware ordering, tool permissions, traces/evals,
  budget/stop rules, provider failure, and no fake runtime acceptance.

## [2026-06-05] Wave 3 /prd-to-tasks completed
- Decomposed FT-006, FT-007, and FT-009 into implementation plans and schema-backed
  JSON task records.
- Created `.memory-bank/tasks/plans/IMPL-FT-006.md`, `IMPL-FT-007.md`, and
  `IMPL-FT-009.md`, and updated `.memory-bank/tasks/plans/index.md` routing.
- Created TASK-035..TASK-052 and updated `.memory-bank/tasks/index.json`.
- Created feature protocol plans and decision logs under `.protocols/FT-006/`,
  `.protocols/FT-007/`, and `.protocols/FT-009/`.
- Kept all Wave 3 tasks `planned` because Wave 1 and Wave 2 dependencies are not done.
- Applied `agents-best-practices` guidance to shared AgentHarness control-plane
  ownership, typed tool contracts, runtime permission decisions, context isolation,
  traces/evals, budgets, MessageEnvelope/Bus boundaries, and no prompt-only safety.

## [2026-06-05] Wave 2 /prd-to-tasks completed
- Decomposed FT-003, FT-004, and FT-005 into implementation plans and schema-backed
  JSON task records.
- Created `.memory-bank/tasks/plans/IMPL-FT-003.md`, `IMPL-FT-004.md`, and
  `IMPL-FT-005.md`, and added `.memory-bank/tasks/plans/index.md` routing.
- Created TASK-017..TASK-034 and updated `.memory-bank/tasks/index.json`.
- Created feature protocol plans and decision logs under `.protocols/FT-003/`,
  `.protocols/FT-004/`, and `.protocols/FT-005/`.
- Kept all Wave 2 tasks `planned` because Wave 1 dependencies are not done.
- Applied `agents-best-practices` guidance to privileged admin, identity/access,
  authorized Plant operations, untrusted user/upload data, backend-owned permission
  checks, Bus publication boundaries, redacted traces/observations, and evidence refs.

## [2026-06-05] Wave 1 /prd-to-tasks completed
- Decomposed FT-001, FT-002, and FT-017 into implementation plans and schema-backed
  JSON task records.
- Created `.memory-bank/tasks/plans/IMPL-FT-001.md`, `IMPL-FT-002.md`, and
  `IMPL-FT-017.md`.
- Created TASK-001..TASK-016 and updated `.memory-bank/tasks/index.json`.
- Created feature protocol plans and decision logs under `.protocols/FT-001/`,
  `.protocols/FT-002/`, and `.protocols/FT-017/`.
- Marked independent foundations ready: TASK-001, TASK-011, and TASK-013. Kept
  downstream auth, Plant access, LAN, and regression tasks planned with explicit
  dependencies.
- Applied `agents-best-practices` guidance to task decomposition for backend-owned
  permission decisions, narrow tool/context boundaries, redacted traces/observations,
  prompt-injection treatment, and secret handling.

## [2026-06-05] Spec review fixes B1-B4
- Fixed semantic review findings across FT-007, FT-008, FT-009, and FT-015 alignment:
  AgentProfile risk classes now stay within the shared enum, governance-summary
  authority role is explicit in context items, adapted model claims cannot become
  `trusted` by adapter validation alone, and pre-clearance physical-action wording is
  barred from agent-consumable Bus context.

## [2026-06-05] Wave 6 /spec-improve completed
- Completed feature-level SDD design for FT-014, FT-015, and FT-016.
- Added feature-local tech specs under `.memory-bank/tech-specs/` for Companion
  governance typed state and DecisionRecord semantics, approved governance summary
  context isolation, and dataset governance/local storage prompt behavior.
- Updated the three feature frontmatter blocks to `spec_design_status: complete` with
  `spec_design_links`.
- Updated `.memory-bank/spec-index.md`, `.memory-bank/index.md`,
  `.memory-bank/features/index.md`, and `.memory-bank/tech-specs/index.md` routing.
- Preserved FT-017 as the authoritative Wave 1 `/spec-improve` pass and checked FT-016
  against FT-017 local privacy, `local_only`, no-upload, and redaction constraints.
- Applied `agents-best-practices` to keep governance proposals approval-gated and
  typed, approved summaries compact/filtered, raw proposal/chat/rationale excluded from
  agent context, trainability governed by evidence-backed lifecycle rules, and storage
  prompts local-only with no server-sync implication.

## [2026-06-05] Wave 5 /spec-improve completed
- Completed feature-level SDD design for FT-012 and FT-013.
- Added feature-local tech specs under `.memory-bank/tech-specs/` for Safety Gate
  routing/approval eligibility and for task/approval/action/follow-up outcome
  semantics.
- Updated the two feature frontmatter blocks to `spec_design_status: complete` with
  `spec_design_links`.
- Updated `.memory-bank/spec-index.md`, `.memory-bank/index.md`,
  `.memory-bank/features/index.md`, and `.memory-bank/tech-specs/index.md` routing.
- Applied `agents-best-practices` to keep physical-action advice as typed proposals,
  split draft/propose from commit/approval, enforce runtime permission decisions,
  preserve audit traces, require safety evals, and block automated actuation.

## [2026-06-05] Wave 4 /spec-improve completed
- Completed feature-level SDD design for FT-008, FT-010, and FT-011.
- Added feature-local tech specs under `.memory-bank/tech-specs/` for permission-aware
  context and AgentMemoryRecord, real model-backed product-agent profiles, and Plant
  State trust/Hydroponics Advisor behavior.
- Updated the three feature frontmatter blocks to `spec_design_status: complete` with
  `spec_design_links`.
- Updated `.memory-bank/spec-index.md`, `.memory-bank/index.md`,
  `.memory-bank/features/index.md`, and `.memory-bank/tech-specs/index.md` routing.
- Applied `agents-best-practices` to lock no-fake-runtime acceptance, context/memory
  trust boundaries, permission-scoped retrieval, structured observations, traces/evals,
  budget/stop behavior, prompt-cache-aware context ordering, and provider failure
  handling.

## [2026-06-05] Wave 3 /spec-improve completed
- Completed feature-level SDD design for FT-006, FT-007, and FT-009.
- Added feature-local tech specs under `.memory-bank/tech-specs/` for runtime Plant
  state/history/timeline audit, shared AgentHarness/AgentProfile runtime, and
  MessageEnvelope/Agent Chat Bus/UI Feed isolation.
- Updated the three feature frontmatter blocks to `spec_design_status: complete` with
  `spec_design_links`.
- Updated `.memory-bank/spec-index.md`, `.memory-bank/index.md`,
  `.memory-bank/features/index.md`, and `.memory-bank/tech-specs/index.md` routing.
- Applied `agents-best-practices` to FT-007 and FT-009: model proposes, harness
  validates/authorizes/executes/records; tools are narrow and typed; runtime
  permissions, traces, evals, and untrusted-content isolation are explicit.

## [2026-06-05] Wave 2 /spec-improve completed
- Completed feature-level SDD design for FT-003, FT-004, and FT-005.
- Added feature-local tech specs under `.memory-bank/tech-specs/` for Boss Admin
  Surface/admin audit, authorized Plant selector/daily check-in, and photo
  intake/catalog/capture manifests.
- Updated the three feature frontmatter blocks to `spec_design_status: complete` with
  `spec_design_links`.
- Updated `.memory-bank/spec-index.md`, `.memory-bank/index.md`,
  `.memory-bank/features/index.md`, and `.memory-bank/tech-specs/index.md` routing.

## [2026-06-05] Wave 1 /spec-improve completed
- Completed feature-level SDD design for FT-001, FT-002, and FT-017.
- Added feature-local tech specs under `.memory-bank/tech-specs/` for local
  Accounts/sessions/ActorContext, Farm/Plant lifecycle/access grants, and local privacy
  deployment/secret redaction.
- Updated the three feature frontmatter blocks to `spec_design_status: complete` with
  `spec_design_links`.
- Updated `.memory-bank/spec-index.md`, `.memory-bank/index.md`,
  `.memory-bank/features/index.md`, and `.memory-bank/tech-specs/index.md` routing.
- Recorded FT-017 Wave 1 as the authoritative `/spec-improve` pass if a later wave list
  repeats FT-017.

## [2026-06-04] MVP v2 global /spec-design completed
- Completed the global SDD architecture backbone for MVP v2 with `standard_ai_first`
  mode and `single-file` architecture strategy.
- Added `.memory-bank/architecture/system-architecture.md` as the global architecture
  hub and `.memory-bank/domains/runtime-data-model.md` for runtime authority and shared
  entity groups.
- Added active contract specs for API guidelines, AgentHarness, Agent Chat Bus,
  MessageEnvelope/UI Feed projection, and Safety Gate.
- Added `.memory-bank/states/core-lifecycles.md` with shared lifecycle guardrails.
- Updated `.memory-bank/spec-index.md`, `.memory-bank/spec-backbone.md`,
  `.memory-bank/testing/index.md`, `.memory-bank/index.md`, epics/features routing,
  and FT-001..FT-017 gate metadata.
- Kept feature-local design pending: each feature remains `spec_design_status:
  needs_spec_improve` before `/prd-to-tasks`.

## [2026-06-04] MVP v2 PRD decomposed into L1-L3 Memory Bank
- Ran `/prd` from the clarified MVP v2 PRD and active pre-PRD spec framing.
- Updated `.memory-bank/product.md` and `.memory-bank/requirements.md` with MVP v2 product summary, REQ-001..REQ-024, out-of-scope, and RTM.
- Created active MVP v2 epic router and six epics under `.memory-bank/epics/`.
- Created active MVP v2 feature router and FT-001..FT-017 under `.memory-bank/features/`.
- Updated `.memory-bank/testing/index.md`, `.memory-bank/index.md`, and `.memory-bank/analysis/index.md` routing for the post-`/prd` state.
- Preserved task registry/records out of scope; `/prd` created no TASK records or implementation plans.

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
