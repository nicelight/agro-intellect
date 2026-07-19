---
description: Implementation plan for FT-010 Hydroponics Advisor missing-data policy and pending handoff.
status: active
type: implementation_plan
feature_id: FT-010
last_updated: 2026-07-20
source_of_truth:
  - .memory-bank/features/FT-010-hydroponics-advisor-missing-data-policy.md
  - .memory-bank/contracts/hydroponics-advisor-runtime.md
  - .memory-bank/testing/hydroponics-advisor.md
---
# IMPL FT-010 Hydroponics Advisor Missing Data Policy

## Goal

Run the canonical Hydroponics Advisor over current authorized PostgreSQL Plant
evidence, enforce the independent 24-hour pH/EC missing-data policy, and return
only the existing pending MessageEnvelope handoff without inventing evidence
or gaining Safety/task/action authority.

## Scope

- Add bounded `backend/app/hydroponics_advisor/` command, strict value objects,
  PostgreSQL assembler, policy validation, definition, service, and tests.
- Reuse current ActorContext/active-Plant authorization, Plant Operations
  measurement freshness, classified Plant-state records, the strict provider-
  neutral executor seam, post-I/O guard, sanitized audit, common closed outcome, and
  pending MessageEnvelope.
- Register the strict advisor request/result with production composition that
  fails closed while no endpoint is selected, plus deterministic fake/spy evidence.
- Use project-owned concise wording for missing/stale pH/EC measurement
  requests; keep fresh-evidence model text opaque and pending.

## Non-goals

- No Safety classifier, Safety Gate decision, ordinary/action task storage,
  approval, follow-up, Bus/UI publication, Plant-state mutation, frontend, or
  automated device action.
- No public prompt/model or advisor HTTP endpoint, background worker, outbox,
  new table/migration, provider history, Agno memory/RAG/tools/Team, or raw
  response persistence.
- No sensor ingestion, crop recipes, target ranges, nutrient schedules, dosage
  formulas, or agronomic rule engine.

## Ordered implementation strategy

1. Implement strict advisor command/request/result values and canonical
   `hydroponics_advisor` definition.
2. Assemble current authorized Plant/check-in/pH/EC/Plant-state rows in exact
   order and compute independent analysis freshness from PostgreSQL.
3. Enforce the missing-data matrix and project-owned measurement-request
   mapping before creating the common pending envelope.
4. Reuse the provider-neutral executor seam, post-I/O current guard, and
   sanitized Agent Runtime audit with no fallback or new storage.
5. Add deterministic policy, authorization, outbound-spy, timeout/error,
   redaction, and no-fake-production regressions.

## Dependencies

- `TASK-035-T3-FT-009-W2` supplies classified PostgreSQL Plant-state records
  and is the direct dependency.
- Through TASK-035, completed FT-004/FT-005/FT-007 work supplies canonical
  pH/EC freshness, accepted evidence, provider/runtime/envelope seams, and the
  verified Foundation dependency chain.
- FT-011 and FT-012 are downstream consumers, not prerequisites: until they
  exist, every advisor output remains pending and effect-free.

## Expected touched files

- `backend/app/hydroponics_advisor/`
- `backend/app/agent_runtime/providers.py`
- `tests/backend/hydroponics_advisor/`
- focused Agent Runtime, Plant Operations, and Plant State regressions only as
  necessary to prove compatibility.

## Constitution Check

- Spec Before Code: the exact advisor runtime and verification specs govern the
  task card.
- KISS/low maintenance: one read-only internal module, no API, table, worker,
  outbox, rule engine, or alternate context/provider framework.
- Authority/safety: PostgreSQL remains evidence authority; model output remains
  pending; FT-010 creates no task, approval, confirmed state, or action.
- Bounded autonomy: missing/stale data produces only a safe measurement request
  candidate; physical-action meaning remains blocked behind project-owned
  classification and human approval.
- Blockers: none for the completed W1 deterministic boundary; TASK-035 is
  scheduler-recorded `done`. Provider/model/base URL, credentials, egress,
  network, and live smoke are not current code-phase inputs or closure gates;
  production remains unbound and fail-closed until a later owner choice.

## Source Artifacts

- `.memory-bank/features/FT-010-hydroponics-advisor-missing-data-policy.md`
- `.memory-bank/epics/EP-003-agent-runtime-context-hygiene.md`
- `.memory-bank/requirements.md`: REQ-003, REQ-008, REQ-011, REQ-013, REQ-014.
- FT-010 BHV-001 through BHV-003.

## Normative Inputs

- `.memory-bank/contracts/hydroponics-advisor-runtime.md`
- `.memory-bank/contracts/agent-runtime-adapter.md`
- `.memory-bank/contracts/agent-model-provider-profiles.md`
- `.memory-bank/contracts/agent-roster-bootstrap.md`
- `.memory-bank/contracts/message-envelope.md`
- `.memory-bank/contracts/access/actor-context.md`
- `.memory-bank/domains/plant-operations.md`
- `.memory-bank/domains/plant-state-observations.md`
- `.memory-bank/states/plant-state-trust.md`
- `.memory-bank/states/safety-action-lifecycle.md`
- `.memory-bank/states/plants/plant-and-access-lifecycle.md`
- `.memory-bank/testing/hydroponics-advisor.md`

## Constraints and invariants

- Both pH and EC are independently required fresh for analysis under the
  existing 24-hour closed interval before recommendation/hypothesis/
  clarification is accepted.
- Any missing/stale set maps only to the exact project-owned measurement
  request; the model cannot invent values, refs, task kind, action, or wording.
- Fresh-evidence candidate text remains opaque and cannot publish or classify
  itself; source refs include both authoritative measurement inputs.
- UI Feed, raw chat, Timeline replay, provider history, auth material,
  credentials, local paths, and hidden reasoning never enter provider input or
  evidence.
- Archive/revoke/audit failure after model I/O blocks handoff and restore never
  replays it.

## Verification Targets

- `.venv/bin/python -m pytest tests/backend/hydroponics_advisor -m "not real_model" -q`
- `.venv/bin/python -m pytest tests/backend/plant_operations tests/backend/agent_runtime tests/backend/plant_state tests/backend/hydroponics_advisor -m "not real_model" -q`
- `.venv/bin/python -m pytest tests -m "not real_model" -q`
- `node scripts/mb-lint.mjs`
- `git diff --check`

## UAT

Seed one authorized active Plant with the specified missing/stale pH/EC mix,
invoke the canonical advisor through a test-only fake/spy executor, and verify
the exact outbound request plus one audited pending `task_request`
MessageEnvelope with the project-computed measurement set and exact safe
wording. Exercise timeout, provider failure, invalid output, post-I/O denial,
redaction, and unbound production. Confirm zero task, Safety, Bus/UI,
Plant-state, approval, or action effects. Browser composition and actual
measurement-task creation follow in FT-016 and FT-012.

Real request/response verification is deferred to the shared future selected-
endpoint milestone and is not claimed or required by this plan.

## Current W1 Boundary State

- `TASK-036-T3-FT-010-W1` is scheduler-recorded `done` from current ATTEMPT 02
  implementation `PASS`, independent functional `VERDICT: PASS`, separate
  `SEMANTIC_VERDICT: semantic-pass`, and closure evidence.
- The bounded ATTEMPT 02 repair composes exact canonical Advisor identity,
  competence, and schema metadata from immutable `CANONICAL_ROSTER_V1`; all
  original authorization, freshness, pending-only, redaction, provider-neutral,
  and zero-authority acceptance remains intact.
- The absent human checkpoint is preserved as an accepted advisory warning.
  No provider, model, credential, egress, network, or live result is claimed.
- FT-010 lifecycle remains `planned` pending an explicit owner decision.
  Dependent TASK-037 remains `planned`; boundary sync does not promote or
  select it.

Current evidence:
[implementation](../../../.tasks/TASK-036-T3-FT-010-W1/TASK-036-T3-FT-010-W1-S-IMPL-final-report-code-02.md),
[functional verification](../../../.tasks/TASK-036-T3-FT-010-W1/TASK-036-T3-FT-010-W1-S-VERIFY-final-report-docs-02.md),
[semantic verification](../../../.tasks/TASK-036-T3-FT-010-W1/TASK-036-T3-FT-010-W1-S-RED-VERIFY-final-report-docs-02.md),
and [scheduler closure](../../../.tasks/TASK-036-T3-FT-010-W1/TASK-036-T3-FT-010-W1-S-CLOSURE-final-report-docs-02.md).
