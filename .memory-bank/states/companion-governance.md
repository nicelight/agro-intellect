---
description: Global Companion governance lifecycle boundary for MVP v2.
status: active
type: state
last_updated: 2026-07-23
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

Exact DB fields and transaction rules live in
[.memory-bank/domains/companion-governance.md](../domains/companion-governance.md).
The protected HTTP boundary lives in
[.memory-bank/contracts/companion-governance-http.md](../contracts/companion-governance-http.md),
and the explicit provider-neutral invocation lives in
[.memory-bank/contracts/companion-runtime.md](../contracts/companion-runtime.md).

## Scope Boundaries

- Defines: global governance state boundaries, proposal supersede rule,
  DecisionRecord authority limits, approved summary consumability, and
  verification requirements.
- Out of scope: exact proposal payload shape, UI conversation layout, task route
  schemas, or Companion implementation internals.
- Related specs:
  - [.memory-bank/domains/companion-governance.md](../domains/companion-governance.md):
    defines authoritative records, idempotency, concurrency, and atomic effects.
  - [.memory-bank/contracts/companion-governance-http.md](../contracts/companion-governance-http.md):
    defines protected commands, reads, and stable errors.
  - [.memory-bank/contracts/companion-runtime.md](../contracts/companion-runtime.md):
    defines explicit provider-neutral invocation and proposal handoff.
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

## Classification-only governance boundary

Companion model output uses the shared classifier as persisted routing
evidence, not as automatic dispatcher authority. A validated Companion
MessageEnvelope plus its persisted matching classification always derives the
server-owned
`ClassificationConsumerRouteV1=companion_governance_hold`; neither user nor
provider/model content can select or override that route.

- Matching `safe_information` is eligible for proposal persistence only when
  the strict Companion effect is `discussion_only|none`.
- Matching `safe_task_request` is eligible only when its exact
  `check|measurement|follow_up` kind equals the strict Companion effect.
- The matching evidence authorizes only the guarded
  `persist_companion_proposal` command. It creates no DecisionRecord or
  workflow effect by itself.
- `physical_action|blocked_uncertain`, class/kind mismatch, classifier
  conflict/failure, or current-guard denial creates no governance row.

Before an approved DecisionRecord, every held branch produces zero FT-008
candidate Bus/UI publication, zero FT-011 Safety decision/status projection,
and zero FT-012 ordinary Task. Candidate/proposal/rationale/provider result
text does not enter Bus or UI Feed through this held branch. Dedicated governance UI may show
only compact summaries derived from committed governance rows and remains
non-agent-consumable.

Classification retry, restart, restore, reconciliation, feed read, and page
refresh never replay a held downstream effect. Only a later approved
DecisionRecord may invoke the existing `governance_decision` ordinary-task
branch and/or guarded compact DecisionRecord Bus-fact path. Ordinary
non-Companion classification consumers keep their existing behavior.

## Exact MVP lifecycle

### IssueStack and issue focus

`IssueStackV1` is the typed Plant-scoped aggregate over retained Issue rows. It
is not a separate mutable authority or a model-owned memory store.

- `Issue.status` is exactly `open|resolved|closed`.
- A successful explicit Companion run either creates one new `open` issue or
  targets one caller-selected existing `open` issue.
- The target issue becomes the Plant's current focus. At most one open issue is
  focused per Plant; changing focus clears the previous focus without changing
  either issue state.
- A current pending proposal may be decided while its open issue is focused or
  unfocused. A DecisionRecord selects exactly `keep_open|resolved`. `resolved`
  leaves another issue's focus unchanged and makes the target resolved and
  unfocused; `keep_open` leaves the target open, makes it focused, and
  atomically clears a different previous focus under the same Plant/focus lock.
- `resolved -> closed` is a separate authorized human command. Closed issues
  are immutable and cannot be focused, proposed against, resolved again, or
  reopened in MVP.
- There is no Farm-scoped stack, automatic issue detection worker, scheduler,
  time-based transition, or Timeline replay into IssueStack.

### HumanAttentionNeeded

- `HumanAttentionNeeded.status` is exactly `active|satisfied`.
- A successful non-silent Companion run creates the first active attention and
  current pending proposal for its issue in one transaction.
- While attention remains active, a later explicit run for the same open issue
  may supersede the pending proposal and replace its current proposal without
  creating a second attention row. This preserves the proposal-supersede rule
  without duplicating the human request.
- Approving or rejecting the current proposal satisfies the active attention
  in the same transaction as DecisionRecord creation.
- A later explicit run may create a new attention only after the prior one is
  satisfied. There is no separate acknowledge/dismiss command.

### CompanionProposal

- State is exactly `pending|approved|rejected|superseded`.
- New proposals use a monotonic per-issue `proposal_sequence`.
- At most one proposal is pending per issue. Creating a newer proposal locks
  the issue/current proposal, transitions the previous pending proposal to
  `superseded`, and creates the replacement atomically.
- Different explicit `run_id` values are independent commands. If their
  current guards remain valid, row locks serialize them and both may commit;
  for one issue the later governance writer supersedes the earlier writer's
  pending proposal. Same-run retries remain idempotent. Overlap alone is not a
  conflict, and provider finish time does not define proposal order.
- Only the current pending proposal at its expected version may be approved or
  rejected. Terminal proposals are retained and immutable.
- There is no time expiry. Elapsed time alone changes neither proposal nor
  attention state.

### DecisionRecord and workflow effects

- Human decision authority is exactly active `boss` or active granted
  `engineer` after the shared current `can_operate=true` guard. Consultant is
  denied. No governance permission member or `plant_approve_actions` reuse is
  allowed.
- There is no separate self-approval guard: Companion authored the proposal;
  the human actor is recorded on DecisionRecord.
- The closed effect enum is
  `discussion_only|check|measurement|follow_up|none`.
- Approval adopts the current proposal's exact allowed effect. Rejection forces
  `none`. `action` and every unknown value reject the whole decision.
- `check|measurement|follow_up` call the existing ordinary-task authority with
  a DecisionRecord source extension. `discussion_only|none` create no Task.
- Proposal transition, attention satisfaction, DecisionRecord, requested issue
  resolution, ordinary Task when applicable, approved-decision Bus reference,
  UI projections, and authoritative DB refs commit as one PostgreSQL
  transaction. A rejected DecisionRecord produces no Bus fact. Failure of
  any operative effect or DB projection rolls back the DecisionRecord and all
  same-transaction DB changes; no `failed/no_effect` record is persisted.
- Timeline append follows the canonical append-before-commit policy. An event
  left by a later failed DB commit is non-authoritative audit noise and cannot
  recreate a decision or effect.

### CompanionConclusion

`CompanionConclusionV1` is a derived typed read summary over authoritative
issue, current proposal/attention, and latest DecisionRecord state. It is not a
table, event, MessageEnvelope, Bus command, or second human-confirmation
boundary. The DecisionRecord is the sole human confirmation. The data spec
owns the deterministic latest row, exact `awaiting_human|decided|closed`
nullability matrix, and canonical `companion_issue|companion_attention|
companion_proposal|decision_record` refs; derived reads never fall back to UI,
Bus, or Timeline projections. Focus is independent for open rows: an open
unfocused issue remains `awaiting_human` when it retains active attention and a
pending proposal, or `decided` when its attention is satisfied and its latest
DecisionRecord kept it open.

### Invocation trigger

The only MVP model trigger is the explicit protected user command defined by
the Companion HTTP/runtime contracts. Domain events, Task completion, startup,
reconciliation, feed reads, page refresh, and manual feed refresh MUST NOT
invoke Companion.

## Shared Bus And UI Projection Boundary

- Human-facing `HumanAttentionNeeded`, `CompanionProposal`, and
  `DecisionRecord` projections use the single `companion_governance` UI Feed
  route and its strict attention/proposal/decision payload variants.
- No `HumanAttentionNeeded` or `CompanionProposal` record enters Agent Chat
  Bus, regardless of proposal state. Raw proposal text, rationale, raw chat,
  and UI content are always excluded.
- Only a valid approved projectable `DecisionRecord` may publish the existing
  Bus `domain_event_ref` with `record_type=decision_record`. The Bus stores a
  reference, and the context builder loads only the exact non-persisted
  `ApprovedGovernanceSummaryV1` defined by the FT-013 data spec from
  authoritative DecisionRecord/proposal storage.
- Every loaded summary preserves `safety_gate_authority=not_granted`; neither
  Bus nor UI projection creates governance, Plant-state, task, or Safety
  authority.
- Projection writes require the same current active-Plant and authorization
  guards as their owning governance command. Archive blocks new projections
  and restore never replays them automatically.

Exact shared envelope variants live in
[.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md) and
[.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md). Exact FT-013
record fields, summary bounds, transition idempotency, and workflow-effect
catalog remain feature-local design.

## Rules

- No parallel pending proposals may exist for the same Plant-scoped issue.
- A new proposal for the same Plant issue supersedes the previous pending
  proposal.
- Proposal state has no time-based expiry in MVP. Elapsed time alone never
  transitions a `pending` proposal; it remains pending until an authorized
  decision or a later same-issue proposal supersedes it.
- Superseded proposals are not approvable and cannot become agent facts.
- DecisionRecord may direct Plant-scoped discussion/workflow or safe check,
  measurement, or follow-up task requests through backend rules.
- DecisionRecord must not mutate Plant state, create `action_task`, authorize
  physical action, replace Safety Gate approval, or turn raw chat into fact.
- Agent Chat Bus consumers receive only compact approved governance summary
  facts and refs. The owning Companion provider contract may separately load
  strict typed governance context; UI markdown and raw chat remain excluded.
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
- If a proposal or decision requests a workflow effect outside the closed
  catalog, reject the whole command; never downgrade or repair it.

## Verification

Tests must prove:

- Proposal supersede behavior prevents parallel pending proposals.
- Elapsed time alone does not expire or transition a pending proposal.
- Superseded proposal cannot be approved.
- DecisionRecord cannot authorize Safety Gate or physical action.
- Approved summary has `safety_gate_authority=not_granted`.
- Typed governance input matches the owning provider allowlist and remains
  non-authoritative; UI markdown and raw chat are excluded.
- Archiving with a pending proposal leaves it pending but non-operative;
  decision/publication attempts fail while archived, and restore requires
  current authorization/state checks before any later transition.
- Focus uniqueness, proposal sequence/partial uniqueness, current-version
  decision, identical retry versus conflict, and concurrent supersede are
  enforced by PostgreSQL-backed integration tests.
- Refocusing preserves valid reads for both open/unfocused cases: active
  attention remains `awaiting_human`, and a prior keep-open decision remains
  `decided`. Deciding an unfocused pending issue with `keep_open` atomically
  transfers focus under the existing Plant/focus lock.
- A failed ordinary-task effect leaves proposal/attention/issue unchanged and
  creates no DecisionRecord, Bus row, or UI decision row.
- Companion-hold compatibility proves safe information creates no FT-008
  candidate Bus/UI row, safe task request creates no FT-012 Task, held
  physical/blocked/mismatch/failure creates no governance or ordinary
  downstream row, retry/restore/reconciliation performs no replay, and only a
  later approved DecisionRecord can produce Task/compact Bus effects.
- Approved Bus context returns exactly `ApprovedGovernanceSummaryV1`, including
  canonical identities, proposal version, decision/effect/role/time/source
  refs, and `safety_gate_authority=not_granted`, with none of the forbidden
  raw or mutable governance fields.
