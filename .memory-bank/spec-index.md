---
description: SDD Design Specs Index and route map for source-of-truth documents.
status: active
owner: architecture
last_updated: 2026-05-31
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/constitution.md
  - .memory-bank/testing/index.md
---
# SDD Design Specs Index

## Purpose
- Use this file as the route map for SDD design specs and explicit normative docs.
- Read this index before creating new specs or doing serious T2/T3 work.
- If a design area is not needed, mark it `not_applicable` with a short reason.
- Do not create authoritative specs unless PRD/user/spec evidence contains the decision.
- Treat [project_dossier.md](../project_dossier.md) as upstream dossier context for ambiguities or insufficient context until a narrower SDD spec exists.

## Hard rules
- Do not create a new spec before checking existing specs through this index.
- `/spec-init` may mark areas as planned/candidate/unknown/not_applicable, but must not invent authoritative architecture/contracts/states/data specs.
- `/spec-design` owns the mandatory global SDD backbone after `/prd`; `/spec-improve FT-<NNN>` owns feature-level design before `/prd-to-tasks FT-<NNN>`.
- `T2` / `T3` tasks must carry relevant linked specs in task richer fields.
- Draft placeholder docs are not binding unless their content explicitly defines evidence-backed rules.

## Source Inputs For Routing
- [project_dossier.md](../project_dossier.md): upstream dossier context for product intent, architecture rationale, contracts, safety, data, and staging; use for ambiguities or missing context.
- [.memory-bank/prd.md](prd.md): clarified PRD and acceptance criteria for MVP scope and non-goals.
- [.memory-bank/analysis/product-brief.md](analysis/product-brief.md): product brief input contract.
- [.memory-bank/constitution.md](constitution.md): governing policy for AI-first, KISS, Memory Bank, safety gates, and low maintenance.
- [.memory-bank/testing/index.md](testing/index.md): active baseline quality gates and risk-surface verification.

## Global Backbone Status
- Status: complete.
- Completed by: `/spec-design` on 2026-05-31.
- Scope: global architecture/source-of-truth/module/contracts/state/testing backbone for the current PRD feature set.
- Blockers: none at global backbone level.
- Downstream gate: every feature still requires `/spec-improve FT-<NNN>` before `/prd-to-tasks FT-<NNN>`.

## Existing Authoritative Specs
- [.memory-bank/constitution.md](constitution.md): governance.
- [.memory-bank/testing/index.md](testing/index.md): verification strategy.
- [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md): global architecture, authority model, module boundaries, and Agno boundary.
- [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md): runtime data model.
- [.memory-bank/domains/photo-artifacts.md](domains/photo-artifacts.md): photo artifacts.
- [.memory-bank/contracts/api-guidelines.md](contracts/api-guidelines.md): API guidelines.
- [.memory-bank/contracts/timeline-event.md](contracts/timeline-event.md): timeline events.
- [.memory-bank/contracts/agent-chat-bus.md](contracts/agent-chat-bus.md): Agent Chat Bus.
- [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md): MessageEnvelope.
- [.memory-bank/contracts/ui-feed.md](contracts/ui-feed.md): UI Feed.
- [.memory-bank/states/plant-state.md](states/plant-state.md): plant state.
- [.memory-bank/states/safety-approval.md](states/safety-approval.md): safety approval.
- [.memory-bank/states/task-follow-up.md](states/task-follow-up.md): tasks/follow-up.
- [.memory-bank/states/dataset-governance.md](states/dataset-governance.md): dataset governance.
- [.memory-bank/runbooks/local-security.md](runbooks/local-security.md): local security.
- [.memory-bank/testing/first-demo.md](testing/first-demo.md): first-demo gates.
- [.memory-bank/adrs/ADR-001-local-modular-monolith-and-authority-boundaries.md](adrs/ADR-001-local-modular-monolith-and-authority-boundaries.md): local monolith ADR.
- [.memory-bank/tech-specs/FT-001-daily-check-in-observations-manual-measurements.md](tech-specs/FT-001-daily-check-in-observations-manual-measurements.md): FT-001 tech spec.
- [.memory-bank/tech-specs/FT-002-photo-intake-catalog-capture-manifests.md](tech-specs/FT-002-photo-intake-catalog-capture-manifests.md): FT-002 tech spec.
- [.memory-bank/tech-specs/FT-003-runtime-state-timeline-audit.md](tech-specs/FT-003-runtime-state-timeline-audit.md): FT-003 tech spec.
- [.memory-bank/tech-specs/FT-004-agent-chat-bus-event-stream-publication-boundary.md](tech-specs/FT-004-agent-chat-bus-event-stream-publication-boundary.md): FT-004 tech spec.
- [.memory-bank/tech-specs/FT-005-ui-feed-context-hygiene.md](tech-specs/FT-005-ui-feed-context-hygiene.md): FT-005 tech spec.
- [.memory-bank/tech-specs/FT-009-dataset-governance-trainability.md](tech-specs/FT-009-dataset-governance-trainability.md): FT-009 tech spec.
- [.memory-bank/tech-specs/FT-010-local-security-privacy-lazy-sync.md](tech-specs/FT-010-local-security-privacy-lazy-sync.md): FT-010 tech spec.
- [.memory-bank/tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md](tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md): FT-012 tech spec.
- [.memory-bank/tech-specs/FT-013-safety-gate-physical-action-advice.md](tech-specs/FT-013-safety-gate-physical-action-advice.md): FT-013 tech spec.
- [.memory-bank/glossary.md](glossary.md): vocabulary.
- [.memory-bank/invariants.md](invariants.md): invariants.

## Planned Design Areas
- `.memory-bank/tech-specs/FT-<NNN>-<slug>.md`: feature-local tech specs.
- Feature-local details: endpoints, schemas, migrations, files, auth, upload, UI.

## Candidate Design Areas
- `.memory-bank/contracts/vision-observation.md`: candidate; vision adapter.
- `.memory-bank/contracts/companion-output.md`: candidate; companion output.
- `.memory-bank/contracts/hydroponics-advisor.md`: candidate; advisor policy.
- `.memory-bank/contracts/training-data-curator.md`: candidate; curator policy.
- `.memory-bank/runbooks/export-snapshot.md`: candidate; export snapshot.
- `.memory-bank/states/sync-status.md`: candidate for future server sync lifecycle beyond FT-010 MVP `local_only`; not required for `/prd-to-tasks FT-010`.
- `.memory-bank/tech-specs/FT-011-minimal-web-app-pwa-operator-surface.md`: candidate; UI/PWA flow.
- `.memory-bank/contracts/sensor-window.md`: candidate; sensor refs.

## Unknown Design Areas
- Per-feature task decomposition order.
- API route shapes and request/response schemas.
- PostgreSQL migration/tooling outside FT-003 where needed.
- LLM/vision provider and metadata format.
- UI details beyond React/Next.js/PWA baseline.

## Not Applicable Areas
- Production SaaS, multi-user tenancy, commercial farm management.
- Automated device commands and physical actuation.
- Full dataset registry and real fine-tuning.
- InfluxDB runtime dependency before real sensors.
- Agno Team `coordinate`.
- Server sync and `server_verified`.
- Microservices and production-grade orchestration.

## Feature Design Status Map
Current feature set from `/prd`. Global `/spec-design` has produced the shared backbone. Feature rows marked `complete` have also passed feature-local `/spec-improve`.

| Feature | Parent epic | spec_design_status | Likely linked specs / design areas | Notes |
|---|---|---|---|---|
| [FT-001 Daily Check-in, Observations, and Manual Measurements](features/FT-001-daily-check-in-observations-manual-measurements.md) | [EP-001](epics/EP-001-evidence-intake-runtime-authority.md) | complete | [FT-001 tech spec](tech-specs/FT-001-daily-check-in-observations-manual-measurements.md), [runtime data model](domains/runtime-data-model.md), [system architecture](architecture/system-architecture.md), [timeline event](contracts/timeline-event.md), [FT-003 tech spec](tech-specs/FT-003-runtime-state-timeline-audit.md), [safety approval](states/safety-approval.md), [API guidelines](contracts/api-guidelines.md), [first demo](testing/first-demo.md), [invariants](invariants.md) | Feature-local design resolves observation/measurement fields, explicit no-data state, pH/EC units/provenance, computed freshness projection, API shape, timeline payloads, and verification targets. |
| [FT-002 Photo Intake, Catalog, and Capture Manifests](features/FT-002-photo-intake-catalog-capture-manifests.md) | [EP-001](epics/EP-001-evidence-intake-runtime-authority.md) | complete | [FT-002 tech spec](tech-specs/FT-002-photo-intake-catalog-capture-manifests.md), [photo artifacts](domains/photo-artifacts.md), [runtime data model](domains/runtime-data-model.md), [timeline event](contracts/timeline-event.md), [FT-003 tech spec](tech-specs/FT-003-runtime-state-timeline-audit.md), [FT-010 tech spec](tech-specs/FT-010-local-security-privacy-lazy-sync.md), [local security](runbooks/local-security.md), [API guidelines](contracts/api-guidelines.md), [first demo](testing/first-demo.md), [invariants](invariants.md) | Feature-local design resolves photo upload API, backend-generated `photo_id`, file path layout, initial capture manifest v1, publication sequence, `user_photo` timeline payload, and verification targets. |
| [FT-003 Runtime State and Timeline Audit](features/FT-003-runtime-state-timeline-audit.md) | [EP-001](epics/EP-001-evidence-intake-runtime-authority.md) | complete | [FT-003 tech spec](tech-specs/FT-003-runtime-state-timeline-audit.md), [system architecture](architecture/system-architecture.md), [runtime data model](domains/runtime-data-model.md), [timeline event](contracts/timeline-event.md), [API guidelines](contracts/api-guidelines.md), [first demo](testing/first-demo.md), [invariants](invariants.md) | Feature-local design resolves table/migration boundaries, runtime-authority reads, timeline append semantics, common payload identifiers, read API surface, and verification targets. |
| [FT-004 Agent Chat Bus Event Stream and Publication Boundary](features/FT-004-agent-chat-bus-event-stream-publication-boundary.md) | [EP-002](epics/EP-002-agent-advisory-safety-loop.md) | complete | [FT-004 tech spec](tech-specs/FT-004-agent-chat-bus-event-stream-publication-boundary.md), [Agent Chat Bus](contracts/agent-chat-bus.md), [MessageEnvelope](contracts/message-envelope.md), [system architecture](architecture/system-architecture.md), [timeline event](contracts/timeline-event.md), [FT-003 tech spec](tech-specs/FT-003-runtime-state-timeline-audit.md), [first demo](testing/first-demo.md), [invariants](invariants.md) | Feature-local design resolves Bus working-stream persistence, envelope validation, event payload minimums, publication service, context filtering, influence levels, and anti-cheat verification targets. |
| [FT-005 UI Feed and Context Hygiene](features/FT-005-ui-feed-context-hygiene.md) | [EP-002](epics/EP-002-agent-advisory-safety-loop.md) | complete | [FT-005 tech spec](tech-specs/FT-005-ui-feed-context-hygiene.md), [UI Feed](contracts/ui-feed.md), [FT-012 tech spec](tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md), [MessageEnvelope](contracts/message-envelope.md), [FT-004 tech spec](tech-specs/FT-004-agent-chat-bus-event-stream-publication-boundary.md), [system architecture](architecture/system-architecture.md), [timeline event](contracts/timeline-event.md), [first demo](testing/first-demo.md), [invariants](invariants.md) | Feature-local design resolves UI Feed presentation storage, event payloads, controlled spoiler notes, context filtering, timeline/export snapshots, display safety, API surface, and verification targets. |
| [FT-006 Vision Observation and Plant State Trust](features/FT-006-vision-observation-plant-state-trust.md) | [EP-002](epics/EP-002-agent-advisory-safety-loop.md) | backbone_ready; needs_spec_improve | [plant state](states/plant-state.md), [MessageEnvelope](contracts/message-envelope.md), [runtime data model](domains/runtime-data-model.md), [dataset governance](states/dataset-governance.md) | Preserves observation-vs-diagnosis boundaries and prevents agent hypotheses from becoming confirmed state. |
| [FT-007 Hydroponics Advisor and Missing Data Policy](features/FT-007-hydroponics-advisor-missing-data-policy.md) | [EP-002](epics/EP-002-agent-advisory-safety-loop.md) | backbone_ready; needs_spec_improve | [safety approval](states/safety-approval.md), [MessageEnvelope](contracts/message-envelope.md), [task follow-up](states/task-follow-up.md), [first demo](testing/first-demo.md) | Covers advisor inputs, cautious recommendations, missing/stale pH/EC requests, no action-task creation, and Safety Gate handoff. |
| [FT-008 Tasks, Approvals, and Follow-up Outcomes](features/FT-008-tasks-approvals-follow-up-outcomes.md) | [EP-002](epics/EP-002-agent-advisory-safety-loop.md) | backbone_ready; needs_spec_improve | [task follow-up](states/task-follow-up.md), [safety approval](states/safety-approval.md), [runtime data model](domains/runtime-data-model.md), [timeline event](contracts/timeline-event.md) | Tracks check/measurement tasks, approved human action tasks, follow-up, and outcomes. |
| [FT-009 Dataset Governance and Trainability](features/FT-009-dataset-governance-trainability.md) | [EP-003](epics/EP-003-learning-governance.md) | complete | [FT-009 tech spec](tech-specs/FT-009-dataset-governance-trainability.md), [dataset governance](states/dataset-governance.md), [runtime data model](domains/runtime-data-model.md), [photo artifacts](domains/photo-artifacts.md), [MessageEnvelope](contracts/message-envelope.md), [FT-003 tech spec](tech-specs/FT-003-runtime-state-timeline-audit.md), [FT-005 tech spec](tech-specs/FT-005-ui-feed-context-hygiene.md), [first demo](testing/first-demo.md), [invariants](invariants.md) | Feature-local design resolves dataset item boundary, transition service, trainability recomputation, evidence refs, curator rules, API/service surface, lifecycle transitions, split restrictions, and gold constraints without creating a full dataset registry. |
| [FT-010 Local Security, Privacy, and Lazy Sync](features/FT-010-local-security-privacy-lazy-sync.md) | [EP-004](epics/EP-004-local-operations-operator-ui.md) | complete | [FT-010 tech spec](tech-specs/FT-010-local-security-privacy-lazy-sync.md), [local security](runbooks/local-security.md), [API guidelines](contracts/api-guidelines.md), [system architecture](architecture/system-architecture.md), [runtime data model](domains/runtime-data-model.md), [photo artifacts](domains/photo-artifacts.md), [first demo](testing/first-demo.md), [invariants](invariants.md) | Feature-local design resolves loopback/LAN auth shape, CORS allowlist, upload limits/MIME allowlist, safe path handling, redaction boundary, private artifacts, `local_only`, and 200 MB prompt-only behavior. |
| [FT-011 Minimal Web App/PWA Operator Surface](features/FT-011-minimal-web-app-pwa-operator-surface.md) | [EP-004](epics/EP-004-local-operations-operator-ui.md) | backbone_ready; needs_spec_improve | [system architecture](architecture/system-architecture.md), [API guidelines](contracts/api-guidelines.md), [UI Feed](contracts/ui-feed.md), [safety approval](states/safety-approval.md), [first demo](testing/first-demo.md) | First product surface for the daily operator workflow; UI Feed remains presentation-only. |
| [FT-012 Agent Runtime Decisions and MessageEnvelope Output Contracts](features/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md) | [EP-002](epics/EP-002-agent-advisory-safety-loop.md) | complete | [FT-012 tech spec](tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md), [MessageEnvelope](contracts/message-envelope.md), [FT-004 tech spec](tech-specs/FT-004-agent-chat-bus-event-stream-publication-boundary.md), [Agent Chat Bus](contracts/agent-chat-bus.md), [system architecture](architecture/system-architecture.md), [UI Feed](contracts/ui-feed.md), [dataset governance](states/dataset-governance.md), [first demo](testing/first-demo.md), [invariants](invariants.md) | Feature-local design resolves runtime decision state machine, adapter boundary, `MessageEnvelope` schema, decision-to-event mapping, concise output, `silent` audit, `ui_spoiler_note_ref`, and safety/escalation boundary. |
| [FT-013 Safety Gate for Physical-Action Advice](features/FT-013-safety-gate-physical-action-advice.md) | [EP-002](epics/EP-002-agent-advisory-safety-loop.md) | complete | [FT-013 tech spec](tech-specs/FT-013-safety-gate-physical-action-advice.md), [safety approval](states/safety-approval.md), [FT-001 tech spec](tech-specs/FT-001-daily-check-in-observations-manual-measurements.md), [FT-012 tech spec](tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md), [MessageEnvelope](contracts/message-envelope.md), [FT-004 tech spec](tech-specs/FT-004-agent-chat-bus-event-stream-publication-boundary.md), [FT-005 tech spec](tech-specs/FT-005-ui-feed-context-hygiene.md), [task follow-up](states/task-follow-up.md), [first demo](testing/first-demo.md), [invariants](invariants.md) | Feature-local design resolves deterministic Safety Gate policy, action taxonomy, pH/EC approval freshness, `SafetyGateDecision`, fail-closed outcomes, display checks, Bus/UI/task handoffs, and verification targets. |
| [FT-014 Human Approval and Action Unlock Semantics](features/FT-014-human-approval-action-unlock-semantics.md) | [EP-002](epics/EP-002-agent-advisory-safety-loop.md) | backbone_ready; needs_spec_improve | [safety approval](states/safety-approval.md), [task follow-up](states/task-follow-up.md), [runtime data model](domains/runtime-data-model.md), [timeline event](contracts/timeline-event.md) | Covers approval/rejection records, pending action proposals/tasks, human-performed action task unlocks, and no automated device execution. |

## Expected Spec Locations
- Feature hubs: `.memory-bank/tech-specs/FT-<NNN>-<slug>.md`
- Global architecture backbone: `.memory-bank/architecture/system-architecture.md`
- Optional future architecture notes, when a topic outgrows the backbone: `.memory-bank/architecture/<topic>.md`
- Contracts: `.memory-bank/contracts/<boundary>.md`
- Domain/data models: `.memory-bank/domains/<domain>.md`
- States: `.memory-bank/states/<lifecycle>.md`
- ADRs: `.memory-bank/adrs/ADR-<NNN>-<slug>.md`
- Testing/runbooks: `.memory-bank/testing/` and `.memory-bank/runbooks/`

## Gaps and Open Questions
- No global backbone blocker remains.
- FT-001 has completed feature-local `/spec-improve`; no FT-001 blocker remains for `/prd-to-tasks FT-001`.
- FT-002 has completed feature-local `/spec-improve`; no FT-002 blocker remains for `/prd-to-tasks FT-002`.
- FT-003 has completed feature-local `/spec-improve`; no FT-003 blocker remains for `/prd-to-tasks FT-003`.
- FT-004 has completed feature-local `/spec-improve`; no FT-004 blocker remains for `/prd-to-tasks FT-004`.
- FT-005 has completed feature-local `/spec-improve`; no FT-005 blocker remains for `/prd-to-tasks FT-005`.
- FT-009 has completed feature-local `/spec-improve`; no FT-009 blocker remains for `/prd-to-tasks FT-009`.
- FT-010 has completed feature-local `/spec-improve`; no FT-010 blocker remains for `/prd-to-tasks FT-010`.
- FT-012 has completed feature-local `/spec-improve`; no FT-012 blocker remains for `/prd-to-tasks FT-012`.
- FT-013 has completed feature-local `/spec-improve`; no FT-013 blocker remains for `/prd-to-tasks FT-013`.
- Remaining features still need feature-local `/spec-improve` to decide exact API route shapes, Pydantic/schema fields, migration/tooling where applicable, file path naming, feature-specific upload/photo workflow details, UI interaction details, and per-feature verification evidence.
- `project_dossier.md` remains upstream context for ambiguity resolution, but binding decisions must live in PRD, requirements, constitution, or narrower SDD specs.

## Update Rules
- When a planned/candidate area receives an evidence-backed spec, move it to `Existing Authoritative Specs` or link it from the relevant area with `authoritative` status.
- Keep the Feature Design Status Map aligned with the current `/prd` feature set and do not add EP/FT IDs outside the existing PRD decomposition.
- `T2` and `T3` task records must link the relevant authoritative specs before execution.
- Do not mark empty directories or placeholder docs as authoritative.
- If a new design area is intentionally deferred or excluded, record it under `candidate`, `unknown`, or `not_applicable` instead of inventing a spec.

## Compatibility Note
- Duo docs в `architecture/` и `guides/` остаются валидными.
- Этот слой уточняет source-of-truth, а не отменяет duo docs.
