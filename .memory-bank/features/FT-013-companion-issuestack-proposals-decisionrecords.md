---
description: FT-013 Companion IssueStack Proposals And DecisionRecords.
status: draft
type: feature
feature_id: FT-013
epic: EP-005
lifecycle: planned
last_updated: 2026-07-17
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/states/companion-governance.md
---
# FT-013 Companion IssueStack Proposals And DecisionRecords

## Use Cases

- Companion tracks Plant-scoped issues in IssueStack.
- Companion raises HumanAttentionNeeded.
- Companion creates a CompanionProposal for a Plant-scoped issue.
- Human decision creates a DecisionRecord.
- Valid DecisionRecord produces compact approved governance summary facts and allowed workflow effects.

## Acceptance Criteria

- Companion governance state is explicit and typed.
- No parallel pending proposals exist for the same Plant-scoped issue; a new proposal supersedes the previous pending proposal.
- DecisionRecord may direct Plant-scoped discussion/workflow and safe check/measurement/follow-up task requests through backend rules.
- DecisionRecord cannot mutate Plant state, create action_task, authorize physical action, replace Safety Gate approval, or turn raw chat into a fact.
- Agents may consume only compact approved governance summary facts and refs.
- Archived Plant preserves governance records but blocks proposal decisions,
  DecisionRecord workflow effects, and agent-consumable publication.

## Edge Cases & Failure Modes

- Superseded proposal is not approvable and cannot become agent fact.
- Raw proposal text, raw rationale, UI markdown, raw chat, and unapproved discussion content remain non-consumable.
- Companion cannot bypass backend authorization or Safety Gate.
- Farm-level issue governance remains out of MVP.
- Archive does not approve, reject, supersede, close, or publish an open
  governance record; restore requires current authorization/state checks.

## Verification Targets

- Unit: proposal supersede and DecisionRecord authority rules.
- Integration: approved governance summary context builder includes only compact allowed fields and explicit `safety_gate_authority=not_granted`.
- Integration: pending proposal remains unchanged and non-operative during
  archive and does not auto-resume after restore.
- E2E: Companion HumanAttentionNeeded plus proposal/decision path appears without unlocking physical action.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Companion Governance module and authority boundary.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): governance record ownership.
- [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md): approved governance summary consumability rules.
- [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): human-facing Companion projection rules.
- [.memory-bank/states/companion-governance.md](../states/companion-governance.md): IssueStack/proposal/DecisionRecord lifecycle boundary.
- [.memory-bank/states/safety-action-lifecycle.md](../states/safety-action-lifecycle.md): governance approval separation from physical-action approval.
- [.memory-bank/states/plants/plant-and-access-lifecycle.md](../states/plants/plant-and-access-lifecycle.md): global archived-Plant operational guard.

## Feature-Local Design Pressure

- Exact IssueStack/proposal/decision state machines, workflow-effect catalog,
  approved-summary schema, UI projection behavior, and tests.

## SDD Design Gate

- Global/shared status: complete; `AD-007`, Plant lifecycle, Companion
  Governance, Agent Chat Bus, UI Feed, shared Bus/UI storage, and Plant Feed
  HTTP define the archived behavior and exact shared projection routes.
- Shared projection decision: only a valid DecisionRecord reference may enter
  Bus; human attention/proposal/decision use the non-agent-consumable
  `companion_governance` UI route. No parallel Companion Bus/UI contract is
  allowed.
- Feature-local status: pending `/prd-to-tasks FT-013` for exact governance
  record schemas, compact-summary bounds, transitions, workflow effects,
  command/API contracts, projection idempotency, and tests.
