---
description: Verification contract for photo-byte integrity, provider-neutral Vision, and Plant state trust behavior.
status: active
type: testing_spec
last_updated: 2026-07-20
source_of_truth:
  - .memory-bank/contracts/vision-observation-runtime.md
  - .memory-bank/contracts/plant-state-runtime.md
  - .memory-bank/domains/plant-state-observations.md
  - .memory-bank/domains/photo-artifacts.md
  - .memory-bank/contracts/plant-state-http.md
  - .memory-bank/testing/agent-runtime.md
---
# Vision Observation And Plant State Verification

## Deterministic matrix

- Exact Vision request/record/media/result shapes, order, unknown-field
  rejection, source-ref subset, and finding-to-envelope mapping.
- Accepted catalog lookup, path containment, content type, fresh size/hash
  equality, real byte attachment, and zero provider calls for invalid input.
- Missing/unavailable photo returns exact
  `context_denied/input_contract_violation` with no provider, runtime audit,
  clarification envelope, state candidate, or follow-up task.
- Current ActorContext plus post-model session/membership/grant/Plant guard;
  archive/revoke races return blocked audit-only outcomes with no replay.
- Provider-neutral Vision composition, exact outbound-spy media identity,
  unbound production, no fake/canned/default/fallback production path, and
  redacted diagnostics.
- Pending MessageEnvelope and candidate have no direct DB/Bus/UI/task/Safety
  effect.
- PostgreSQL migration/check constraints, restrictive FKs, unique message id,
  classified-only atomic insert requiring the canonical
  `classification=safe_information` plus matching `message_id`, idempotency,
  and content-conflict rollback.
- Real-PostgreSQL Vision persistence proves valid photo-only Plant A to A and
  valid ordered Plant A/photo A provenance, and rejects with zero rows:
  explicit source Plant A rebound to destination B, photo A rebound to B even
  when the actor is authorized for both, explicit target B plus photo A,
  unknown photo, wrong Farm/scope, and message/classification mismatch.
- Strict source-ref boundary tests reject plant-only, two-photo, reversed-order,
  duplicated, and malformed refs. Provenance mismatch is
  `PLANT_STATE_CANDIDATE_INVALID`; current authorization mismatch is
  `AUTH_PLANT_FORBIDDEN`; neither exposes a raw `IntegrityError`.
- An identical valid classified duplicate remains idempotent after catalog
  validation.
- A retained-session real-PostgreSQL regression preloads a Plant A photo in
  Session A and commits, changes the authoritative catalog ownership to Plant B
  in Session B and commits, then reuses Session A for Plant A persistence. The
  locked catalog read MUST refresh or project current authoritative metadata;
  persistence returns `PLANT_STATE_CANDIDATE_INVALID`, writes zero Plant-state
  rows, and exposes no raw database error.
- Trust mapping at `0`, `0.499`, `0.50`, and `1`; no agent-created confirmed
  record. Low-confidence/uncertain Vision findings are exactly `unknown`, while
  pending envelope claim type remains non-authoritative transport metadata.
- Severity/polarity compatibility and exact monotonic/mixed trend validation.
- Plant State request uses only latest authorized state records and excludes
  UI Feed, raw chat, timeline replay, confirmation actors, provider history,
  and hidden reasoning.
- Trend/conflict/unknown structural validation; contradictory evidence stays
  conflicting and never resolves by recency or confidence alone.
- Boss/Engineer human review, Consultant/unauthorized/archive denial, conflict
  and optimistic-version checks, retained-history reads, and no Safety/task
  authority.
- Exact list/review HTTP, no-store, stable cursor, wrong-Plant plus every
  malformed/noncanonical cursor returning `422 VALIDATION_FAILED`, authorization
  denial before cursor decoding/no enumeration, safe errors, and internal-field
  exclusion.

## Current code-phase executor evidence

- Upload the committed tomato fixture through production photo intake; the
  outbound spy must receive exactly the verified bytes/ref/content type/hash.
- A strict fake result exercises `speak`, `clarify`, and `silent` mappings;
  timeout, executor failure, invalid result, post-I/O denial, and audit failure
  remain fail closed with no downstream effect.
- Seed persisted classified trust records and use a strict fake/spy Plant State
  result to prove pending assessment and structural conflict/trend validation.
- Evidence must label every executor result synthetic/test-only and must not
  claim a real image, response, provider, model, network call, or credential.

Real image/response verification is deferred to the selected-endpoint
milestone in `.memory-bank/runbooks/agent-runtime-providers.md` and is
`not_applicable_for_current_code_phase`.

## Commands

- `.venv/bin/python -m pytest tests/backend/vision_observation -m "not real_model" -q`
- `.venv/bin/python -m pytest tests/backend/plant_state tests/backend/api/test_ft009_plant_state_routes.py -m "not real_model" -q`
- `.venv/bin/python -m pytest tests -m "not real_model" -q`
- `node scripts/mb-lint.mjs`
- `git diff --check`

Browser rendering of the list response belongs to FT-016. Safety
classification policy and physical-action routes belong to FT-011/FT-012.
