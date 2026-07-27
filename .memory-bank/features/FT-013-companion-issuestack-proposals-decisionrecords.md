---
description: FT-013 Companion IssueStack Proposals And DecisionRecords.
status: draft
type: feature
feature_id: FT-013
epic: EP-005
lifecycle: planned
last_updated: 2026-07-27
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
- Feature-local R4 B3-B6 are closed in the registered subject specs: exact
  Companion HTTP views and total runtime/classifier/domain error mapping;
  deterministic latest completed check-in plus exactly one manual-measurement
  row without cross-row pH/EC synthesis; serialized multi-effect semantics for
  distinct run ids; and one canonical ref/read ordering/nullability grammar.
- TASK-040 and TASK-042 are explicitly serialized because both may write the
  Task Follow-Up package. TASK-043 directly composes the Safety classifier
  runtime/storage/testing contracts and the two-executor provider-neutral path.

## Behavior specs

- `.memory-bank/behavior-specs/FT-013-BHV-001-proposal-supersede-attention-reuse.behavior.json`
- `.memory-bank/behavior-specs/FT-013-BHV-002-decision-task-atomicity.behavior.json`
- `.memory-bank/behavior-specs/FT-013-BHV-003-real-companion-explicit-run.behavior.json`

## SDD Design Gate

- Global/shared status is complete. The provider profile has no blanket
  approval-status ban on governance input; registered agent-specific requests
  own exact typed allowlists. The current authorized explicit Companion
  `existing_issue` request includes persisted open-Issue `summary_text` as
  non-authoritative context.
  `AD-007`, repaired `AD-008`, Plant lifecycle, the
  one closed ordinary-task command, evidence-only classification with
  `companion_governance_hold`, Companion Governance, Agent Chat Bus, UI Feed,
  shared Bus/UI storage, and Plant Feed HTTP define shared authority and
  archive/no-replay behavior.
- Shared projection decision: only a valid approved DecisionRecord reference
  may enter Bus; human attention/proposal/decision use the non-agent-consumable
  `companion_governance` UI route. No parallel Companion Bus/UI contract is
  allowed.
- Feature-local deterministic design is closed for accepted authority,
  lifecycle, effect, atomicity, derived-conclusion, HTTP, evidence selection,
  concurrency, ref/read, and provider-neutral classifier composition. Safety/action/Plant/
  device authority remains excluded; final feature status is complete.
- The post-repair deterministic findings are also closed: open/unfocused issues
  have valid awaiting/decided conclusions and focus-transition semantics; the
  ordinary-task seam accepts the exact flushed approved proposal phase in the
  caller UoW; `ApprovedGovernanceSummaryV1` is exact and derived-only; nested
  Task failures have a total reachable translation; and TASK-042 links the
  canonical Task command directly.
- Provider-input decision: `CompanionProviderRequestV1` includes persisted
  open-Issue `summary_text` from current authorized PostgreSQL scope as
  untrusted, non-authoritative context. The reconciled next step is
  `/review-tasks-plan FT-013`.
- Provider-integration decision: current code-phase closure uses explicit
  Companion and Safety fake/spy executors and does not require credentials,
  egress, network, or live smoke. Production remains unbound and fail closed;
  real response/classifier evidence belongs to the shared future milestone.
- Execution note: TASK-041 is owner-recorded `done` from Attempt 05
  independent functional PASS. Its latest semantic-fail remains unchanged and
  is accepted as residual risk without a semantic-pass claim. TASK-042 and
  TASK-043 remain `planned`; neither was promoted or selected by the W1
  closure. Their `touched_files` are advisory; hard semantics remain in their
  canonical specs, `forbidden_scope`, and `stop_conditions`.
- Simplification decision: the new bounded T3 repair task removes the redundant
  attention-to-proposal pointer, scopes read integrity to supported paths,
  ownership, and response serialization, and makes proposal projection repair
  authority-derived. TASK-042 must consume that repaired authority before
  DecisionRecord implementation begins.
