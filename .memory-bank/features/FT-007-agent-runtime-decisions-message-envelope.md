---
description: FT-007 Agent Runtime Decisions And MessageEnvelope.
status: draft
type: feature
feature_id: FT-007
epic: EP-003
lifecycle: planned
last_updated: 2026-07-06
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

## Edge Cases & Failure Modes

- Invalid or unsafe model output is blocked, clarified, escalated, or audit-only.
- Raw model reasoning/provider history is never stored as fact or agent working context.
- Agent cannot bypass PlantAccessGrant or ActorContext.
- Silent behavior leaves audit evidence without creating Bus/UI events.
- Restore does not replay output blocked by archive.

## Verification Targets

- Unit: runtime decision classification after spec defines states.
- Integration: real model-backed adapter path over actual scoped Plant data.
- Integration: archive during model execution blocks MessageEnvelope/Bus/UI
  publication without replay after restore.
- Anti-cheat: runtime demo path cannot be satisfied by fake/stubbed agent output.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Agent Runtime module and external integration boundaries.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): runtime decision and publishable output boundary.
- [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md): Bus publication and consumability rules.
- [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): human-facing projection boundary that remains unavailable as agent context.
- [.memory-bank/states/plant-state-trust.md](../states/plant-state-trust.md): observation/hypothesis promotion rules.
- [.memory-bank/states/plants/plant-and-access-lifecycle.md](../states/plants/plant-and-access-lifecycle.md): archived-Plant publication guard.

## Feature-Local Design Pressure

- Exact runtime decision model, adapter contract, MessageEnvelope schema, audit
  behavior, provider configuration, and anti-cheat tests.

## SDD Design Gate

- Global/shared status: ready; `AD-007`, MessageEnvelope, Agent Chat Bus, and
  Plant lifecycle specs define the archive-race publication block.
- Feature-local status: pending `/prd-to-tasks FT-007` for exact adapter,
  runtime-decision, provider, audit, and schema contracts.
