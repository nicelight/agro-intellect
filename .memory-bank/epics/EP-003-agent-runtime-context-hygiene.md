---
description: EP-003 Agent Runtime And Context Hygiene.
status: draft
type: epic
epic_id: EP-003
lifecycle: planned
last_updated: 2026-07-20
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
---
# EP-003 Agent Runtime And Context Hygiene

## Value

Allow product agents to help with actual scoped Plant data while preventing raw model output, UI presentation, or unauthorized context from becoming agent facts and keeping authorized governance input explicitly typed and non-authoritative.

## Features

- [FT-007 Agent Runtime Decisions And MessageEnvelope](../features/FT-007-agent-runtime-decisions-message-envelope.md)
- [FT-008 Agent Chat Bus And UI Feed Context Hygiene](../features/FT-008-agent-chat-bus-ui-feed-context-hygiene.md)
- [FT-009 Vision Observation And Plant State Trust](../features/FT-009-vision-observation-plant-state-trust.md)
- [FT-010 Hydroponics Advisor Missing Data Policy](../features/FT-010-hydroponics-advisor-missing-data-policy.md)

## Success Metrics

- Current code-phase agent behavior is provider-neutral and deterministically
  verified over actual scoped Plant data; real endpoint behavior is deferred.
- UI Feed is never consumed as agent working context; governance content enters only through an owning strict agent-specific provider contract.
- Vision outputs remain observations/hypotheses unless human review or follow-up evidence promotes state.
- Advisor output asks for missing/stale critical data instead of inventing evidence.

## Acceptance Criteria

- Agno/model execution is execution layer only, not source of truth.
- Agent outputs pass through project-owned adapter/runtime decision and MessageEnvelope before publication.
- Agent Chat Bus and UI Feed are separate boundaries.
- Fake/spy executors are test-only; production has no fake/canned/fallback
  behavior and fails closed without a selected endpoint.

## Constraints / Invariants

- Single-competence product-agent boundaries are mandatory.
- Raw reasoning, provider history, UI Feed, spoiler notes, and raw chat never enter agent working context. Typed governance input does not gain fact or authority semantics.
- Agent hypotheses cannot become confirmed Plant state without human review or follow-up evidence.

## Feature-Local Design Pressure

- Exact MessageEnvelope, BusEventEnvelope, and UIFeedEvent contracts.
- Exact adapter validation and runtime decision flow.
- Exact agent context-builder filters and anti-cheat verification.

## Current Lifecycle Evidence

- FT-008 is `verified` for durable roster introductions, guarded typed Bus and
  literal UI publication, current-authority agent-context isolation, and the
  protected Plant feed API. REQ-013 is correspondingly `verified` across its
  FT-007/FT-008 boundary.
- FT-009's W1/W2 task queue is complete: TASK-034 has an owner-accepted
  provider-neutral administrative closure, and TASK-035 is `done` from current
  ATTEMPT 04 implementation, functional `PASS`, and `semantic-pass` evidence.
  FT-009's feature lifecycle remains `planned` because this evidence sync does
  not make an owner feature-lifecycle decision; real selected-endpoint image
  behavior remains deferred and unverified.
- FT-010's sole W1 task is scheduler-recorded `done` from current ATTEMPT 02
  implementation `PASS`, independent functional `VERDICT: PASS`, separate
  `SEMANTIC_VERDICT: semantic-pass`, and closure evidence. The deterministic
  boundary preserves provider-neutral fail-closed operation, current
  authorization, exact missing-data behavior, and zero downstream authority.
- EP-003 and FT-010 remain `planned`: this evidence sync does not make an owner
  feature/epic lifecycle decision, and the future provider-integration
  milestone under REQ-011 remains deferred. Dependent TASK-037 remains
  scheduler-owned `planned`; this sync does not promote or select it. FT-008,
  FT-009, and FT-010 do not claim FT-011 Safety classification or FT-016
  frontend rendering.
