---
description: Implementation plan for FT-007 Agent Runtime, canonical roster, provider bindings, and MessageEnvelope.
status: active
type: implementation_plan
feature_id: FT-007
last_updated: 2026-07-12
source_of_truth:
  - .memory-bank/features/FT-007-agent-runtime-decisions-message-envelope.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/contracts/agent-roster-bootstrap.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/testing/agent-runtime.md
---
# IMPL FT-007 Agent Runtime Decisions And MessageEnvelope

## Goal

Implement a project-owned Agent Runtime that processes authorized actual Plant
context through an explicitly configured real Agno-backed provider, converts
only validated non-silent output into an immutable pending MessageEnvelope,
returns one closed runtime outcome, and activates the canonical agent roster
after Plant commit without faking downstream chat or safety authority.

## Scope

- Add bounded `backend/app/agent_runtime/` contracts and service composition.
- Reuse ActorContext/AuthorizedPlantContext and assemble exact PostgreSQL
  Plant/check-in/measurement input into the closed `ProviderRequestV1`; reject
  caller-built context/refs and legacy oversized observations before provider
  I/O.
- Add the authoritative 2000-code-point Plant Operations backend rejection and
  zero-write tests required by the current canonical input contract.
- Implement the exact model-result, eight-branch outcome, pending
  MessageEnvelope, current authorization guard, classification handoff, and
  sanitized Timeline Event matrices.
- Add the exact eight-member roster, UUIDv5 identities, one strict eight-item
  batch port, closed 8-or-0 result handling, and post-commit bootstrap hook.
- Add strict per-agent DeepSeek/Gemini/ChatGPT-OAuth profile resolution,
  deployment model ids, explicit typed egress, secret redaction, and no
  fallback.
- Bind native DeepSeek/Gemini Agno adapters and a recognized fail-closed
  ChatGPT OAuth broker port.

## Non-goals

- BusEventEnvelope/chat/UI Feed persistence, context query, projection, worker,
  or outbox; no FT-008 task is created here.
- Safety classifier/policy or any Bus/UI/task/Safety effect; FT-007 implements
  and tests only the strict pending-envelope/classification handoff.
- Vision-specific photo input, Advisor policy, Safety Gate effects, tasks,
  Companion governance, or dataset lifecycle.
- Operator UI/PWA input and counter implementation. The UI half of the
  observation limit remains an explicit FT-016-owned delta because this
  brownfield tree has no Operator UI implementation.
- Provider history, prompt storage, Agno memory/session state, RAG, tools, Team
  coordination, fallback models, or a new public HTTP agent endpoint.
- Undocumented ChatGPT token acquisition, Codex credential reuse, or claiming
  the reserved OAuth profile is operational without an approved broker.

## Constitution Check

- Spec Before Code: direct adapter, provider, roster, envelope, timeline,
  access, lifecycle, testing, and runbook contracts govern implementation.
- KISS: one internal runtime service, static roster, narrow provider factory,
  no agent-run/provider-history table, and no Bus/UI/outbox implementation.
- Safety/authority: current Plant authorization, archive races, secrets,
  provider egress, and fake-runtime boundaries are T3 and fail closed.
- Low maintenance: reuse existing Plant context/timeline/creation seams; model
  ids are configuration rather than hardcoded policy.
- Design blockers: none. W2 execution still needs one explicit DeepSeek or
  Gemini model id, matching credential, and egress opt-in for its non-skipped
  smoke evidence.

## Source Artifacts

- `.memory-bank/features/FT-007-agent-runtime-decisions-message-envelope.md`
- `.memory-bank/epics/EP-003-agent-runtime-context-hygiene.md`
- `.memory-bank/requirements.md`: REQ-003, REQ-010, REQ-011, REQ-013, and
  REQ-020.
- `.memory-bank/behavior-specs/FT-007-BHV-001-real-model-envelope.behavior.json`
- `.memory-bank/behavior-specs/FT-007-BHV-002-agent-roster-bootstrap.behavior.json`
- `.memory-bank/behavior-specs/FT-007-BHV-003-archive-race.behavior.json`

## Normative Inputs

- `.memory-bank/contracts/agent-runtime-adapter.md`
- `.memory-bank/contracts/agent-model-provider-profiles.md`
- `.memory-bank/contracts/agent-roster-bootstrap.md`
- `.memory-bank/contracts/message-envelope.md`
- `.memory-bank/contracts/timeline-event.md`
- `.memory-bank/contracts/evidence-redaction.md`
- `.memory-bank/contracts/access/actor-context.md`
- `.memory-bank/domains/auth/session-storage.md`
- `.memory-bank/domains/identity/account-membership.md`
- `.memory-bank/states/auth/session-lifecycle.md`
- `.memory-bank/contracts/farm/plant-management-http.md`
- `.memory-bank/domains/farm/farm-plant-access-storage.md`
- `.memory-bank/contracts/plant-operations-http.md`
- `.memory-bank/domains/plant-operations.md`
- `.memory-bank/domains/runtime-data-model.md`
- `.memory-bank/states/safety-action-lifecycle.md`
- `.memory-bank/states/plants/plant-and-access-lifecycle.md`
- `.memory-bank/testing/agent-runtime.md`
- `.memory-bank/testing/plant-operations.md`
- `.memory-bank/runbooks/agent-runtime-providers.md`

## Dependencies

- `TASK-025-T3-FT-004-W3` is the completed direct baseline and transitively
  includes Foundation, access, Plant lifecycle, normalized pH/EC, and timeline
  seams.
- `TASK-027-T3-FT-006-W3` is not a dependency because Agent Runtime assembles
  authoritative Plant-operation rows rather than Plant-history projections.
- FT-008 may later consume MessageEnvelope and introduction handoffs. FT-007
  does not depend on a Bus/UI implementation and must not create that cycle.

## Ordered implementation strategy

### W1 - Authorized runtime and envelope core

`TASK-028-T3-FT-007-W1` implements Agent Runtime types/service, exact
PostgreSQL typed-input assembly, the Plant Operations backend observation cap,
legacy-row pre-provider denial, model-result/outcome/MessageEnvelope validation,
current session/account/membership/Plant/grant recheck, strict classifier
handoff, sanitized timeline audit, deterministic tests, and explicit test-only
executor injection. It does not implement classifier effects or Operator UI.

### W2 - Canonical roster, bootstrap, and production providers

`TASK-029-T3-FT-007-W2` implements the eight immutable roster metadata records,
immutable UUIDv5 identities, one-call batch port/result matrix, strict
deployment binding resolver, native DeepSeek/Gemini Agno composition,
fail-closed ChatGPT OAuth broker port, config/redaction, a post-commit Plant
hook that preserves the canonical public create contract, anti-cheat tests,
and a credentialed non-skipped real-provider transport smoke over actual Plant
data using the isolated test-only definition through the explicit test seam.

## Expected touched areas

- `pyproject.toml`
- `.env.example`
- `backend/app/config.py`
- `backend/app/agent_runtime/`
- `backend/app/plant_operations/service.py`
- `backend/app/api/operations.py`
- `backend/app/timeline/writer.py`
- `backend/app/api/plants.py`
- `backend/app/main.py`
- `tests/backend/agent_runtime/`
- focused Plant Operations service/API observation-boundary tests;
- focused Plant-create composition tests and FT-007 evidence/task records.

## Constraints and invariants

- `ProviderRequestV1` is the sole provider payload; ActorContext, account,
  membership, role, grant, session, provider selection, and credentials remain
  outside it.
- Input records use exact `{record_type, source_ref, payload}` shapes and the
  canonical Plant/check-in/pH/EC order with same-row pH/EC deduplication.
- Observation text is normalized and limited to 2000 Unicode code points at
  the authoritative backend; no truncation, chunking, implicit summary, or
  write occurs on rejection. Legacy oversized rows fail before provider/audit.
- Model-selected candidate claims have no safety authority. Every non-silent
  envelope remains pending/non-consumable until the separate project-owned
  classification result is available.
- Failure/denial branches remain distinct closed outcomes and never become
  synthetic model silence.
- Provider/model failure never changes identity or selects fallback/fake output.
- Plant creation commits before bootstrap, holds no transaction across the
  handoff, performs no provider call, and preserves the existing request,
  authorization, `201 PlantSummary`, no-store, atomicity, and error contract.
- Introductions use the canonical UUIDv5 namespace/name strings and one strict
  eight-item batch. Partial acceptance is invalid; durable reconciliation and
  visible projection remain FT-008.
- PostgreSQL stays runtime authority; Timeline Event remains sanitized
  append-only audit/export.

## Verification strategy

- Exact provider-request/input/model-result/outcome/envelope/event matrices.
- Plant Operations service/API boundaries at 1, 2000, and 2001 Unicode code
  points, including authoritative `OBSERVATION_TEXT_TOO_LONG` zero-write
  behavior and legacy-row pre-provider denial.
- Existing ActorContext plus post-invocation archive/authorization integration.
- Sanitized timeline audit and audit-failure fail-closed tests.
- Exact classifier-handoff tests without FT-008/FT-011/FT-012 effects.
- Exact roster/order/competence, UUIDv5 namespace/name, one-batch, and 8-or-0
  sink-result tests.
- Post-commit bootstrap ordering, no-provider-call, repeat, committed-Plant
  failure behavior, and full Plant-create compatibility assertions.
- Strict binding/config/redaction/no-fallback tests for all profiles.
- Native DeepSeek/Gemini constructor tests and fail-closed ChatGPT OAuth scan.
- Credentialed non-skipped DeepSeek or Gemini transport smoke using actual
  persisted Plant evidence and the isolated test-only definition. Only audited
  `envelope_ready` or strict audited model-declared `model_silent` passes;
  downstream competence features retain product-agent acceptance.
- Focused/full regressions, `mb-lint`, and scoped diff check.

## Quality gates

- `.venv/bin/python -m pytest tests/backend/agent_runtime -m "not real_model" -q`
- `.venv/bin/python -m pytest tests/backend/plant_operations/test_ft004_service.py tests/backend/api/test_ft004_operations_routes.py -q`
- `AGENT_REAL_SMOKE=1 .venv/bin/python -m pytest tests/backend/agent_runtime/test_real_model_smoke.py -m real_model -q`
- `.venv/bin/python -m pytest tests/backend/access_admin tests/backend/api tests/backend/agent_runtime -m "not real_model" -q`
- `.venv/bin/python -m pytest tests -m "not real_model" -q`
- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- `git diff --check`

## UAT

1. Configure explicit typed egress plus one DeepSeek or Gemini smoke binding,
   model id, and matching secret.
2. Create a Plant and confirm its transaction commits before the eight-member
   deterministic introduction handoff; confirm no model call occurs merely on
   creation.
3. Resolve an active authorized Plant with actual check-in or pH/EC evidence
   and invoke the production transport through the isolated smoke definition.
4. Receive either an audited `envelope_ready` with a valid pending
   MessageEnvelope or strict audited model-declared `model_silent`; every
   blocked, failed, invalid, skipped, fake, fallback, or unaudited result fails
   the smoke.
5. Archive/revoke during invocation and confirm no downstream effect or replay.
6. Select unconfigured `chatgpt_oauth` and confirm fail-closed behavior without
   reading Codex/ChatGPT credentials or trying another provider.

## Queue handoff

- `TASK-028-T3-FT-007-W1` and `TASK-029-T3-FT-007-W2` are the complete ordered
  FT-007 queue; both remain `planned`.
- Next and only semantic gate: `/review-tasks-plan FT-007`.
- Execution is forbidden until that fresh review returns exact
  `VERDICT: APPROVE`.
- No FT-008 decomposition or task record is part of this handoff.
