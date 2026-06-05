---
description: Implementation plan for Dataset Governance And Local Storage Prompt.
status: active
---
# IMPL-FT-016 Dataset Governance And Local Storage Prompt

## Goals

- Create dataset candidate metadata and evidence-ref governance without full dataset registry.
- Keep trainability non-trainable by default and backend-policy computed.
- Implement local 200 MB storage prompt with no upload/server-sync implication.

## Constitution Check

- Aligns with Spec Before Code, Bounded Agent Autonomy, low-maintenance MVP scope, and risk-based DoD.
- No conflict found with the Constitution.
- Tier policy: tasks are T2/T3 according to data, context, security, privacy, access, and agent-contract impact.
- KISS boundary: implement bounded MVP records, services, and tests only; no broad workflow engine, SaaS, server sync, real fine-tuning, or automated actuation.

## Source Artifacts

- .memory-bank/features/FT-016-dataset-governance-and-local-storage-prompt.md
- .memory-bank/tech-specs/FT-016-dataset-governance-and-local-storage-prompt.md
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
- .memory-bank/tech-specs/FT-005-photo-intake-catalog-and-capture-manifests.md
- .memory-bank/tech-specs/FT-006-runtime-plant-state-history-and-timeline-audit.md
- .memory-bank/tech-specs/FT-008-permission-aware-context-builder-and-agent-memory-record.md
- .memory-bank/tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md
- .memory-bank/tech-specs/FT-013-tasks-approvals-and-follow-up-outcomes.md
- .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md

## Constraints

- can_train_on=true cannot be client-forced or agent-forced.
- UI Feed, timeline, manifests, raw agent output, AgentMemoryRecord, raw chat, and Bus events alone never grant trainability.
- sync.status remains local_only; server_verified/upload/cloud backup/server copy fields remain absent.
- Secret/auth material is redacted or rejected across dataset, export, prompt, Bus/UI, trace, and agent context surfaces.

## Dependency Notes

- Depends on photo/evidence/runtime/task/outcome/privacy foundations and FT-017 local_only/redaction tasks.
- All tasks remain planned because prerequisites are not done.

## Expected Touched Files

- backend/app/dataset_governance/*
- backend/app/storage/*
- backend/app/agent_harness/*
- backend/app/privacy/*
- backend/app/photo_intake/*
- backend/app/tasks/*
- backend/app/db/migrations/*
- backend/app/api/*
- backend/tests/dataset/*
- backend/tests/storage/*
- backend/tests/privacy/*
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

- TASK-094: Implement DatasetCandidate schema, lifecycle, and evidence refs.
- TASK-095: Implement trainability recomputation and transition guardrails.
- TASK-096: Implement Dataset Governance Agent proposal boundary and transition observations.
- TASK-097: Implement LocalStorageStatus measurement and 200 MB prompt state.
- TASK-098: Integrate dataset governance with FT-017 local-only privacy and redaction boundaries.
- TASK-099: Add dataset governance, storage prompt, privacy, and eval coverage.
