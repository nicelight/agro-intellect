---
description: Active MVP v2 feature router.
status: active
last_updated: 2026-06-16
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/epics/index.md
---
# Features Index

Active MVP v2 features are draft L3 decomposition artifacts. Global `/spec-design` is complete.

First-wave `/spec-improve`, `/prd-to-tasks`, and task-artifact verification are complete for FT-001, FT-002, and FT-003. Their current normative feature designs are registered in [.memory-bank/spec-index.md](../spec-index.md), implementation plans live under [.memory-bank/tasks/plans/](../tasks/plans/), and schema-backed TASK records live under [.memory-bank/tasks/](../tasks/).

Only TASK-001 is `ready`. TASK-002..TASK-015 remain `planned` behind explicit dependencies and must not be executed until their prerequisites and verification gates are satisfied. The next execution route is `/execute TASK-001`.

All other features still require their own `/spec-improve FT-<NNN>` gate before `/prd-to-tasks FT-<NNN>`.

## EP-001 Local Farm Access And Admin

- [FT-001 Local Accounts Sessions And ActorContext](FT-001-local-accounts-sessions-actor-context.md): `/prd-to-tasks` complete; plan [.memory-bank/tasks/plans/IMPL-FT-001.md](../tasks/plans/IMPL-FT-001.md); tasks TASK-001..TASK-005.
- [FT-002 Farm Plant Lifecycle And Access Grants](FT-002-farm-plant-lifecycle-access-grants.md): `/prd-to-tasks` complete; plan [.memory-bank/tasks/plans/IMPL-FT-002.md](../tasks/plans/IMPL-FT-002.md); tasks TASK-006..TASK-010.
- [FT-003 Boss Admin Surface And Admin Audit](FT-003-boss-admin-surface-admin-audit.md): `/prd-to-tasks` complete; plan [.memory-bank/tasks/plans/IMPL-FT-003.md](../tasks/plans/IMPL-FT-003.md); tasks TASK-011..TASK-015.

## EP-002 Plant Operations Evidence Authority

- [FT-004 Authorized Plant Operations And Daily Check-In](FT-004-authorized-plant-operations-daily-check-in.md): authorized Plant selector, observations, pH/EC, Plant card/history, and workflow entry points.
- [FT-005 Photo Intake Catalog And Capture Manifests](FT-005-photo-intake-catalog-capture-manifests.md): local photo files, catalog metadata, checksums, manifests, and audit refs.
- [FT-006 Runtime State Timeline And Plant History](FT-006-runtime-state-timeline-plant-history.md): PostgreSQL/read model authority, timeline audit/export, and retained history.

## EP-003 Agent Runtime And Context Hygiene

- [FT-007 Agent Runtime Decisions And MessageEnvelope](FT-007-agent-runtime-decisions-message-envelope.md): real model-backed runtime path, adapter validation, runtime decisions, and structured output.
- [FT-008 Agent Chat Bus And UI Feed Context Hygiene](FT-008-agent-chat-bus-ui-feed-context-hygiene.md): Bus working context, UI Feed presentation, and context anti-cheat rules.
- [FT-009 Vision Observation And Plant State Trust](FT-009-vision-observation-plant-state-trust.md): real vision processing, observation boundaries, and Plant state trust statuses.
- [FT-010 Hydroponics Advisor Missing Data Policy](FT-010-hydroponics-advisor-missing-data-policy.md): cautious hydroponics advice, stale/missing data behavior, and Safety Gate handoff.

## EP-004 Safety Tasks And Follow-Up

- [FT-011 Safety Gate Physical-Action Routing](FT-011-safety-gate-physical-action-routing.md): fail-closed physical-action wording classification and approval routing.
- [FT-012 Human Approval Tasks And Follow-Up Outcomes](FT-012-human-approval-tasks-follow-up-outcomes.md): approval authority, action_task creation, and outcome capture.

## EP-005 Companion Governance

- [FT-013 Companion IssueStack Proposals And DecisionRecords](FT-013-companion-issuestack-proposals-decisionrecords.md): typed Plant-scoped governance state and approved governance summary boundary.

## EP-006 Local Privacy And Operator Surface

- [FT-014 Dataset Governance And Trainability](FT-014-dataset-governance-trainability.md): non-trainable default, evidence refs, and future trainability guardrails.
- [FT-015 Local Security Privacy And Storage Prompt](FT-015-local-security-privacy-storage-prompt.md): loopback/LAN exposure, secret redaction, `local_only`, and 200 MB prompt.
- [FT-016 Web App PWA Operator Surface And First Demo](FT-016-web-app-pwa-operator-surface-first-demo.md): first usable role-aware PWA surface and first-demo route.
