---
description: Implementation plan for FT-008 Agent Chat Bus, UI Feed, reconciliation, and context hygiene.
status: active
type: implementation_plan
feature_id: FT-008
last_updated: 2026-07-12
source_of_truth:
  - .memory-bank/features/FT-008-agent-chat-bus-ui-feed-context-hygiene.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/ui-feed.md
  - .memory-bank/domains/agent-chat-ui-feed-storage.md
  - .memory-bank/contracts/plant-feed-http.md
  - .memory-bank/testing/agent-chat-ui-feed.md
---
# IMPL FT-008 Agent Chat Bus And UI Feed Context Hygiene

## Goal

Deliver a durable local Bus/UI boundary in which every active Plant converges
to exactly eight non-agent-consumable roster introductions, classified safe
information is atomically separated into typed Bus quotation and literal UI
data, and every context/feed read reuses current backend authorization.

## Scope

- Add bounded `backend/app/agent_chat/` persistence and services.
- Add one Alembic migration for introduction batches, UI Feed events, and Bus
  events using the project UUID/FK conventions.
- Replace the unavailable FT-007 introduction sink with a concrete PostgreSQL
  sink and run idempotent active-Plant reconciliation at local startup.
- Implement strict Bus/UI v1 contracts and classified-publication routing.
- Reuse ActorContext and the current active-Plant write guard.
- Add protected paginated Plant feed reads, retained-history reads, stable
  errors, no-store, and generated OpenAPI coverage.
- Add typed agent-context reads that exclude every presentation/raw/unauthorized
  source and preserve candidate text only as quotation data.

## Non-goals

- No classifier algorithm, Safety Gate policy, ordinary task, action task,
  approval, follow-up, Companion, dataset, or provider/model implementation.
- No frontend scaffold or Svelte component; FT-016 consumes the exact feed API.
- No distributed queue, broker, worker fleet, outbox, event sourcing, timeline
  replay, or provider-history/prompt persistence.
- No change to the public Plant-create request/response or rollback behavior.
- No UI Feed-to-Bus bridge and no storage of secrets, auth material, provider
  payloads, hidden reasoning, raw chat, or unapproved proposals.

## Ordered implementation strategy

1. Add migration/models/repositories and prove exact constraints.
2. Implement the strict introduction sink, wire it into app composition, and
   add idempotent startup reconciliation using the existing deterministic
   roster batch builder.
3. Add strict Bus/UI value objects and one guarded publication service that
   consumes existing immutable envelope/classification types.
4. Add current-authorized Bus context queries and Plant feed service/API.
5. Run focused, access/runtime regression, full deterministic, MB lint, and
   diff checks.

## Dependencies

- `TASK-031-T3-FT-007-W2` is done and provides the strict sink port, roster
  batch builder, MessageEnvelope, and SafetyClassificationResultV1 types.
- Foundation is complete transitively through the implemented Plant/runtime
  baseline.
- FT-011/FT-012 callers may later use the strict handoff; their policy/effects
  are not prerequisites for testing the FT-008 boundary.

## Expected touched files

- `backend/app/agent_chat/`
- `backend/app/api/feed.py`, API router composition, and `backend/app/main.py`
- `backend/app/access_admin/context_builders.py`
- `backend/migrations/versions/ft008_agent_chat_ui_feed.py`
- `tests/backend/agent_chat/` and `tests/backend/api/test_ft008_feed_routes.py`

## Constitution Check

- Spec Before Code: direct storage, Bus/UI, HTTP, access, lifecycle, and testing
  specs define each boundary.
- KISS/low maintenance: one local module, three tables, one startup
  reconciliation pass, no broker/outbox/event-sourcing layer.
- Safety/authority: current authorization and active Plant are checked at each
  write/read boundary; presentation and candidate text gain no authority.
- Blockers: none.

## Source Artifacts

- `.memory-bank/features/FT-008-agent-chat-bus-ui-feed-context-hygiene.md`
- `.memory-bank/epics/EP-003-agent-runtime-context-hygiene.md`
- `.memory-bank/requirements.md`: REQ-003, REQ-013, REQ-020.
- FT-008 BHV-001 through BHV-003.

## Normative Inputs

- `.memory-bank/contracts/agent-chat-bus.md`
- `.memory-bank/contracts/ui-feed.md`
- `.memory-bank/domains/agent-chat-ui-feed-storage.md`
- `.memory-bank/contracts/plant-feed-http.md`
- `.memory-bank/contracts/agent-roster-bootstrap.md`
- `.memory-bank/contracts/message-envelope.md`
- `.memory-bank/contracts/access/actor-context.md`
- `.memory-bank/states/safety-action-lifecycle.md`
- `.memory-bank/states/plants/plant-and-access-lifecycle.md`
- `.memory-bank/testing/agent-chat-ui-feed.md`

## Constraints And Invariants

- PostgreSQL/read model owns durable rows; UI Feed is presentation and Bus is
  agent working context only.
- Introduction acceptance is exactly eight or zero, deterministic, and
  transactionally truthful.
- Archive denies new projection/context; restore never replays without fresh
  reconciliation/current authorization.
- Candidate text remains unchanged opaque data: literal UI text and typed Bus
  quotation only.
- Frontend and backend authorization are separate; only backend checks grant
  access.

## Verification Targets

- `.venv/bin/python -m pytest tests/backend/agent_chat -q`
- `.venv/bin/python -m pytest tests/backend/api/test_ft008_feed_routes.py -q`
- `.venv/bin/python -m pytest tests/backend/access_admin tests/backend/agent_runtime tests/backend/agent_chat -m "not real_model" -q`
- `.venv/bin/python -m pytest tests -m "not real_model" -q`
- `node scripts/mb-lint.mjs`
- `git diff --check`

## UAT

- Create or reuse an active Plant, trigger/reconcile its deterministic roster,
  and observe exactly eight feed API items with no Bus copies.
- Retry/restart and confirm no duplicates.
- Archive and confirm no new projection or agent context; restore and run a
  fresh reconciliation.
- Publish representative markup/prompt/URL-looking safe information and confirm
  unchanged JSON text plus typed Bus quotation, with no active action or
  instruction semantics. Browser DOM proof follows in FT-016.

