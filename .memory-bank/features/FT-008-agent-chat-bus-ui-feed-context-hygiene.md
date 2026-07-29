---
description: FT-008 Agent Chat Bus And UI Feed Context Hygiene.
status: draft
type: feature
feature_id: FT-008
epic: EP-003
lifecycle: verified
last_updated: 2026-07-29
spec_design_status: complete
spec_design_links:
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/ui-feed.md
  - .memory-bank/domains/agent-chat-ui-feed-storage.md
  - .memory-bank/contracts/plant-feed-http.md
  - .memory-bank/contracts/agent-roster-bootstrap.md
  - .memory-bank/contracts/farm/plant-management-http.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/states/safety-action-lifecycle.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
  - .memory-bank/testing/agent-chat-ui-feed.md
  - .memory-bank/testing/agent-runtime.md
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/contracts/boundary-map.md
---
# FT-008 Agent Chat Bus And UI Feed Context Hygiene

## Use Cases

- Validated domain events are published to the Agent Chat Bus as agent-consumable working context.
- Human-facing messages, cards, prompts, tasks, approvals, history, and storage status are projected to UI Feed.
- UI Feed remains unavailable as agent working context.
- Context builders filter by ActorContext, PlantAccessGrant, and approved consumability flags.

## Acceptance Criteria

- Agent Chat Bus is the domain-owned working stream for agents.
- UI Feed is presentation-only.
- UI Feed, spoiler notes, UI markdown, raw chat, and admin notices do not enter agent working context. Agent-specific typed governance input is outside the FT-008 Bus context-builder path.
- MessageEnvelope and Bus/UI projections preserve source refs and consumability boundaries.
- Authorized/classified candidate text is literal escaped/text-node UI data;
  no Markdown/HTML rendering, unsafe URL/action activation, or reuse as agent
  context/runtime authority is allowed.
- If classified candidate content enters agent-consumable Bus context, FT-008
  preserves it in a typed quoted-data field and never concatenates it into
  system/developer/instruction/prompt/tool/routing channels.
- On an authorized Feed open for an active Plant, FT-008 idempotently
  materializes only missing canonical roster introduction `UIFeedEvent` rows.
  Repeated opens create no duplicates; the UI renders those same rows and no
  copy enters Agent Chat Bus or agent context.
- Plant creation/`201`, process startup, restore, and archived retained-history
  Feed reads perform no introduction batch, sink, scan, pending-state, or
  reconciliation work. The public Feed response/cursor schema is unchanged.
- Archived Plant produces no operational Bus/agent context or new operational
  projection; explicit retained-history UI remains presentation-only.

## Edge Cases & Failure Modes

- Presentation-only summary cannot be replayed into agent context.
- Unauthorized Plant context cannot leak through Bus or UI projections.
- FT-008 publishes only compact approved DecisionRecord facts to Agent Chat Bus. An owning feature may separately assemble strict typed governance input directly for its model without routing it through UI Feed or Bus.
- UI spoiler notes remain `visible_to_agents=false` and `consumable_by_agents=false` when represented.
- An event prepared before archive cannot publish after archive, and restore
  does not replay it.
- Archived retained-history reads and restore create no introduction rows.
  After restore, only a later authorized active-Plant Feed open may fill missing
  rows.
- Lazy persistence failure returns existing `FEED_PERSISTENCE_FAILED`; a later
  authorized Feed retry is sufficient and no background recovery lifecycle is
  introduced.

## Verification Targets

- Unit: context filtering and consumability flags.
- Integration: BusEventEnvelope and UIFeedEvent projection boundaries after specs define them.
- Integration: an authorized active-Plant Feed open creates only missing
  canonical introduction rows, repeated/retried opens are idempotent, and no
  introduction enters Agent Chat Bus or agent context.
- Integration: Plant create/`201`, startup, restore, and archived
  retained-history reads create no introduction rows; Feed response/cursor
  schema stays unchanged and retry after `FEED_PERSISTENCE_FAILED` can finish
  materialization.
- Integration: archive race blocks Bus publication and agent context while
  preserving authorized retained-history presentation.
- Anti-cheat: UI Feed and raw chat are absent from agent context builder fixtures.
- Anti-cheat: markup-/prompt-looking candidate text stays literal in UI and
  typed as quotation on Bus; it cannot instruct agents or alter routing.

## Behavior specs

- `.memory-bank/behavior-specs/FT-008-BHV-001-introduction-reconciliation.behavior.json`
- `.memory-bank/behavior-specs/FT-008-BHV-002-archive-reconciliation-guard.behavior.json`
- `.memory-bank/behavior-specs/FT-008-BHV-003-literal-ui-typed-bus.behavior.json`

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Bus/UI module boundary.
- [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md): agent-consumable event stream rules.
- [.memory-bank/contracts/agent-roster-bootstrap.md](../contracts/agent-roster-bootstrap.md): canonical ordered roster and deterministic introduction metadata without a batch/sink lifecycle.
- [.memory-bank/contracts/farm/plant-management-http.md](../contracts/farm/plant-management-http.md): unchanged Plant-create transaction and `201` response.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): MessageEnvelope projection boundary.
- [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): global presentation-only UI Feed contract.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): audit/export refs that cannot publish directly to Bus.
- [.memory-bank/states/plants/plant-and-access-lifecycle.md](../states/plants/plant-and-access-lifecycle.md): archived-Plant publication/context guard.
- [.memory-bank/domains/agent-chat-ui-feed-storage.md](../domains/agent-chat-ui-feed-storage.md): PostgreSQL Bus/UI rows, data-preserving batch-table removal, and lazy materialization transaction.
- [.memory-bank/contracts/plant-feed-http.md](../contracts/plant-feed-http.md): protected Plant feed read and pagination boundary.
- [.memory-bank/testing/agent-chat-ui-feed.md](../testing/agent-chat-ui-feed.md): executable verification matrix.
- [.memory-bank/testing/agent-runtime.md](../testing/agent-runtime.md): roster metadata and Plant-create/startup negative-path verification.

## Feature-Local Design Pressure

- The Bus/UI and context-isolation boundaries remain closed. The accepted
  roster, storage, Feed, behavior, Plant-create, and testing specs define one
  cohesive replacement of batch/startup reconciliation with lazy authorized
  Feed-open materialization.

## Implementation Ownership

- FT-008 owns backend persistence, lazy missing-introduction materialization
  inside the protected authorized active-Plant Feed open, guarded Bus/UI
  publication, context reads, and the protected Plant feed API. It owns no
  post-create sink, startup scan, or restore reconciliation.
- FT-011 owns classification policy; FT-008 consumes only the strict matching
  `SafetyClassificationResultV1` and does not implement classifier semantics.
- FT-012 owns ordinary task effects. FT-008 creates none for
  `safe_task_request|physical_action`.
- FT-016 owns the Svelte/PWA Plant chat/feed component because the current
  brownfield tree has no frontend scaffold. It must render the exact FT-008
  event text literally and may not create a second feed record or agent-context
  copy.

## Current Implementation Evidence

- `TASK-032-T3-FT-008-W1` is `done`: independent real-PostgreSQL verification
  passed durable exactly-eight-or-zero introduction persistence, idempotent
  retry/conflict handling, restart reconciliation, archive-race denial,
  restore-without-replay, fresh-scan convergence, guarded rollback, and the
  unchanged post-commit Plant-create contract.
- Per-task adversarial review records `SEMANTIC_VERDICT: semantic-pass`; the
  user confirmed `HUMAN_CHECKPOINT: done` after checking the completed result.
- `TASK-033-T3-FT-008-W2` is `done` after one bounded repair and fresh
  independent re-verification. Evidence proves closed Bus/UI value objects,
  atomic guarded safe-information publication, current-authority agent-context
  isolation, fail-closed persisted-row validation, literal candidate data, and
  the protected retained-history Plant feed API.
- W2 records `VERDICT: PASS`, per-task
  `SEMANTIC_VERDICT: semantic-pass`, and user-confirmed
  `HUMAN_CHECKPOINT: done`.
- These tasks remain immutable `done` history and still support the unchanged
  Bus/UI publication, context isolation, literal-data, and protected-feed
  baseline. Their superseded batch/startup reconciliation evidence is not used
  as proof of the accepted lazy Feed-open outcome.
- `TASK-046-T3-FT-008-W3` is `done` after approved Planning Revision 2,
  independent functional `PASS`, task-level `semantic-pass`, and the exact T3
  human checkpoint. Fresh evidence proves data-preserving removal of the batch
  lifecycle, same-transaction current authorization, missing-only lazy
  materialization, retry convergence, forbidden-trigger write freedom, and
  unchanged Feed behavior.
- FT-008 is therefore `verified`. FT-016 still owns the Svelte/PWA consumer and
  literal DOM rendering.

## SDD Design Gate

- `spec_design_status: complete`: each affected concern has one canonical
  subject spec, the revised behavior examples match those specs, and no
  unresolved product, contract, storage, authorization, migration, or task
  boundary remains.
- Existing Bus/Message/Safety/Plant lifecycle and context-isolation design
  remains applicable and must not be widened during implementation.
- Planning Revision 2 received fresh `/review-tasks-plan FT-008` `APPROVE`;
  TASK-046 then completed every T3 closure gate without changing the registered
  design links.
