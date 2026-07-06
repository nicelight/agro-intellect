---
description: Global risk-based testing strategy and cross-cutting verification rules for MVP v2.
status: active
type: testing_strategy
last_updated: 2026-07-06
source_of_truth:
  - .memory-bank/constitution.md
  - .memory-bank/invariants.md
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
---
# Testing Strategy

## Scope

This document defines stable, cross-cutting testing policy. Concrete endpoint
fixtures, feature-specific matrices, executable test names, and task-run
evidence belong to subject verification specs, code, and operational artifacts.

## Quality Gates

- Memory Bank changes pass `node scripts/mb-lint.mjs`.
- Readiness checks use `node scripts/mb-doctor.mjs` where the active workflow
  requires them.
- Diffs pass `git diff --check`.
- Implementation evidence is risk-based: unit tests cover policies and state,
  integration tests cover boundaries and contracts, and e2e tests cover real
  user flows.
- Changes to shared state or contract boundaries verify the applicable
  canonical domain, contract, state, and testing specifications.

## Unit Test Areas

- Role, membership, Plant access, and action-approval authority policies.
- Farm-scoped Plant creation permits active Boss/Engineer, denies
  Consultant/disabled membership, and does not widen Engineer lifecycle/access
  administration authority.
- ActorContext construction and fail-closed authorization.
- Plant lifecycle, retained-history, provenance, freshness, and trust rules.
- Archived-Plant policy leaves dependent records unchanged, denies all
  state-advancing commands, and makes restore require current guards.
- Runtime decision, MessageEnvelope validation, and publish/block behavior.
- Agent-context filtering and UI Feed isolation.
- Safety Gate classification, approval authority, and no-device-execution rules.
- Companion proposal and DecisionRecord authority boundaries.
- Dataset trainability defaults and evidence requirements.
- Secret redaction and local-storage threshold rules.

## Integration Test Areas

- Farm/Plant routes and context builders enforce backend authorization.
- Engineer Plant creation atomically persists the Plant, active creator grant
  with `plant_approve_actions=false`, and required audit records; failure leaves
  no partial state.
- Administrative mutations produce durable audit evidence.
- Photo intake preserves file, catalog, checksum, manifest, and timeline refs.
- PostgreSQL/read-model authority remains separate from timeline audit/export.
- Real model and vision adapters process actual scoped Plant data.
- Agent Chat Bus and UI Feed preserve consumability boundaries.
- Timeline replay cannot mutate runtime state or publish directly to the Bus.
- Safety approval remains separate from Companion governance decisions.
- Archive/restore contract tests span open tasks, approvals, follow-ups, and
  Companion proposals: no transition while archived and no automatic resume
  after restore.
- Dataset/export context stays Plant-scoped and non-trainable by default.
- Loopback/LAN, local-only, redaction, and storage-prompt controls hold.

## E2E Flow Areas

- Boss administration, Account creation, Plant access, and admin audit.
- Engineer authorized Plant selection, check-in, photo upload, measurements,
  history, tasks, approvals, and follow-up.
- Engineer creates a Plant, immediately selects it through the creator grant,
  and remains unable to archive/restore it or manage its grants.
- Real agent output through validated Bus/UI boundaries.
- Missing or stale evidence produces clarification instead of invented facts.
- Physical-action advice passes Safety Gate and authorized approval before a
  human-performed action task is created.
- Companion proposal/decision behavior does not authorize physical action.
- Plant archive/restore preserves authorized retained history.
- Plant archive/restore preserves grant identity/status/approval flags; active
  grants resume after restore and revoked grants remain denied.
- Plant archive with open operational/governance records preserves their state,
  blocks execution/decision/publication, and restore revalidates current
  authorization, version, freshness, Safety Gate, and governance rules.
- Local storage prompts do not imply upload or server availability.

## Anti-Cheat Rules

- Fake, mock, hardcoded, or stubbed product-agent outputs are test-only and do
  not satisfy runtime/demo acceptance.
- Test doubles remain visibly scoped to test fixtures and never become the
  runtime product-agent path.
- UI Feed, UI markdown, spoiler notes, raw chat, admin notices, unapproved
  proposals, and raw model reasoning never enter agent-context fixtures.
- Timeline replay, manifests, UI Feed, and raw agent output cannot override
  mutable runtime authority.
- DecisionRecord cannot count as Safety Gate approval, Plant-state evidence, or
  action unlock.
- Physical-action approval evidence proves fresh inputs, Safety Gate pass,
  authorized human approval, and human-performed task tracking.

## Risk Surfaces

- local identity, sessions, and authentication;
- Farm/Plant authorization and per-Plant access;
- admin audit and Boss administration;
- ActorContext propagation;
- Agent Chat Bus and UI Feed context hygiene;
- Companion governance and DecisionRecord semantics;
- Safety Gate approval and no automated actuation;
- dataset/export isolation by Farm and Plant.
