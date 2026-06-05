---
description: Pure SDD spec registry and planned-spec index.
status: active
owner: architecture
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/constitution.md
  - .memory-bank/prd.md
  - .memory-bank/spec-backbone.md
---
# SDD Spec Index

## Purpose
- Keep a concise registry of existing and planned SDD specs.
- Read this index before creating new specs or doing serious T2/T3 work.
- Keep readiness, open design questions, backbone status, and routing handoffs in [.memory-bank/spec-backbone.md](spec-backbone.md).
- Feature `spec_design_status` lives in feature frontmatter, not in this index.

## Spec Registry
| Spec | Type | Path | Status | Owner command | Scope |
|---|---|---|---|---|---|
| Project Constitution | governance | [.memory-bank/constitution.md](constitution.md) | active | /constitution | Top governing policy. |
| Invariants | invariants | [.memory-bank/invariants.md](invariants.md) | active | /spec-init or /spec-design | Global MUST/NEVER rules. |
| Glossary | glossary | [.memory-bank/glossary.md](glossary.md) | active | /spec-init or /spec-design | Shared MVP v2 vocabulary. |
| User Scenarios | scenarios | [.memory-bank/user-scenarios.md](user-scenarios.md) | active | /spec-init | Primary actors, core scenarios, out-of-scope scenarios, and decomposition implications. |
| Core Domain | domain | [.memory-bank/domains/core-domain.md](domains/core-domain.md) | active | /spec-init | Main entities, roles, business rules, lifecycle hints, and decomposition constraints. |
| Runtime Data Model | domain | [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md) | active | /spec-design | Runtime authority, storage ownership, and shared entity groups. |
| System Architecture | architecture | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md) | active | /spec-design | Global architecture style, module boundaries, data flow, deployment, and handoff rules. |
| Contracts Index | contracts | [.memory-bank/contracts/index.md](contracts/index.md) | active | /spec-design | Router for active MVP v2 contract specs. |
| API Guidelines | contract | [.memory-bank/contracts/api-guidelines.md](contracts/api-guidelines.md) | active | /spec-design | Frontend/backend API, auth, errors, uploads, CORS, and OpenAPI generation policy. |
| Agent Harness Contract | contract | [.memory-bank/contracts/agent-harness.md](contracts/agent-harness.md) | active | /spec-design | Shared AgentHarness, AgentProfile, tool/action, permission, memory, trace, and eval rules. |
| Agent Chat Bus Contract | contract | [.memory-bank/contracts/agent-chat-bus.md](contracts/agent-chat-bus.md) | active | /spec-design | BusEventEnvelope and agent-consumable working event rules. |
| Message Envelope Contract | contract | [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md) | active | /spec-design | MessageEnvelope, runtime decisions, UI Feed projection, and presentation isolation. |
| Safety Gate Contract | contract | [.memory-bank/contracts/safety-gate.md](contracts/safety-gate.md) | active | /spec-design | Physical-action advice, Safety Gate decision, human approval, and action_task unlock rules. |
| Core Lifecycles | states | [.memory-bank/states/core-lifecycles.md](states/core-lifecycles.md) | active | /spec-design | Global lifecycle states and transition guardrails for shared entities. |
| Tech Specs Index | tech_specs | [.memory-bank/tech-specs/index.md](tech-specs/index.md) | active | /spec-improve | Router for active feature-local SDD tech specs. |
| FT-001 Local Accounts, Sessions, And ActorContext Tech Spec | tech_spec | [.memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md](tech-specs/FT-001-local-accounts-sessions-and-actor-context.md) | active | /spec-improve | Feature-local auth/session, role preset, ActorContext, audit attribution, and redaction design. |
| FT-002 Farm, Plant Lifecycle, And PlantAccessGrant Tech Spec | tech_spec | [.memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md](tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md) | active | /spec-improve | Feature-local single-Farm, Plant archive/restore, retained history, and PlantAccessGrant design. |
| FT-003 Boss Admin Surface And Admin Audit Tech Spec | tech_spec | [.memory-bank/tech-specs/FT-003-boss-admin-surface-and-admin-audit.md](tech-specs/FT-003-boss-admin-surface-and-admin-audit.md) | active | /spec-improve | Feature-local Boss Admin Surface, privileged admin mutations, local add/invite, role/access changes, and durable AdminAuditRecord design. |
| FT-004 Authorized Plant Selector And Daily Check-In Tech Spec | tech_spec | [.memory-bank/tech-specs/FT-004-authorized-plant-selector-and-daily-check-in.md](tech-specs/FT-004-authorized-plant-selector-and-daily-check-in.md) | active | /spec-improve | Feature-local authorized Plant selector, CheckIn, observation/manual measurement, and backend Bus publication trigger design. |
| FT-005 Photo Intake, Catalog, And Capture Manifests Tech Spec | tech_spec | [.memory-bank/tech-specs/FT-005-photo-intake-catalog-and-capture-manifests.md](tech-specs/FT-005-photo-intake-catalog-and-capture-manifests.md) | active | /spec-improve | Feature-local photo upload validation, local storage, catalog, sha256, initial capture manifest, refs, and authorization design. |
| FT-006 Runtime Plant State, History, And Timeline Audit Tech Spec | tech_spec | [.memory-bank/tech-specs/FT-006-runtime-plant-state-history-and-timeline-audit.md](tech-specs/FT-006-runtime-plant-state-history-and-timeline-audit.md) | active | /spec-improve | Feature-local runtime Plant state, history projections, timeline event taxonomy, append-only audit/export refs, and authority separation design. |
| FT-007 Shared AgentHarness And AgentProfile Runtime Tech Spec | tech_spec | [.memory-bank/tech-specs/FT-007-shared-agent-harness-and-agent-profile-runtime.md](tech-specs/FT-007-shared-agent-harness-and-agent-profile-runtime.md) | active | /spec-improve | Feature-local shared AgentHarness loop, AgentProfile schema, typed tools, permissions, observations, traces, evals, and budget design. |
| FT-008 Permission-Aware Context Builder And AgentMemoryRecord Tech Spec | tech_spec | [.memory-bank/tech-specs/FT-008-permission-aware-context-builder-and-agent-memory-record.md](tech-specs/FT-008-permission-aware-context-builder-and-agent-memory-record.md) | active | /spec-improve | Feature-local context package, AgentMemoryRecord lifecycle/retrieval, trust labels, compaction, permission filtering, and memory non-authority design. |
| FT-009 MessageEnvelope, Agent Chat Bus, And UI Feed Isolation Tech Spec | tech_spec | [.memory-bank/tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md](tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md) | active | /spec-improve | Feature-local runtime decision, MessageEnvelope variants, Bus publication, UI Feed projection, context isolation, and anti-leak design. |
| FT-010 Real Model-Backed Product Agent Profiles Tech Spec | tech_spec | [.memory-bank/tech-specs/FT-010-real-model-backed-product-agent-profiles.md](tech-specs/FT-010-real-model-backed-product-agent-profiles.md) | active | /spec-improve | Feature-local real model-backed runtime/demo profiles, provider adapters, vision-over-actual-photo behavior, test-only mock boundaries, failure handling, and launch gates. |
| FT-011 Plant State Trust And Hydroponics Advisor Tech Spec | tech_spec | [.memory-bank/tech-specs/FT-011-plant-state-trust-and-hydroponics-advisor.md](tech-specs/FT-011-plant-state-trust-and-hydroponics-advisor.md) | active | /spec-improve | Feature-local Plant State trust mapping, freshness handoff, missing/stale-data behavior, advisor output contract, and Safety Gate routing design. |
| FT-012 Safety Gate For Physical-Action Advice Tech Spec | tech_spec | [.memory-bank/tech-specs/FT-012-safety-gate-for-physical-action-advice.md](tech-specs/FT-012-safety-gate-for-physical-action-advice.md) | active | /spec-improve | Feature-local Safety Gate routing, physical-action taxonomy, fail-closed decisions, approval eligibility, and safe wording design. |
| FT-013 Tasks, Approvals, And Follow-Up Outcomes Tech Spec | tech_spec | [.memory-bank/tech-specs/FT-013-tasks-approvals-and-follow-up-outcomes.md](tech-specs/FT-013-tasks-approvals-and-follow-up-outcomes.md) | active | /spec-improve | Feature-local check/measurement/follow-up tasks, approvals, human-performed action_task unlock, outcomes, and audit design. |
| FT-014 Companion IssueStack, HumanAttention, Proposal, And DecisionRecord Tech Spec | tech_spec | [.memory-bank/tech-specs/FT-014-companion-issue-stack-human-attention-proposal-and-decision-record.md](tech-specs/FT-014-companion-issue-stack-human-attention-proposal-and-decision-record.md) | active | /spec-improve | Feature-local Companion governance typed state, proposal supersede policy, DecisionRecord authority limits, safe workflow effects, and audit/context boundaries. |
| FT-015 Approved Governance Summary And Agent Context Isolation Tech Spec | tech_spec | [.memory-bank/tech-specs/FT-015-approved-governance-summary-and-agent-context-isolation.md](tech-specs/FT-015-approved-governance-summary-and-agent-context-isolation.md) | active | /spec-improve | Feature-local approved governance summary schema, derivation from DecisionRecord, context filtering, permission retrieval, and anti-leak tests. |
| FT-016 Dataset Governance And Local Storage Prompt Tech Spec | tech_spec | [.memory-bank/tech-specs/FT-016-dataset-governance-and-local-storage-prompt.md](tech-specs/FT-016-dataset-governance-and-local-storage-prompt.md) | active | /spec-improve | Feature-local dataset candidate lifecycle, evidence refs, can_train_on guardrails, Dataset Governance Agent boundary, and 200 MB local storage prompt design. |
| FT-017 Local Privacy, Deployment Controls, And Secret Redaction Tech Spec | tech_spec | [.memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md](tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md) | active | /spec-improve | Feature-local loopback/LAN, local_only sync, and secret redaction design. |
| Boundary Map | boundary_hints | [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md) | active | /spec-init | Preliminary boundary hints retained as framing evidence. |
| Lifecycle Map | lifecycle_hints | [.memory-bank/states/lifecycle-map.md](states/lifecycle-map.md) | active | /spec-init | Pre-PRD lifecycle hints retained as decomposition evidence. |
| Testing Index | testing | [.memory-bank/testing/index.md](testing/index.md) | active | /spec-design | Verification strategy, global test contract map, and harness eval requirements. |

## Planned Specs
| Area | Expected path | Needed by | Notes |
|---|---|---|---|
| feature_design | .memory-bank/tech-specs/FT-<NNN>-<slug>.md | /spec-improve | Feature-local specs only when needed before task decomposition. |
| generated_openapi | implementation-generated OpenAPI artifact | feature implementation | Generated from FastAPI/Pydantic once backend schemas exist; not hand-written before feature design. |

## Broken / Missing Links
- No known broken links recorded by `/spec-design`.

## Update Rules
- Keep this file as index/registry only: names, paths, statuses, owners, scopes, and broken links.
- Do not add global backbone status, backbone matrices, feature status maps, long hard rules, or open design question dumps here.
- Use [.memory-bank/spec-backbone.md](spec-backbone.md) for pre-PRD readiness, decomposition inputs, global backbone status, matrix, and handoffs.
- Use linked specs or ADRs for detailed decisions, rationale, contracts, state transitions, schemas, invariants, and testing rules.
