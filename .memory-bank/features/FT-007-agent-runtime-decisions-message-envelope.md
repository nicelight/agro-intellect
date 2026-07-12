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
- Schema-valid `candidate_output` is opaque untrusted normalized text within
  the existing 1..2000 Unicode-code-point bound. Markdown-, HTML-, prompt-,
  instruction-, command-, and URL-looking sequences are accepted as data and
  have no executable or authority semantics.
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

- Invalid model output creates no MessageEnvelope. Formatting-looking syntax
  alone is not invalid; strict schema/type/normalization/length, decision/claim,
  ref, and confidence failures remain invalid. Safety classification is
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
  rejection matrices, including acceptance of representative schema-valid
  Markdown/HTML/prompt-like candidate data.
- Deferred manual UAT: real model-backed adapter path over actual scoped Plant
  data. Its absence does not block TASK-031/code-phase closure and does not
  satisfy BHV-001 or the live-provider portion of REQ-011.
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
- Candidate text remains opaque data across FT-007. It is never parsed as
  markup/prompt, promoted to instructions, or used to select classification,
  publication, task, Safety, or action authority.
- Roster Bootstrap owns the post-commit eight-item batch and 8-or-0 sink result.
  Plant creation never calls a provider or rolls back after commit.
- FT-008 owns Bus/UI publication and durable introduction reconciliation;
  FT-011/FT-012 own Safety/task effects. FT-007 implements only their strict
  handoff contracts.
- Provider/model selection is deployment configuration. The credentialed
  smoke is retained as optional/manual UAT; when explicitly invoked, its strict
  acceptance is defined by Agent Runtime testing and the provider runbook.

## Feature-Local Design Pressure

- Exact runtime decision model, adapter contract, MessageEnvelope schema,
  roster/bootstrap, provider configuration, audit behavior, and anti-cheat
  tests.

## SDD Design Gate

- Global/shared and FT-007 design status: complete; exact rules live in the
  canonical links above.
- Historical TASK-028 verification/semantic failures and BUG-001 were correct
  under the superseded syntax-rejection contract. They remain historical and
  their lifecycle is not changed by this design pass.
- Manual-UAT inputs, only when that UAT is explicitly invoked: explicit
  DeepSeek/Gemini model id, matching credential, and egress opt-in. Their
  absence does not block TASK-031/code-phase closure. `chatgpt_oauth` remains
  fail-closed without an approved broker.
- TASK-028 (`failed`) and TASK-029 (`blocked`) remain lifecycle/history
  artifacts only and must never be re-executed or rewritten.
- Current `backend/app/agent_runtime/contracts.py` and its FT-007 tests still
  contain the superseded partial markup/prompt regex rejection. The bounded
  implementation delta is routed to planned TASK-030 without rewriting the
  historical failed/blocked lifecycle records.

## /prd-to-tasks FT-007 Reconciled Handoff

Bounded reconciliation preserves the historical records and creates this
active replacement queue without executing any task:

| Artifact | Reconciled result |
|---|---|
| TASK-028 / TASK-029 | Preserved verbatim as `failed` / `blocked` history, including dependencies and evidence. |
| TASK-030 | Planned W1 replacement depending on completed TASK-025. Removes syntax/prompt regex rejection, accepts representative schema-valid formatting-looking values unchanged, and re-proves the full existing runtime core without downstream authority. |
| TASK-031 | Planned W2 replacement depending on TASK-030. Preserves the legitimate TASK-029 roster/provider/bootstrap/Plant-create/real-provider-smoke scope under its own protocol/evidence identity. |
| IMPL-FT-007 | Active dependency graph and scopes now match TASK-030 -> TASK-031; no canonical or behavior spec was added. |

The only allowed next gate is a fresh `/review-tasks-plan FT-007`. No active
replacement task may execute unless that review returns exact
`VERDICT: APPROVE`. Explicit DeepSeek/Gemini model id, matching credential, and
egress opt-in are later manual-UAT inputs, not planning or TASK-031/code-phase
closure blockers.

## Owner-Directed Smoke Deferral

- As of 2026-07-12, credentialed DeepSeek/Gemini smoke is strict
  optional/manual UAT and is not TASK-031/code-phase closure evidence.
- Deterministic roster, provider-construction, no-fallback, bootstrap,
  Plant-create compatibility, redaction, and regression evidence may support
  code-phase closure without a live provider call.
- `FT-007-BHV-001` and the live-provider portion of REQ-011 remain explicitly
  deferred and unverified. Deterministic introduction, constructor, binding,
  or anti-cheat tests must not be presented as satisfying them.
- If the smoke is invoked later, explicit mode, profile/model, matching
  credential, installed provider dependencies, and egress opt-in are required;
  every skip, fake, fallback, blocked/failed, or unaudited outcome fails that
  UAT, and evidence remains redacted.

## Semantic Verification

SEMANTIC_VERDICT: semantic-pass

- Feature-level adversarial review accepts the owner-approved deterministic
  code-phase and explicit replacement-based administrative closure boundary.
  TASK-028 FAIL/semantic-fail and TASK-029 dependency-block history remain
  preserved; their current administrative `done` records point explicitly to
  independently verified TASK-030/TASK-031 replacements and do not claim the
  original implementations passed.
- `FT-007-BHV-001`, the live-provider portion of REQ-011, and real
  DeepSeek/Gemini transport remain deferred/unverified and are not satisfied by
  deterministic evidence. FT-008 retains durable introduction reconciliation,
  Bus/UI publication, and downstream current-guard ownership.
- Report: [FT-007 feature semantic review](../../.tasks/FT-007/FT-007-S-RED-VERIFY-final-report-docs-01.md).

## Implementation

- [Implementation plan](../tasks/plans/IMPL-FT-007.md): historical TASK-028/029
  plus active ordered T3 replacements TASK-030 -> TASK-031.
