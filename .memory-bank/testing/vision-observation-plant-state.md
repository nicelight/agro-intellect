---
description: Verification contract for real vision input and Plant state trust behavior.
status: active
type: testing_spec
last_updated: 2026-07-16
source_of_truth:
  - .memory-bank/contracts/vision-observation-runtime.md
  - .memory-bank/contracts/plant-state-runtime.md
  - .memory-bank/domains/plant-state-observations.md
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
- Gemini-only v1 vision composition, explicit model id/egress/credential,
  no DeepSeek/OAuth/fake/cross-provider fallback, and redacted diagnostics.
- Pending MessageEnvelope and candidate have no direct DB/Bus/UI/task/Safety
  effect.
- PostgreSQL migration/check constraints, restrictive FKs, unique message id,
  classified-only atomic insert requiring the canonical
  `classification=safe_information` plus matching `message_id`, idempotency,
  and content-conflict rollback.
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
- Exact list/review HTTP, no-store, stable cursor, wrong-Plant rejection, safe
  errors, and internal-field exclusion.

## Credentialed product-agent UAT

Two non-skipped product-agent smokes remain required before FT-009 may claim
REQ-011/REQ-012 runtime acceptance:

1. `vision_observation`: upload the committed tomato fixture through the
   production photo-intake path, invoke the canonical production definition
   with its explicit Gemini binding, prove exactly one real image-capable call,
   and require `runtime_decision=speak` with an audited valid pending envelope
   and `VisionStateCandidateV1`. The photo ref and verified bytes must match the
   accepted catalog artifact. `clarify` remains a valid envelope-only runtime
   result and `silent` remains valid without either artifact, but neither
   satisfies the committed tomato fixture behavior.
2. `plant_state`: seed classified persisted Plant records, invoke the canonical
   production definition through its explicit DeepSeek or Gemini binding, and
   require an audited schema-valid pending assessment envelope/candidate for
   the seeded conflict/trend fixture; model silence does not satisfy it.

Skip, xfail, test executor, canned output, constructor-only evidence, missing
provider call, fallback, unconfigured/blocked/failed/audit-failed result, or
unvalidated raw response fails an explicitly requested smoke. Credentials,
photo bytes, prompts, raw response, and hidden reasoning stay out of evidence.

## Commands

- `.venv/bin/python -m pytest tests/backend/vision_observation -m "not real_model" -q`
- `.venv/bin/python -m pytest tests/backend/plant_state tests/backend/api/test_ft009_plant_state_routes.py -m "not real_model" -q`
- `AGENT_REAL_VISION_SMOKE=1 .venv/bin/python -m pytest tests/backend/vision_observation/test_real_vision_smoke.py -m real_model -q`
- `AGENT_REAL_PLANT_STATE_SMOKE=1 .venv/bin/python -m pytest tests/backend/plant_state/test_real_plant_state_smoke.py -m real_model -q`
- `.venv/bin/python -m pytest tests -m "not real_model" -q`
- `node scripts/mb-lint.mjs`
- `git diff --check`

Browser rendering of the list response belongs to FT-016. Safety
classification policy and physical-action routes belong to FT-011/FT-012.
