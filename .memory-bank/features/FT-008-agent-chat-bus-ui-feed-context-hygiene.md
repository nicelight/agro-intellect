---
description: FT-008 Agent Chat Bus And UI Feed Context Hygiene.
status: draft
type: feature
feature_id: FT-008
epic: EP-003
lifecycle: verified
last_updated: 2026-07-13
spec_design_status: complete
spec_design_links:
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/ui-feed.md
  - .memory-bank/domains/agent-chat-ui-feed-storage.md
  - .memory-bank/contracts/plant-feed-http.md
  - .memory-bank/contracts/agent-roster-bootstrap.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/states/safety-action-lifecycle.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
  - .memory-bank/testing/agent-chat-ui-feed.md
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
- UI Feed, spoiler notes, UI markdown, raw chat, admin notices, and unapproved Companion proposals do not enter agent working context.
- MessageEnvelope and Bus/UI projections preserve source refs and consumability boundaries.
- Authorized/classified candidate text is literal escaped/text-node UI data;
  no Markdown/HTML rendering, unsafe URL/action activation, or reuse as agent
  context/runtime authority is allowed.
- If classified candidate content enters agent-consumable Bus context, FT-008
  preserves it in a typed quoted-data field and never concatenates it into
  system/developer/instruction/prompt/tool/routing channels.
- Every active Plant eventually has exactly one `UIFeedEvent` per deterministic
  roster introduction. The Plant chat/feed UI renders that same event; no copy
  enters Agent Chat Bus. FT-008 reconciles missing batches after failure or
  restart without rolling back Plant creation. Archived Plants receive no new
  projection.
- Archived Plant produces no operational Bus/agent context or new operational
  projection; explicit retained-history UI remains presentation-only.

## Edge Cases & Failure Modes

- Presentation-only summary cannot be replayed into agent context.
- Unauthorized Plant context cannot leak through Bus or UI projections.
- Raw CompanionProposal content remains human-visible only until a valid DecisionRecord produces compact approved governance summary facts.
- UI spoiler notes remain `visible_to_agents=false` and `consumable_by_agents=false` when represented.
- An event prepared before archive cannot publish after archive, and restore
  does not replay it.
- Introduction intent is retained while archived but not projected. After
  restore, a new reconciliation must revalidate current active-Plant state
  before continuing idempotent delivery.

## Verification Targets

- Unit: context filtering and consumability flags.
- Integration: BusEventEnvelope and UIFeedEvent projection boundaries after specs define them.
- Integration: active-Plant scan and durable reconciliation yield exactly eight
  unique, non-agent-consumable `UIFeedEvent` records after retry/restart, with no
  partial batch acceptance or Agent Chat Bus copy.
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
- [.memory-bank/contracts/agent-roster-bootstrap.md](../contracts/agent-roster-bootstrap.md): deterministic batch/result contract and FT-008 reconciliation ownership.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): MessageEnvelope projection boundary.
- [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): global presentation-only UI Feed contract.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): audit/export refs that cannot publish directly to Bus.
- [.memory-bank/states/plants/plant-and-access-lifecycle.md](../states/plants/plant-and-access-lifecycle.md): archived-Plant publication/context guard.
- [.memory-bank/domains/agent-chat-ui-feed-storage.md](../domains/agent-chat-ui-feed-storage.md): PostgreSQL rows, atomic writes, and restart-safe introduction reconciliation.
- [.memory-bank/contracts/plant-feed-http.md](../contracts/plant-feed-http.md): protected Plant feed read and pagination boundary.
- [.memory-bank/testing/agent-chat-ui-feed.md](../testing/agent-chat-ui-feed.md): executable verification matrix.

## Feature-Local Design Pressure

- Closed by the linked Bus/UI v1 envelopes, PostgreSQL storage/reconciliation,
  protected feed API, context-builder rules, and verification matrix.

## Implementation Ownership

- FT-008 owns backend persistence, the concrete FT-007 introduction sink,
  active-Plant reconciliation, guarded Bus/UI publication, context reads, and
  the protected Plant feed API.
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
- Per-task adversarial review records `SEMANTIC_VERDICT: semantic-pass`. The
  exact `HUMAN_CHECKPOINT: done` marker is absent and was not fabricated; the
  scheduler explicitly accepted that process-only warning without waiving
  safety, authorization, data integrity, source-of-truth, or scope rules.
- `TASK-033-T3-FT-008-W2` is `done` after one bounded repair and fresh
  independent re-verification. Evidence proves closed Bus/UI value objects,
  atomic guarded safe-information publication, current-authority agent-context
  isolation, fail-closed persisted-row validation, literal candidate data, and
  the protected retained-history Plant feed API.
- W2 records `VERDICT: PASS` and per-task
  `SEMANTIC_VERDICT: semantic-pass`. The exact `HUMAN_CHECKPOINT: done` marker
  remains absent; the scheduler recorded a process-only waiver without
  weakening product, authorization, context-isolation, data-integrity,
  source-of-truth, or scope requirements.
- FT-008 is `verified` for its owned backend persistence, publication, context,
  reconciliation, and feed API outcome. FT-016 still owns the Svelte/PWA
  consumer and literal DOM rendering; this feature claims no frontend evidence
  and creates no second feed or agent-context copy.

## SDD Design Gate

- Global/shared status: complete; `AD-007`, `AD-008`, the strict introduction
  batch/result contract, and linked Bus/Message/Safety/Plant lifecycle specs
  define pending classification, durable active-Plant reconciliation, archived
  context, guarded publication, literal UI rendering, and typed Bus quotation
  behavior.
- Feature-local status: complete. Exact envelopes, persistence, atomicity,
  reconciliation, ordering, HTTP reads, context filters, ownership handoffs,
  and verification are defined by `spec_design_links`.
