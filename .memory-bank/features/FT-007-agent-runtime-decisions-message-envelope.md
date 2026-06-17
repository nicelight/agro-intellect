---
description: FT-007 Agent Runtime Decisions And MessageEnvelope.
status: draft
type: feature
feature_id: FT-007
epic: EP-003
lifecycle: planned
last_updated: 2026-06-14
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

## Edge Cases & Failure Modes

- Invalid or unsafe model output is blocked, clarified, escalated, or audit-only.
- Raw model reasoning/provider history is never stored as fact or agent working context.
- Agent cannot bypass PlantAccessGrant or ActorContext.
- Silent behavior leaves audit evidence without creating Bus/UI events.

## Verification Targets

- Unit: runtime decision classification after spec defines states.
- Integration: real model-backed adapter path over actual scoped Plant data.
- Anti-cheat: runtime demo path cannot be satisfied by fake/stubbed agent output.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Agent Runtime module and external integration boundaries.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): runtime decision and publishable output boundary.
- [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md): Bus publication and consumability rules.

## SDD Design Gate

Run global `/spec-design` before this feature is task-decomposed. Then run `/spec-improve FT-007` to define exact runtime decision model, adapter contract, MessageEnvelope schema, audit behavior, and anti-cheat tests before `/prd-to-tasks FT-007`.
