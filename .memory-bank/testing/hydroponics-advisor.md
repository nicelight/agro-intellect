---
description: Verification contract for Hydroponics Advisor freshness policy, provider-neutral execution, and pending Safety/task handoff.
status: active
type: testing_spec
last_updated: 2026-07-29
source_of_truth:
  - .memory-bank/contracts/hydroponics-advisor-runtime.md
  - .memory-bank/domains/plant-operations.md
  - .memory-bank/domains/plant-state-observations.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/states/safety-action-lifecycle.md
---
# Hydroponics Advisor Verification

## Deterministic matrix

- Exact command/request/result shapes, unknown-field rejection, canonical
  `hydroponics_advisor` definition, record order, request refs derived read-only
  from records, result-citation subset/order against those refs, maximum four
  input/envelope refs, and compatibility with the shared runtime audit bound.
- Current authorized active-Plant input from PostgreSQL only: Plant, latest
  latest independent pH/EC rows with deduplication, plus remaining bounded
  context slots filled from the latest completed check-in and latest non-
  rejected Plant-state record.
- ActorContext, session/account/membership/grant state, UI Feed, raw chat,
  Timeline replay, provider history, hidden reasoning, credentials, and local
  paths remain absent from external egress.
- pH and EC are independently fresh only inside the existing closed 24-hour
  analysis interval; exact-boundary values are fresh, older/missing and
  future-dated values are stale/missing as specified.
- Any non-empty missing/stale set accepts only the exact structured
  measurement request, exact project-owned wording, exact deterministic refs,
  `task_request`, pending/non-consumable envelope, and zero direct task/Safety/
  Bus/UI/state effect. Advice, clarification, or silence is invalid there.
- Fresh pH and EC are required before recommendation/hypothesis/clarification;
  output refs include both authoritative measurement refs and model text stays
  opaque pending candidate data.
- Model-selected labels or candidate wording cannot publish, classify itself,
  create an ordinary or action task, approve physical action, confirm Plant
  state, or authorize actuation.
- Current post-model session/membership/grant/Plant guard, archive/revoke race,
  audit failure, no replay after restore, and existing shared outcome/error
  matrices remain unchanged.
- Provider-neutral fake/spy execution, unbound fail-closed production, no
  default/fallback/fake production result, and redacted diagnostics/evidence.

## Current code-phase executor evidence

Seed one active authorized Plant with a deterministic missing/stale pH/EC mix
and at least one actual persisted Plant/check-in/measurement or classified
Plant-state source. Invoke the canonical service with an explicitly injected
fake/spy executor and require:

1. exactly one spy call over the production strict request;
2. a schema-valid model `measurement_request` matching exactly the
   project-computed missing/stale set and policy refs;
3. audited `outcome_kind=envelope_ready`, `final_decision=speak`, and one
   pending `candidate_claim_type=task_request` MessageEnvelope with the exact
   project-owned wording;
4. no classification, task record, approval, Bus/UI publication, Plant-state
   mutation, or action effect.

Separate fake/spy cases cover timeout, executor error, invalid output,
post-I/O guard denial, audit failure, and unbound production. No case may fall
back, gain direct downstream authority, or claim real-provider integration.
Real response/error/timeout evidence belongs to the future provider milestone.

## Commands

- `.venv/bin/python -m pytest tests/backend/hydroponics_advisor -m "not real_model" -q`
- `.venv/bin/python -m pytest tests/backend/plant_operations tests/backend/agent_runtime tests/backend/plant_state tests/backend/hydroponics_advisor -m "not real_model" -q`
- `.venv/bin/python -m pytest tests -m "not real_model" -q`
- `node scripts/mb-lint.mjs`
- `git diff --check`

Public invocation/orchestration and browser rendering remain FT-016. The
project-owned classifier, Safety Gate, and durable measurement-task effect
remain FT-011/FT-012 and are not pre-claimed by this verification contract.
