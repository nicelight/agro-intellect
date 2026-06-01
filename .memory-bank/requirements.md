---
description: Требования (REQ-IDs) + traceability matrix (RTM).
status: draft
---
# Requirements

## Status model
- Document `status`: `draft|active|deprecated|archived`
- RTM `Lifecycle`: `planned|implemented|verified`

## REQ list

### REQ-001 Daily check-in for one plant

The system MUST support a daily monitoring flow for `tomato_001`, including user observation text, optional photos, optional pH/EC input, and traceable state/event records.

### REQ-002 Photo intake and catalog integrity

The system MUST allow photo upload for `tomato_001`; every photo MUST have `plant_id`, globally unique `photo_id`, `captured_at`, `photo_type`, file path, and `sha256`. Photo binaries MUST be stored as files, not PostgreSQL or InfluxDB blobs.

### REQ-003 Photo manifest and export snapshot boundary

Each photo MUST receive an initial capture JSON manifest next to the photo file. Initial capture manifests and later export snapshot manifests MUST be distinguishable, immutable as export artifacts, and MUST NOT become runtime authority for mutable state.

### REQ-004 Manual pH/EC freshness and provenance

The system MUST allow manual pH and EC entry with timestamp/provenance. pH/EC measurements are fresh for analysis for up to 24 hours and fresh for physical action approval for up to 2 hours. Missing or stale values MUST trigger measurement requests or Safety Gate blocks where relevant.

### REQ-005 Runtime authority and timeline audit

PostgreSQL/read model MUST be the runtime authority for mutable operational state. `timeline.jsonl` MUST be append-only audit/export and MUST include traceable identifiers; `event_type=user_photo` MUST include mandatory `payload.plant_id`.

### REQ-006 Agent runtime boundary and Agent Chat Bus

Agno invocation MUST NOT equal Agent Chat Bus publication. Agent Chat Bus events MUST pass through `BusEventEnvelope`; agent work outputs published to the Bus MUST pass through `MessageEnvelope`; each invoked agent MUST return one runtime decision: `speak`, `silent`, `clarify`, or `escalate`.

### REQ-007 UI Feed separation and concise communication

UI Feed MUST remain a presentation layer separate from Agent Chat Bus and MUST NOT be passed to agents as working context. `ui_spoiler_note` MUST have `consumable_by_agents=false` and `visible_to_agents=false`. Ordinary agent outputs SHOULD stay concise by default.

### REQ-008 Vision observation and plant state trust

The system MUST support mock or real Vision Observation for the first demo, distinguishing observation from diagnosis. Plant State MUST track state over time with confidence/status metadata and MUST NOT promote agent-labeled conclusions to confirmed state without human review or follow-up evidence.

### REQ-009 Hydroponics advice, Safety Gate, and human approval

Hydroponics advice MUST be cautious, request missing critical data, and never bypass Safety Gate. Any user-visible phrase that instructs or implies a physical action MUST fail closed into Safety Gate review unless fresh data, safety check, and human approval are satisfied.

### REQ-010 Tasks, approvals, and follow-up outcomes

The system MUST create check/measurement tasks without approval when more data is needed, create action tasks only from approved action proposals, support follow-up after 1-3 days, and record outcome as improved, worsened, unchanged, or no data.

### REQ-011 Dataset governance and trainability

The system MUST track dataset lifecycle fields from the PRD, preserve provenance, enforce split restrictions, forbid training on raw/agent-labeled hypotheses, and allow `can_train_on=true` only when curator decision, split, evidence refs, status, and confirmation source rules permit it. `gold` requires human/expert review or batch review approval.

### REQ-012 Local security, privacy, and lazy sync

The backend MUST bind to loopback by default; LAN mode requires explicit enablement and authentication/token protection. CORS, upload validation, path safety, path traversal rejection, and secret redaction are required. Local plant photos/manifests MUST remain private by default. MVP sync status MUST support `local_only`; the 200 MB local storage prompt MUST NOT imply server/upload availability or change sync status. Server/upload sync is TODO for a later version.

### REQ-013 Minimal Web App/PWA operator surface

The first product surface MUST be a local Web App/PWA that lets the user run the daily `tomato_001` flow through chat, daily check-in, photo upload, plant card, manual pH/EC input, task list, day/photo history, recommendations, human approval prompts, and controlled spoiler notes without exposing UI Feed content to agents or bypassing Safety Gate display checks.

## Out of scope

- Production SaaS, multi-user tenancy, and commercial farm-management scope.
- Automated physical actuation: pumps, dosing, pH/EC adjustment, solution changes, light control, autowatering, autodosing, or immediate device commands.
- Automatic mandatory dosing instructions without Safety Gate clearance and human approval.
- Complex RAG, expert panel, full dataset registry, or real fine-tuning.
- Photo binary storage in PostgreSQL or InfluxDB.
- InfluxDB runtime dependency before real sensors exist.
- Treating Agno, Agno Team, Agno Workflow events, Agno memory, or Agno storage as domain source of truth.
- Agno Team `coordinate` as a domain coordinator.
- Treating UI explanations, raw model reasoning, or agent hypotheses as confirmed facts or trainable labels.
- Server sync and `server_verified` status before a real server sync stage exists.

## Traceability (RTM)
When one requirement spans multiple feature boundaries, the RTM keeps the main owner(s) visible while also listing required supporting or affected features. This prevents task decomposition from losing cross-feature constraints without splitting a single PRD requirement into artificial sub-requirements.

- `Primary Feature(s)` own the main user-visible or domain behavior for the requirement.
- `Supporting / Affected Features` provide required runtime authority, contracts, safety gates, UI surfaces, task handoffs, or audit boundaries needed to satisfy the requirement.

| REQ | Epic | Primary Feature(s) | Supporting / Affected Features | Test | Lifecycle |
|---|---|---|---|---|---|
| REQ-001 | [EP-001](epics/EP-001-evidence-intake-runtime-authority.md) | [FT-001](features/FT-001-daily-check-in-observations-manual-measurements.md) | [FT-003](features/FT-003-runtime-state-timeline-audit.md) | workflow:daily-check-in-smoke; integration:observation-state-events; integration:postgres-runtime-authority | planned |
| REQ-002 | [EP-001](epics/EP-001-evidence-intake-runtime-authority.md) | [FT-002](features/FT-002-photo-intake-catalog-capture-manifests.md) | [FT-003](features/FT-003-runtime-state-timeline-audit.md) | schema:photo-catalog; integration:photo-upload; policy:photo-required-plant-id | planned |
| REQ-003 | [EP-001](epics/EP-001-evidence-intake-runtime-authority.md) | [FT-002](features/FT-002-photo-intake-catalog-capture-manifests.md) | [FT-003](features/FT-003-runtime-state-timeline-audit.md) | schema:photo-manifest; integration:initial-vs-export-manifest; policy:no-runtime-read-from-stale-manifest; integration:postgres-runtime-authority | planned |
| REQ-004 | [EP-001](epics/EP-001-evidence-intake-runtime-authority.md)<br>[EP-002](epics/EP-002-agent-advisory-safety-loop.md) | [FT-001](features/FT-001-daily-check-in-observations-manual-measurements.md) | [FT-003](features/FT-003-runtime-state-timeline-audit.md)<br>[FT-007](features/FT-007-hydroponics-advisor-missing-data-policy.md)<br>[FT-008](features/FT-008-tasks-approvals-follow-up-outcomes.md)<br>[FT-013](features/FT-013-safety-gate-physical-action-advice.md) | policy:ph-ec-freshness; workflow:missing-or-stale-measurement-task; policy:safety-gate-physical-actions | planned |
| REQ-005 | [EP-001](epics/EP-001-evidence-intake-runtime-authority.md) | [FT-003](features/FT-003-runtime-state-timeline-audit.md) | - | schema:timeline-event; integration:postgres-runtime-authority; policy:append-only-jsonl | planned |
| REQ-006 | [EP-002](epics/EP-002-agent-advisory-safety-loop.md) | [FT-004](features/FT-004-agent-chat-bus-event-stream-publication-boundary.md)<br>[FT-012](features/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md) | - | schema:bus-event-envelope; schema:message-envelope; policy:agno-adapter-boundary; policy:silent-audit | planned |
| REQ-007 | [EP-002](epics/EP-002-agent-advisory-safety-loop.md) | [FT-005](features/FT-005-ui-feed-context-hygiene.md)<br>[FT-012](features/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md) | [FT-011](features/FT-011-minimal-web-app-pwa-operator-surface.md) | schema:ui-feed-event; policy:context-filtering; policy:concise-output | planned |
| REQ-008 | [EP-002](epics/EP-002-agent-advisory-safety-loop.md) | [FT-006](features/FT-006-vision-observation-plant-state-trust.md) | [FT-002](features/FT-002-photo-intake-catalog-capture-manifests.md)<br>[FT-003](features/FT-003-runtime-state-timeline-audit.md)<br>[FT-009](features/FT-009-dataset-governance-trainability.md) | workflow:vision-to-plant-state; policy:agent-hypothesis-not-confirmed | planned |
| REQ-009 | [EP-002](epics/EP-002-agent-advisory-safety-loop.md) | [FT-007](features/FT-007-hydroponics-advisor-missing-data-policy.md)<br>[FT-013](features/FT-013-safety-gate-physical-action-advice.md)<br>[FT-014](features/FT-014-human-approval-action-unlock-semantics.md) | [FT-008](features/FT-008-tasks-approvals-follow-up-outcomes.md)<br>[FT-011](features/FT-011-minimal-web-app-pwa-operator-surface.md) | policy:safety-gate-physical-actions; policy:user-visible-action-advice-fail-closed; workflow:approval-prompt-human-action | planned |
| REQ-010 | [EP-002](epics/EP-002-agent-advisory-safety-loop.md) | [FT-008](features/FT-008-tasks-approvals-follow-up-outcomes.md) | [FT-014](features/FT-014-human-approval-action-unlock-semantics.md) | workflow:task-follow-up-outcome; integration:approved-action-task-transition | planned |
| REQ-011 | [EP-003](epics/EP-003-learning-governance.md) | [FT-009](features/FT-009-dataset-governance-trainability.md) | [FT-006](features/FT-006-vision-observation-plant-state-trust.md)<br>[FT-012](features/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md) | policy:dataset-trainability; policy:split-restrictions; schema:dataset-provenance | planned |
| REQ-012 | [EP-004](epics/EP-004-local-operations-operator-ui.md) | [FT-010](features/FT-010-local-security-privacy-lazy-sync.md) | [FT-002](features/FT-002-photo-intake-catalog-capture-manifests.md)<br>[FT-005](features/FT-005-ui-feed-context-hygiene.md)<br>[FT-011](features/FT-011-minimal-web-app-pwa-operator-surface.md) | security:local-backend-baseline; security:cors-allowlist; security:upload-validation; security:secret-redaction-logs-timeline-manifests-ui-agent-chat-bus-screenshots; policy:private-artifact-approval-sync-privacy; policy:lazy-sync-local-only | planned |
| REQ-013 | [EP-004](epics/EP-004-local-operations-operator-ui.md)<br>[EP-002](epics/EP-002-agent-advisory-safety-loop.md) | [FT-011](features/FT-011-minimal-web-app-pwa-operator-surface.md) | [FT-005](features/FT-005-ui-feed-context-hygiene.md)<br>[FT-008](features/FT-008-tasks-approvals-follow-up-outcomes.md)<br>[FT-013](features/FT-013-safety-gate-physical-action-advice.md)<br>[FT-014](features/FT-014-human-approval-action-unlock-semantics.md) | e2e:daily-ui-smoke; integration:ui-feed-presentation; policy:user-visible-action-advice-fail-closed; workflow:approval-prompt-human-action | planned |
