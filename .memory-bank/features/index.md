---
description: Router for active MVP v2 features derived from the clarified PRD.
status: draft
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/epics/index.md
---
# Features Index

## EP-001 Local Farm Access And Admin

- [FT-001 Local Accounts, Sessions, And ActorContext](FT-001-local-accounts-sessions-and-actor-context.md)
- [FT-002 Farm, Plant Lifecycle, And PlantAccessGrant](FT-002-farm-plant-lifecycle-and-plant-access-grant.md)
- [FT-003 Boss Admin Surface And Admin Audit](FT-003-boss-admin-surface-and-admin-audit.md)

## EP-002 Plant Evidence And Runtime Authority

- [FT-004 Authorized Plant Selector And Daily Check-In](FT-004-authorized-plant-selector-and-daily-check-in.md)
- [FT-005 Photo Intake, Catalog, And Capture Manifests](FT-005-photo-intake-catalog-and-capture-manifests.md)
- [FT-006 Runtime Plant State, History, And Timeline Audit](FT-006-runtime-plant-state-history-and-timeline-audit.md)

## EP-003 Shared Agent Harness And Context Boundaries

- [FT-007 Shared AgentHarness And AgentProfile Runtime](FT-007-shared-agent-harness-and-agent-profile-runtime.md)
- [FT-008 Permission-Aware Context Builder And AgentMemoryRecord](FT-008-permission-aware-context-builder-and-agent-memory-record.md)
- [FT-009 MessageEnvelope, Agent Chat Bus, And UI Feed Isolation](FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md)
- [FT-010 Real Model-Backed Product Agent Profiles](FT-010-real-model-backed-product-agent-profiles.md)

## EP-004 Safety-Gated Advisory And Task Loop

- [FT-011 Plant State Trust And Hydroponics Advisor](FT-011-plant-state-trust-and-hydroponics-advisor.md)
- [FT-012 Safety Gate For Physical-Action Advice](FT-012-safety-gate-for-physical-action-advice.md)
- [FT-013 Tasks, Approvals, And Follow-Up Outcomes](FT-013-tasks-approvals-and-follow-up-outcomes.md)

## EP-005 Companion Governance

- [FT-014 Companion IssueStack, HumanAttention, Proposal, And DecisionRecord](FT-014-companion-issue-stack-human-attention-proposal-and-decision-record.md)
- [FT-015 Approved Governance Summary And Agent Context Isolation](FT-015-approved-governance-summary-and-agent-context-isolation.md)

## EP-006 Dataset Privacy And Local Deployment

- [FT-016 Dataset Governance And Local Storage Prompt](FT-016-dataset-governance-and-local-storage-prompt.md)
- [FT-017 Local Privacy, Deployment Controls, And Secret Redaction](FT-017-local-privacy-deployment-controls-and-secret-redaction.md)

Global `/spec-design` is complete. Run feature-level `/spec-improve FT-<NNN>` before
`/prd-to-tasks FT-<NNN>`.
