---
description: Implementation plan for Approved Governance Summary And Agent Context Isolation.
status: active
---
# IMPL-FT-015 Approved Governance Summary And Agent Context Isolation

## Goals

- Derive compact approved governance summaries from valid DecisionRecord records.
- Allow context builder retrieval only through scoped, redacted, authority-labeled records.
- Prevent raw governance/chat/UI content from entering agent context or memory.

## Constitution Check

- Aligns with Spec Before Code, Bounded Agent Autonomy, low-maintenance MVP scope, and risk-based DoD.
- No conflict found with the Constitution.
- Tier policy: tasks are T2/T3 according to data, context, security, privacy, access, and agent-contract impact.
- KISS boundary: implement bounded MVP records, services, and tests only; no broad workflow engine, SaaS, server sync, real fine-tuning, or automated actuation.

## Source Artifacts

- .memory-bank/features/FT-015-approved-governance-summary-and-agent-context-isolation.md
- .memory-bank/tech-specs/FT-015-approved-governance-summary-and-agent-context-isolation.md
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
- .memory-bank/tech-specs/FT-008-permission-aware-context-builder-and-agent-memory-record.md
- .memory-bank/tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md
- .memory-bank/tech-specs/FT-014-companion-issue-stack-human-attention-proposal-and-decision-record.md
- .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md

## Constraints

- Approved summary cannot mutate Plant state, create tasks by itself, authorize physical action, replace Safety Gate approval, or grant trainability.
- Context builder must exclude raw proposal/rationale/chat/UI/hidden reasoning/provider memory.
- Compaction and AgentMemoryRecord cannot upgrade forbidden content into trusted facts.

## Dependency Notes

- Depends on FT-014 DecisionRecord, FT-008 context builder, FT-009 Bus/UI isolation, and FT-017 redaction.
- All tasks remain planned because prerequisites are not done.

## Expected Touched Files

- backend/app/companion_governance/*
- backend/app/agent_context/*
- backend/app/agent_harness/*
- backend/app/publication/*
- backend/app/privacy/*
- backend/tests/companion/*
- backend/tests/agent_harness/*
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

- TASK-088: Implement ApprovedGovernanceSummary derivation schema from DecisionRecord.
- TASK-089: Implement governance summary context-builder retrieval filters.
- TASK-090: Implement governance summary MessageEnvelope, Bus, and UI projection handoff.
- TASK-091: Implement compaction and AgentMemory governance-summary boundaries.
- TASK-092: Implement governance summary access-change filtering and redacted diagnostics.
- TASK-093: Add governance summary anti-leak, context isolation, and integration coverage.
