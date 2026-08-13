---
description: Active MVP v2 feature router.
status: active
last_updated: 2026-08-13
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/epics/index.md
---
# Features Index

## Foundation

- [FT-000 Foundation Dev Path](FT-000-foundation.md) — `verified`: executable Foundation baseline.

## EP-001 Local Farm Access And Admin

- [FT-001 Local Accounts Sessions And ActorContext](FT-001-local-accounts-sessions-actor-context.md) — `verified`: identity, session, and ActorContext.
- [FT-002 Farm Plant Lifecycle And Access Grants](FT-002-farm-plant-lifecycle-access-grants.md) — `verified`: Farm/Plant lifecycle and access grants.
- [FT-003 Boss Admin Surface And Admin Audit](FT-003-boss-admin-surface-admin-audit.md) — `implemented`: Boss administration and durable audit.

## EP-002 Plant Operations Evidence Authority

- [FT-004 Authorized Plant Operations And Daily Check-In](FT-004-authorized-plant-operations-daily-check-in.md) — `verified`: daily operations, check-ins, and measurements.
- [FT-005 Photo Intake Catalog And Capture Manifests](FT-005-photo-intake-catalog-capture-manifests.md) — `verified`: local photo catalog and capture manifests.
- [FT-006 Runtime State Timeline And Plant History](FT-006-runtime-state-timeline-plant-history.md) — `verified`: runtime state, Timeline, and Plant history.

## EP-003 Agent Runtime And Context Hygiene

- [FT-007 Agent Runtime Decisions And MessageEnvelope](FT-007-agent-runtime-decisions-message-envelope.md) — `planned`: agent runtime decisions and MessageEnvelope.
- [FT-008 Agent Chat Bus And UI Feed Context Hygiene](FT-008-agent-chat-bus-ui-feed-context-hygiene.md) — `verified`: guarded Bus/UI publication, context hygiene, protected Feed reads, and lazy active-Feed introduction materialization.
- [FT-009 Vision Observation And Plant State Trust](FT-009-vision-observation-plant-state-trust.md) — `planned`: Vision observations and Plant-state trust.
- [FT-010 Hydroponics Advisor Missing Data Policy](FT-010-hydroponics-advisor-missing-data-policy.md) — `planned`: cautious advice under missing/stale data.

## EP-004 Safety Tasks And Follow-Up

- [FT-011 Safety Gate Physical-Action Routing](FT-011-safety-gate-physical-action-routing.md) — `planned`: physical-action classification and Safety routing.
- [FT-012 Human Approval Tasks And Follow-Up Outcomes](FT-012-human-approval-tasks-follow-up-outcomes.md) — `planned`: approvals, human tasks, follow-up, and outcomes.

## EP-005 Companion Governance

- [FT-013 Companion IssueStack Proposals And DecisionRecords](FT-013-companion-issuestack-proposals-decisionrecords.md) — `verified`: IssueStack, proposals, DecisionRecords, and explicit provider-neutral Companion runtime.

## EP-006 Local Privacy And Operator Surface

- [FT-014 Dataset Governance And Trainability](FT-014-dataset-governance-trainability.md) — `implemented`: evidence-gated trainability; all thirteen tasks `done` (TASK-047/048/049/050/051/052/053/054/055/057 plus W6 remediation TASK-058/059/060); feature-level `SEMANTIC_VERDICT: semantic-pass` recorded.
- [FT-015 Local Security Privacy And Storage Prompt](FT-015-local-security-privacy-storage-prompt.md) — `planned`: local privacy/exposure plus photo-only `>200 MiB` prompt policy and transient per-Account interaction.
- [FT-016 Web App PWA Operator Surface And First Demo](FT-016-web-app-pwa-operator-surface-first-demo.md) — `planned`: role-aware SvelteKit first-demo PWA with read-only backend consumers, transient FT-015 prompt state, and browser-capture redaction.
