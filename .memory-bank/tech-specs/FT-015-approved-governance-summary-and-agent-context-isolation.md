---
description: Feature-local SDD tech spec for FT-015 approved governance summary and strict agent context isolation.
status: active
feature_id: FT-015
owner: spec-improve
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/features/FT-015-approved-governance-summary-and-agent-context-isolation.md
  - .memory-bank/requirements.md
  - .memory-bank/contracts/agent-harness.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/tech-specs/FT-008-permission-aware-context-builder-and-agent-memory-record.md
  - .memory-bank/tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md
  - .memory-bank/tech-specs/FT-014-companion-issue-stack-human-attention-proposal-and-decision-record.md
  - .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
  - agents-best-practices
---
# FT-015 Approved Governance Summary And Agent Context Isolation Tech Spec

## Purpose

Define the minimum feature-local design needed before task decomposition for compact
approved governance summaries derived from valid `DecisionRecord` records and for the
context-builder filters that keep raw governance, chat, rationale, and UI content out
of agent working context.

This spec applies `agents-best-practices`: context is assembled just in time, trust
labels and source refs are explicit, untrusted/presentation content is data or UI only,
and compaction cannot upgrade raw discussion into trusted facts.

## Scope

In scope:

- approved governance summary schema;
- derivation from FT-014 DecisionRecord;
- source refs and retrieval permissions;
- context-builder inclusion/exclusion rules;
- Bus/MessageEnvelope handoff for `governance_summary` claim type;
- anti-leak tests for raw proposal, rationale, raw chat, UI markdown, hidden reasoning,
  and unapproved discussion.

Out of scope:

- FT-014 proposal/decision state machine;
- Safety Gate approval and physical-action task unlock owned by FT-012 and FT-013;
- UI proposal card layout and raw human discussion display;
- broad RAG over chat transcripts or full governance history.

## Authority And Derivation

`ApprovedGovernanceSummary` is derived only from a valid FT-014 `DecisionRecord`.
PostgreSQL/read model owns the current summary record or projection. UI Feed, raw chat,
CompanionProposal text, rationale, timeline snapshots, Bus events, MessageEnvelope
display text, and AgentMemoryRecord cannot create approved summaries by themselves.

Creation rules:

1. load DecisionRecord from authoritative governance state;
2. verify `decision=approved`;
3. verify proposal version was current and not superseded when decided;
4. verify Farm/Plant scope and active ActorContext for the original decision;
5. copy only allowed compact fields;
6. set `safety_gate_authority=not_granted`;
7. store source refs and trace refs;
8. redact before any Bus/UI/context exposure.

Rejected, superseded, malformed, unauthorized, or redaction-failed proposal/decision
paths produce no operative approved governance summary.

## ApprovedGovernanceSummary Shape

Minimum semantics:

```yaml
governance_summary_id: string
schema_version: string
created_at: datetime
farm_id: string
plant_id: string
issue_id: string
proposal_id: string
proposal_version: integer
decision_id: string
decision: approved
decision_summary: string
allowed_workflow_effect: none | continue_discussion | request_check_task | request_measurement_task | request_follow_up_task
decider_role: engineer | boss
decided_at: datetime
source_refs: []
trace_ref: string
safety_gate_authority: not_granted
trust_label: trusted
authority_role: governance_summary
redaction_status: redacted | no_sensitive_fields
```

Allowed content is limited to the fields above or exact equivalents. The summary must
not include raw proposal text, raw rationale, raw chat, UI markdown, unapproved
discussion, hidden model reasoning, provider memory, screenshots, or freeform
transcripts.

## Context Builder Retrieval

The context builder may include approved governance summaries only when all filters
pass:

- ActorContext is resolved;
- Farm/Plant scope matches the run;
- current actor has PlantAccessGrant visibility for the Plant;
- Plant is active for normal operation, unless an explicit authorized history mode is
  requested;
- AgentProfile allows `governance_summary` source family;
- source DecisionRecord and summary have redaction success;
- summary is not revoked/filtered by access changes;
- result-size and source-count budgets allow inclusion.

Context item mapping:

```yaml
source_family: governance_summary
trust_label: trusted
freshness_label: not_applicable
authority_role: governance_summary
source_refs:
  - governance_summary:<id>
  - decision:<decision_id>
  - proposal:<proposal_id>:v<proposal_version>
evidence_refs: []
```

Revoked PlantAccessGrant blocks future retrieval for that actor/context without deleting
the retained governance audit record.

## Forbidden Context Sources

The context builder must exclude:

- raw CompanionProposal text and rationale;
- raw governance chat or discussion history;
- unapproved, rejected, or superseded proposal content;
- UI Feed cards, display payloads, markdown, screenshots, and spoiler notes;
- raw provider output, hidden reasoning, provider memory, and Agno events;
- AgentMemoryRecord that summarizes unapproved governance content;
- timeline replay as governance authority;
- secrets, auth material, `.env` values, API keys, credentials, and raw logs.

If forbidden content appears inside an otherwise allowed record, the context builder
must redact, truncate, downgrade, or reject the item. It must not summarize forbidden
content into trusted facts during compaction.

## Bus And MessageEnvelope Handoff

Approved governance summary may publish through FT-009 as:

- `MessageEnvelope.claim_type=governance_summary`;
- `BusEventEnvelope.source_type=governance`;
- payload carrying summary refs and compact allowed fields only.

Rules:

- Bus payloads use the approved summary fields, not UI projection text.
- `safety_gate_authority=not_granted` is mandatory in agent-consumable payloads.
- UI Feed may show human-friendly governance status, but agents later retrieve the
  approved summary record through context builder, never the UI card.
- Summary publication cannot create tasks, approvals, action tasks, Plant-state
  mutations, or trainability changes by itself.

## Compaction And Memory Boundaries

Compaction may preserve `governance_summary_id`, DecisionRecord refs, allowed workflow
effect, and `safety_gate_authority=not_granted`.

Compaction must not:

- include raw proposal/rationale/chat;
- convert unapproved discussion into approved facts;
- erase superseded/rejected status;
- widen ActorContext or PlantAccessGrant scope;
- change the summary's trust label or authority role.

AgentMemoryRecord may store a `governance_summary_ref` only when the source is an
approved summary and retrieval remains scoped by FT-008. Memory remains non-authority
and cannot replace the summary record.

## API / Service Surface To Refine In Tasks

Task decomposition may define exact backend services and schemas for:

- derive approved governance summary from DecisionRecord;
- read summaries for authorized context-builder use;
- publish governance summary Bus/MessageEnvelope refs;
- filter summaries after PlantAccessGrant changes;
- run anti-leak and context isolation eval fixtures;
- read redacted governance-summary trace diagnostics.

Generated OpenAPI comes from implementation schemas later.

## Verification Targets

Required tests before FT-015 can be considered implemented:

- approved summary is created only from a valid approved DecisionRecord;
- rejected, superseded, pending, malformed, unauthorized, or redaction-failed proposal
  paths create no operative summary;
- summary schema includes only compact allowed fields and mandatory
  `safety_gate_authority=not_granted`;
- raw proposal text, raw rationale, raw chat, UI markdown, UI Feed, screenshots,
  unapproved discussion, hidden reasoning, and provider memory are excluded from
  context;
- revoked PlantAccessGrant blocks future summary retrieval for that actor/context;
- Bus/MessageEnvelope governance-summary payload uses approved compact fields, not UI
  projection text;
- compaction preserves summary refs and authority labels without upgrading forbidden
  content;
- summary cannot mutate Plant state, create tasks by itself, create `action_task`,
  authorize physical action, replace Safety Gate approval, or grant trainability.

## Open Questions

No blocker for `/prd-to-tasks FT-015`. Exact service names, UI wording, context item
count limits, trace-ref format, and first-demo projection layout can be chosen during
task decomposition as long as approved-summary derivation, raw-content exclusion,
permission filtering, and Safety Gate separation hold.
