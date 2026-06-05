---
description: Implementation plan for FT-009 MessageEnvelope, Agent Chat Bus, And UI Feed Isolation.
status: active
---
# IMPL-FT-009 MessageEnvelope, Agent Chat Bus, And UI Feed Isolation

## Goals

- Adapt AgentHarness output into exactly one project-owned runtime decision before any
  publication.
- Validate MessageEnvelope payloads, publish only allowed BusEventEnvelope refs, and
  project human-facing UIFeedEvent records without making UI Feed agent context.
- Prove raw provider output, raw chat, UI text, spoiler notes, unapproved proposals,
  admin markdown, timeline replay, Agno events, and secrets cannot bypass adapters into
  Bus or agent working context.

## Constitution Check

- Aligns with Spec Before Code, Bounded Agent Autonomy, local privacy, Safety Gate
  separation, and stability-first handling for Agent Chat Bus, MessageEnvelope, and UI
  Feed isolation.
- No conflict found with the Constitution.
- Tier policy: all slices are T3 because this is an agent publication/context
  isolation, redaction, and safety-sensitive boundary.
- KISS boundary: implement first-demo envelope variants and projection refs only; no
  full Safety Gate/task-loop implementation, real provider selection, or context-memory
  system outside owning features.

## Source Artifacts

- .memory-bank/features/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md
- .memory-bank/tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md
- .memory-bank/epics/EP-003-shared-agent-harness-and-context-boundaries.md
- .memory-bank/requirements.md
- .tasks/SPEC-IMPROVE-REVIEW/final-report.md
- .tasks/SPEC-IMPROVE-REVIEW-FIXES/final-report.md

## Normative Inputs

- .memory-bank/contracts/message-envelope.md
- .memory-bank/contracts/agent-chat-bus.md
- .memory-bank/contracts/agent-harness.md
- .memory-bank/contracts/safety-gate.md
- .memory-bank/tech-specs/FT-006-runtime-plant-state-history-and-timeline-audit.md
- .memory-bank/tech-specs/FT-007-shared-agent-harness-and-agent-profile-runtime.md
- .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
- .memory-bank/architecture/system-architecture.md
- .memory-bank/domains/runtime-data-model.md
- .memory-bank/states/core-lifecycles.md
- .memory-bank/testing/index.md
- agents-best-practices: raw model output is data; publication is validated,
  permissioned, traced, redacted, bounded, and separated from UI presentation.

## Constraints

- Raw provider output alone cannot choose publication authority.
- `silent` creates trace/eval evidence but no MessageEnvelope and no Bus event.
- Bus payloads use `consumable_output` and structured fields, not UI projection text.
- `trusted` Bus payloads are reserved for backend-owned policy, approval/decision, and
  approved governance-summary facts.
- UI Feed events must have `visible_to_agents=false` and `consumable_by_agents=false`.
- Physical-action wording routes through Safety Gate before user-visible action wording
  or action-task creation.

## Invariants

- UI Feed, spoiler notes, raw chat, raw provider output, hidden reasoning, raw Agno
  events, unapproved CompanionProposal content, admin UI text, timeline replay, and
  secrets are forbidden agent context sources.
- MessageEnvelope validation rejects, downgrades, escalates, or records malformed,
  overlong, unsafe, out-of-profile, or secret-containing output before publication.
- Duplicate publication attempts are rejected or idempotently ignored by message/event
  refs.
- Pre-clearance physical-action wording must not be published to agent-consumable Bus
  context.

## Steps

1. Build runtime decision adapter and MessageEnvelope validation schemas.
2. Persist speak/silent/clarify/escalate decision evidence and trace refs.
3. Publish MessageEnvelope-derived BusEventEnvelope records with trust labels and
   idempotency.
4. Project MessageEnvelope/domain refs to UI Feed and authorized human feed reads.
5. Add context-filter anti-leak gates for UI Feed/raw/admin/unapproved sources.
6. Add integration, Safety Gate pre-clearance routing, OpenAPI, and e2e smoke coverage.

## Expected Touched Files

- backend/app/publication/*
- backend/app/agent_harness/*
- backend/app/runtime_state/*
- backend/app/access/*
- backend/app/safety/*
- backend/app/db/migrations/*
- backend/app/api/*
- frontend/src/*
- backend/tests/publication/*
- backend/tests/agent_harness/*
- backend/tests/integration/*
- backend/tests/security/*
- frontend/tests/*
- .memory-bank/changelog.md

## Tests

- Unit: runtime decision mapping, MessageEnvelope validation, redaction, overlong
  output handling, trust-label mapping, and duplicate event idempotency.
- Integration: raw output cannot bypass MessageEnvelope, silent decision trace/no Bus,
  Bus publication refs, UI Feed projection isolation, context-filter forbidden sources,
  and Safety Gate pre-clearance routing.
- Contract: generated OpenAPI validation, MessageEnvelope and BusEventEnvelope schema
  tests, UIFeedEvent flags.
- UI/e2e: human-facing feed displays allowed projections while agents cannot retrieve
  UI Feed content.
- Security/context: secret-like payloads are rejected/redacted; UI markdown and raw
  proposal/chat/provider data cannot enter Bus or agent context.

## Quality Gates

- pytest backend/tests/publication backend/tests/agent_harness backend/tests/integration backend/tests/security
- Frontend/UI smoke or e2e evidence under the task report when a frontend test runner exists; otherwise record the missing-runner reason in /verify
- generated OpenAPI validation after implementation schemas exist
- MessageEnvelope/Bus/UI Feed contract tests
- node scripts/mb-lint.mjs
- node scripts/mb-doctor.mjs
- /verify and /red-verify before T3 closure
- T3 human checkpoint and rollback/recovery note before closure

## UAT Steps

- Agent output is published only after runtime decision and MessageEnvelope validation.
- Silent decision creates trace evidence with no Bus/UI publication.
- UI Feed shows allowed human presentation but cannot be retrieved as agent context.
- Physical-action-like recommendation is blocked or routed safely before clearance.

## Task Slice

- TASK-047: Runtime decision adapter and MessageEnvelope validation schemas.
- TASK-048: Speak/silent/clarify/escalate decision persistence and trace evidence.
- TASK-049: MessageEnvelope-derived BusEventEnvelope publication.
- TASK-050: UI Feed projection isolation and authorized human feed reads.
- TASK-051: Agent context-filter anti-leak gates for forbidden presentation/raw sources.
- TASK-052: MessageEnvelope/Bus/UI Feed integration, Safety Gate routing, and coverage.
