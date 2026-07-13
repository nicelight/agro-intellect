---
description: Global UI Feed projection contract for MVP v2.
status: active
type: contract
last_updated: 2026-07-12
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/message-envelope.md
---
# UI Feed

## Scope

UI Feed is the human-facing presentation stream for cards, prompts, messages,
history snippets, task/approval cards, storage warnings, and admin notices. It
is not Agent Chat Bus, not MessageEnvelope, not timeline authority, and not
agent working context.

The verified FT-000 executable baseline does not implement UI Feed runtime
code. This contract is a global guardrail; concrete projection payloads,
frontend routes, and component behavior belong to feature-level SDD design
inside `/prd-to-tasks FT-008`, `/prd-to-tasks FT-016`, or another owning
feature when a projection is feature-specific.

## Contract Scope

- Defines: global presentation-only rules, projection boundary, consumability
  flags, redaction expectations, and verification requirements for keeping UI
  content out of agent context.
- Out of scope: concrete frontend component layout, route/view map, exact card
  payload fields, endpoint schemas, or task execution state machines.
- Related specs:
  - [.memory-bank/contracts/agent-chat-bus.md](agent-chat-bus.md): defines
    agent-consumable working events.
  - [.memory-bank/contracts/message-envelope.md](message-envelope.md): defines
    validated pending agent-output boundary before classification and UI
    projection.
  - [.memory-bank/contracts/agent-roster-bootstrap.md](agent-roster-bootstrap.md):
    defines deterministic introduction batches and FT-007/FT-008 ownership.
  - [.memory-bank/contracts/timeline-event.md](timeline-event.md): defines
    append-only audit/export events.

## UIFeedEvent version 1

FT-008 implements one strict Plant-scoped object with unknown fields rejected:

- `schema_version=1`;
- `ui_event_id`: UUID; introductions reuse their deterministic
  `introduction_id`, other projections use application-generated UUIDv4;
- `created_at`: timezone-aware UTC timestamp;
- `farm_id`, `plant_id`: native UUID identities;
- `source_type`: `system | agent_message | safety`;
- `source_id`: stable introduction/message/classification identity;
- `source_refs`: zero through four unique safe `kind:identifier` refs;
- `display_kind`: `agent_introduction | agent_message | block_notice`;
- `display_payload`: exactly one variant below;
- `visible_to_roles`: non-empty unique subset of
  `boss|engineer|consultant`;
- `visible_to_agents=false`;
- `consumable_by_agents=false`.

Payload variants:

- `agent_introduction`: exactly
  `{payload_kind:"agent_introduction",agent_id,display_name,competence_summary,introduction_text,roster_version}`
  copied from the strict canonical introduction item.
- `agent_message`: exactly
  `{payload_kind:"agent_message",agent_id,candidate_claim_type,quoted_text}`;
  `quoted_text` equals the authorized/classified candidate and remains literal
  presentation data.
- `block_notice`: exactly
  `{payload_kind:"block_notice",notice_code:"classification_uncertain",text:"Сообщение заблокировано до уточнения безопасности."}`;
  it never copies candidate text.

`display_payload` must not be reused as agent input, runtime truth, timeline
authority, task/action authority, URL/action input, or HTML/Markdown source.

## Rules

- UI Feed may project candidate text only for `safe_information` with the
  matching `SafetyClassificationResultV1` and current guard. Other classes use
  an authoritative task/Safety record or a generic block notice; the notice
  never copies candidate text. UI Feed may also project authorized domain,
  timeline, admin, storage, and Companion records under their owning contracts.
- Candidate text on that authorized/classified route is rendered literally
  through escaped/text-node semantics (for example, framework text
  interpolation or `textContent`). UI Feed never sends it through an HTML or
  Markdown renderer, raw-HTML insertion, URL/link activation, or action parser.
  Markup-, prompt-, instruction-, command-, and URL-looking sequences remain
  inert visible text.
- UI Feed is the visible projection owner for deterministic roster
  introductions. FT-008 durably reconciles one strict eight-item batch per
  active Plant and writes exactly one `UIFeedEvent` per
  `(plant_id, agent_id, roster_version)`. The Plant chat/feed UI renders that
  same event; no introduction is copied to Agent Chat Bus. Introductions remain
  `visible_to_agents=false` and `consumable_by_agents=false`.
- UI Feed must never publish directly to Agent Chat Bus.
- UI Feed, UI markdown, cards, spoiler notes, raw chat, admin notices, and
  unapproved Companion content must never enter agent working context.
- Candidate text displayed by UI Feed must not be copied into agent context,
  runtime instructions, command handlers, routing inputs, or authority fields.
- UI Feed may show a Safety block or pending approval prompt, but it cannot
  authorize a physical action.
- UI Feed may show a DecisionRecord summary, but it cannot make raw proposal
  text, raw rationale, or raw chat agent-consumable.
- UI Feed must apply the same ActorContext and PlantAccessGrant visibility
  constraints as backend reads.
- Secrets, tokens, auth headers, `.env` values, provider payloads, hidden
  reasoning, and credentials must not appear in UI Feed.

Persisted Plant feed reads use the protected
`.memory-bank/contracts/plant-feed-http.md` boundary. Actual Svelte/PWA DOM
rendering remains FT-016 ownership because no frontend scaffold exists in the
current brownfield tree; that consumer must render these text fields through
text-node/framework interpolation semantics.

## Edge Cases And Errors

- If projection source authorization cannot be proven, do not emit the UI Feed
  event.
- A classification result or stale MessageEnvelope authorization snapshot is
  not proof of current visibility. The projection writer applies the canonical
  current authorization and active-Plant guard in the same write boundary.
- If a source record is valid but unsafe for agents, UI Feed may still show a
  redacted human notice with `consumable_by_agents=false`.
- If a projection references archived Plant history, it must use an explicit
  retained-history authorization path.
- A pending introduction is retained but not projected while its Plant is
  archived. A later active-Plant reconciliation after restore may continue
  delivery only after reloading current Plant state; it is not timeline replay.
- If a projection references physical-action wording, it must show the current
  Safety Gate/task state instead of cleared action wording unless the safety
  lifecycle permits that wording.

## Verification

Tests must prove:

- UI Feed projections are filtered by ActorContext and PlantAccessGrant.
- UI Feed content is absent from agent context builder fixtures.
- `visible_to_agents=false` and `consumable_by_agents=false` are preserved for
  UI-only content.
- Safety Gate approval, DecisionRecord approval, and UI prompt display remain
  separate authority classes.
- Redaction removes secrets/auth material from UI Feed output.
- Representative HTML/Markdown/prompt-/URL-looking candidate strings render
  literally with no active element, link, command, or action side effect.
- Candidate display remains unavailable to agent context/runtime authority;
  exact component and e2e mechanics remain owned by FT-008/FT-016.
