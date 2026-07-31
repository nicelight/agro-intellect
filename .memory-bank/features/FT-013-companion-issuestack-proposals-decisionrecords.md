---
description: FT-013 Companion IssueStack Proposals And DecisionRecords.
status: draft
type: feature
feature_id: FT-013
epic: EP-005
lifecycle: planned
last_updated: 2026-07-29
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/states/companion-governance.md
spec_design_status: complete
spec_design_links:
  - .memory-bank/states/companion-governance.md
  - .memory-bank/domains/companion-governance.md
  - .memory-bank/contracts/companion-governance-http.md
  - .memory-bank/contracts/companion-runtime.md
  - .memory-bank/testing/companion-governance.md
  - .memory-bank/domains/plant-operations.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
  - .memory-bank/states/task-follow-up-lifecycle.md
  - .memory-bank/domains/task-approval-outcomes.md
  - .memory-bank/contracts/task-approval-http.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/ui-feed.md
  - .memory-bank/domains/agent-chat-ui-feed-storage.md
  - .memory-bank/contracts/plant-feed-http.md
  - .memory-bank/contracts/timeline-event.md
  - .memory-bank/states/safety-action-lifecycle.md
  - .memory-bank/contracts/safety-gate-runtime.md
  - .memory-bank/domains/safety-action-routing.md
  - .memory-bank/testing/safety-gate.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/contracts/agent-roster-bootstrap.md
  - .memory-bank/runbooks/agent-runtime-providers.md
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
- Only an explicit protected user command invokes the Companion model; page
  reads, refresh, domain events, Task completion, and startup are not triggers.
- No parallel pending proposals exist for the same Plant-scoped issue; a new proposal supersedes the previous pending proposal.
- HumanAttentionNeeded stores no reverse current-proposal pointer. The current
  proposal is derived from the unique pending proposal linked to the active
  attention, while the public `current_proposal_ref` remains unchanged.
- DecisionRecord may direct Plant-scoped discussion/workflow and safe check/measurement/follow-up task requests through backend rules.
- DecisionRecord cannot mutate Plant state, create action_task, authorize physical action, replace Safety Gate approval, or turn raw chat into a fact.
- Agent Chat Bus and general agent working context may consume only compact
  approved governance summary facts and refs. The explicit Companion
  `existing_issue` provider request may additionally receive only that issue's
  persisted `summary_text` as non-authoritative typed context.
- Archived Plant preserves governance records but blocks proposal decisions,
  DecisionRecord workflow effects, and agent-consumable publication.

## Edge Cases & Failure Modes

- Superseded proposal is not approvable and cannot become agent fact.
- UI markdown and raw chat remain excluded. The exact persisted issue-summary
  exception does not admit attention/proposal/rationale/decision/history/caller
  content and does not become a fact, DecisionRecord, Task, Safety,
  Plant-state, or publication authority.
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

- Shared blockers are resolved by the one canonical ordinary-task source union
  and the server-derived Companion governance hold in the linked Task/Safety/
  MessageEnvelope/Bus/UI specs.
- Registered subject specs define exact
  Companion HTTP views and total runtime/classifier/domain error mapping;
  deterministic latest completed check-in plus exactly one manual-measurement
  row without cross-row pH/EC synthesis; serialized multi-effect semantics for
  distinct run ids; and one canonical ref/read ordering/nullability grammar.

## Behavior specs

- `.memory-bank/behavior-specs/FT-013-BHV-001-proposal-supersede-attention-reuse.behavior.json`
- `.memory-bank/behavior-specs/FT-013-BHV-002-decision-task-atomicity.behavior.json`
- `.memory-bank/behavior-specs/FT-013-BHV-003-real-companion-explicit-run.behavior.json`

## Current Feature State

- SDD design is complete. The IssueStack/proposal aggregate and one-way current
  proposal authority are implemented.
- DecisionRecord/effect and explicit Companion runtime slices remain planned,
  so feature `lifecycle` remains `planned`.
- Their cards are reconciled to Global Planning Revision 2 and the current
  repository baseline; the Planning Revision 1 approval is historical, so
  fresh `/review-tasks-plan FT-013` is required before execution.

## Accepted Design Decisions

- PostgreSQL Issue, HumanAttentionNeeded, CompanionProposal, and
  DecisionRecord rows are the governance authority. UI, Timeline, Bus,
  MessageEnvelope, classification, and model output are projections or inputs
  and cannot independently transition that authority.
- The current proposal is derived one-way from the unique pending proposal for
  the active attention. Supported reads enforce Plant/issue ownership and
  strict response serialization; derived proposal UI may be rebuilt from the
  authoritative proposal row.
- Only a valid approved DecisionRecord reference may enter Bus. Human
  attention, proposal, and decision projections use the non-agent-consumable
  `companion_governance` UI route.
- DecisionRecord effects remain limited to the closed ordinary-task boundary.
  Safety approval, action Task, Plant-state mutation, device authority, Task
  completion, and Outcome remain outside Companion governance.
- `CompanionProviderRequestV1.existing_issue.summary_text` is typed persisted
  open-Issue context from the current authorized PostgreSQL scope. It remains
  untrusted and non-authoritative and does not admit attention, proposal,
  rationale, decision, history, caller, or UI content.
- Companion execution remains provider-neutral, explicit, and fail closed.
  Deterministic verification uses explicit Companion and Safety fake/spy
  executors; production has no implicit fallback or fake output.
- Archive retains governance records and authorized reads but grants no
  transition, publication, replay, or workflow-effect authority. Current
  authorization, version, idempotency, lock ordering, and same-run versus
  distinct-run concurrency rules remain defined by the linked canonical specs.
