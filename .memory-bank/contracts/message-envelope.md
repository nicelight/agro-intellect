---
description: Global MessageEnvelope contract boundary for MVP v2.
status: active
owner: architecture
type: contract
last_updated: 2026-06-26
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/ui-feed.md
  - .memory-bank/states/safety-action-lifecycle.md
  - .memory-bank/states/plant-state-trust.md
---
# MessageEnvelope

## Scope

MessageEnvelope is the structured boundary for publishable agent-originated output after project-owned runtime decision handling. It is not raw model output, hidden reasoning, provider history, or UI markup.

The verified FT-000 executable baseline does not implement MessageEnvelope
runtime code. This contract is a global guardrail for future product features;
field refinements and implementation tasks belong to `/prd-to-tasks FT-<NNN>`.

## Ownership

- Owns: project-owned publishable agent-output boundary, runtime decision
  categories, envelope minimum, forbidden content, claim/safety rules, and
  Bus/UI projection handoff.
- Does not own: raw provider messages, hidden reasoning, model prompt history,
  concrete adapter implementation, UI component payloads, or final Plant state.
- Related specs:
  - [.memory-bank/contracts/agent-chat-bus.md](agent-chat-bus.md): owns
    agent-consumable event publication.
  - [.memory-bank/contracts/ui-feed.md](ui-feed.md): owns human presentation
    projection.
  - [.memory-bank/states/safety-action-lifecycle.md](../states/safety-action-lifecycle.md):
    owns physical-action approval lifecycle.
  - [.memory-bank/states/plant-state-trust.md](../states/plant-state-trust.md):
    owns Plant state promotion rules.

## Runtime Decision

Every model-backed product-agent invocation must resolve to one runtime decision:

- `speak`: publish concise structured output through MessageEnvelope.
- `silent`: publish no MessageEnvelope, but keep audit evidence.
- `clarify`: publish a short missing-data request.
- `escalate`: publish a Safety Block or Team Signal style route.

Feature-local specs define exact state shapes and audit fields before tasks.

## Envelope Minimum

Feature-local specs may refine fields, but every publishable MessageEnvelope must carry:

- `message_id`
- `agent_id`
- `created_at`
- `farm_id`
- `plant_id` when Plant-scoped
- `runtime_decision`
- `claim_type`
- `confidence`
- `source_refs`
- `consumable_output`
- `requires_human_approval`
- `safety_gate_route`
- `authorization_scope`

## Forbidden Content

MessageEnvelope must not contain:

- hidden chain-of-thought or raw reasoning;
- raw provider messages/history;
- secrets, tokens, credentials, API keys, `.env` values, or auth material;
- raw UI markdown as agent-consumable content;
- raw CompanionProposal text/rationale/chat discussion;
- unauthorized Farm/Plant context.

## Safety And Claims

- Observation, hypothesis, recommendation, clarification, task request, safety block, and team signal are distinct claim categories.
- Agent hypotheses cannot become confirmed Plant state without human review or follow-up evidence.
- Any physical-action implication must set a Safety Gate route before display/action tracking.
- `requires_human_approval=true` does not itself authorize action.
- `confidence` is advisory metadata only; it cannot replace evidence refs,
  human review, Safety Gate, or backend authorization.

## Bus And UI Projection

- MessageEnvelope may be referenced by Agent Chat Bus events after validation.
- UI Feed may project human-facing display from MessageEnvelope.
- UI Feed projection does not become MessageEnvelope or agent context.

## Verification

Tests must prove:

- test mocks are not wired as runtime/demo product-agent outputs;
- invalid envelopes are blocked;
- raw reasoning/provider history is absent;
- physical-action wording routes to Safety Gate;
- UI Feed projection cannot be consumed by agents.
