---
description: Implementation plan for FT-011 model-backed Safety classification and physical-action routing.
status: active
last_updated: 2026-07-17
---
# IMPL-FT-011 — Safety Gate Physical-Action Routing

## Goal

Implement the canonical `safety_gate` real-model classifier and the
project-owned, PostgreSQL-backed Safety route from a pending MessageEnvelope to
safe publication/task handoff, fail-closed block, or an immutable physical
action decision ending at `pending_human_approval`.

## Scope

- strict `SafetyGateProviderRequestV1` and model candidate validation;
- backend-owned `SafetyClassificationResultV1` mapping and immutable
  classification persistence;
- first-write-wins idempotency/concurrency and current authorization/archive
  guards;
- exact supported and unsupported action kinds;
- current approval authority and independent pH/EC `approval_input=2h`
  evaluation;
- immutable Safety decision/proposal persistence and expiry;
- additive, non-consumable `safety_status` UI Feed/read projection;
- focused, integration, compatibility, concurrency, migration, and optional
  credentialed real-model evidence.

## Non-goals

- human approve/reject API or state;
- `Approval`, `action_task`, completion, follow-up, or outcome records;
- automated device commands or actuation;
- dosage, target-value, nutrient-recipe, or schedule calculation;
- a new public FT-011 HTTP endpoint or frontend component;
- dedicated Timeline events or raw candidate/provider persistence;
- changing the separate FT-010 24-hour analysis freshness policy.

## Ordered implementation strategy

### 1. Real model-backed authoritative classification

1. Add a cohesive `backend/app/safety_gate/` package with strict command,
   provider request/candidate, backend mapping, service, repository, and ORM
   seams.
2. Reconcile the existing prototype `SafetyClassificationResultV1` with the
   canonical shared contract; do not duplicate or widen its route matrix.
3. Extend the existing provider executor/factory only as needed to bind the
   competence-specific Safety candidate schema. Keep explicit provider/model
   selection and no fallback.
4. Add the `safety_classifications` migration/model/repository with exact
   constraints, fingerprints, immutable duplicate/conflict semantics, current
   pre/post-provider guards, and no raw candidate column.
5. Expose a persisted classification result/handoff that later routing can
   consume; provider/error/invalid/uncertain paths become durable
   `blocked_uncertain` only when the current write guard succeeds.
6. Add deterministic and optional credentialed product-agent tests.

### 2. Deterministic Safety action routing and projection

1. Add `safety_action_decisions` persistence and the route orchestrator over a
   persisted classification.
2. Reuse current ActorContext resolution and the Plant Operations latest
   measurement/freshness semantics inside the decision transaction. Stabilize
   the repository/service seam only if required for one-transaction reads.
3. Enforce the exact action matrix, current approver authority, independent
   two-hour pH/EC evidence, project-owned summaries, and deterministic expiry.
4. Extend the existing UI Feed model/storage/read union with the strict
   `safety_status` variant. Commit the decision and UI row atomically; do not
   add a new endpoint or Bus event for physical text.
5. Wire route outcomes: existing guarded FT-008 safe/block projection,
   ordinary-task handoff without FT-012 persistence, and FT-011 physical Safety
   evaluation. Every effect repeats its current guard.
6. Add migration/model, PostgreSQL service, feed compatibility, archive/race,
   no-actuation, and deterministic regression tests.

## Dependencies and waves

- Foundation gate `TASK-004-T2-FT-000-W0` is satisfied transitively.
- `TASK-037-T3-FT-011-W1` depends on
  `TASK-036-T3-FT-010-W1` so the upstream canonical Advisor pending handoff is
  available for integration/regression.
- `TASK-038-T3-FT-011-W2` depends on TASK-037 and owns the later deterministic
  route/projection slice.
- FT-012 consumes only the final immutable pending decision after this plan; it
  is not an implementation dependency for FT-011.

## Expected touched files

Classifier slice:

- `backend/app/safety_gate/__init__.py`
- `backend/app/safety_gate/contracts.py`
- `backend/app/safety_gate/provider_adapter.py`
- `backend/app/safety_gate/models.py`
- `backend/app/safety_gate/repository.py`
- `backend/app/safety_gate/service.py`
- `backend/app/agent_runtime/contracts.py`
- `backend/app/agent_runtime/providers.py`
- `backend/app/agent_runtime/__init__.py`
- `backend/app/main.py` for internal production composition only;
- `backend/migrations/versions/*_ft011_safety_classifications.py` for the
  `safety_classifications` Alembic revision;
- `tests/backend/safety_gate/test_classifier.py`
- `tests/backend/safety_gate/test_classification_persistence.py`
- `tests/backend/safety_gate/test_real_safety_gate_smoke.py`
- focused Agent Runtime/provider/publication regression tests when behavior is
  directly affected.

Routing/projection slice:

- `backend/app/safety_gate/models.py`
- `backend/app/safety_gate/repository.py`
- `backend/app/safety_gate/service.py`
- `backend/app/plant_operations/repository.py` and/or `service.py` only for a
  stable same-transaction latest-measurement seam;
- `backend/app/agent_chat/contracts.py`
- `backend/app/agent_chat/models.py`
- `backend/app/agent_chat/repository.py`
- `backend/app/agent_chat/publication.py`
- `backend/app/api/feed.py`
- `backend/app/main.py` if the route orchestrator requires composition wiring;
- `backend/migrations/versions/*_ft011_safety_action_decisions.py` for the
  `safety_action_decisions` and additive UI-check Alembic revision;
- `tests/backend/safety_gate/test_action_routing.py`
- `tests/backend/safety_gate/test_migration_models.py`
- focused FT-004/FT-008 feed/publication regression tests.

Exact migration filenames and any narrowly adjacent test file are selected
against the current post-dependency migration head during execution.

Both migration-owning waves also own compatibility updates to the repository's
existing exact-head assertions. W1 advances them to the classification
revision; W2 advances the same assertions to the action-decision/UI revision:

- `tests/backend/access_admin/test_ft002_schema_migration.py`
- `tests/backend/photo_intake/test_ft005_migration_models.py`
- `tests/backend/plant_operations/test_ft004_migration_models.py`
- `tests/backend/agent_chat/test_ft008_migration_models.py`
- `tests/backend/test_foundation_database_contract.py`

## Source artifacts

- `.memory-bank/features/FT-011-safety-gate-physical-action-routing.md`
- `.memory-bank/epics/EP-004-safety-tasks-follow-up.md`
- `.memory-bank/requirements.md` (`REQ-003`, `REQ-004`, `REQ-008`, `REQ-011`,
  `REQ-013`, `REQ-014`, `REQ-015`, `REQ-018`)
- `.memory-bank/features/FT-010-hydroponics-advisor-missing-data-policy.md`
- `.memory-bank/features/FT-012-human-approval-tasks-follow-up-outcomes.md`
- `.protocols/FT-011/decision-log.md`
- the three FT-011 behavior specs.

## Normative inputs and direct design links

- `.memory-bank/contracts/safety-gate-runtime.md`
- `.memory-bank/domains/safety-action-routing.md`
- `.memory-bank/states/safety-action-lifecycle.md`
- `.memory-bank/contracts/message-envelope.md`
- `.memory-bank/contracts/agent-runtime-adapter.md`
- `.memory-bank/contracts/agent-model-provider-profiles.md`
- `.memory-bank/contracts/agent-roster-bootstrap.md`
- `.memory-bank/contracts/access/actor-context.md`
- `.memory-bank/domains/plant-operations.md`
- `.memory-bank/states/plants/plant-and-access-lifecycle.md`
- `.memory-bank/contracts/agent-chat-bus.md`
- `.memory-bank/contracts/ui-feed.md`
- `.memory-bank/domains/agent-chat-ui-feed-storage.md`
- `.memory-bank/contracts/plant-feed-http.md`
- `.memory-bank/testing/safety-gate.md`

## Constraints and invariants

- A model result is candidate data; only a validated and durably persisted
  backend result is classification authority.
- Invalid, unavailable, failed, or uncertain classifier branches fail closed
  to the generic non-consumable block route. A conflicting retry creates no
  downstream effect and cannot replace the first result.
- Pending/blocked UI content is project-owned, non-imperative, contains no raw
  candidate text, and is never agent-consumable.
- Every physical action decision uses current actor/Plant guards. Supported
  kinds require both pH and EC under `approval_input=2h`; fresh evidence alone
  is never approval.
- No human decision, task, follow-up, device command, or automated actuation is
  created by FT-011.
- PostgreSQL is operational authority. Timeline/UI/Bus/model output cannot
  substitute for classification, evidence, Safety, or approval state.
- Archive preserves existing records but blocks new state advancement; restore
  performs no replay or implicit refresh.

## Verification targets

- exact strict classifier request/candidate/result and ten-kind action union;
- real-provider no-fallback anti-cheat and redacted outbound allowlist;
- PostgreSQL matrix constraints, UUID/FK parity, fingerprints, immutable
  duplicate/conflict behavior, and migration head;
- current authorization, Plant, grant, and archive races before and after
  provider I/O and at each write;
- all three supported kinds, all seven unsupported kinds, current role matrix,
  pH/EC missing/stale/future/exact-boundary cases, and deterministic expiry;
- atomic Safety decision/UI projection, strict feed response union, literal
  safe summary, candidate absence, and no Bus/task/approval/actuation effect;
- FT-004, FT-007, FT-008, and FT-010 compatibility plus full deterministic
  regression.

## Quality gates and UAT

- Run the task-specific commands in `.memory-bank/testing/safety-gate.md`.
- After each FT-011 revision, run the five existing exact-head regression files
  named above and keep their ordered-history assertions aligned with that
  wave's new product head.
- Run `node scripts/mb-lint.mjs` and `git diff --check`.
- Run the full deterministic suite before handoff when the environment permits.
- Credentialed Safety Gate smoke is an explicit opt-in UAT using
  `AGENT_REAL_SAFETY_GATE_SMOKE=1`; missing credentials do not make
  deterministic implementation evidence false, but REQ-011 product-agent
  acceptance must not be claimed without an accepted real run.
- Browser-level rendering remains FT-016; backend feed union and inert JSON
  semantics are verified here.

## Constitution Check

- Principle I: implementation is derived from current feature, requirements,
  and concrete subject specs.
- Principle II/VIII: two cohesive tasks reuse existing runtime, evidence,
  authorization, feed, and PostgreSQL seams; no new service, endpoint, worker,
  outbox, Timeline type, or device framework is introduced.
- Principle VI/VII: model autonomy ends at a strict candidate; physical action
  remains behind fresh evidence, backend Safety, and later human approval.
- Principle IX: unsafe unknowns and provider failures fail closed; no fake
  runtime acceptance or undocumented fallback is permitted.

No Constitution blocker remains.
