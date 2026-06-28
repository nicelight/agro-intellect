---
description: Testing and verification router for MVP v2 migration.
status: active
owner: quality
last_updated: 2026-06-26
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
  - .memory-bank/contracts/ui-feed.md
  - .memory-bank/contracts/timeline-event.md
  - .memory-bank/contracts/evidence-redaction.md
  - .memory-bank/states/plant-state-trust.md
  - .memory-bank/states/safety-action-lifecycle.md
  - .memory-bank/states/companion-governance.md
  - .memory-bank/states/dataset-governance.md
  - .memory-bank/foundation.md
  - .memory-bank/testing/foundation-test-harness.md
---
# Testing Index

## Current State

The active MVP v2 testing router has been rebuilt from the clarified PRD, `/prd` L1-L3 decomposition, and global `/spec-design` backbone.

MVP v1 testing docs are archived under
[.memory-bank/archive/mvp-v1/testing/](../archive/mvp-v1/testing/).

Concrete product endpoint schemas, DB migrations, state-machine fixtures,
detailed event/message payloads, and executable test names still belong to
feature-level SDD design inside `/prd-to-tasks` and later task decomposition.
Shared global contract/state owners now define the minimum boundaries for UI
Feed, timeline audit/export, photo artifacts, Plant state trust, Safety action
lifecycle, Companion governance, and dataset governance. The Foundation test
harness has its own substrate owner at
[.memory-bank/testing/foundation-test-harness.md](foundation-test-harness.md).
Standalone `/spec-improve` is reserved for repair or advanced refresh without
task generation.

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
- Product feature task decomposition must not start before global `/spec-design`, required Foundation closure, and feature-level SDD design completion inside `/prd-to-tasks FT-<NNN>`.
- Global `/spec-design` is complete; Foundation is closed and verified. Current product tasking gate is `/prd-to-tasks FT-<NNN>` followed by `/review-tasks-plan FT-<NNN>` before implementation.
- Runtime implementation later must include risk-based evidence: unit tests for policies/state, integration tests for boundaries/contracts, and e2e tests for real user flows.
- T2/T3 task records that touch shared state/contract boundaries must link the
  relevant owner: UI Feed, timeline audit/export, photo artifacts, Plant state
  trust, Safety action lifecycle, Companion governance, or dataset governance.

## Foundation Gate

Before product feature tasking, the required [.memory-bank/foundation.md](../foundation.md)
path was generated through `/foundation-to-tasks` and verified through the
final `FT-000` gate task.

Foundation harness details live in
[.memory-bank/testing/foundation-test-harness.md](foundation-test-harness.md).

Foundation evidence must prove:

- `task.schema.json`, `mb-lint`, and `mb-doctor` agree on `TASK-<NNN>-T<N>-FT-<NNN>-W<N>`, `tier`, optional `runtime_context`, and `FT-000/W0` semantics.
- Backend scaffold anchors exist for app factory, settings,
  database/session helpers, app factory extension point for future route
  registration, and tests proving import/start behavior; concrete product
  modules/packages belong to owning feature tasks.
- Linux Mint local bootstrap can create/use `.venv`, install project/test deps, prepare `.env` from `.env.example`, and verify Python/PostgreSQL tooling without printing secrets.
- Local PostgreSQL init is idempotent and produces actionable redacted failures when local prerequisites are missing.
- Alembic migration path can run against the configured local PostgreSQL database and is inspectable.
- `/health` and `/ready` pass; `/ready` proves configured DB connectivity when DB readiness is enabled.
- DB session and rollback-safe test session are verified.
- Local data/artifact root settings exist with `local_only` default semantics.
- Redaction tests cover `.env`, tokens, passwords, DB URLs with credentials, and auth material.
- `.venv/bin/python -m pytest tests`, `node scripts/mb-lint.mjs`, `node scripts/mb-doctor.mjs`, and `git diff --check` pass.

## Unit Test Areas

- Role preset, FarmMembership, PlantAccessGrant, and `plant_approve_actions` policy.
- ActorContext construction and fail-closed authorization.
- Plant archive/restore and retained-history policy.
- pH/EC provenance, freshness projections, and missing-data policy after specs define exact windows.
- Plant state trust promotion rules: hypotheses, conflicts, confirmed state, and review/evidence gates.
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
- Timeline replay cannot mutate runtime state or publish directly to Agent Chat Bus.
- UI Feed, timeline, and manifests cannot grant dataset trainability.
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
