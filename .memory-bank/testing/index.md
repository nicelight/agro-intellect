---
description: Testing and verification router for MVP v2 migration.
status: active
owner: quality
last_updated: 2026-06-23
source_of_truth:
  - .memory-bank/constitution.md
  - .memory-bank/invariants.md
  - .memory-bank/spec-index.md
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/contracts/foundation-critical-path.md
---
# Testing Index

## Current State

The active MVP v2 testing router has been rebuilt from the clarified PRD, `/prd` L1-L3 decomposition, and global `/spec-design` backbone.

MVP v1 testing docs are archived under
[.memory-bank/archive/mvp-v1/testing/](../archive/mvp-v1/testing/).

Concrete endpoint schemas, DB migrations, state-machine fixtures, detailed event/message payloads, and executable test names still belong to feature-level `/spec-improve` and later task decomposition.

## Migration Gates

After Memory Bank routing or spec-layer changes, run:

```bash
node scripts/mb-lint.mjs
node scripts/mb-doctor.mjs
git diff --check
```

After `/prd` and `/spec-design`, run fresh-context Memory Bank review before task decomposition.

## Quality Gates

- Memory Bank docs must pass `node scripts/mb-lint.mjs`.
- Readiness before autonomous/task selection must pass `node scripts/mb-doctor.mjs`.
- Diffs must pass `git diff --check`.
- Product feature task decomposition must not start before global `/spec-design`, required Foundation closure, and the relevant `/spec-improve FT-<NNN>`.
- Global `/spec-design` is complete; current pre-product-task gate is `/foundation-to-tasks`, foundation `/mb-doctor`, and final `FT-000` gate closure.
- Runtime implementation later must include risk-based evidence: unit tests for policies/state, integration tests for boundaries/contracts, and e2e tests for real user flows.

## Foundation Critical Path Gate

Before product feature tasking, the required [.memory-bank/foundation.md](../foundation.md) path must be generated through `/foundation-to-tasks` and verified through the final `FT-000` gate task. The executable contract is [.memory-bank/contracts/foundation-critical-path.md](../contracts/foundation-critical-path.md).

Foundation evidence must prove:

- Photo/User input creates authorized source refs and a valid BusEventEnvelope.
- Agent invocation goes through a project-owned adapter and runtime decision boundary.
- MessageEnvelope and UIFeedEvent projection are separate; UI Feed projection is not consumed by agents.
- Safety/State/Task transitions fail closed for physical-action implication.
- PostgreSQL/read model, `timeline.jsonl`, and photo JSON export are produced as separate authority/audit/export artifacts.
- Secret/auth material and raw provider output do not appear in logs, Bus, UI Feed, timeline, screenshots, or export artifacts.
- Test-only stubs remain scoped to tests and cannot satisfy MVP runtime/demo acceptance.
- `C-FND-001` through `C-FND-009` in the Foundation Critical Path contract are satisfied by linked task evidence.

## Unit Test Areas

- Role preset, FarmMembership, PlantAccessGrant, and `plant_approve_actions` policy.
- ActorContext construction and fail-closed authorization.
- Plant archive/restore and retained-history policy.
- pH/EC provenance, freshness projections, and missing-data policy after specs define exact windows.
- Runtime decision, MessageEnvelope validation, and publish/block rules.
- Context filtering: UI Feed, raw chat, spoiler notes, admin notices, and unapproved proposals excluded from agent working context.
- Safety Gate classification, freshness, authority checks, and no-device-execution rules.
- CompanionProposal supersede behavior and DecisionRecord authority boundaries.
- Dataset trainability default false and evidence-ref requirements.
- Secret redaction and local storage threshold rules.

## Integration Test Areas

- Every Farm/Plant route and context builder enforces ActorContext and backend authorization.
- Boss Admin mutations create durable AdminAuditRecord entries.
- Photo upload creates local file, catalog row, checksum, initial capture manifest, and timeline refs.
- Runtime state remains PostgreSQL/read-model authority while timeline remains append-only audit/export.
- Real model-backed product-agent adapter path runs over actual scoped Plant data.
- Vision Observation processes actual uploaded photo data through a real vision-capable model or real vision integration.
- Agent Chat Bus and UI Feed projections preserve consumability boundaries.
- Safety Gate separates governance approval from physical-action approval.
- Companion DecisionRecord produces only compact approved governance summary facts.
- Dataset/export context stays Plant-scoped and non-trainable by default.
- Loopback/LAN controls, `local_only`, redaction, and 200 MB prompt behavior.

## E2E / Flow Tests

- Boss creates or uses the local Farm, adds an Engineer, grants `tomato_001` access, and sees admin audit.
- Engineer logs in, sees only assigned Plants, selects `tomato_001`, completes daily check-in, uploads a photo, enters pH/EC, and sees Plant history.
- Real agent outputs appear through validated Bus/UI boundaries and not from runtime stubs.
- Missing/stale pH/EC produces a safe measurement request or clarification, not invented evidence.
- Physical-action advice routes through Safety Gate and authorized approval before creating a human-performed action task.
- Follow-up outcome preserves evidence and audit trail.
- Companion HumanAttentionNeeded, proposal, supersede/decision behavior is visible without authorizing physical actions.
- Archived Plant disappears from normal operations but retained history remains authorized.
- Storage prompt appears over 200 MB without upload/server implication.

## Anti-Cheat Rules

- Fake, mock, hardcoded, or stubbed product-agent outputs are allowed only in automated tests and never satisfy MVP runtime/demo acceptance.
- Test mocks must be visibly scoped to test fixtures and must not be wired as the runtime/demo product-agent path.
- UI Feed, UI markdown, spoiler notes, raw chat, admin notices, unapproved proposals, and raw model reasoning must not appear in agent context fixtures.
- Timeline replay, photo manifests, UI Feed, and raw agent output cannot override PostgreSQL/read-model runtime authority.
- Governance DecisionRecord cannot be counted as Safety Gate approval, Plant-state evidence, or action unlock.
- Any test/evidence claiming physical-action approval must prove fresh data, Safety Gate pass, authorized human approval, and human-performed task tracking.

## MVP v2 Risk Surfaces

- local account/session/authentication behavior;
- farm/plant authorization and per-Plant access;
- admin audit and Boss admin workflows;
- ActorContext propagation through APIs and workflows;
- Agent Chat Bus and UI Feed permission/context hygiene;
- Companion governance state and `DecisionRecord` semantics;
- Safety Gate approval roles and no automated physical actuation;
- dataset/export isolation by Farm/Plant context.
