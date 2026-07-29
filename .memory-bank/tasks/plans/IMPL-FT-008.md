---
description: Implementation plan for FT-008 Agent Chat Bus, UI Feed, lazy roster introductions, and context hygiene.
status: active
type: implementation_plan
feature_id: FT-008
last_updated: 2026-07-29
source_of_truth:
  - .memory-bank/features/FT-008-agent-chat-bus-ui-feed-context-hygiene.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/agent-roster-bootstrap.md
  - .memory-bank/contracts/ui-feed.md
  - .memory-bank/domains/agent-chat-ui-feed-storage.md
  - .memory-bank/contracts/plant-feed-http.md
  - .memory-bank/contracts/farm/plant-management-http.md
  - .memory-bank/testing/agent-chat-ui-feed.md
  - .memory-bank/testing/agent-runtime.md
---
# IMPL FT-008 Agent Chat Bus And UI Feed Context Hygiene

## Goal

Replace the presentation-only introduction batch lifecycle with one lazy,
idempotent active-Feed materialization boundary while preserving the canonical
ordered roster, deterministic introduction identities, every existing
`UIFeedEvent` row, and the already verified Bus/UI/context/public Feed
contracts.

## Cohesive Outcome And Ownership

`TASK-046-T3-FT-008-W3` is the only new implementation outcome.

- Primary orchestration owner: **Agent Chat Bus & UI Feed** under
  `backend/app/agent_chat/`.
- Crossed boundaries: Agent Runtime static roster metadata, Plant-create
  compatibility, application startup composition, protected Plant Feed HTTP,
  PostgreSQL migration/model state, and current ActorContext/Plant grant locks.
- The Agent Chat Bus & UI Feed application service owns lazy materialization.
  HTTP handlers delegate to it; generic utilities and the composition root do
  not own business orchestration.
- Agent Runtime may expose only canonical roster/introduction metadata. It does
  not write presentation rows or retain a sink/result/retry lifecycle.

The removal and replacement stay in one card because neither half has an
independently releasable or observable product outcome. Shipping only removal
loses introductions; shipping only the lazy writer leaves duplicate ownership
and the obsolete startup/create lifecycle.

## Scope

- Retain the exact eight-agent roster, order, competence metadata, immutable
  UUIDv5 namespace/name grammar, introduction payload mapping, and both
  non-agent-consumability flags.
- Remove FT-007 batch command/value/result/sink code and post-create Plant
  handoff; keep only the smallest deterministic per-item metadata builder.
- Remove the concrete FT-008 batch sink, digest/conflict/result machinery,
  startup reconciliation service, composition state, logging, and obsolete
  tests.
- Add one forward migration after the current Alembic head that drops only
  `agent_introduction_batches`; do not rewrite the applied FT-008 migration.
- Extend the existing protected Feed application transaction to lock/recheck
  current Account, FarmMembership, applicable PlantAccessGrant, and Plant
  state, insert only missing canonical rows for an active Plant, then read the
  unchanged ordered page.
- Preserve archived retained-history reads as read-only. Plant create,
  startup, archive/restore, Agent Chat Bus, and agent-context paths write no
  introduction row.
- Prove repeat, concurrent, rollback, and client-retry idempotency plus
  unchanged public response/order/cursor and `FEED_PERSISTENCE_FAILED`.

## Non-goals

- No new table, pending flag, materialization receipt, lifecycle, endpoint,
  response field, cursor version, worker, scheduler, outbox, maintenance scan,
  or repair API.
- No rewrite/delete/backfill of existing `ui_feed_events`, Bus rows, or applied
  migrations.
- No change to roster membership/content, MessageEnvelope, classified
  publication, Safety/Task/Companion behavior, agent context, Plant lifecycle,
  or frontend/PWA rendering.
- No unrelated cleanup and no mutation of historical TASK-031, TASK-032,
  TASK-033, or TASK-045 records, protocols, or evidence.

## Ordered Implementation Strategy

1. Reduce Agent Runtime introduction support to deterministic per-item metadata
   and remove the Plant-create batch/sink handoff and its composition imports.
2. Remove batch model/sink/reconciliation code; add a forward migration from
   the executor-confirmed current head that drops only the batch table and
   advance exact-head tests.
3. Put missing-row insertion in the existing Agent Chat Bus & UI Feed
   `PlantFeedService` transaction after current no-leak authorization and
   active/archive resolution, before the normal page query.
4. Replace batch/reconciliation tests with PostgreSQL and HTTP evidence for
   data preservation, sole trigger, current locks, missing-only writes,
   concurrency, rollback/retry, negative triggers, and unchanged pagination.
5. Run focused, migration-head, access/runtime, full deterministic, Memory
   Bank lint, and diff checks.

## Dependencies And Queue

- `TASK-033-T3-FT-008-W2` is the current terminal FT-008 Feed/Bus/context
  baseline and reaches TASK-032/TASK-031/Foundation transitively.
- `TASK-045-T3-FT-007-W3` is the current terminal FT-007 production-composition
  baseline and reaches TASK-031/Foundation transitively.
- `TASK-046-T3-FT-008-W3` depends directly on both and is `done` after fresh
  `/review-tasks-plan FT-008` approval for Planning Revision 2 and all required
  T3 closure gates.

## Completion Evidence

- The indexed
  [TASK-046 task record](../TASK-046-T3-FT-008-W3.task.json) is authoritative
  for the owner-recorded `done` decision and its implementation, functional
  verification, semantic verification, and human-checkpoint evidence links.
- The completed outcome matches this plan without a new state, lifecycle,
  public contract, or follow-up task.

## Expected Advisory Change Surface

- `backend/app/agent_runtime/bootstrap.py` and exports;
- `backend/app/agent_chat/` models, Feed service, obsolete sink/reconciliation
  files, and package exports;
- `backend/app/api/plants.py`, `backend/app/api/feed.py`, and
  `backend/app/main.py`;
- one new `backend/migrations/versions/*_ft008_lazy_introductions.py`;
- Agent Runtime, Agent Chat, Plant-create, Feed API, migration-model,
  Foundation database-contract, and exact-head regression tests.

## Constitution And Architecture Check

- Spec-driven: AD-010 and the registered roster/storage/Feed/Plant/testing
  specs define the complete outcome.
- KISS/low maintenance: one existing Feed transaction replaces batch state,
  sink/result/digest code, startup scan, and reconciliation tests without new
  state or operations.
- Security/data: same-transaction current authorization and active-state locks
  keep the task T3; a data-preserving forward migration and fresh independent
  verification are mandatory.
- Recovery: an active Feed request rolls back on persistence failure and the
  existing client retry is sufficient. No background repair cost is accepted.
- Blockers: none.

## Invariants

- Existing introduction rows retain identity, payload, `created_at`, order,
  uniqueness, FKs, and non-agent-consumability.
- Only an authorized active-Plant Feed open inserts missing introduction rows;
  every other named path writes zero.
- Repeat, concurrent, and retried opens converge without updating existing rows
  or copying an introduction into Bus/context.
- Plant creation commit/`201` and public Feed response/order/cursor stay exact.
- Secrets, auth/session material, provider data, hidden reasoning, and raw chat
  never enter presentation rows or evidence.

## Verification Targets And UAT

- Focused Agent Runtime/Agent Chat/Plant-create/Feed tests.
- Real-PostgreSQL migration preservation and lazy materialization probes.
- Current authorization, grant-revocation, archive race, archived read,
  restore, concurrent open, injected failure/rollback, and successful retry.
- Static absence of batch/result/digest/sink/reconciliation/startup wiring.
- Exact OpenAPI/response/order/cursor compatibility and zero Bus/context copy.
- Full T3 route: `/verify`, per-task `/red-verify`, and
  `HUMAN_CHECKPOINT: done` before closure.

Manual UAT may open an active Plant Feed with zero/partial/existing
introductions, repeat the request, archive/read/restore/reopen, and observe the
same public API with no duplicates. Automated PostgreSQL evidence remains the
authoritative reproducible proof.
