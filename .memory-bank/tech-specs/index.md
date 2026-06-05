---
description: Router for active feature-local SDD tech specs.
status: active
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/spec-index.md
  - .memory-bank/features/index.md
  - .memory-bank/spec-backbone.md
---
# Tech Specs Index

## Purpose

Route active feature-local SDD tech specs created by `/spec-improve`. These specs refine
the global backbone for task decomposition without replacing architecture, domain,
contract, state, or testing specs.

## Wave 1 Feature Specs

- [FT-001 Local Accounts, Sessions, And ActorContext](FT-001-local-accounts-sessions-and-actor-context.md): local Account/session baseline, FarmMembership, role presets, ActorContext, audit attribution, and auth-material redaction.
- [FT-002 Farm, Plant Lifecycle, And PlantAccessGrant](FT-002-farm-plant-lifecycle-and-plant-access-grant.md): one local Farm, `tomato_001`, Plant archive/restore, retained history, and per-Plant access grants.
- [FT-017 Local Privacy, Deployment Controls, And Secret Redaction](FT-017-local-privacy-deployment-controls-and-secret-redaction.md): loopback/LAN controls, `local_only` sync, forbidden server-sync semantics, and redaction across product/agent/export surfaces.

## Wave 2 Feature Specs

- [FT-003 Boss Admin Surface And Admin Audit](FT-003-boss-admin-surface-and-admin-audit.md): Boss-only admin surface, local account add/invite, role and access changes, Plant lifecycle entry points, and durable AdminAuditRecord.
- [FT-004 Authorized Plant Selector And Daily Check-In](FT-004-authorized-plant-selector-and-daily-check-in.md): authorized active Plant selector, CheckIn lifecycle, observations, manual pH/EC/no-data handling, and backend Bus publication refs.
- [FT-005 Photo Intake, Catalog, And Capture Manifests](FT-005-photo-intake-catalog-and-capture-manifests.md): authorized photo upload validation, local file/catalog/sha256, initial capture manifest, timeline/export refs, and failure ordering.

## Wave 3 Feature Specs

- [FT-006 Runtime Plant State, History, And Timeline Audit](FT-006-runtime-plant-state-history-and-timeline-audit.md): runtime Plant state authority, history projections, timeline event taxonomy, append-only audit/export refs, and artifact/UI non-authority.
- [FT-007 Shared AgentHarness And AgentProfile Runtime](FT-007-shared-agent-harness-and-agent-profile-runtime.md): shared harness loop, AgentProfile runtime, narrow tools, permission matrix, structured observations, traces, evals, and budgets.
- [FT-009 MessageEnvelope, Agent Chat Bus, And UI Feed Isolation](FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md): runtime decisions, MessageEnvelope variants, Bus publication mapping, UI Feed projection, context isolation, and anti-leak tests.

## Wave 4 Feature Specs

- [FT-008 Permission-Aware Context Builder And AgentMemoryRecord](FT-008-permission-aware-context-builder-and-agent-memory-record.md): context package assembly, AgentMemoryRecord lifecycle/retrieval, trust/freshness labels, compaction handoff, and memory non-authority.
- [FT-010 Real Model-Backed Product Agent Profiles](FT-010-real-model-backed-product-agent-profiles.md): real model-backed runtime/demo profiles, provider adapters, vision over actual uploaded photos, test-only mock boundaries, and first-demo evidence gates.
- [FT-011 Plant State Trust And Hydroponics Advisor](FT-011-plant-state-trust-and-hydroponics-advisor.md): Plant State trust mapping, pH/EC freshness handoff, missing/stale-data behavior, advisor output contract, and Safety Gate routing.

## Wave 5 Feature Specs

- [FT-012 Safety Gate For Physical-Action Advice](FT-012-safety-gate-for-physical-action-advice.md): Safety Gate routing, physical-action taxonomy, proposal shape, fail-closed decisions, approval eligibility, safe wording, and safety evals.
- [FT-013 Tasks, Approvals, And Follow-Up Outcomes](FT-013-tasks-approvals-and-follow-up-outcomes.md): check, measurement, follow-up, and approved action task records; Approval records; exact action_task unlock; follow-up Outcome semantics; audit refs.

## Wave 6 Feature Specs

- [FT-014 Companion IssueStack, HumanAttention, Proposal, And DecisionRecord](FT-014-companion-issue-stack-human-attention-proposal-and-decision-record.md): Companion governance typed state, proposal supersede policy, DecisionRecord authority limits, safe workflow effects, and audit/context boundaries.
- [FT-015 Approved Governance Summary And Agent Context Isolation](FT-015-approved-governance-summary-and-agent-context-isolation.md): approved governance summary schema, DecisionRecord derivation, context-builder filtering, permissioned retrieval, and raw governance/chat/UI anti-leak tests.
- [FT-016 Dataset Governance And Local Storage Prompt](FT-016-dataset-governance-and-local-storage-prompt.md): DatasetCandidate lifecycle, evidence refs, `can_train_on` guardrails, Dataset Governance Agent boundary, and 200 MB local storage prompt behavior.

## Routing Rules

- Read [.memory-bank/spec-index.md](../spec-index.md) and
  [.memory-bank/spec-backbone.md](../spec-backbone.md) before adding new specs.
- Keep shared/global decisions in their natural shared specs.
- Use feature-local specs only for exact feature design needed before
  `/prd-to-tasks FT-<NNN>`.
