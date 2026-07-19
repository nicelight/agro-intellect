---
description: Active MVP v2 feature router.
status: active
last_updated: 2026-07-20
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/epics/index.md
---
# Features Index

## Foundation

- [FT-000 Foundation Dev Path](FT-000-foundation.md): executable Foundation baseline.

## EP-001 Local Farm Access And Admin

- [FT-001 Local Accounts Sessions And ActorContext](FT-001-local-accounts-sessions-actor-context.md): verified local identity, session, and ActorContext boundary.
- [FT-002 Farm Plant Lifecycle And Access Grants](FT-002-farm-plant-lifecycle-access-grants.md): verified Farm/Plant lifecycle and access-grant boundary; downstream retained-history/UI/Safety/agent scopes remain with later features.
- [FT-003 Boss Admin Surface And Admin Audit](FT-003-boss-admin-surface-admin-audit.md): implemented backend Boss administration and durable audit boundary; PWA/admin UI and downstream demo scopes remain with later features.

## EP-002 Plant Operations Evidence Authority

- [FT-004 Authorized Plant Operations And Daily Check-In](FT-004-authorized-plant-operations-daily-check-in.md): verified backend/API daily operations, check-ins, canonical measurements, freshness, and timeline refs.
- [FT-005 Photo Intake Catalog And Capture Manifests](FT-005-photo-intake-catalog-capture-manifests.md): verified backend/API local photo intake, catalog pagination, manifests, checksum, and evidence refs.
- [FT-006 Runtime State Timeline And Plant History](FT-006-runtime-state-timeline-plant-history.md): verified backend/API runtime-authority history projections, retained history, strict cursors, and URL-first/KISS response handling.

## EP-003 Agent Runtime And Context Hygiene

- [FT-007 Agent Runtime Decisions And MessageEnvelope](FT-007-agent-runtime-decisions-message-envelope.md): SDD design complete; TASK-028/TASK-029 remain planned and non-executable until `/prd-to-tasks FT-007` reconciliation and fresh review approval.
- [FT-008 Agent Chat Bus And UI Feed Context Hygiene](FT-008-agent-chat-bus-ui-feed-context-hygiene.md): verified durable introductions, guarded typed Bus/literal UI publication, current-authority agent-context isolation, and protected Plant feed API; FT-016 retains frontend rendering ownership.
- [FT-009 Vision Observation And Plant State Trust](FT-009-vision-observation-plant-state-trust.md): W1/W2 task boundary complete with accepted deterministic Vision and Plant-state trust evidence; lifecycle remains planned pending an explicit owner feature decision, and live-provider image behavior remains deferred.
- [FT-010 Hydroponics Advisor Missing Data Policy](FT-010-hydroponics-advisor-missing-data-policy.md): SDD design complete; its T3 advisor-runtime task is planned after scheduler-recorded FT-009 dependency recovery, with no promotion or selection by sync.

## EP-004 Safety Tasks And Follow-Up

- [FT-011 Safety Gate Physical-Action Routing](FT-011-safety-gate-physical-action-routing.md): SDD design complete; two planned T3 tasks add provider-neutral immutable classification and two-hour-evidence Safety routing through pending human approval.
- [FT-012 Human Approval Tasks And Follow-Up Outcomes](FT-012-human-approval-tasks-follow-up-outcomes.md): SDD design complete; two planned T3 tasks add authoritative approval/task/follow-up/outcome state and the provider-neutral classified `task_follow_up` path.

## EP-005 Companion Governance

- [FT-013 Companion IssueStack Proposals And DecisionRecords](FT-013-companion-issuestack-proposals-decisionrecords.md): design is complete after removing the blanket approval-status ban and retaining selected open-Issue `summary_text` as typed, non-authoritative Companion input; three reconciled T3 cards await fresh task-plan review.

## EP-006 Local Privacy And Operator Surface

- [FT-014 Dataset Governance And Trainability](FT-014-dataset-governance-trainability.md): evidence-gated trainability.
- [FT-015 Local Security Privacy And Storage Prompt](FT-015-local-security-privacy-storage-prompt.md): local privacy/exposure/storage behavior.
- [FT-016 Web App PWA Operator Surface And First Demo](FT-016-web-app-pwa-operator-surface-first-demo.md): role-aware first-demo UI.
