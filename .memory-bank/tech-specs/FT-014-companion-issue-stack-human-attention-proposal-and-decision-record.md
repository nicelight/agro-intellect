---
description: Feature-local SDD tech spec for FT-014 Companion IssueStack, HumanAttentionNeeded, CompanionProposal, CompanionConclusion, and DecisionRecord.
status: active
feature_id: FT-014
owner: spec-improve
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/features/FT-014-companion-issue-stack-human-attention-proposal-and-decision-record.md
  - .memory-bank/requirements.md
  - .memory-bank/analysis/companion-issue-stack-decision-governance.md
  - .memory-bank/contracts/agent-harness.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/contracts/safety-gate.md
  - .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
  - .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
  - .memory-bank/tech-specs/FT-008-permission-aware-context-builder-and-agent-memory-record.md
  - .memory-bank/tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md
  - .memory-bank/tech-specs/FT-012-safety-gate-for-physical-action-advice.md
  - .memory-bank/tech-specs/FT-013-tasks-approvals-and-follow-up-outcomes.md
  - agents-best-practices
---
# FT-014 Companion IssueStack, HumanAttention, Proposal, And DecisionRecord Tech Spec

## Purpose

Define the minimum feature-local design needed before task decomposition for typed
Plant-scoped Companion governance state: `IssueStack`, `HumanAttentionNeeded`,
`CompanionProposal`, `CompanionConclusion`, and `DecisionRecord`.

This spec applies `agents-best-practices`: Companion may propose and coordinate, but
the harness/backend validates schemas, resolves ActorContext, enforces permissions,
records traces, and returns structured observations. Companion does not approve itself
and does not bypass backend, Safety Gate, context-builder, or task rules.

## Scope

In scope:

- Plant-scoped issue state and current focus;
- human attention marker state;
- proposal creation, versioning, supersede policy, and decision eligibility;
- DecisionRecord authority limits and allowed workflow effects;
- governance audit refs, Bus/UI handoff refs, and anti-leak rules;
- verification that governance approval and Safety Gate approval remain separate.

Out of scope:

- approved governance summary schema and context retrieval owned by FT-015;
- Safety Gate decision, physical-action approval, and action-task unlock owned by
  FT-012 and FT-013;
- UI component layout and markdown styling beyond non-authority rules;
- Farm-level governance, Boss override semantics, time-based proposal expiry, broad
  workflow orchestration, or automated actuation.

## Authority And Ownership

PostgreSQL/read model is mutable authority for Companion governance records. Timeline,
Bus, UI Feed, raw chat, raw provider output, AgentMemoryRecord, and UI markdown may
reference or present governance state but cannot replace it.

Every governance mutation must:

1. resolve ActorContext;
2. check Farm/Plant scope, active Plant state, role preset, and PlantAccessGrant;
3. validate a strict typed command schema;
4. reject unknown properties for command payloads;
5. persist authoritative state before Bus/UI/timeline success refs are published;
6. redact secrets/auth material before persistence, publication, traces, or exports.

## IssueStack And Current Focus

Minimum `IssueStackItem` semantics:

```yaml
issue_id: string
schema_version: string
created_at: datetime
updated_at: datetime
farm_id: string
plant_id: string
kind: finding | gap | problem | open_question | disagreement
severity: P0 | P1 | P2 | P3
status: open | current | closed | superseded
title: string
bounded_summary: string
current_focus_reason: string | null
waiting_on: none | consultant | engineer | boss | any_human | agent
source_refs: []
trace_refs: []
redaction_status: redacted | no_sensitive_fields
```

Rules:

- IssueStack is explicit state, not hidden Companion memory.
- MVP issues are Plant-scoped; Farm-level issue stacks are deferred.
- At most one issue per Plant is `current` unless a later spec adds parallel focus.
- Companion may open, focus, close, or supersede issues through backend rules.
- Closing an issue means discussion is resolved enough; it is not a binding system
  decision and does not authorize backend action by itself.
- Raw chat snippets and UI markdown are not stored as agent-consumable facts; use
  bounded summaries plus source refs.

## HumanAttentionNeeded

Minimum `HumanAttentionNeeded` semantics:

```yaml
attention_id: string
schema_version: string
created_at: datetime
resolved_at: datetime | null
farm_id: string
plant_id: string
issue_id: string
status: raised | acknowledged | resolved
reason_code: decision_needed | missing_input | disagreement | blocked_workflow | review_requested
needed_role: engineer | boss | any_human
raised_by_agent_ref: companion
acknowledged_by_actor_ref: string | null
source_refs: []
trace_ref: string
redaction_status: redacted | no_sensitive_fields
```

Rules:

- HumanAttentionNeeded is a marker only; it is not approval.
- Consultant may respond as advisory input but cannot satisfy a decision marker when a
  governance decision is required.
- Acknowledgement does not create DecisionRecord unless a valid proposal decision is
  also submitted.

## CompanionProposal

Minimum `CompanionProposal` semantics:

```yaml
proposal_id: string
schema_version: string
created_at: datetime
farm_id: string
plant_id: string
issue_id: string
proposal_version: integer
status: pending | approved | rejected | superseded
proposal_summary: string
recommended_next_direction: string
allowed_workflow_effect: none | continue_discussion | request_check_task | request_measurement_task | request_follow_up_task
created_by_agent_ref: companion
supersedes_proposal_ref: string | null
source_refs: []
trace_ref: string
visible_to_humans: true
visible_to_agents: false
redaction_status: redacted | no_sensitive_fields
```

Proposal rules:

- no parallel pending proposal may exist for the same Farm/Plant/issue;
- creating a new pending proposal for the same issue automatically marks the previous
  pending proposal `superseded`;
- superseded proposals cannot be approved, rejected as operative, or become agent facts;
- `proposal_summary` and `recommended_next_direction` are bounded human-visible fields,
  not raw proposal rationale;
- raw proposal text, rationale, raw chat, hidden reasoning, UI markdown, and
  unapproved discussion remain non-consumable by agents before and after decision;
- proposal creation does not mutate Plant state, create tasks, create approvals, or
  authorize physical action.

## CompanionConclusion

Minimum `CompanionConclusion` semantics:

```yaml
conclusion_id: string
schema_version: string
created_at: datetime
farm_id: string
plant_id: string
issue_id: string
conclusion_summary: string
requires_decision_record: boolean
decision_record_ref: string | null
source_refs: []
trace_ref: string
redaction_status: redacted | no_sensitive_fields
```

CompanionConclusion can close discussion or explain a proposed path. It is not binding
authority unless a valid DecisionRecord exists and backend rules allow the requested
effect.

## DecisionRecord

Minimum `DecisionRecord` semantics:

```yaml
decision_id: string
schema_version: string
created_at: datetime
farm_id: string
plant_id: string
issue_id: string
proposal_id: string
proposal_version: integer
decision: approved | rejected
decision_summary: string
allowed_workflow_effect: none | continue_discussion | request_check_task | request_measurement_task | request_follow_up_task
decided_by_actor_ref: string
decider_role: engineer | boss
source_refs: []
trace_ref: string
safety_gate_authority: not_granted
redaction_status: redacted | no_sensitive_fields
```

Decision rules:

- DecisionRecord requires a current pending CompanionProposal version and resolved
  ActorContext for the deciding human.
- Boss and Engineer may approve/reject governance proposals for authorized active
  Plant scope. `plant_approve_actions` is not required because governance approval is
  not physical-action approval.
- Consultant input remains advisory and cannot create DecisionRecord in MVP.
- The first valid decision records the proposal outcome; later duplicate decision
  attempts on the same proposal version return conflict/denied without changing state.
- Rejected decisions create no operative workflow effect.
- Approved decisions may direct only the listed workflow effects through backend rules.
- DecisionRecord cannot mutate Plant state, create `action_task`, authorize physical
  action, replace Safety Gate approval, grant `can_train_on`, or turn raw chat into
  fact.

## Backend Workflow Effects

Allowed workflow effects are deliberately small:

- `continue_discussion`: records direction for Companion/UI flow only;
- `request_check_task`: asks FT-013 task logic to create or propose a low-risk
  `check_task` if ActorContext and PlantAccessGrant allow it;
- `request_measurement_task`: asks FT-013 task logic to create or propose a
  `measurement_task`;
- `request_follow_up_task`: asks FT-013 task logic to create or propose a
  `follow_up_task`;
- `none`: no downstream effect.

Backend rules decide whether a requested task is actually allowed. DecisionRecord may
request safe task paths, but it never creates `action_task` and never bypasses task,
authorization, Safety Gate, or redaction checks.

## Bus, UI, Timeline, And Context Handoff

Allowed publication refs after authoritative persistence:

- governance issue opened/focused/closed;
- human attention raised/acknowledged/resolved;
- proposal created/superseded/decided;
- DecisionRecord created;
- safe workflow-effect request accepted or denied.

Rules:

- UI Feed may display governance cards/prompts but remains presentation-only.
- Bus may receive compact refs and bounded summaries when marked consumable by the
  owning adapter; raw proposal/rationale/chat remains forbidden.
- FT-015 is the only route for an approved governance summary to become agent context.
- Timeline stores append-only refs and redacted summaries only.
- Failed, denied, stale, superseded, unauthorized, or malformed governance mutations
  must not publish success events.

## API / Service Surface To Refine In Tasks

Task decomposition may define exact backend services and schemas for:

- open/focus/close/supersede IssueStackItem;
- raise/acknowledge/resolve HumanAttentionNeeded;
- create CompanionProposal and supersede previous pending proposal for an issue;
- approve/reject current proposal version and create DecisionRecord;
- request allowed workflow effect from a valid DecisionRecord;
- read authorized governance state, redacted timeline refs, and trace summaries.

Generated OpenAPI comes from implementation schemas later.

## Verification Targets

Required tests before FT-014 can be considered implemented:

- IssueStack, HumanAttentionNeeded, CompanionProposal, CompanionConclusion, and
  DecisionRecord are typed, Farm/Plant/ActorContext scoped records;
- no parallel pending proposal exists for the same Plant issue;
- creating a new proposal supersedes the previous pending proposal;
- superseded proposal cannot be approved and cannot become agent context;
- Consultant cannot create DecisionRecord in MVP;
- Boss/Engineer decision works only for authorized active Plant scope;
- DecisionRecord records `safety_gate_authority=not_granted`;
- DecisionRecord cannot mutate Plant state, create `action_task`, authorize physical
  action, replace Safety Gate approval, or grant trainability;
- allowed workflow effects can request only safe check/measurement/follow-up paths
  through backend rules;
- raw proposal text, rationale, raw chat, UI markdown, hidden reasoning, UI Feed, and
  unapproved discussion cannot enter Bus/context as facts;
- denied or failed governance mutations do not publish success Bus/UI/timeline refs.

## Open Questions

No blocker for `/prd-to-tasks FT-014`. Exact route names, proposal card layout, issue
severity labels, idempotency key shape, and first-demo UI controls can be chosen during
task decomposition as long as typed governance state, supersede behavior, DecisionRecord
authority limits, context isolation, and Safety Gate separation hold.
