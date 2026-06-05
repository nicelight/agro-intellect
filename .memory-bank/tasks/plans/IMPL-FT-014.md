---
description: Implementation plan for Companion IssueStack, HumanAttention, Proposal, And DecisionRecord.
status: active
---
# IMPL-FT-014 Companion IssueStack, HumanAttention, Proposal, And DecisionRecord

## Goals

- Create typed Plant-scoped Companion governance state.
- Enforce proposal versioning, supersede, and DecisionRecord semantics.
- Keep governance approval separate from Safety Gate and physical-action approval.

## Constitution Check

- Aligns with Spec Before Code, Bounded Agent Autonomy, low-maintenance MVP scope, and risk-based DoD.
- No conflict found with the Constitution.
- Tier policy: tasks are T2/T3 according to data, context, security, privacy, access, and agent-contract impact.
- KISS boundary: implement bounded MVP records, services, and tests only; no broad workflow engine, SaaS, server sync, real fine-tuning, or automated actuation.

## Source Artifacts

- .memory-bank/features/FT-014-companion-issue-stack-human-attention-proposal-and-decision-record.md
- .memory-bank/tech-specs/FT-014-companion-issue-stack-human-attention-proposal-and-decision-record.md
- .memory-bank/requirements.md
- .tasks/SPEC-IMPROVE-REVIEW/final-report.md
- .tasks/SPEC-IMPROVE-REVIEW-FIXES/final-report.md

## Normative Inputs

- .memory-bank/constitution.md
- .memory-bank/invariants.md
- .memory-bank/architecture/system-architecture.md
- .memory-bank/domains/runtime-data-model.md
- .memory-bank/states/core-lifecycles.md
- .memory-bank/contracts/api-guidelines.md
- .memory-bank/contracts/agent-harness.md
- .memory-bank/contracts/agent-chat-bus.md
- .memory-bank/contracts/message-envelope.md
- .memory-bank/testing/index.md
- agents-best-practices
- .memory-bank/contracts/safety-gate.md
- .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
- .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
- .memory-bank/tech-specs/FT-007-shared-agent-harness-and-agent-profile-runtime.md
- .memory-bank/tech-specs/FT-008-permission-aware-context-builder-and-agent-memory-record.md
- .memory-bank/tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md
- .memory-bank/tech-specs/FT-012-safety-gate-for-physical-action-advice.md
- .memory-bank/tech-specs/FT-013-tasks-approvals-and-follow-up-outcomes.md
- .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md

## Constraints

- Companion governance state is explicit backend state, not hidden prompt memory.
- DecisionRecord cannot mutate Plant state, create action_task, authorize physical action, replace Safety Gate approval, grant trainability, or turn raw chat into fact.
- Raw proposal text, rationale, chat, UI markdown, hidden reasoning, and secrets remain non-consumable by agents.

## Dependency Notes

- Depends on ActorContext, PlantAccessGrant, shared harness, MessageEnvelope/Bus/UI isolation, redaction, and safe task services.
- All tasks remain planned because prerequisites are not done.

## Expected Touched Files

- backend/app/companion_governance/*
- backend/app/agent_harness/*
- backend/app/publication/*
- backend/app/access/*
- backend/app/privacy/*
- backend/app/db/migrations/*
- backend/app/api/*
- backend/tests/companion/*
- backend/tests/integration/*
- frontend/src/*
- .memory-bank/changelog.md

## Quality Gates

- Relevant pytest suites once backend exists.
- Frontend smoke/e2e command once UI exists.
- Harness eval fixtures where agent/context behavior is in scope.
- Generated OpenAPI validation after implementation schemas exist.
- node scripts/mb-lint.mjs
- node scripts/mb-doctor.mjs
- /verify and /red-verify before T2/T3 closure, with T3 human checkpoint and rollback/recovery where required.

## Task Slice

- TASK-082: Implement Companion IssueStack and HumanAttention typed state.
- TASK-083: Implement CompanionProposal versioning and supersede policy.
- TASK-084: Implement DecisionRecord authorization and authority limits.
- TASK-085: Implement allowed governance workflow effects and safe task request handoffs.
- TASK-086: Publish Companion governance audit, Bus, and UI refs without raw content leaks.
- TASK-087: Add Companion governance integration, eval, and UI smoke coverage.
