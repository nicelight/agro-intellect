---
description: Implementation plan for FT-009 provider-neutral vision observation and Plant state trust.
status: active
type: implementation_plan
feature_id: FT-009
last_updated: 2026-07-19
source_of_truth:
  - .memory-bank/features/FT-009-vision-observation-plant-state-trust.md
  - .memory-bank/contracts/vision-observation-runtime.md
  - .memory-bank/contracts/plant-state-runtime.md
  - .memory-bank/domains/plant-state-observations.md
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

## Expected touched files

- `backend/app/vision_observation/`
- `backend/app/agent_runtime/providers.py`
- `backend/app/plant_state/`
- `backend/app/api/plant_state.py`, API composition, and `backend/app/main.py`
- `backend/migrations/versions/ft009_plant_state.py`
- `tests/backend/vision_observation/`, `tests/backend/plant_state/`, focused
  API/migration regressions, and `tests/fixtures/vision/`.

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
