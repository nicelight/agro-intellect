---
description: Feature-local SDD tech spec for FT-013 task, approval, action_task, and follow-up outcome semantics.
status: active
feature_id: FT-013
owner: spec-improve
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/features/FT-013-tasks-approvals-and-follow-up-outcomes.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/contracts/safety-gate.md
  - .memory-bank/contracts/agent-harness.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
  - .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
  - .memory-bank/tech-specs/FT-004-authorized-plant-selector-and-daily-check-in.md
  - .memory-bank/tech-specs/FT-006-runtime-plant-state-history-and-timeline-audit.md
  - .memory-bank/tech-specs/FT-007-shared-agent-harness-and-agent-profile-runtime.md
  - .memory-bank/tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md
  - .memory-bank/tech-specs/FT-011-plant-state-trust-and-hydroponics-advisor.md
  - .memory-bank/tech-specs/FT-012-safety-gate-for-physical-action-advice.md
  - agents-best-practices
---
# FT-013 Tasks, Approvals, And Follow-Up Outcomes Tech Spec

## Purpose

Define the minimum feature-local design needed before task decomposition for check
tasks, measurement tasks, follow-up tasks, Safety Gate approval requests/results,
human-performed `action_task` records, and follow-up outcomes.

This spec applies `agents-best-practices`: agents may propose task or approval actions
through typed tool/action proposals, but the backend validates schemas, permissions,
approval state, and audit refs before creating or mutating records. Draft/propose and
commit are separate for safety-sensitive actions.

## Scope

In scope:

- `Task` types: `check_task`, `measurement_task`, `follow_up_task`, and `action_task`;
- task status lifecycle and actor/Farm/Plant scoping;
- `Approval` request/result records for physical actions;
- exact action unlock semantics from FT-012 SafetyGateDecision;
- follow-up `Outcome` semantics, including improved/worsened/unchanged/no-data;
- Bus/UI/history/timeline refs for task, approval, and outcome records;
- audit/eval requirements proving no automated actuation.

Out of scope:

- Safety Gate classification, decision, and approver eligibility owned by FT-012;
- Hydroponics Advisor wording and Plant State trust behavior owned by FT-011;
- Companion governance proposal/DecisionRecord schema owned by FT-014 and FT-015;
- Boss Admin access management owned by FT-003;
- automatic device control, sensor runtime dependency, scheduling engine, notifications,
  email delivery, or broad farm-management task system.

## Authority And Ownership

PostgreSQL/read model is mutable authority for `Task`, `Approval`, and `Outcome`.
Timeline JSONL, Bus events, UI Feed cards, raw recommendation text, raw chat, and
MessageEnvelope display text are refs or projections only.

Every task, approval, and outcome mutation must:

1. resolve ActorContext;
2. check single Farm scope, active Plant state, and PlantAccessGrant;
3. validate payload schema and reject unknown properties for command payloads;
4. record actor or agent proposal attribution;
5. create source/evidence refs and timeline/audit refs where required;
6. redact secrets and auth material before publication or trace visibility.

## Task Types

Minimum `Task` semantics:

```yaml
task_id: string
schema_version: string
created_at: datetime
updated_at: datetime
farm_id: string
plant_id: string
task_type: check_task | measurement_task | follow_up_task | action_task
status: open | in_progress | completed | cancelled | blocked
created_by_actor_ref: string | null
created_by_agent_ref: string | null
assigned_actor_ref: string | null
source_message_ref: string | null
safety_gate_ref: string | null
approval_ref: string | null
source_refs: []
evidence_refs: []
timeline_refs: []
trace_ref: string | null
redaction_status: redacted | no_sensitive_fields
```

Task rules:

- `check_task` requests human observation or visual check and does not require
  physical-action approval.
- `measurement_task` requests pH/EC or similar measurement and does not require
  physical-action approval.
- `follow_up_task` requests later outcome collection after a check, measurement, or
  action.
- `action_task` is created only after FT-012 has produced a valid
  `cleared_for_approval` decision and FT-013 has recorded authorized human approval.
- Consultant does not create domain task/recommendation/action records by default.
- Task records never trigger automated device execution.

## Task Status Lifecycle

Allowed transitions:

| From | To | Guardrail |
|---|---|---|
| none | `open` | Authorized create path; `action_task` additionally requires valid approval. |
| `open` | `in_progress` | Authorized actor with Plant work access. |
| `open` or `in_progress` | `completed` | Requires completion evidence or explicit no-data/blocked reason where applicable. |
| `open` or `in_progress` | `cancelled` | Authorized actor and cancellation reason. |
| `open` or `in_progress` | `blocked` | Safe reason, such as missing access, stale evidence, or rejected approval. |
| `blocked` | `open` | Only after blocker source changes and authorization is rechecked. |

Rules:

- archived Plants block new normal task creation and mutation except authorized
  history/audit closure paths chosen during task decomposition;
- revoked PlantAccessGrant blocks future task mutation for that actor without deleting
  retained task/audit evidence;
- failed task creation must not publish successful Bus/UI/timeline refs.

## Approval Records

Minimum `Approval` semantics:

```yaml
approval_id: string
schema_version: string
created_at: datetime
decided_at: datetime | null
expires_at: datetime | null
farm_id: string
plant_id: string
safety_gate_ref: string
proposal_ref: string
status: requested | approved | rejected | expired | revoked
requested_by_actor_ref: string | null
requested_by_agent_ref: string | null
decided_by_actor_ref: string | null
decision_reason: string | null
approval_scope: exact_proposal_only
source_refs: []
evidence_refs: []
timeline_refs: []
trace_ref: string
redaction_status: redacted | no_sensitive_fields
```

Approval rules:

- Approval request creation requires a current FT-012 `cleared_for_approval` decision.
- Approval result requires an eligible human approver from FT-012 and fresh ActorContext.
- The model, Companion, AgentMemoryRecord, DecisionRecord, UI Feed, or raw chat cannot
  approve.
- Approval is scoped to the exact proposal and expires when Safety Gate freshness,
  Plant scope, PlantAccessGrant, ActorContext, or proposal wording/parameters become
  invalid.
- Rejected, expired, revoked, or stale approval creates no `action_task`.
- Approval never authorizes automated actuation.

## Action Task Unlock

Creating `action_task` requires all of:

1. active Plant and valid Farm/Plant scope;
2. resolved ActorContext for the deciding human;
3. PlantAccessGrant and role eligibility from FT-012;
4. valid `SafetyGateDecision.decision=cleared_for_approval`;
5. `Approval.status=approved` scoped to the exact proposal;
6. source/evidence refs retained;
7. no stale or changed proposal context;
8. no device command or external side effect.

`action_task` records describe human-performed work only. They may include checklist
steps or safe summary text after approval, but must not call actuators, emit device
commands, or imply automatic execution.

## Follow-Up Outcomes

Minimum `Outcome` semantics:

```yaml
outcome_id: string
schema_version: string
created_at: datetime
farm_id: string
plant_id: string
task_ref: string
outcome_type: improved | worsened | unchanged | no_data | conflict | superseded
recorded_by_actor_ref: string
summary: string
evidence_refs: []
measurement_refs: []
photo_refs: []
observation_refs: []
timeline_refs: []
source_refs: []
redaction_status: redacted | no_sensitive_fields
```

Outcome rules:

- follow-up after approved physical actions should be requested when useful for the
  first-demo flow, but exact due windows can be chosen during task decomposition;
- `no_data` is explicit and cannot backfill success;
- `conflict` preserves refs and asks for re-check instead of silent resolution;
- `superseded` retains old outcome refs and points to the replacement where useful;
- outcomes may provide evidence for Plant State trust updates only through FT-006 and
  FT-011 rules; outcome text alone cannot confirm Plant state.

## Agent And Tool Proposal Boundary

Task & Follow-up Agent proposals are typed, narrow, and permissioned:

- `propose_check_task`
- `propose_measurement_task`
- `propose_follow_up_task`
- `request_physical_action_approval`
- `create_action_task_from_approved_proposal`
- `record_follow_up_outcome`

Commit-style tools that create or mutate records require backend policy checks. Safety
sensitive commits require FT-012 decision refs and human approval refs. Every proposal
receives exactly one structured observation: success, denied, approval_required, error,
aborted, or blocked.

Unknown tools, invalid arguments, stale approval refs, unauthorized Plant scope, and
prompt-injection-like attempts to bypass approval return structured observations and do
not mutate records.

## Bus, UI, Timeline, And History Handoff

Allowed event families:

- task created or status changed;
- approval requested or decided;
- outcome recorded;
- safety/task block refs;
- follow-up requested.

Publication rules:

- publish refs only after authoritative record persistence;
- UI Feed may display task and approval cards but remains presentation-only;
- Bus payloads use structured refs and bounded summaries, not raw UI text;
- timeline refs are append-only audit/export evidence and cannot recreate authority by
  replay;
- failed or denied mutations must not publish success events.

## API / Service Surface To Refine In Tasks

Task decomposition may define exact backend services and schemas for:

- create/list/update check, measurement, follow-up, and action tasks;
- create approval request from a `cleared_for_approval` SafetyGateDecision;
- approve/reject/expire/revoke Approval;
- create `action_task` from approved exact proposal;
- record and supersede Outcome;
- read authorized task/approval/outcome history;
- run task/approval/outcome eval fixtures.

Generated OpenAPI comes from implementation schemas later.

## Verification Targets

Required tests before FT-013 can be considered implemented:

- check and measurement tasks can be created without physical-action approval when
  ActorContext and PlantAccessGrant allow the operation;
- Consultant cannot create domain task/recommendation/action records by default;
- `action_task` cannot be created without Safety Gate clearance and authorized human
  approval;
- rejected, expired, revoked, stale, or mismatched approval creates no `action_task`;
- Boss and eligible Engineer approval paths create only human-performed action tasks;
- no automated actuation tool, command, external side effect, or device execution path
  exists;
- missing/revoked PlantAccessGrant blocks task, approval, and outcome mutations;
- follow-up outcomes preserve evidence refs and explicit `no_data` semantics;
- outcome text alone cannot promote confirmed Plant state;
- governance DecisionRecord cannot create `action_task` or replace Safety Gate
  approval;
- task, approval, and outcome Bus/UI/timeline refs publish only after authoritative
  persistence and remain redacted.

## Open Questions

No blocker for `/prd-to-tasks FT-013`. Exact route names, due-date defaults, assignment
UX, first-demo follow-up window, status labels, pagination, and enum spelling can be
chosen during task decomposition as long as task/approval/action/outcome authority,
draft/commit separation, exact approval scoping, audit refs, and no automated actuation
hold.
