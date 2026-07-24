---
description: Implementation plan for FT-012 human approval, task/follow-up outcomes, and provider-neutral Task and Follow-up Agent.
status: active
last_updated: 2026-07-24
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
- linear best-effort `task_follow_up` invocation with no pre-classification
  runtime ledger, durable delivery identity, or zero-call replay contract;
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
5. Route one valid non-silent proposal linearly through the post-I/O current
   guard, sanitized attempt audit, actual Safety classifier, and TASK-039
   ordinary-task service. Require exact task-kind equality. Every other class,
   mismatch, conflict, or current-guard denial has no Task effect. Repeated
   internal invocation may repeat model/audit/classifier work but must recheck
   current authority and cannot create a duplicate Task.
6. Remove `TaskFollowUpRuntimeDisposition`, its repository/runtime/service
   coupling, runtime preflight/replay resolver, shared runtime writer lock
   protocol, and `TaskFollowUpDispositionResultV1`. Keep
   `TaskFollowUpRunResultV1`, global `AgentRuntimeOutcomeV1`, and the
   classified ordinary writer's transaction/run-key serialization unchanged.
7. Add one forward cleanup migration after the executor-confirmed current
   head. Always remove `expected_task_create_fingerprint`, its matrix,
   function, and trigger. Remove `task_follow_up_runtime_dispositions` only
   after a before-DDL preflight proves it empty; any deployment row stops
   execution without schema/data mutation. Fresh ORM metadata omits all removed
   objects and existing FT-012/FT-013 revisions are never rewritten.
8. Split W2 source revalidation from the existing W1 Outcome evidence
   resolver. The competence resolver may load its strict Task/Outcome/evidence
   record union; `record_follow_up_outcome` continues rejecting `task:` and
   `outcome:` refs.
9. Add deterministic outbound-snapshot, schema, archive-race, timeout/error,
   redaction, unbound-production, and no-authority fake/spy tests. Keep the
   cheapest sufficient real PostgreSQL write-side matrix: identical/conflicting
   classified writers, consumed/denied uniqueness, current-authority duplicate
   read, Task/disposition/audit rollback, and at most one Task. Remove the
   independent commitment, runtime-ledger replay/crash/advisory matrices,
   coordinated direct-SQL probes, and related hostile tests. Prove linear
   routing, no mapped/written runtime ledger, data-safe forward cleanup,
   fresh-schema absence, and current exact-head compatibility.

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
- The accepted W1 boundary is `ft012_task_approval_outcomes` directly after
  `ft011_safety_action_decisions`. Historical TASK-040 added
  `ft012_runtime_dispositions`; subsequent FT-013 work may already be the
  repository head. The reopened repair therefore adds one forward cleanup
  revision after the executor-confirmed current head and does not rewrite
  either existing revision.
- W2 `TASK-040-T3-FT-012-W2` preserves its complete ATTEMPT 01-06 history and
  the owner-accepted ATTEMPT 06 implementation/functional closure with the
  explicit semantic-stage waiver. The final 2026-07-24 operator decision
  supersedes both coordinated direct-PostgreSQL-corruption hardening and the
  pre-classification runtime ledger/replay/crash matrix, and keeps the same
  task `planned`. Its ID, T3 tier, W2 wave, dependency, provider-neutral product
  outcome, public contracts, and real classified write-side
  concurrency/idempotency requirements remain unchanged.

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
  linear service/orchestration, ordinary-writer decoupling, and simplified ORM
  metadata;
- `backend/migrations/versions/ft012_simplify_task_follow_up_runtime.py` as
  one forward cleanup revision after the executor-confirmed current head;
- `tests/backend/task_follow_up/test_runtime.py`
- `tests/backend/task_follow_up/test_domain_loop.py` for the W1 evidence-union
  non-regression;
- `tests/backend/task_follow_up/test_migration_models.py`.

The canonical roster id and generic Agent Runtime request/service already
exist. `backend/app/agent_runtime/roster.py`, generic contracts, Plant
Operations, Access/Admin, and the future Safety package are touched only if
the implemented upstream seam proves a narrow compatibility edit necessary;
execution must stop rather than silently widening their public contracts.

The reopened TASK-040 advances the executor-confirmed current head to its
forward cleanup revision and updates every repository exact-head assertion
below in the same execution:

- `tests/backend/access_admin/test_ft002_schema_migration.py`
- `tests/backend/photo_intake/test_ft005_migration_models.py`
- `tests/backend/plant_operations/test_ft004_migration_models.py`
- `tests/backend/agent_chat/test_ft008_migration_models.py`
- `tests/backend/plant_state/test_migration_models.py`
- `tests/backend/safety_gate/test_migration_models.py`
- `tests/backend/safety_gate/test_classification_persistence.py`
- `tests/backend/companion_governance/test_migration_models.py`
- `tests/backend/test_foundation_database_contract.py`

## Source artifacts

- `SIMPLIFICATION.md`
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
- `task_follow_up` is a linear best-effort invocation with no
  pre-classification runtime authority. It repeats current guards after model
  I/O, keeps provider/Safety I/O outside Task write transactions, and may
  repeat non-authoritative model/audit/classifier work when explicitly
  reinvoked.
- `TaskFollowUpRunResultV1` remains the only competence-local result. No
  runtime disposition result union or global `AgentRuntimeOutcomeV1` widening
  is permitted.
- The existing classified writer atomically persists Task, audit ref, and the
  consumed disposition. Exact classified retry resolves the uniquely linked
  Task only after current ActorContext/Farm/Plant read/task authority and no
  second Task write. It does not depend on a runtime row, persist an independent
  commitment, or deep-reconstruct historical Task text/kind/sources/
  attribution. Direct coordinated PostgreSQL corruption is outside the current
  threat model.
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
- linear provider -> post-I/O guard -> audit -> transient envelope -> Safety ->
  ordinary writer routing, including allowed repeated internal model/audit/
  classifier work and no mapped/written runtime ledger;
- service-owned classified retry through classification/disposition identity
  plus the unique Task link, current authority block, missing-link redacted
  failure, rollback, and no raw-envelope persistence;
- forward cleanup migration after the executor-confirmed current head, fresh
  ORM absence of the removed commitment and runtime-ledger objects,
  before-DDL refusal when historical runtime rows exist,
  rollback-compatible downgrade, and exact-head consumer updates without
  rewriting FT-013 migration history;
- real write-side concurrency matrix: identical classified writers resolve one
  Task, conflicting writers preserve the winner, denial commits no Task,
  Task/disposition/audit atomic rollback, and provider/Safety I/O outside the
  Task transaction;
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
- Run all current exact-head compatibility tests after the TASK-040 cleanup
  migration:
  `.venv/bin/python -m pytest tests/backend/access_admin/test_ft002_schema_migration.py tests/backend/photo_intake/test_ft005_migration_models.py tests/backend/plant_operations/test_ft004_migration_models.py tests/backend/agent_chat/test_ft008_migration_models.py tests/backend/plant_state/test_migration_models.py tests/backend/safety_gate/test_migration_models.py tests/backend/safety_gate/test_classification_persistence.py tests/backend/companion_governance/test_migration_models.py tests/backend/test_foundation_database_contract.py -q`.
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
