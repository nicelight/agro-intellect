---
description: Global Companion governance lifecycle boundary for MVP v2.
status: active
type: state
last_updated: 2026-07-06
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
---
# Companion Governance

## Scope

Companion Governance defines the Plant-scoped typed workflow for IssueStack,
HumanAttentionNeeded, CompanionProposal, CompanionConclusion, DecisionRecord,
and approved governance summaries. It is not Safety Gate approval, Plant-state
confirmation, raw chat authority, or action-task authority.

Exact DB fields, endpoint schemas, workflow-effect catalog, and UI behavior
belong to `/prd-to-tasks FT-013`.

## Scope Boundaries

- Defines: global governance state boundaries, proposal supersede rule,
  DecisionRecord authority limits, approved summary consumability, and
  verification requirements.
- Out of scope: exact proposal payload shape, UI conversation layout, task route
  schemas, or Companion implementation internals.
- Related specs:
  - [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md):
    defines approved governance summary consumability.
  - [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): defines
    human-facing projection.
  - [.memory-bank/states/safety-action-lifecycle.md](safety-action-lifecycle.md):
    defines physical-action approval separation.
  - [.memory-bank/states/plants/plant-and-access-lifecycle.md](plants/plant-and-access-lifecycle.md):
    defines the archived-Plant operational guard.

## Lifecycle Shape

Feature-local specs may refine fields, but Companion governance must preserve:

- `IssueStack`
- `HumanAttentionNeeded`
- `CompanionProposal`
- `CompanionConclusion`
- `DecisionRecord`
- compact approved governance summary

Proposal states must include:

- `pending`
- `approved`
- `rejected`
- `superseded`

Decision records must include:

- `decision_record_id`
- `plant_id`
- `issue_id`
- `proposal_id`
- `decision`
- `decision_summary`
- `allowed_workflow_effect`
- `decider_ref`
- `decided_at`
- `source_refs`
- `safety_gate_authority=not_granted`

## Rules

- No parallel pending proposals may exist for the same Plant-scoped issue.
- A new proposal for the same Plant issue supersedes the previous pending
  proposal.
- Superseded proposals are not approvable and cannot become agent facts.
- DecisionRecord may direct Plant-scoped discussion/workflow or safe check,
  measurement, or follow-up task requests through backend rules.
- DecisionRecord must not mutate Plant state, create `action_task`, authorize
  physical action, replace Safety Gate approval, or turn raw chat into fact.
- Agents may consume only compact approved governance summary facts and refs,
  never raw proposal text, rationale, UI markdown, or raw chat.
- Every proposal decision, DecisionRecord creation/workflow effect, and
  agent-consumable governance publication requires current
  `Plant.status=active` at its transactional authorization boundary.
- Archive preserves IssueStack, HumanAttentionNeeded, CompanionProposal,
  CompanionConclusion, and DecisionRecord records without approving,
  rejecting, superseding, closing, publishing, or otherwise transitioning
  them.
- Restore does not resume governance automatically; each next transition must
  revalidate ActorContext/grant, current proposal/issue state and version, and
  the allowed workflow-effect rules.

## Edge Cases And Errors

- Farm-level issue governance is out of MVP.
- Missing Plant scope blocks governance record creation.
- Invalid, stale, or superseded proposal decisions fail closed.
- Archived Plant blocks new governance records and transitions of existing
  records while leaving retained governance history readable to authorized
  actors.
- If a governance decision requests a workflow effect outside the allowed
  catalog, it must be rejected or downgraded to human-visible discussion.

## Verification

Tests must prove:

- Proposal supersede behavior prevents parallel pending proposals.
- Superseded proposal cannot be approved.
- DecisionRecord cannot authorize Safety Gate or physical action.
- Approved summary has `safety_gate_authority=not_granted`.
- Raw proposal/rationale/chat content is excluded from agent context.
- Archiving with a pending proposal leaves it pending but non-operative;
  decision/publication attempts fail while archived, and restore requires
  current authorization/state checks before any later transition.
