---
description: Главная карта знаний проекта (table of contents) для агентов.
status: active
---
# Memory Bank Index

## Навигация

- [.memory-bank/constitution.md](constitution.md): Project Constitution — top governing policy for agents.
- [.memory-bank/mbb/index.md](mbb/index.md): Правила ведения Memory Bank (MBB).
- [.memory-bank/product.md](product.md): Продукт (C4 L1).
- [.memory-bank/prd.md](prd.md): Product Requirements Document после `/write-prd`.
- [.memory-bank/requirements.md](requirements.md): Требования + RTM.
- [.memory-bank/epics/index.md](epics/index.md): Router for epics (C4 L2).
- [.memory-bank/epics/EP-001-evidence-intake-runtime-authority.md](epics/EP-001-evidence-intake-runtime-authority.md): EP-001, parent epic for FT-001..FT-003 evidence intake and runtime authority.
- [.memory-bank/epics/EP-002-agent-advisory-safety-loop.md](epics/EP-002-agent-advisory-safety-loop.md): EP-002, parent epic for FT-004..FT-008 and FT-012..FT-014 agent advisory and safety loop.
- [.memory-bank/epics/EP-003-learning-governance.md](epics/EP-003-learning-governance.md): EP-003, parent epic for FT-009 dataset governance and trainability.
- [.memory-bank/epics/EP-004-local-operations-operator-ui.md](epics/EP-004-local-operations-operator-ui.md): EP-004, parent epic for FT-010..FT-011 local operations and operator UI.
- [.memory-bank/features/index.md](features/index.md): Router for features (C4 L3).
- [.memory-bank/features/FT-001-daily-check-in-observations-manual-measurements.md](features/FT-001-daily-check-in-observations-manual-measurements.md): FT-001, daily check-in, observations, and manual measurements under EP-001.
- [.memory-bank/features/FT-002-photo-intake-catalog-capture-manifests.md](features/FT-002-photo-intake-catalog-capture-manifests.md): FT-002, photo intake, catalog, and capture manifests under EP-001.
- [.memory-bank/features/FT-003-runtime-state-timeline-audit.md](features/FT-003-runtime-state-timeline-audit.md): FT-003, runtime state and timeline audit under EP-001.
- [.memory-bank/features/FT-004-agent-chat-bus-event-stream-publication-boundary.md](features/FT-004-agent-chat-bus-event-stream-publication-boundary.md): FT-004, Agent Chat Bus event stream and publication boundary under EP-002.
- [.memory-bank/features/FT-005-ui-feed-context-hygiene.md](features/FT-005-ui-feed-context-hygiene.md): FT-005, UI Feed and context hygiene under EP-002.
- [.memory-bank/features/FT-006-vision-observation-plant-state-trust.md](features/FT-006-vision-observation-plant-state-trust.md): FT-006, Vision Observation and plant state trust under EP-002.
- [.memory-bank/features/FT-007-hydroponics-advisor-missing-data-policy.md](features/FT-007-hydroponics-advisor-missing-data-policy.md): FT-007, Hydroponics Advisor and missing data policy under EP-002.
- [.memory-bank/features/FT-008-tasks-approvals-follow-up-outcomes.md](features/FT-008-tasks-approvals-follow-up-outcomes.md): FT-008, tasks, approvals, and follow-up outcomes under EP-002.
- [.memory-bank/features/FT-009-dataset-governance-trainability.md](features/FT-009-dataset-governance-trainability.md): FT-009, dataset governance and trainability under EP-003.
- [.memory-bank/features/FT-010-local-security-privacy-lazy-sync.md](features/FT-010-local-security-privacy-lazy-sync.md): FT-010, local security, privacy, and lazy sync under EP-004.
- [.memory-bank/features/FT-011-minimal-web-app-pwa-operator-surface.md](features/FT-011-minimal-web-app-pwa-operator-surface.md): FT-011, minimal Web App/PWA operator surface under EP-004.
- [.memory-bank/features/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md](features/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md): FT-012, Agent runtime decisions and MessageEnvelope output contracts under EP-002.
- [.memory-bank/features/FT-013-safety-gate-physical-action-advice.md](features/FT-013-safety-gate-physical-action-advice.md): FT-013, Safety Gate for physical-action advice under EP-002.
- [.memory-bank/features/FT-014-human-approval-action-unlock-semantics.md](features/FT-014-human-approval-action-unlock-semantics.md): FT-014, human approval and action unlock semantics under EP-002.
- Next route: `/spec-design -> /spec-improve FT-<NNN> -> /prd-to-tasks FT-<NNN>`.
- [.memory-bank/tasks/index.json](tasks/index.json): Authoritative JSON task record index.
- [.memory-bank/schemas/task.schema.json](schemas/task.schema.json): JSON schema for task records.
- [.memory-bank/workflows/index.md](workflows/index.md): Workflow policies and execution-loop router.

- [.memory-bank/spec-index.md](spec-index.md): SDD Design Specs Index and source-of-truth route map.
- [.memory-bank/glossary.md](glossary.md): Общий словарь терминов и доменных значений.
- [.memory-bank/invariants.md](invariants.md): Глобальные MUST/NEVER правила.
- [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md): Global MVP architecture, authority model, module boundaries, Agno boundary, data flow, and sequence.
- [.memory-bank/tech-specs/index.md](tech-specs/index.md): Router for feature-local SDD tech specs.
- [.memory-bank/tech-specs/FT-001-daily-check-in-observations-manual-measurements.md](tech-specs/FT-001-daily-check-in-observations-manual-measurements.md): Feature-local SDD tech spec for daily check-in, observations, manual measurements, and freshness.
- [.memory-bank/tech-specs/FT-002-photo-intake-catalog-capture-manifests.md](tech-specs/FT-002-photo-intake-catalog-capture-manifests.md): Feature-local SDD tech spec for photo intake, catalog, file layout, and initial capture manifests.
- [.memory-bank/tech-specs/FT-003-runtime-state-timeline-audit.md](tech-specs/FT-003-runtime-state-timeline-audit.md): Feature-local SDD tech spec for PostgreSQL runtime authority and `timeline.jsonl` audit/export.
- [.memory-bank/tech-specs/FT-004-agent-chat-bus-event-stream-publication-boundary.md](tech-specs/FT-004-agent-chat-bus-event-stream-publication-boundary.md): Feature-local SDD tech spec for Agent Chat Bus publication boundary.
- [.memory-bank/tech-specs/FT-005-ui-feed-context-hygiene.md](tech-specs/FT-005-ui-feed-context-hygiene.md): Feature-local SDD tech spec for UI Feed and context hygiene.
- [.memory-bank/tech-specs/FT-009-dataset-governance-trainability.md](tech-specs/FT-009-dataset-governance-trainability.md): Feature-local SDD tech spec for dataset governance and trainability.
- [.memory-bank/tech-specs/FT-010-local-security-privacy-lazy-sync.md](tech-specs/FT-010-local-security-privacy-lazy-sync.md): Feature-local SDD tech spec for local security, privacy, upload validation, and lazy sync.
- [.memory-bank/tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md](tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md): Feature-local SDD tech spec for agent runtime decisions and MessageEnvelope output contracts.
- [.memory-bank/tech-specs/FT-013-safety-gate-physical-action-advice.md](tech-specs/FT-013-safety-gate-physical-action-advice.md): Feature-local SDD tech spec for Safety Gate physical-action advice checks.
- [.memory-bank/guides/](guides/): Valid HOW docs для использования, запуска и troubleshooting.
- [.memory-bank/adrs/](adrs/): ADR решения.
- [.memory-bank/adrs/ADR-001-local-modular-monolith-and-authority-boundaries.md](adrs/ADR-001-local-modular-monolith-and-authority-boundaries.md): Accepted decision for local modular monolith and authority boundaries.

- [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md): Conceptual MVP runtime entity/ref model.
- [.memory-bank/domains/photo-artifacts.md](domains/photo-artifacts.md): Photo catalog, files, and manifest boundary.
- [.memory-bank/contracts/index.md](contracts/index.md): Router for global contract and boundary specs.
- [.memory-bank/contracts/api-guidelines.md](contracts/api-guidelines.md): HTTP API, OpenAPI, error, security, upload, and compatibility guidelines.
- [.memory-bank/contracts/timeline-event.md](contracts/timeline-event.md): Timeline JSONL append-only audit/export event contract.
- [.memory-bank/contracts/agent-chat-bus.md](contracts/agent-chat-bus.md): Agent Chat Bus event and publication boundary.
- [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md): Agent runtime decision and MessageEnvelope contract.
- [.memory-bank/contracts/ui-feed.md](contracts/ui-feed.md): UI Feed presentation and context hygiene contract.
- [.memory-bank/states/index.md](states/index.md): Router for lifecycle/state specs.
- [.memory-bank/states/plant-state.md](states/plant-state.md): Plant state confidence/status lifecycle.
- [.memory-bank/states/safety-approval.md](states/safety-approval.md): Safety Gate and human approval lifecycle.
- [.memory-bank/states/task-follow-up.md](states/task-follow-up.md): Task and follow-up lifecycle.
- [.memory-bank/states/dataset-governance.md](states/dataset-governance.md): Dataset governance and trainability lifecycle.
- [.memory-bank/runbooks/local-security.md](runbooks/local-security.md): Local security, privacy, upload validation, and lazy-sync runbook.
- [.memory-bank/testing/index.md](testing/index.md): Testing strategy.
- [.memory-bank/testing/first-demo.md](testing/first-demo.md): First demo verification plan.
- [.memory-bank/skills/index.md](skills/index.md): Skill registry.
