---
description: FT-007 Agent Runtime Decisions And MessageEnvelope.
status: draft
type: feature
feature_id: FT-007
epic: EP-003
lifecycle: planned
last_updated: 2026-07-11
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
  - .memory-bank/domains/plant-operations.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/states/plant-state-trust.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
  - .memory-bank/testing/agent-runtime.md
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
- Agent output is concise, permission-aware, and safe for downstream publication only after validation.

## Acceptance Criteria

- MVP runtime/demo product-agent outputs use real LLM/model-backed agents or real model-backed adapters.
- Fake, mock, hardcoded, or stubbed outputs are allowed only in automated tests, not as MVP runtime/demo behavior.
- Agno/model execution is execution layer only and not source of truth.
- Agent output must pass adapter/runtime decision and MessageEnvelope validation before Bus/UI publication.
- Plant-scoped output must pass a current active-Plant check at publication;
  archive after model invocation makes the result audit-only rather than
  publishable.
- Runtime recognizes explicit `deepseek`, `gemini`, and `chatgpt_oauth`
  profiles, uses deployment-selected per-agent model ids, and never selects a
  default or cross-provider fallback.
- External provider egress is permitted only for the authorized typed input
  contract and requires explicit runtime opt-in; auth material, raw chat, UI
  content, and unapproved data remain forbidden.
- After a new Plant commits, the system activates the exact eight-agent roster
  and creates one deterministic non-agent-consumable introduction handoff per
  member without invoking a model.

## Edge Cases & Failure Modes

- Invalid or unsafe model output is blocked, clarified, escalated, or audit-only.
- Raw model reasoning/provider history is never stored as fact or agent working context.
- Agent cannot bypass PlantAccessGrant or ActorContext.
- Silent behavior leaves audit evidence without creating Bus/UI events.
- Restore does not replay output blocked by archive.
- Missing model binding, credential, provider dependency, explicit egress, or
  approved ChatGPT OAuth broker fails closed without fake output or fallback.
- A post-commit bootstrap failure cannot roll back or falsely report failure of
  an already committed Plant.

## Verification Targets

- Unit: runtime decision classification after spec defines states.
- Integration: real model-backed adapter path over actual scoped Plant data.
- Integration: archive during model execution blocks MessageEnvelope/Bus/UI
  publication without replay after restore.
- Anti-cheat: runtime demo path cannot be satisfied by fake/stubbed agent output.
- Integration: Plant creation commits before the exact roster/introduction
  handoff and performs no provider call.
- Configuration: DeepSeek/Gemini native composition, reserved fail-closed
  ChatGPT OAuth profile, strict model bindings, redaction, and no fallback.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Agent Runtime module and external integration boundaries.
- [.memory-bank/contracts/agent-runtime-adapter.md](../contracts/agent-runtime-adapter.md): exact invocation, typed input, adapter, failure, audit, and handoff boundary.
- [.memory-bank/contracts/agent-model-provider-profiles.md](../contracts/agent-model-provider-profiles.md): strict multi-provider/model binding, egress, credentials, and ChatGPT OAuth support boundary.
- [.memory-bank/contracts/agent-roster-bootstrap.md](../contracts/agent-roster-bootstrap.md): exact roster identities, deterministic introductions, and post-commit bootstrap semantics.
- [.memory-bank/contracts/evidence-redaction.md](../contracts/evidence-redaction.md): secret-safe provider configuration, diagnostics, and evidence.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): runtime decision and publishable output boundary.
- [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md): Bus publication and consumability rules.
- [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): human-facing projection boundary that remains unavailable as agent context.
- [.memory-bank/states/plant-state-trust.md](../states/plant-state-trust.md): observation/hypothesis promotion rules.
- [.memory-bank/states/plants/plant-and-access-lifecycle.md](../states/plants/plant-and-access-lifecycle.md): archived-Plant publication guard.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): sanitized runtime decision audit event.
- [.memory-bank/domains/plant-operations.md](../domains/plant-operations.md): canonical check-in and normalized pH/EC source rows for typed input v1.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): PostgreSQL authority and audit/Bus/UI separation.
- [.memory-bank/testing/agent-runtime.md](../testing/agent-runtime.md): exact deterministic, real-model, anti-cheat, and archive-race verification.
- [.memory-bank/runbooks/agent-runtime-providers.md](../runbooks/agent-runtime-providers.md): provider configuration and credentialed real-model smoke.

## Behavior specs

- `.memory-bank/behavior-specs/FT-007-BHV-001-real-model-envelope.behavior.json`
- `.memory-bank/behavior-specs/FT-007-BHV-002-agent-roster-bootstrap.behavior.json`
- `.memory-bank/behavior-specs/FT-007-BHV-003-archive-race.behavior.json`

## Feature Design Decisions

- FT-007 adds one internal Agent Runtime application service and no public HTTP
  agent endpoint.
- Exact input v1 is assembled inside the service from the active Plant, latest
  completed daily check-in, and latest pH/EC PostgreSQL rows; callers cannot
  submit context mappings or refs.
- FT-007 owns the stable eight-agent identity/competence/introduction roster;
  FT-009 through FT-014 own competence-specific instructions, triggers, and
  effects.
- Plant creation invokes only a post-commit local bootstrap handoff. It does
  not hold the Plant transaction open or call providers. Deterministic
  introduction metadata is neither MessageEnvelope nor agent context.
- Per-agent provider/model resolution is deployment configuration. DeepSeek
  and Gemini have native Agno bindings; `chatgpt_oauth` is a recognized
  fail-closed broker port until an approved executable OAuth contract exists.
- MessageEnvelope is an immutable validated handoff; sanitized Timeline Event
  is audit/export evidence. No agent-run, provider-history, prompt, or raw-output
  PostgreSQL table is required.
- FT-008 owns BusEventEnvelope, Bus storage/context reads, UIFeedEvent, and
  durable chat/feed projection behavior; FT-007 exposes validated
  MessageEnvelope and deterministic introduction handoff ports. No FT-008 task
  is created by this decomposition.

## Feature-Local Design Pressure

- Exact runtime decision model, adapter contract, MessageEnvelope schema,
  roster/bootstrap, provider configuration, audit behavior, and anti-cheat
  tests.

## SDD Design Gate

- Global/shared status: ready; `AD-007`, MessageEnvelope, Agent Chat Bus, and
  Plant lifecycle specs define the archive-race publication block.
- Feature-local status: complete. Canonical runtime, envelope, audit, exact
  roster/bootstrap, provider bindings, egress, failure, verification, and
  operator setup are designed and taskable.
- Deployment model ids are intentionally selected later. TASK-029 cannot close
  its real-provider evidence without one explicit DeepSeek or Gemini model id
  and credential, but this is an execution input rather than a design blocker.
- Generic third-party ChatGPT OAuth is not overclaimed: the profile is reserved
  behind a fail-closed broker port and cannot become operational until an
  approved token/refresh/endpoint contract exists. Codex/ChatGPT browser
  credentials are never reused.

## Implementation

- [Implementation plan](../tasks/plans/IMPL-FT-007.md): two ordered T3 task
  cards for the runtime core and roster/provider/bootstrap production binding.
