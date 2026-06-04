---
description: Agent Chat Bus working-event contract for MVP v2.
status: active
owner: architecture
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/agent-harness.md
  - .memory-bank/invariants.md
---
# Agent Chat Bus Contract

## Purpose

The Agent Chat Bus is the domain-owned working event stream for agent-consumable
events. It is not UI Feed, not raw chat, not timeline replay, and not Agno workflow
events.

Only validated, permission-scoped, adapter-produced events may enter the Bus.

## BusEventEnvelope

Minimum global fields:

```yaml
event_id: string
event_type: string
schema_version: string
created_at: datetime
farm_id: string
plant_id: string | null
actor_ref: string | null
source_type: user | agent | system | task | safety | governance | dataset
source_id: string
topic: string
payload: object
source_refs: []
consumable_by_agents: true
trust_label: trusted | semi_trusted | untrusted_data
visibility_scope:
  farm_id: string
  plant_id: string | null
  allowed_agent_ids: []
trace_ref: string | null
redaction_status: redacted | no_sensitive_fields
```

Feature specs own exact event-specific payload schemas.

## Allowed Event Families

- user-submitted Plant observations after backend validation;
- accepted photo refs and metadata after upload/catalog validation;
- manual measurement refs and freshness/trust labels;
- validated agent conclusions after MessageEnvelope adaptation;
- clarification requests;
- Safety Block or Safety Gate route events;
- task, approval, and outcome refs;
- compact approved governance summary facts;
- dataset governance status refs;
- harness structured observation summaries when explicitly consumable.

## Forbidden Bus Content

The Bus must not include:

- UI Feed cards, markdown, spoiler notes, or presentation-only strings;
- raw chat history as fact;
- raw CompanionProposal text/rationale;
- unapproved governance discussion;
- raw model output before adapter validation;
- hidden model reasoning;
- provider memory;
- raw Agno Team synthesis or workflow events as domain facts;
- secrets, API keys, tokens, credentials, `.env` values, or auth material;
- unauthorized Plant/Farm data.

## Publication Rules

- Every Bus event must be actor/Farm/Plant scoped where relevant.
- Publisher must be a backend/domain adapter or harness component, not a direct model
  response.
- Runtime state changes should publish refs after persistence, not before authority is
  established.
- Timeline events may be referenced, but timeline replay cannot publish authoritative
  state by itself.
- Revoked PlantAccessGrant blocks future retrieval of Bus events for that actor/context.

## Consumption Rules

- Agents consume Bus events only through the shared context builder.
- Context builder filters by ActorContext, PlantAccessGrant, AgentProfile, source refs,
  trust/freshness labels, and allowed event families.
- UI Feed projection may display Bus-derived content, but UI Feed content must not be
  replayed into the Bus as agent context.
- Untrusted data in payloads must remain trust-labeled when included in context.

## Ordering And Idempotency

- `event_id` is unique.
- Consumers should not infer state solely from event ordering when PostgreSQL/read model
  has the current authority.
- Duplicate publication attempts must be detectable through IDs, source refs, or
  feature-level idempotency keys.
- Out-of-order events must not overwrite current runtime state.

## Verification

Feature specs must test:

- unauthorized event retrieval is filtered;
- UI Feed content cannot enter Bus;
- unapproved proposals cannot become consumable events;
- malformed events are rejected;
- secret-like payloads are redacted or rejected;
- timeline replay cannot mutate runtime authority.
