---
description: Verification contract for model-backed classification and physical-action Safety routing through pending approval.
status: active
type: testing_spec
last_updated: 2026-07-17
source_of_truth:
  - .memory-bank/features/FT-011-safety-gate-physical-action-routing.md
  - .memory-bank/contracts/safety-gate-runtime.md
  - .memory-bank/domains/safety-action-routing.md
  - .memory-bank/states/safety-action-lifecycle.md
  - .memory-bank/domains/plant-operations.md
  - .memory-bank/contracts/ui-feed.md
---
# Safety Gate Verification

## Scope

Defines deterministic, PostgreSQL integration, compatibility, concurrency, and
credentialed product-agent evidence for FT-011. The terminal owned state is
`pending_human_approval`; FT-012 owns human decisions and every later task or
follow-up assertion.

## Classifier matrix

- Exact `SafetyGateClassificationCommandV1`, provider request, and model
  candidate shapes; unknown-field/type/enum/matrix rejection.
- Canonical `safety_gate` identity and one explicit DeepSeek/Gemini binding;
  no default, fallback, fake/canned runtime result, or operational
  `chatgpt_oauth` without its approved adapter.
- Provider egress contains only the five pending-message candidate fields and
  excludes Farm/Plant, ActorContext, session/account/membership/grant,
  authorization snapshot, source/evidence refs, UI/Bus/Timeline, credentials,
  local paths, provider history, and hidden reasoning.
- All four shared classes and exact safe-task kinds map to the canonical
  `SafetyClassificationResultV1` rows; only backend validation constructs the
  authoritative result.
- All ten physical-action kinds validate. Manual nutrient addition/top-up maps
  only to `ec_adjustment`; device dosing maps to unsupported
  `dosing_command`.
- Model-selected upstream claim labels and prompt/markup/command-looking text
  cannot select schema, authority, or a downstream route.
- Not configured, provider failure, invalid output, or explicit uncertainty
  persists only fail-closed `blocked_uncertain` when the current write guard
  succeeds.
- PostgreSQL rows enforce exact matrix constraints, restrictive UUID FKs, raw
  candidate absence, safe model refs, and first-write-wins immutability.
- An identical retry avoids another provider call and is idempotent. A
  concurrent different input/result fingerprint leaves the first row unchanged
  and returns blocked/no-effect.

## Safety decision matrix

- Unsupported device, pruning, transplanting, root-trimming, and unknown kinds
  create immutable `safety_blocked/unsupported_action` decisions without
  evaluating pH/EC.
- Supported `ph_adjustment|ec_adjustment|solution_change` requires current
  Boss authority or current Engineer grant with
  `plant_approve_actions=true`; Consultant and missing/revoked permission
  produce `safety_blocked/approval_authority_missing`.
- For every supported/authorized kind, latest pH and EC come from PostgreSQL
  and are independently evaluated in the closed `approval_input=2h` interval.
  Missing, stale, and future-dated cases produce `needs_fresh_evidence`; the
  separate FT-010 24-hour analysis window is never reused.
- Both fresh values produce only `pending_human_approval`, with exact evidence
  refs and `expires_at=min(ph+2h,ec+2h)`. Exact-boundary evidence is covered.
- Decision and exact `safety_status` UI row commit atomically. Duplicate versus
  conflict, strict payload union, role visibility, project-owned summary,
  literal JSON data, both agent flags false, and no candidate text are asserted.
- The route creates no approval, `action_task`, follow-up, Bus event, Timeline
  event, executable command, target value, quantity, dosage, or device call.

## Current-state and compatibility matrix

- Pre-provider and post-provider session/account/membership/grant/Plant guards;
  archive/revoke races write no unauthorized classification, decision, or UI
  effect.
- Archive preserves committed FT-011 rows unchanged and non-operative. Restore
  performs no replay/promotion; a new Agent Runtime request/message id is
  required.
- Existing FT-004 freshness, FT-007 runtime/provider/roster, FT-008 Bus/UI/feed,
  and FT-010 pending-advisor contracts remain valid after the additive Safety
  package/migrations/unions.
- Migration-head assertions advance to the new product head without weakening
  earlier table constraints.
- Error/log/evidence inspection contains no credentials, auth material, raw
  provider payload, prompt, candidate text, hidden reasoning, or absolute path.

## Behavior traceability

- `FT-011-BHV-001`: supported manual action plus current approver and fresh pH/EC
  -> immutable pending proposal with safe summary and expiry only.
- `FT-011-BHV-002`: recognized device action -> unsupported Safety block with no
  evidence evaluation or downstream execution.
- `FT-011-BHV-003`: supported action with missing/stale approval input ->
  `needs_fresh_evidence`, never pending approval.

## Credentialed product-agent UAT

Seed one authorized active Plant and one validated pending envelope with an
unambiguous manual solution-related action. Invoke the canonical production
`safety_gate` definition with exactly one explicit DeepSeek or Gemini binding
and require:

1. exactly one real provider call over `SafetyGateProviderRequestV1`;
2. the expected strict physical-action candidate and action kind;
3. one matching durably persisted project-owned classification;
4. no direct Safety decision unless the owning service is explicitly invoked,
   and never an approval, task, Bus publication, Timeline event, or action.

Skip, xfail, injected executor, canned output, fallback, missing provider call,
unconfigured/provider-failed/output-invalid/guard-denied/persistence-failed
result, or direct action effect fails an explicitly requested smoke. Evidence
records only safe profile/model/result/record refs.

## Commands

- Classifier slice:
  `.venv/bin/python -m pytest tests/backend/safety_gate/test_classifier.py tests/backend/safety_gate/test_classification_persistence.py -m "not real_model" -q`
- Safety decision/UI slice:
  `.venv/bin/python -m pytest tests/backend/safety_gate/test_action_routing.py tests/backend/safety_gate/test_migration_models.py tests/backend/agent_chat/test_ft008_guarded_publication.py tests/backend/api/test_ft008_feed_routes.py -m "not real_model" -q`
- Aggregate deterministic regression:
  `.venv/bin/python -m pytest tests/backend/plant_operations tests/backend/agent_runtime tests/backend/agent_chat tests/backend/hydroponics_advisor tests/backend/safety_gate -m "not real_model" -q`
- Credentialed classifier smoke:
  `AGENT_REAL_SAFETY_GATE_SMOKE=1 .venv/bin/python -m pytest tests/backend/safety_gate/test_real_safety_gate_smoke.py -m real_model -q`
- Full deterministic suite: `.venv/bin/python -m pytest tests -m "not real_model" -q`
- Memory Bank lint: `node scripts/mb-lint.mjs`
- Diff check: `git diff --check`
