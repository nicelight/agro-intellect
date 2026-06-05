---
description: Implementation plan for FT-008 Permission-Aware Context Builder And AgentMemoryRecord.
status: active
---
# IMPL-FT-008 Permission-Aware Context Builder And AgentMemoryRecord

## Goals

- Implement the only allowed route for product-agent context assembly.
- Persist and retrieve AgentMemoryRecord entries as scoped, source-ref backed,
  permission-aware, auditable, stale-aware, non-authoritative memory.
- Preserve active objective, approvals, scope, source refs, memory refs, trust/freshness
  labels, trace refs, and budget telemetry through compaction.

## Constitution Check

- Aligns with Spec Before Code, bounded agent autonomy, Memory Bank durability,
  schema-backed task execution, and stability-first treatment for agent-contract
  boundaries.
- No conflict found with the Constitution.
- Tier policy: all slices are T3 because context and memory are authorization,
  redaction, prompt-injection, source-of-truth, and Safety Gate bypass surfaces.
- KISS boundary: source-ref backed PostgreSQL/local-table memory and deterministic
  retrieval first; no broad RAG, vector database, external connector memory, or hidden
  provider memory authority.

## Source Artifacts

- .memory-bank/features/FT-008-permission-aware-context-builder-and-agent-memory-record.md
- .memory-bank/tech-specs/FT-008-permission-aware-context-builder-and-agent-memory-record.md
- .memory-bank/epics/EP-003-shared-agent-harness-and-context-boundaries.md
- .memory-bank/requirements.md
- .tasks/SPEC-IMPROVE-REVIEW/final-report.md
- .tasks/SPEC-IMPROVE-REVIEW-FIXES/final-report.md

## Normative Inputs

- .memory-bank/contracts/agent-harness.md
- .memory-bank/contracts/agent-chat-bus.md
- .memory-bank/contracts/message-envelope.md
- .memory-bank/contracts/safety-gate.md
- .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
- .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
- .memory-bank/tech-specs/FT-006-runtime-plant-state-history-and-timeline-audit.md
- .memory-bank/tech-specs/FT-007-shared-agent-harness-and-agent-profile-runtime.md
- .memory-bank/tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md
- .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
- .memory-bank/architecture/system-architecture.md
- .memory-bank/domains/runtime-data-model.md
- .memory-bank/states/core-lifecycles.md
- .memory-bank/testing/index.md
- agents-best-practices: context is assembled just in time, memory is scoped and
  source-ref backed, untrusted content remains labeled as data, compaction is an
  operational handoff, stable context comes before volatile context, and traces/evals
  prove permission, redaction, budget, and false-authority behavior.

## Constraints

- Context builder resolves ActorContext before any context lookup.
- Context retrieval filters by Farm, Plant, PlantAccessGrant, AgentProfile,
  source-family allowlist, trust/freshness labels, redaction status, and evidence refs.
- AgentMemoryRecord starts as `candidate` and becomes retrievable only after validation.
- Memory stores bounded summaries/structured refs, never raw transcripts, raw provider
  output, hidden reasoning, UI Feed text, secrets, auth material, or oversized blobs.
- Compaction cannot erase permissions, approval state, active objective, source refs,
  trust/freshness labels, or denial/blocker state.

## Invariants

- Hidden provider memory, raw chat history, UI Feed replay, unapproved governance
  content, raw model reasoning, Agno events, and unauthorized data never enter agent
  working context.
- AgentMemoryRecord cannot confirm Plant state, unlock Safety Gate, create
  `action_task`, approve governance, or change dataset trainability.
- Compaction and memory activation never upgrade trust labels or authority roles.
- Revoked PlantAccessGrant blocks future memory retrieval without deleting retained
  audit/evidence.

## Steps

1. Define AgentContextPackage schemas and permission-aware assembly service boundary.
2. Add AgentMemoryRecord persistence, lifecycle fields, audit refs, and non-authority
   metadata.
3. Implement permission-aware memory retrieval and forbidden-source filtering.
4. Implement compaction handoff, cache-aware ordering, context-size/source-count/budget
   telemetry, and trace refs.
5. Add memory write validation, activation, stale/supersede/archive/reject APIs, and
   trace evidence.
6. Add context/memory/compaction integration, redaction, prompt-injection, and eval
   coverage.

## Expected Touched Files

- backend/app/agent_harness/*
- backend/app/context/*
- backend/app/memory/*
- backend/app/access/*
- backend/app/runtime_state/*
- backend/app/publication/*
- backend/app/privacy/*
- backend/app/db/migrations/*
- backend/app/api/*
- backend/tests/agent_harness/*
- backend/tests/context/*
- backend/tests/memory/*
- backend/tests/integration/*
- backend/tests/security/*
- .memory-bank/changelog.md

## Tests

- Unit: AgentContextPackage schema validation, source-family allowlists, trust/freshness
  labels, AgentMemoryRecord lifecycle transitions, write validation, stale/supersede
  rules, compaction payload shape, and deterministic context ordering.
- Integration: ActorContext/PlantAccessGrant filtering, revoked grant memory exclusion,
  runtime/photo/timeline/Bus refs as evidence only, and memory retrieval scope.
- Security/context: UI Feed, spoiler notes, raw chat, raw provider output, hidden
  reasoning, Agno events, unapproved proposals, admin UI text, and secrets cannot enter
  context or memory.
- Harness evals: prompt injection in retrieved/uploaded/user content, context overflow,
  compaction retention, memory non-authority, redaction failure, and budget stop.

## Quality Gates

- pytest backend/tests/context backend/tests/memory backend/tests/agent_harness backend/tests/integration backend/tests/security
- Harness eval fixture evidence through the task-specific pytest/eval suite and /red-verify semantic-pass
- generated OpenAPI validation after implementation schemas exist
- node scripts/mb-lint.mjs
- node scripts/mb-doctor.mjs
- /verify and /red-verify before T3 closure
- T3 human checkpoint and rollback/recovery note before closure

## UAT Steps

- Authorized Plant State run builds context containing only scoped runtime/evidence refs
  and allowed memory.
- Revoked PlantAccessGrant blocks future memory retrieval.
- Stale memory appears only as labeled historical context when explicitly allowed.
- Compaction preserves objective, ActorContext, PlantAccessGrant scope, approvals,
  source refs, memory refs, trust/freshness labels, trace refs, and safe next action.

## Task Slice

- TASK-053: AgentContextPackage schemas and permission-aware assembly boundary.
- TASK-054: AgentMemoryRecord persistence, lifecycle, and non-authority metadata.
- TASK-055: Permission-aware memory retrieval and forbidden-source filtering.
- TASK-056: Context compaction handoff and cache-aware ordering telemetry.
- TASK-057: Memory write validation, activation, stale/supersede/archive APIs.
- TASK-058: Context/memory/compaction regression and eval coverage.
