---
description: Implementation plan for FT-009 provider-neutral vision observation and Plant state trust.
status: active
type: implementation_plan
feature_id: FT-009
last_updated: 2026-07-20
source_of_truth:
  - .memory-bank/features/FT-009-vision-observation-plant-state-trust.md
  - .memory-bank/contracts/vision-observation-runtime.md
  - .memory-bank/contracts/plant-state-runtime.md
  - .memory-bank/domains/plant-state-observations.md
  - .memory-bank/domains/photo-artifacts.md
  - .memory-bank/contracts/plant-state-http.md
  - .memory-bank/testing/vision-observation-plant-state.md
---
# IMPL FT-009 Vision Observation And Plant State Trust

## Goal

Process one authorized accepted Plant photo through the strict provider-neutral
Vision executor seam, preserve its output as a pending non-authoritative handoff, and
provide PostgreSQL-backed trust records where trends/conflicts remain visible
and only explicit human/evidence review can confirm Plant state.

## Scope

- Add bounded `backend/app/vision_observation/` request, media, definition,
  executor adapter, service, and tests.
- Reuse photo catalog authority, file integrity, ActorContext, provider
  profiles, current publication guard, sanitized timeline audit, and pending
  MessageEnvelope.
- Add `backend/app/plant_state/` models/repository/service, one guarded Alembic
  migration, classified-only record creation, Plant State assessment input,
  conflict validation, and explicit confirm/reject transitions.
- Add protected paginated Plant state list and human review HTTP.
- Add deterministic anti-cheat, outbound-spy, timeout/error, and redaction tests.

## Non-goals

- No disease diagnosis, physical-action recommendation, Safety classifier,
  approval/action task, automated device action, Companion, dataset, or sensor
  implementation.
- No public prompt/model endpoint, automatic background worker, outbox,
  provider file persistence, provider history, agent memory/RAG/tools, or raw
  response storage.
- No Svelte/PWA scaffold or browser-visible success claim; FT-016 consumes the
  API. No Bus/UI publication policy; FT-008/FT-011 own those boundaries.

## Ordered implementation strategy

1. Implement strict vision value objects and canonical definition.
2. Assemble one authorized catalog photo, verify containment/size/hash, and
   attach its bytes to exactly one outbound-spy call without path/auth leakage.
3. Reuse the existing post-model guard, audit, outcome, and pending envelope;
   prove deterministic provider-neutral behavior without a live-provider claim.
4. Add the guarded `plant_state_records` migration/model/repository.
5. Add classified-only creation, Plant State assessment validation, conflict
   handling, and optimistic human promotion.
6. Add list/review API and focused/full deterministic regression.

## Dependencies

- `TASK-026-T2-FT-005-W3` is done and provides the accepted photo catalog,
  local artifact layout, safe refs, and protected catalog behavior.
- `TASK-031-T3-FT-007-W2` is done and provides the canonical roster, explicit
  providers, current authorization guard, pending MessageEnvelope, and audit
  seams. Its deferred generic transport UAT does not satisfy FT-009.
- Foundation is complete transitively through those baselines.

## Current W2 Boundary State

- The scheduler subsequently completed the authorized recovery sequence and
  recorded `TASK-035-T3-FT-009-W2` `done` from current ATTEMPT 04 implementation
  `PASS`, independent functional `VERDICT: PASS`, and separate
  `SEMANTIC_VERDICT: semantic-pass` evidence.
- The direct dependent `TASK-036-T3-FT-010-W1` was scheduler-recorded `planned`
  through dependency recovery at this boundary and was subsequently completed
  under its own FT-010/W1 scheduler evidence. TASK-037 was `planned` at this
  boundary and was subsequently completed under its own FT-011/W1 ATTEMPT 03
  scheduler evidence.
- FT-009 feature lifecycle and all RTM lifecycles remain unchanged by this
  evidence sync. The recovery sections below are retained as append-only
  planning history and do not describe the current task lifecycle.

## TASK-035 owner-authorized recovery ATTEMPT 04

On 2026-07-20 the owner authorized exactly one further post-halt defect-repair
attempt for the existing `TASK-035-T3-FT-009-W2`; this is not new functionality
or a replacement task. ATTEMPT 01–03, their reports, closure decisions, and
terminal history remain immutable. For this task only, the exact next attempt
is `04`, the effective limit is `4`, one recovery attempt is authorized, and
`0` attempts remain after ATTEMPT 04. The global `max_attempts_per_task: 2`
remains unchanged; no ATTEMPT 05 is implied.

The accepted scope is only the ATTEMPT 03 stale identity-map defect. Under the
project session configuration with `expire_on_commit=False`, the authoritative
locked `PhotoCatalogItem` read in `persist_classified()` must refresh an
already-loaded ORM identity (using the established local
`populate_existing=True` pattern) or use a locked scalar projection. A
retained-session real-PostgreSQL regression must preload a photo owned by Plant
A in Session A and commit, move its authoritative catalog metadata to Plant B
in Session B and commit, then prove that reused Session A persistence for Plant
A returns `PLANT_STATE_CANDIDATE_INVALID`, writes zero Plant-state rows, and
exposes no raw database error.

Implementation writes are limited to `backend/app/plant_state/service.py`,
`tests/backend/plant_state/test_service.py`, and TASK-035 protocol/numbered
reports. `backend/app/database.py` and
`backend/app/photo_intake/models.py` are read-only dependencies. API/cursor
files, schemas, models, migrations, Vision/Photo Intake/provider/shared runtime
code, and public contracts are forbidden. Preserve all already-passing
photo-only/ordered refs, direct cross-Plant, authorization, idempotency,
assessment, cursor/no-enumeration, provider-neutral, redaction, and no-authority
behavior. Live-provider credentials, egress, network, and smoke evidence remain
deferred and are neither required nor claimed.

Planning leaves TASK-035 `failed`. After this bounded reconciliation and a
fresh `/review-tasks-plan FT-009` `APPROVE`, the scheduler may record only the
non-attempt, evidence-preserving `failed -> planned` transition. A fresh strict
doctor PASS over that recovered queue is then required before promotion and
selection; only `ready -> in_progress` consumes ATTEMPT 04.

## Historical TASK-035 owner-authorized recovery ATTEMPT 03

The owner approved one post-halt defect-repair attempt for the existing
`TASK-035-T3-FT-009-W2`; this is not new functionality or a replacement task.
ATTEMPT 01–02 and the `HALT_FAILURE_BUDGET` evidence remain immutable. For this
task only, the next attempt is `03`, the effective limit is `3`, and `0`
attempts remain after it. After bounded planning reconciliation and a fresh
`/review-tasks-plan FT-009` `APPROVE`, the scheduler may perform only the
non-attempt `failed -> planned` recovery. That transition preserves all prior
evidence and attempt accounting and does not start or consume ATTEMPT 03. A
fresh `/mb-doctor --strict` PASS over the recovered `planned` queue is then
mandatory before `planned -> ready`, selection, or ATTEMPT 03 consumption.

The first pre-transition strict-doctor run returned exactly one error,
`TASK_QUEUE_DEADLOCK`, because TASK-035 still carried the authorized `failed`
lifecycle hold. This is sequencing evidence for the order above, not a
structural waiver and not a substitute for the required post-transition PASS.

The recovery scope contains exactly two defects:

1. At `persist_classified()`'s PostgreSQL persistence boundary, enforce the
   canonical Vision source-ref grammar and authoritative `PhotoCatalogItem`
   Farm/Plant ownership in the same transaction as current authorization,
   active-Plant validation, and insert. Use catalog metadata only; do not read
   photo bytes. Provenance mismatch returns `PLANT_STATE_CANDIDATE_INVALID`,
   authorization mismatch returns `AUTH_PLANT_FORBIDDEN`, and every denial
   writes zero rows without a raw `IntegrityError`.
2. Map malformed, noncanonical, and wrong-Plant cursors on the existing list
   route to canonical `422 VALIDATION_FAILED`; do not change the public schema
   or introduce another error contract.

Implementation writes are limited to
`backend/app/plant_state/service.py`, `backend/app/api/plant_state.py`,
`tests/backend/plant_state/`,
`tests/backend/api/test_ft009_plant_state_routes.py`, and the task's protocol
and numbered reports. `backend/app/photo_intake/models.py` is a read-only
dependency. Vision/Photo Intake schemas, models, migrations, provider/runtime
code, and every other public schema are out of scope.

Required real-PostgreSQL regression evidence covers valid photo-only A to A;
valid ordered Plant A/photo A; explicit source Plant A to destination B; photo
A to B even with authority for both; target B plus explicit B and photo A;
unknown photo; plant-only, two-photo, reversed, duplicate, or malformed refs at
the applicable strict boundary; wrong Farm/scope; message/classification
mismatch; and a valid idempotent duplicate. HTTP evidence covers wrong-Plant,
malformed, and noncanonical cursors as `422 VALIDATION_FAILED`, plus
authorization denial before cursor decode/no enumeration. No live provider,
credential, egress, network, or Gemini evidence is required or claimed.

## Expected touched files

- `backend/app/vision_observation/`
- `backend/app/agent_runtime/providers.py`
- `backend/app/plant_state/`
- `backend/app/api/plant_state.py`, API composition, and `backend/app/main.py`
- `backend/migrations/versions/ft009_plant_state.py`
- `tests/backend/vision_observation/`, `tests/backend/plant_state/`, focused
  API/migration regressions, and `tests/fixtures/vision/`.

The current ATTEMPT 04 recovery overrides both that original feature-build list
and the historical ATTEMPT 03 scope with the narrower write scope stated above;
it does not reopen completed W1 or original W2 construction scope.

## Constitution Check

- Spec Before Code: exact vision, state, HTTP, lifecycle, authorization, and
  testing specs govern both cards.
- KISS/low maintenance: two bounded modules, one table, one internal invocation
  command, no worker/outbox/event-sourcing/provider-history layer.
- Authority/safety: photo bytes cross only the strict provider-neutral boundary;
  model output stays pending; PostgreSQL owns trust; human promotion and Safety
  approval remain separate.
- Blockers: none. Provider/model/base URL, credentials, egress, network, and
  live smoke are not current code-phase inputs or closure gates.
- Recovery readiness: planning does not mutate the current `failed` lifecycle.
  Scheduler recovery precedes the mandatory post-transition doctor; execution
  remains blocked until that doctor passes and normal promotion occurs.

## Source Artifacts

- `.memory-bank/features/FT-009-vision-observation-plant-state-trust.md`
- `.memory-bank/epics/EP-003-agent-runtime-context-hygiene.md`
- `.memory-bank/requirements.md`: REQ-003, REQ-009, REQ-010, REQ-011,
  REQ-012, and REQ-013.
- FT-009 BHV-001 through BHV-003.

## Normative Inputs

- `.memory-bank/contracts/vision-observation-runtime.md`
- `.memory-bank/contracts/plant-state-runtime.md`
- `.memory-bank/domains/plant-state-observations.md`
- `.memory-bank/contracts/plant-state-http.md`
- `.memory-bank/contracts/agent-runtime-adapter.md`
- `.memory-bank/contracts/agent-model-provider-profiles.md`
- `.memory-bank/contracts/message-envelope.md`
- `.memory-bank/domains/photo-artifacts.md`
- `.memory-bank/contracts/access/actor-context.md`
- `.memory-bank/states/plant-state-trust.md`
- `.memory-bank/states/safety-action-lifecycle.md`
- `.memory-bank/states/plants/plant-and-access-lifecycle.md`
- `.memory-bank/testing/vision-observation-plant-state.md`

## Constraints and invariants

- Real accepted photo bytes, not a URL/path/canned description, reach one
  explicit outbound spy; production remains unbound and has no fake/default/
  canned/fallback path.
- Model output, candidate, pending envelope, Timeline, Bus, and UI never confirm
  Plant state or mutate it without the classified persistence boundary.
- Missing/unavailable photo data ends at the existing fail-closed
  `context_denied/input_contract_violation` branch with no provider call,
  envelope, candidate, or FT-009 follow-up task; FT-016/FT-012 own later UX/task
  composition.
- Low-confidence/uncertain Vision findings persist exactly as `unknown`;
  pending envelope claim type does not select trust state.
- Conflict is explicit and cannot be collapsed by recency/confidence.
- Confirm/reject uses current backend authorization and optimistic versioning;
  confirmation never grants Safety/task/action authority.
- Archived Plants retain records but deny invocation, persistence, review, and
  state advance; restore never replays work.

## Verification Targets

- `.venv/bin/python -m pytest tests/backend/vision_observation tests/backend/plant_state tests/backend/api/test_ft009_plant_state_routes.py -m "not real_model" -q`
- `.venv/bin/python -m pytest tests -m "not real_model" -q`
- `node scripts/mb-lint.mjs`
- `git diff --check`

## UAT

Upload the committed tomato fixture through production photo intake, invoke the
canonical Vision service with an explicit test-only outbound spy, and verify
the exact request/media identity plus an audited strict `speak` result with one
pending MessageEnvelope and one matching VisionStateCandidateV1. Separately
exercise `clarify`, `silent`, timeout, provider failure, invalid output,
post-I/O denial, audit failure, and unbound production.
Persist only a matching
classified safe-information candidate; verify low-confidence remains unknown,
opposing evidence becomes conflict, Consultant cannot review, and a current
Boss/Engineer can resolve then confirm without any Safety/task effect. Consume
the protected list API; browser rendering follows in FT-016.

Real image/response verification is deferred to the shared future selected-
endpoint milestone and is not claimed or required by this plan.
