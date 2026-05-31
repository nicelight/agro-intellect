---
description: Router for Memory Bank features (C4 L3).
status: active
---
# Features Index

## Current Features

- [.memory-bank/features/FT-001-daily-check-in-observations-manual-measurements.md](FT-001-daily-check-in-observations-manual-measurements.md): Daily check-in, user observations, manual pH/EC entry, provenance, and freshness semantics.
- [.memory-bank/features/FT-002-photo-intake-catalog-capture-manifests.md](FT-002-photo-intake-catalog-capture-manifests.md): Photo upload/capture, catalog metadata, file storage, `sha256`, MVP photo types, and initial capture manifests.
- [.memory-bank/features/FT-003-runtime-state-timeline-audit.md](FT-003-runtime-state-timeline-audit.md): PostgreSQL/read-model authority, mutable state boundaries, timeline audit/export events, and event identifiers.
- [.memory-bank/features/FT-004-agent-chat-bus-event-stream-publication-boundary.md](FT-004-agent-chat-bus-event-stream-publication-boundary.md): Agent Chat Bus event stream, `BusEventEnvelope`, event types, `consumable_by_agents`, and Agno publication boundary.
- [.memory-bank/features/FT-005-ui-feed-context-hygiene.md](FT-005-ui-feed-context-hygiene.md): UI Feed separation, spoiler notes, concise display content, and context-filtering rules.
- [.memory-bank/features/FT-006-vision-observation-plant-state-trust.md](FT-006-vision-observation-plant-state-trust.md): Vision Observation, plant state confidence/status values, and confirmed-state trust gates.
- [.memory-bank/features/FT-007-hydroponics-advisor-missing-data-policy.md](FT-007-hydroponics-advisor-missing-data-policy.md): Hydroponics Advisor inputs, cautious recommendations, missing/stale pH/EC requests, and Safety Gate handoff.
- [.memory-bank/features/FT-008-tasks-approvals-follow-up-outcomes.md](FT-008-tasks-approvals-follow-up-outcomes.md): Check/measurement tasks, approved action tasks, pending approvals, 1-3 day follow-up, and outcomes.
- [.memory-bank/features/FT-009-dataset-governance-trainability.md](FT-009-dataset-governance-trainability.md): Dataset lifecycle fields, provenance, curator decisions, split restrictions, and `can_train_on` eligibility.
- [.memory-bank/features/FT-010-local-security-privacy-lazy-sync.md](FT-010-local-security-privacy-lazy-sync.md): Loopback/LAN baseline, CORS/upload/path validation, secret redaction, private artifacts, `local_only`, and 200 MB prompt boundary.
- [.memory-bank/features/FT-011-minimal-web-app-pwa-operator-surface.md](FT-011-minimal-web-app-pwa-operator-surface.md): Minimal Web App/PWA operator surface for intake, state, tasks, history, recommendations, approvals, and controlled spoiler notes.
- [.memory-bank/features/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md](FT-012-agent-runtime-decisions-message-envelope-output-contracts.md): Agent runtime decisions, `MessageEnvelope`, concise output, silent audit, Team Signal/Safety Block routing, and `ui_spoiler_note_ref`.
- [.memory-bank/features/FT-013-safety-gate-physical-action-advice.md](FT-013-safety-gate-physical-action-advice.md): Physical-action detection, fail-closed Safety Gate behavior, 2-hour pH/EC approval freshness, high-risk manual interventions, and user-visible action wording checks.
- [.memory-bank/features/FT-014-human-approval-action-unlock-semantics.md](FT-014-human-approval-action-unlock-semantics.md): Approval/rejection records, pending action proposals/tasks, human-performed action task unlocks, and no automated device execution.
