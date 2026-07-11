---
description: FT-007 Agent Runtime Decisions And MessageEnvelope.
status: draft
type: feature
feature_id: FT-007
epic: EP-003
lifecycle: planned
last_updated: 2026-07-12
spec_design_status: complete
spec_design_links:
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/contracts/agent-roster-bootstrap.md
  - .memory-bank/contracts/evidence-redaction.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/ui-feed.md
  - .memory-bank/contracts/timeline-event.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/contracts/farm/plant-management-http.md
  - .memory-bank/contracts/plant-operations-http.md
  - .memory-bank/domains/auth/session-storage.md
  - .memory-bank/domains/identity/account-membership.md
  - .memory-bank/domains/farm/farm-plant-access-storage.md
  - .memory-bank/domains/plant-operations.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/states/plant-state-trust.md
  - .memory-bank/states/auth/session-lifecycle.md
  - .memory-bank/states/safety-action-lifecycle.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
  - .memory-bank/testing/agent-runtime.md
  - .memory-bank/testing/plant-operations.md
  - .memory-bank/runbooks/agent-runtime-providers.md
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
---
# FT-007 Agent Runtime Decisions And MessageEnvelope

## Use Cases

- Product agent processes actual scoped Plant data entered or uploaded by users.
- Domain adapter converts model output into a project-owned runtime decision.
- Runtime decision produces structured MessageEnvelope or remains silent with audit evidence.
- Agent output is concise, permission-aware, and eligible for a downstream
  route only after adapter validation, project-owned classification, and the
  owning current-authorization guard.

## Acceptance Criteria

- MVP runtime/demo product-agent outputs use real LLM/model-backed agents or real model-backed adapters.
- Fake, mock, hardcoded, or stubbed outputs are allowed only in automated tests, not as MVP runtime/demo behavior.
- Agno/model execution is execution layer only and not source of truth.
- Agent output must pass adapter/runtime-decision validation before a
  MessageEnvelope is created.
- Every non-silent MessageEnvelope is pending and non-consumable until the
  project-owned Safety & Task Loop classifier returns the matching strict
  classification result; model-selected claim labels cannot authorize routing.
- Plant-scoped output must pass the FT-007 current guard before the pending
  handoff and fresh owning guards again before each downstream write; archive
  at either boundary leaves no operative
  Bus/UI/task result.
- Runtime recognizes explicit `deepseek`, `gemini`, and `chatgpt_oauth`
  profiles, uses deployment-selected per-agent model ids, and never selects a
  default or cross-provider fallback.
- External provider egress is permitted only for the authorized typed input
  contract and requires explicit runtime opt-in; auth material, raw chat, UI
  content, and unapproved data remain forbidden.
- After a new Plant commits, the system activates the exact eight-agent roster
  and sends one strict deterministic batch containing eight
  non-agent-consumable introduction handoffs without invoking a model.

## Edge Cases & Failure Modes

- Invalid model output creates no MessageEnvelope. Safety classification is
  project-owned; uncertainty permits only a generic blocked notice.
- Raw model reasoning/provider history is never stored as fact or agent working context.
- Agent cannot bypass PlantAccessGrant or ActorContext.
- Silent behavior leaves audit evidence without creating Bus/UI events.
- Restore does not replay output blocked by archive.
- Missing model binding, credential, provider dependency, explicit egress, or
  approved ChatGPT OAuth broker fails closed without fake output or fallback.
- A post-commit bootstrap failure cannot roll back or falsely report failure of
  an already committed Plant.

## Verification Targets

- Unit: exact ProviderRequest/input/model-result/outcome/envelope contracts and
  rejection matrices.
- Integration: real model-backed adapter path over actual scoped Plant data.
- Integration: archive during model execution blocks MessageEnvelope/Bus/UI
  publication without replay after restore.
- Anti-cheat: runtime demo path cannot be satisfied by fake/stubbed agent output.
- Integration: Plant creation commits before the exact roster/introduction
  handoff and performs no provider call.
- Configuration: DeepSeek/Gemini native composition, reserved fail-closed
  ChatGPT OAuth profile, strict model bindings, redaction, and no fallback.

## Normative Backbone Links

- Runtime I/O and audit: [adapter](../contracts/agent-runtime-adapter.md),
  [provider profiles](../contracts/agent-model-provider-profiles.md),
  [MessageEnvelope](../contracts/message-envelope.md), and
  [Timeline Event](../contracts/timeline-event.md).
- Current identity guard: [ActorContext](../contracts/access/actor-context.md),
  [Session Storage](../domains/auth/session-storage.md),
  [Account/Membership](../domains/identity/account-membership.md),
  [Session Lifecycle](../states/auth/session-lifecycle.md), and
  [Plant Lifecycle](../states/plants/plant-and-access-lifecycle.md).
- Plant input and bootstrap: [Plant Operations](../domains/plant-operations.md),
  [Plant Operations HTTP](../contracts/plant-operations-http.md),
  [Plant Management HTTP](../contracts/farm/plant-management-http.md),
  [Farm/Plant/Access Storage](../domains/farm/farm-plant-access-storage.md), and
  [Roster Bootstrap](../contracts/agent-roster-bootstrap.md).
- Downstream boundaries: [Safety Action Lifecycle](../states/safety-action-lifecycle.md),
  [Agent Chat Bus](../contracts/agent-chat-bus.md), and
  [UI Feed](../contracts/ui-feed.md).
- Verification and operations: [Agent Runtime testing](../testing/agent-runtime.md),
  [Plant Operations testing](../testing/plant-operations.md),
  [provider runbook](../runbooks/agent-runtime-providers.md), and
  [evidence redaction](../contracts/evidence-redaction.md).

## Behavior specs

- `.memory-bank/behavior-specs/FT-007-BHV-001-real-model-envelope.behavior.json`
- `.memory-bank/behavior-specs/FT-007-BHV-002-agent-roster-bootstrap.behavior.json`
- `.memory-bank/behavior-specs/FT-007-BHV-003-archive-race.behavior.json`

## Feature Design Decisions

- FT-007 adds one internal Agent Runtime application service and no public HTTP
  agent endpoint.
- The adapter contract owns exact provider input, model result, outcome, audit,
  and pending MessageEnvelope rules; this router does not restate them.
- Roster Bootstrap owns the post-commit eight-item batch and 8-or-0 sink result.
  Plant creation never calls a provider or rolls back after commit.
- FT-008 owns Bus/UI publication and durable introduction reconciliation;
  FT-011/FT-012 own Safety/task effects. FT-007 implements only their strict
  handoff contracts.
- Provider/model selection is deployment configuration. Smoke acceptance is
  defined by Agent Runtime testing and the provider runbook.

## Feature-Local Design Pressure

- Exact runtime decision model, adapter contract, MessageEnvelope schema,
  roster/bootstrap, provider configuration, audit behavior, and anti-cheat
  tests.

## SDD Design Gate

- Global/shared and FT-007 design status: complete; exact rules live in the
  canonical links above.
- Execution inputs: explicit DeepSeek/Gemini model id, matching credential, and
  egress opt-in. `chatgpt_oauth` remains fail-closed without an approved broker.
- TASK-028 and TASK-029 remain planning artifacts only and must not execute until
  `/prd-to-tasks FT-007` reconciles the implementation plan and task cards, and
  a fresh `/review-tasks-plan FT-007` returns `APPROVE`.

## /prd-to-tasks FT-007 Repair Handoff

The next `/prd-to-tasks FT-007` run must reconcile these stale planning inputs
without executing either task:

| Artifact | Required reconciliation |
|---|---|
| TASK-028 | Add direct Session Lifecycle/Storage and Account/Membership inputs; cover the exact current guard and safe Timeline attribution. Add the unimplemented 2000-code-point UI/backend/legacy-row delta with direct Plant Operations links. Replace stale model/safety assertions with the canonical ProviderRequest/input/model-result/outcome/envelope/event contracts. Test only the classifier handoff; do not implement FT-011/FT-008/FT-012 effects. |
| TASK-029 | Add direct Plant Management HTTP and Farm/Plant/Access Storage inputs; preserve request/auth/`201 PlantSummary`/no-store/atomic commit/error behavior. Cover exact UUIDv5 names, one eight-item sink call, 8-or-0 result matrix, downstream reconciliation boundary, and audited smoke rule. Do not implement FT-008 storage/projection. |
| IMPL-FT-007 | Reconcile write scopes, constraints, gates, dependencies, and verification targets with both task cards and canonical specs. Preserve Plant Operations/Operator UI and FT-008/FT-011/FT-012 ownership. |

After reconciliation, the only allowed next gate is a fresh
`/review-tasks-plan FT-007`. TASK-028/TASK-029 stay `planned` and execution is
forbidden unless that review returns exact `VERDICT: APPROVE`.

## Implementation

- [Implementation plan](../tasks/plans/IMPL-FT-007.md): two ordered T3 task
  cards for the runtime core and roster/provider/bootstrap production binding.
