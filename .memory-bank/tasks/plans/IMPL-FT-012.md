---
description: Implementation plan for FT-012 human approval, task/follow-up outcomes, and provider-neutral Task and Follow-up Agent.
status: active
last_updated: 2026-07-20
---
# IMPL-FT-012 — Human Approval Tasks And Follow-Up Outcomes

## Goal

Implement the authoritative Safety and Task Loop after FT-011: matched
ordinary task requests, current human approve/reject decisions, one
human-performed action Task, completion, deterministic +48-hour follow-up,
evidence-aware Outcome, and one provider-neutral `task_follow_up` path that can create
only a matched ordinary Task.

## Scope

- closed Task, Approval, and Outcome persistence and migration;
- idempotent pending Approval materialization from an immutable FT-011
  `pending_human_approval` decision;
- current ActorContext, Plant, permission, decision, expiry, and pH/EC evidence
  checks at the human-decision transaction;
- approve/reject atomicity and one action Task per Approval;
- ordinary `check|measurement|follow_up` Task creation only from a matched
  validated envelope/classification;
- immutable PostgreSQL one-shot consumption/denial for each classified
  ordinary `run_id`/`message_id`, including denial retention across restore;
- Task list, Approval list, human decision, completion, and Outcome HTTP;
- action completion plus exactly one +48-hour follow-up;
- Outcome plus follow-up completion atomicity and evidence policy;
- request-id/fingerprint idempotency, conflict, concurrency, and archive races;
- raw request-path UUID canonicality before decoded binding and branch-exact
  approval Timeline payloads;
- registered Timeline audit refs and redacted summaries;
- competence-specific `task_follow_up` request/result, strict provider-neutral
  executor seam, pending MessageEnvelope, matching classification, and ordinary-task
  handoff;
- immutable pre-classification `task_follow_up` runtime disposition keyed by
  exact run/command fingerprint, coordinated with the classified-message
  disposition without a transaction across model I/O;
- a competence-only Task/Outcome source-record resolver that does not widen
  W1 Outcome evidence acceptance;
- deterministic, PostgreSQL, HTTP, compatibility, outbound-spy, and anti-cheat
  evidence.

## Non-goals

- automated device commands, pumps, dosing, pH/EC correction, lights,
  autowatering, or any actuator integration;
- target values, quantities, recipes, schedules, or agronomic execution
  instructions;
- a pending-approval Task kind, second mutable proposal state machine,
  `cancelled|expired` stored states, or approval expiry extension;
- scheduler, worker, outbox, reminder execution, generic idempotency service,
  editable arbitrary tasks, or hard delete;
- a public agent invocation API, new Bus/UI payload contract, raw
  candidate/provider persistence, agent memory, tools, or RAG;
- direct Plant-state confirmation from Outcome or agent output;
- frontend/PWA components, owned by FT-016.

## Ordered implementation strategy

### 1. Authoritative Approval, Task, follow-up, and Outcome loop

1. Add the cohesive `backend/app/task_follow_up/` bounded package with strict
   domain commands/results, ORM models, repository locks, and transaction
   service. Reuse existing session/UoW, ActorContext permissions, current Plant
   resolution, redaction, and Timeline writer patterns.
2. Add one post-FT-011 Alembic revision for `approvals`, `tasks`, `outcomes`,
   and immutable `ordinary_task_dispatch_dispositions`, with exact closed
   matrices, restrictive UUID FKs, natural uniqueness, request
   ids/fingerprints, and no-cascade retention. Its
   `down_revision` is the implemented upstream head
   `ft011_safety_action_decisions`.
3. Wire idempotent post-commit Approval materialization at the actual FT-011
   handoff seam. Its failure cannot roll back the immutable Safety decision;
   explicit approve/reject safely retries materialization.
4. Replace the existing `safe_task_request -> no_effect` seam with the closed
   ordinary-task service. Validate the transient envelope plus persisted
   matching classification, then atomically record the first terminal
   PostgreSQL `consumed|denied` disposition under current authorization/Plant
   guard locks. A denial is immutable across restore for that `run_id` or
   `message_id`; only a new invocation with both new identities may be
   evaluated. Eligible consumption commits only
   `check|measurement|follow_up` with its Task audit ref.
5. Implement approve/reject with parent-row locking, current authority,
   immutable decision, exact source expiry, live pH/EC freshness, expected
   version, request fingerprint, and one-transaction approved action Task.
6. Implement Task completion. Action completion creates one unique open
   follow-up at `completed_at+48h`; generic completion rejects follow-up.
7. Implement Outcome recording with exact vocabulary/evidence refs and atomic
   follow-up completion. Keep Outcome evidence separate from Plant-state
   promotion.
8. Register and append exact Task/Approval/Outcome Timeline events before the
   matching PostgreSQL success. Rejected `approval_decided` omits
   `action_task_id`; approved requires its canonical Task UUID. Preserve
   runtime authority when an appended event becomes non-authoritative noise
   after a later commit failure.
9. Add protected list/mutation routes, strict Pydantic schemas, stable safe
   errors, no-store responses, and OpenAPI assertions. Enforce the lowercase
   canonical UUID spelling from raw ASGI path bytes before decoded binding,
   including percent-encoded-equivalent rejection.
10. Map only named concurrent request-id uniqueness losses after rollback and
    clean owner re-read to duplicate or `TASK_VERSION_CONFLICT`; unrelated DB
    errors remain `TASK_PERSISTENCE_FAILED`. Add focused integration,
    concurrency, raw-path, Timeline-branch, and archive/restore tests.

### 2. Provider-neutral Task and Follow-Up Agent through ordinary-task authority

1. Add competence-specific strict command, input assembler, provider request,
   model result, envelope mapping, and orchestration under the existing
   `backend/app/task_follow_up/` boundary. Do not widen generic
   `ProviderRequestV1`.
2. Load only current authorized PostgreSQL Task, Outcome, and evidence
   descriptors in deterministic order. Preserve Task text only in a typed
   untrusted quotation and exclude UI/Bus/Timeline replay, raw chat, auth
   objects, caller refs, prompts, and arbitrary evidence payloads.
3. Compute the allowed proposal set as `check|measurement|follow_up`, removing
   follow-up when the triggering action already has its unique automatic
   follow-up. Reject every action/approval/completion/Outcome/Plant/device
   field.
4. Reuse the provider-neutral executor seam, no fallback, post-I/O current
   authorization, sanitized common audit, and pending
   MessageEnvelope semantics.
5. Route one valid non-silent proposal through the actual Safety classifier.
   Require exact task-kind equality and then invoke the TASK-039 ordinary-task
   service. Every other class, mismatch, conflict, or current-guard denial has
   no Task effect and no restore replay.
6. Add the narrow `ft012_runtime_dispositions` migration after the accepted W1
   head. After model output, commit exactly one immutable
   `envelope_handed_off|publication_denied` row under a short run advisory lock;
   reuse that same lock/row check at the classified Task writer. Allocate an
   eligible message only after the locked current guard, release the
   transaction before Safety classifier I/O, and never persist/replay the
   envelope payload.
7. Split W2 source revalidation from the existing W1 Outcome evidence
   resolver. The competence resolver may load its strict Task/Outcome/evidence
   record union; `record_follow_up_outcome` continues rejecting `task:` and
   `outcome:` refs.
8. Add deterministic outbound-snapshot, schema/matrix, archive-race,
   idempotency, timeout/error, redaction, unbound-production, and no-authority
   fake/spy tests plus PostgreSQL fingerprint, identical/conflicting retry,
   concurrent run, runtime/classified exclusion, rollback, exact-head, and
   new-identity cases.

## Dependencies and waves

- Foundation gate `TASK-004-T2-FT-000-W0` is satisfied transitively through
  the existing FT-011 dependency chain.
- `TASK-039-T3-FT-012-W1` depends on
  `TASK-038-T3-FT-011-W2`, because it consumes the implemented immutable
  pending Safety decision, classification tables, provider route, and current
  migration head.
- `TASK-040-T3-FT-012-W2` depends on TASK-039 because the competence must
  use its authoritative ordinary-task persistence path and Task/Outcome input
  repositories.
- Shared package/composition/provider files are therefore changed
  sequentially, not by parallel execution.

## Current Wave State

- W1 `TASK-039-T3-FT-012-W1` is scheduler-recorded `done` from current
  ATTEMPT 03 implementation `PASS`, independent functional `PASS`, separate
  `semantic-pass`, and immutable closure evidence. ATTEMPT 01/02 remain failed
  history and are not selected as current evidence.
- W1 implemented the authoritative Approval, ordinary/action Task, automatic
  +48-hour follow-up, Outcome, and immutable classified-message disposition
  boundary. It also implements current authority/evidence/archive guards,
  exact retry/conflict/concurrency/rollback behavior, protected raw-path HTTP,
  branch-exact Timeline summaries, and no-actuation/no-Plant-state limits.
- `ft012_task_approval_outcomes` is the current product migration head directly
  after `ft011_safety_action_decisions`; the eight listed compatibility
  consumers pass against this exact head.
- W2 `TASK-040-T3-FT-012-W2` remains scheduler-owned `in_progress`. ATTEMPT 01
  verification reproduced two HIGH defects; ATTEMPT 02 stopped before product
  edits because pre-classification denial had no permissible durable owner.
  This bounded reconciliation defines the repair but does not select/start
  ATTEMPT 03, change lifecycle/status, or consume attempt budget.

## Expected touched files

Core lifecycle/API/persistence slice:

- `backend/app/task_follow_up/__init__.py`
- `backend/app/task_follow_up/contracts.py`
- `backend/app/task_follow_up/models.py`
- `backend/app/task_follow_up/repository.py`
- `backend/app/task_follow_up/service.py`
- `backend/app/agent_chat/publication.py`
- `backend/app/api/task_follow_up.py`
- `backend/app/main.py`
- `backend/app/timeline/writer.py`
- `backend/migrations/versions/ft012_task_approval_outcomes.py`
- `tests/backend/task_follow_up/conftest.py`
- `tests/backend/task_follow_up/test_domain_loop.py`
- `tests/backend/task_follow_up/test_migration_models.py`
- `tests/backend/api/test_ft012_task_follow_up_routes.py`
- the existing exact-head regression files named below.

Provider-neutral runtime slice:

- `backend/app/task_follow_up/` for competence-specific contracts, assembler,
  service/orchestration, and production composition;
- `backend/app/agent_runtime/providers.py`
- `backend/app/agent_runtime/__init__.py`
- `backend/app/main.py` only if composition wiring is needed;
- `backend/migrations/versions/ft012_runtime_dispositions.py`;
- `tests/backend/task_follow_up/test_runtime.py`
- `tests/backend/task_follow_up/test_domain_loop.py` for the W1 evidence-union
  non-regression;
- `tests/backend/task_follow_up/test_migration_models.py`;
- `tests/backend/agent_runtime/test_ft007_roster_providers.py` for the shared
  provider construction/outbound compatibility seam.

The canonical roster id and generic Agent Runtime request/service already
exist. `backend/app/agent_runtime/roster.py`, generic contracts, Plant
Operations, Access/Admin, and the future Safety package are touched only if
the implemented upstream seam proves a narrow compatibility edit necessary;
execution must stop rather than silently widening their public contracts.

TASK-040 advances the implemented W1 head to `ft012_runtime_dispositions` and
updates every repository exact-head assertion below in the same execution:

- `tests/backend/access_admin/test_ft002_schema_migration.py`
- `tests/backend/photo_intake/test_ft005_migration_models.py`
- `tests/backend/plant_operations/test_ft004_migration_models.py`
- `tests/backend/agent_chat/test_ft008_migration_models.py`
- `tests/backend/plant_state/test_migration_models.py`
- `tests/backend/safety_gate/test_migration_models.py`
- `tests/backend/safety_gate/test_classification_persistence.py`
- `tests/backend/test_foundation_database_contract.py`

## Source artifacts

- `.memory-bank/features/FT-012-human-approval-tasks-follow-up-outcomes.md`
- `.memory-bank/epics/EP-004-safety-tasks-follow-up.md`
- `.memory-bank/requirements.md` (`REQ-003`, `REQ-004`, `REQ-010`, `REQ-011`,
  `REQ-013`, `REQ-015`, `REQ-016`, `REQ-018`, `REQ-022`)
- `.memory-bank/features/FT-011-safety-gate-physical-action-routing.md`
- `.protocols/FT-012/decision-log.md`
- the three FT-012 behavior specs.

## Normative inputs and direct design links

- `.memory-bank/states/task-follow-up-lifecycle.md`
- `.memory-bank/domains/task-approval-outcomes.md`
- `.memory-bank/contracts/task-approval-http.md`
- `.memory-bank/contracts/task-follow-up-runtime.md`
- `.memory-bank/testing/task-follow-up.md`
- `.memory-bank/domains/safety-action-routing.md`
- `.memory-bank/states/safety-action-lifecycle.md`
- `.memory-bank/states/plants/plant-and-access-lifecycle.md`
- `.memory-bank/states/plant-state-trust.md`
- `.memory-bank/contracts/access/actor-context.md`
- `.memory-bank/contracts/api-guidelines.md`
- `.memory-bank/contracts/message-envelope.md`
- `.memory-bank/contracts/safety-gate-runtime.md`
- `.memory-bank/contracts/agent-chat-bus.md`
- `.memory-bank/contracts/agent-runtime-adapter.md`
- `.memory-bank/contracts/agent-model-provider-profiles.md`
- `.memory-bank/contracts/agent-roster-bootstrap.md`
- `.memory-bank/contracts/timeline-event.md`
- `.memory-bank/runbooks/agent-runtime-providers.md`

## Constraints and invariants

- PostgreSQL rows are the sole mutable task/approval/outcome authority.
  Timeline/UI/Bus/model data cannot create, repair, replay, or transition them.
- PostgreSQL terminal dispatch dispositions are the sole one-shot authority
  for classified ordinary-message consumption/denial. Their message and run
  identities cannot be cleared or re-evaluated after restore.
- The immutable runtime disposition is the sole pre-classification one-shot
  authority for `task_follow_up`. It stores no envelope/provider/auth payload,
  and the shared short run lock prevents contradiction with the downstream
  classified disposition without spanning Task model or Safety model I/O.
- Human approval revalidates current ActorContext, active Plant, immutable
  Safety decision, exact expiry, and pH/EC evidence; fresh evidence alone is
  never approval.
- An approved transition and one human action Task commit together or neither
  does. Human approval and Task completion never perform the physical action.
- Safe task requests and `task_follow_up` output create only matched ordinary
  kinds. No candidate/provider/model field can create `action`.
- Action completion creates exactly one automatic +48-hour follow-up. Outcome
  completion requires evidence except for `no_data` and does not directly
  confirm Plant state.
- Archive preserves all rows unchanged, blocks transitions, and restore never
  replays or refreshes them.
- A named request-id uniqueness race is rolled back before owner re-read;
  cross-parent/content reuse is a version conflict, while unrelated DB errors
  remain persistence failures.
- The runtime path uses the strict provider-neutral executor seam; production
  remains unbound and fail-closed, test fakes/spies are explicit, and no
  fake/silent production result or fallback can satisfy acceptance.

## Verification targets

- exact state/data/request/response matrices and restrictive migration/FKs;
- PostgreSQL round trip, transaction rollback, Timeline event cardinality,
  request fingerprint, identical/conflicting retry, and concurrent first
  writes;
- terminal consumed/denied disposition matrix, same-identity archived denial
  after restore, new run/message eligibility, and disposition write failure;
- runtime command fingerprint, exact denied retry, conflicting and concurrent
  same-run behavior, post-model archive/revoke durability, one post-guard
  message, runtime/classified exclusion, persistence rollback, and new command/
  run/message eligibility;
- W1 Outcome evidence rejects `task:`/`outcome:` while the competence-only
  source resolver accepts only its strict runtime record union;
- Boss/Engineer/Consultant, grant, archive/restore, expiry boundary, and
  current pH/EC evidence matrix;
- matched ordinary task, approve/reject, action completion +48 hours, Outcome
  evidence, and zero device/Plant-state effects;
- protected HTTP/OpenAPI/no-store/no-leak/redaction behavior, including raw
  percent-encoded-equivalent UUID rejection before decoded binding;
- concurrent cross-parent request-id conflict mapping, unrelated persistence
  failure preservation, and exact approved/rejected Timeline decision shapes;
- exact `TaskFollowUpProviderRequestV1` outbound allowlist, typed quotation,
  strict result, pending envelope, matching classification, and ordinary Task;
- deterministic outbound-spy no-fallback/no-fake-production anti-cheat plus
  FT-004/007/008/010/011 compatibility and full regression.

## Quality gates and UAT

- Run the task-specific commands in `.memory-bank/testing/task-follow-up.md`.
- Run the eight exact-head compatibility tests after the TASK-040 runtime
  disposition migration:
  `.venv/bin/python -m pytest tests/backend/access_admin/test_ft002_schema_migration.py tests/backend/photo_intake/test_ft005_migration_models.py tests/backend/plant_operations/test_ft004_migration_models.py tests/backend/agent_chat/test_ft008_migration_models.py tests/backend/plant_state/test_migration_models.py tests/backend/safety_gate/test_migration_models.py tests/backend/safety_gate/test_classification_persistence.py tests/backend/test_foundation_database_contract.py -q`.
- Run the bounded W2 repair matrix:
  `.venv/bin/python -m pytest tests/backend/task_follow_up/test_runtime.py tests/backend/task_follow_up/test_domain_loop.py tests/backend/task_follow_up/test_migration_models.py -m "not real_model" -q`.
- Run `node scripts/mb-lint.mjs` and `git diff --check` for both waves.
- Run the full deterministic suite before handoff when the environment permits.
- Current acceptance uses deterministic fake/spy evidence, including timeout,
  provider error, invalid output, post-I/O denial, redaction, and unbound
  production. It does not require a provider, model, base URL, credential,
  egress, network call, or non-skipped live smoke.
- Real request/response, error, timeout, redaction, and cost verification is
  deferred to the shared future selected-endpoint milestone and is not current
  closure evidence.
- Browser task/approval cards remain FT-016; backend JSON/OpenAPI behavior is
  verified here.

## Constitution Check

- Principle I/IV: implementation is derived from the current feature, exact
  canonical specs, and schema-backed task cards.
- Principle II/VIII: two cohesive waves reuse the modular monolith,
  PostgreSQL, ActorContext, Timeline, classifier, and provider seams; no
  scheduler, worker, outbox, generic idempotency framework, or device stack is
  added.
- Principle VI/VII: agent autonomy ends at a classified ordinary-task
  proposal; every physical action remains human-performed behind current
  Safety and approval guards.
- Principle IX: conflicts, expiry, archive races, provider failures, and
  unknown/mismatched output fail closed without fallback or speculative state.

No Constitution blocker remains.
