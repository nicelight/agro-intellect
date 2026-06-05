---
description: Feature-local SDD tech spec for FT-009 MessageEnvelope, Agent Chat Bus publication, UI Feed projection, and context isolation.
status: active
feature_id: FT-009
owner: spec-improve
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/features/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md
  - .memory-bank/requirements.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/agent-harness.md
  - .memory-bank/contracts/safety-gate.md
  - .memory-bank/tech-specs/FT-006-runtime-plant-state-history-and-timeline-audit.md
  - .memory-bank/tech-specs/FT-007-shared-agent-harness-and-agent-profile-runtime.md
  - .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
  - agents-best-practices
---
# FT-009 MessageEnvelope, Agent Chat Bus, And UI Feed Isolation Tech Spec

## Purpose

Define the minimum feature-local design needed before task decomposition for
AgentHarness runtime decisions, `MessageEnvelope` payload variants, Agent Chat Bus
publication rules, UI Feed projection rules, and context-filtering tests that prevent
presentation content from becoming agent working context.

This spec applies `agents-best-practices`: raw model output is a proposal/data artifact;
the harness and backend adapters validate, authorize, publish, project, trace, and
filter it.

## Scope

In scope:

- runtime decision handling for `speak`, `silent`, `clarify`, and `escalate`;
- feature-local `MessageEnvelope` payload variants and claim routing;
- Bus publication mapping from validated MessageEnvelope/domain refs;
- UI Feed projection rules for human-facing messages, cards, prompts, task/approval
  cards, and spoiler notes;
- context filtering proving UI Feed, raw chat, raw provider output, unapproved
  CompanionProposal content, and admin UI text cannot become agent working context;
- anti-cheat tests for malformed output, overlong output, and secret leakage.

Out of scope:

- AgentProfile loop/tool/permission core owned by FT-007;
- context-builder memory retrieval and compaction owned by FT-008;
- real provider/model adapter choices owned by FT-010;
- Plant State/advisor trust mapping owned by FT-011;
- Safety Gate decision and action-task unlock owned by FT-012 and FT-013;
- Companion proposal/DecisionRecord schema owned by FT-014 and FT-015.

## Runtime Decision Handling

Every agent invocation ends with exactly one project-owned runtime decision:

| Decision | Result |
|---|---|
| `speak` | Create a valid MessageEnvelope; may publish to Bus and project to UI if allowed. |
| `silent` | Create no MessageEnvelope and no Bus event; record trace/eval evidence. |
| `clarify` | Create a concise clarification MessageEnvelope for missing or stale data. |
| `escalate` | Create a Team Signal, Safety Block, governance route, or safety route envelope. |

Decision rules:

- raw provider output alone cannot choose publication authority;
- malformed, overlong, unsafe, or out-of-profile output is rejected, downgraded to
  `clarify`, escalated, or recorded as `silent` with trace evidence;
- `silent` cannot be used to hide provider failure as successful behavior;
- physical-action wording routes through Safety Gate before user-visible action wording
  or action-task creation;
- all decisions preserve trace refs and redaction status.

## MessageEnvelope Variants

Minimum feature-local MessageEnvelope fields extend the global contract:

```yaml
message_id: string
schema_version: string
created_at: datetime
farm_id: string
plant_id: string | null
agent_id: string
agent_profile_version: string
runtime_decision: speak | clarify | escalate
claim_type: observation | hypothesis | recommendation | safety_block | task_request | clarification | quoted_detail | team_signal | governance_summary
confidence: low | medium | high | not_applicable
requires_human_approval: boolean
safety_gate_required: boolean
safety_gate_status: not_required | required | blocked | cleared_for_approval | pending_approval
consumable_output: string
structured_payload: object
source_refs: []
evidence_refs: []
trace_ref: string
ui_projection_allowed: boolean
bus_publication_allowed: boolean
redaction_status: redacted | no_sensitive_fields
```

Variant rules:

- `cleared_for_approval` is the only Safety Gate clearance value in
  MessageEnvelope/Bus/UI-facing schemas and does not mean human approval.
- `observation` and `hypothesis` may be Bus-consumable only after adapter validation and
  scope/trust labels;
- adapter validation proves only that a model-produced payload matched schema, scope,
  redaction, and profile checks; it does not make adapted model observations,
  hypotheses, or recommendations `trusted`;
- `recommendation` implying physical action sets `safety_gate_required=true` and cannot
  project unsafe action wording before Safety Gate/approval rules allow it;
- `clarification` asks for missing/stale data and may create UI prompt projection;
- `task_request` proposes a backend task path but cannot create an action task without
  the owning task/safety features;
- `governance_summary` may include only approved compact typed facts from FT-015;
- `quoted_detail` is human-facing reference text and cannot become runtime authority by
  itself.

## Bus Publication Mapping

If `bus_publication_allowed=true`, the backend adapter may create one
`BusEventEnvelope`.

Minimum mapping:

```yaml
event_type: agent_message_published | agent_clarification_requested | agent_safety_blocked | agent_task_requested | agent_governance_summary_published
source_type: agent
source_id: message:<message_id>
payload:
  message_ref: message:<message_id>
  claim_type: string
  consumable_output: string
  structured_payload: object
  confidence: string
  safety_gate_status: string
  evidence_refs: []
trust_label: trusted | semi_trusted | untrusted_data
```

Publication rules:

- publisher is backend/harness adapter, never direct model response;
- Bus payload uses `consumable_output` and structured fields, not UI projection text;
- `trusted` Bus payloads are reserved for backend-owned policy facts, approval/decision
  records, or approved governance summaries; adapted model observations, hypotheses,
  and recommendations use `semi_trusted` when backed by validated internal refs, or
  `untrusted_data` when they carry user/uploaded/retrieved/provider-derived freeform
  content;
- Bus events include actor/Farm/Plant scope, allowed AgentProfile visibility, source
  refs, trace refs, and redaction status;
- timeline events may be referenced but cannot publish authoritative state by replay;
- duplicate publication attempts are rejected or idempotently ignored by message/event
  refs;
- raw model output, hidden reasoning, UI Feed content, admin UI notices, raw chat,
  unapproved proposals, provider memory, and secrets are forbidden Bus content.

## UI Feed Projection

UI Feed is human presentation only. Minimum projection behavior:

- MessageEnvelope may project to `UIFeedEvent` only when
  `ui_projection_allowed=true`;
- UI Feed stores display payloads, source message refs, task/approval refs, and safe
  presentation metadata;
- `visible_to_agents=false` and `consumable_by_agents=false` are mandatory;
- `ui_spoiler_note` is allowed only as human-readable explanation and cannot alter
  domain semantics;
- UI Feed may display Safety Block, clarification prompt, task card, approval card, or
  storage prompt refs, but agents must later retrieve underlying approved domain refs
  through the context builder instead of UI Feed replay;
- UI markdown cannot change claim type, safety status, Plant state, governance
  authority, or dataset trainability.

## Context Isolation Rules

Agent working context may include only validated Bus events, runtime records,
approved governance summaries, allowed memory refs, and source refs filtered by the
shared context builder.

Forbidden context sources:

- UI Feed cards, display payloads, spoiler notes, UI snapshots, or UI markdown;
- raw chat history as fact;
- raw provider output, hidden reasoning, provider memory, or Agno events;
- raw CompanionProposal text/rationale or unapproved governance discussion;
- admin UI notices or audit-view markdown;
- timeline replay as authoritative state;
- secrets, auth material, `.env` values, API keys, or credentials.

Untrusted user/uploaded/retrieved content that appears inside an allowed source remains
trust-labeled data and cannot become instructions.

## API / Service Surface To Refine In Tasks

Task decomposition may define exact backend services and schemas for:

- adapt AgentHarness output into runtime decision;
- create/validate MessageEnvelope;
- publish MessageEnvelope-derived BusEventEnvelope;
- project MessageEnvelope/domain refs to UIFeedEvent;
- list UI Feed events for authorized human display;
- verify context-filter input sources for agent runs;
- read silent decision trace summaries for authorized diagnostics.

Generated OpenAPI comes from implementation schemas later.

## Verification Targets

Required tests before FT-009 can be considered implemented:

- raw model/provider output cannot bypass runtime decision and MessageEnvelope
  validation;
- `silent` creates trace/eval evidence but no MessageEnvelope or Bus event;
- malformed, overlong, out-of-profile, or secret-containing output is rejected,
  downgraded, escalated, or redacted before publication;
- Bus publication uses MessageEnvelope refs and consumable structured fields, not UI
  projection text;
- UI Feed events always have `visible_to_agents=false` and
  `consumable_by_agents=false`;
- UI Feed, spoiler notes, admin UI text, raw chat, raw provider output, raw Agno
  events, and unapproved CompanionProposal content cannot enter agent context;
- physical-action recommendations route through Safety Gate before user-visible action
  wording or action-task creation;
- approved governance summary content is the only governance content allowed into
  agent context and remains `safety_gate_authority=not_granted`;
- pre-clearance physical-action wording must not be published to agent-consumable Bus
  context; only safe Safety Block, clarification, or approval-pending refs may be
  published before Safety Gate/approval clearance;
- timeline replay cannot publish authoritative Bus or Plant-state facts.

## Open Questions

No blocker for `/prd-to-tasks FT-009`. Exact endpoint names, UI display payload shapes,
message/event ID prefixes, and first-demo projection variants can be chosen during task
decomposition as long as MessageEnvelope validation, Bus publication, UI Feed isolation,
Safety Gate routing, and redaction constraints hold.
