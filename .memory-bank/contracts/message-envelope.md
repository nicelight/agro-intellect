---
description: MessageEnvelope, runtime decision, Agent Chat Bus publication, and UI Feed projection contract.
status: active
owner: architecture
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/agent-harness.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/invariants.md
---
# Message Envelope Contract

## Purpose

`MessageEnvelope` is the project-owned wrapper for publishable agent output after
harness runtime decision handling. It separates model/provider output from domain
working context and UI presentation.

Raw model output is not a MessageEnvelope.

## Runtime Decisions

Each agent invocation ends with exactly one runtime decision:

- `speak`: create a publishable MessageEnvelope.
- `silent`: no MessageEnvelope and no Bus publication; trace/audit evidence remains.
- `clarify`: publish a short missing-data or targeted clarification request.
- `escalate`: publish a Team Signal, Safety Block, or governance/safety route.

Runtime decision is owned by project harness/adapters, not by raw provider output alone.

## MessageEnvelope

Minimum global fields:

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
safety_gate_status: not_required | required | blocked | cleared | pending_approval
consumable_output: string
source_refs: []
evidence_refs: []
trace_ref: string
ui_projection_allowed: boolean
bus_publication_allowed: boolean
redaction_status: redacted | no_sensitive_fields
```

Feature specs own exact payload variants.

## Validation Rules

- MessageEnvelope content must be concise and bounded.
- Claims must be compatible with the AgentProfile competence boundary.
- Recommendations implying physical action must route to Safety Gate before user-visible
  action wording or `action_task` creation.
- Agent-labeled hypotheses cannot become confirmed Plant state without owning
  runtime/state rules and human/follow-up evidence.
- Raw provider output, hidden reasoning, unapproved governance content, UI markdown, and
  secrets are rejected before envelope creation.
- Malformed output is rejected, downgraded to `clarify`, or escalated with trace
  evidence.

## Bus Publication

If `bus_publication_allowed=true`, the MessageEnvelope may produce a
`BusEventEnvelope` under [.memory-bank/contracts/agent-chat-bus.md](agent-chat-bus.md).

Bus content must use `consumable_output` and structured fields, not UI projection text.

## UIFeedEvent

UI Feed is a human-facing projection. Minimum global fields:

```yaml
ui_event_id: string
schema_version: string
created_at: datetime
farm_id: string
plant_id: string | null
source_message_id: string | null
visible_to_agents: false
consumable_by_agents: false
presentation_kind: message | card | prompt | task_card | approval_card | storage_prompt | spoiler_note
display_payload: object
source_refs: []
redaction_status: redacted | no_sensitive_fields
```

UI Feed content is never agent working context. A future agent run must retrieve the
underlying approved domain refs through context builder, not UI Feed replay.

## Spoiler Notes

`ui_spoiler_note` may provide human-readable explanation in UI Feed only.

Rules:

- `visible_to_agents=false`
- `consumable_by_agents=false`
- may reference a MessageEnvelope or task but cannot alter domain semantics;
- cannot become Bus content, Plant fact, governance authority, or dataset evidence by
  itself.

## Silent Decision

`silent` creates no MessageEnvelope and no Bus event, but must record trace/eval evidence:

- agent id/version;
- reason category;
- context refs used;
- budget/tool status;
- final status.

Do not fake useful agent behavior by silently suppressing provider errors without a
structured trace and safe UI/backend handling.

## Verification

Feature specs must test:

- raw model output cannot bypass MessageEnvelope;
- `silent` produces trace but no Bus event;
- UI Feed projection cannot be consumed by agents;
- unapproved CompanionProposal text remains non-consumable;
- physical-action recommendation routes to Safety Gate;
- malformed or overlong output is rejected/downgraded;
- secret-like content is redacted or rejected.
