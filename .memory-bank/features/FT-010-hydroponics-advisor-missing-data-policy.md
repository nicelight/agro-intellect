---
description: FT-010 Hydroponics Advisor Missing Data Policy.
status: draft
type: feature
feature_id: FT-010
epic: EP-003
lifecycle: planned
last_updated: 2026-07-20
spec_design_status: complete
spec_design_links:
  - .memory-bank/contracts/hydroponics-advisor-runtime.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/domains/plant-operations.md
  - .memory-bank/domains/plant-state-observations.md
  - .memory-bank/states/plant-state-trust.md
  - .memory-bank/states/safety-action-lifecycle.md
  - .memory-bank/testing/hydroponics-advisor.md
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
---
# FT-010 Hydroponics Advisor Missing Data Policy

## Use Cases

- Hydroponics Advisor reviews authorized Plant observations, photo-derived observations, and manual pH/EC.
- Advisor asks for missing or stale critical measurements.
- Advisor provides cautious recommendations only within evidence boundaries.
- Advisor output that implies a physical action is routed to Safety Gate.

## Acceptance Criteria

- Advisor cannot invent pH/EC or other missing critical evidence.
- Missing/stale data produces clarification, measurement task request, or safe non-action advice.
- Physical-action wording cannot bypass Safety Gate.
- Output remains permission-aware and concise.

## Edge Cases & Failure Modes

- Fresh data alone is not enough for physical action.
- Stale pH/EC blocks action approval path and should request measurement/follow-up as appropriate.
- Unauthorized Plant context cannot enter Advisor input.
- Advisor cannot create direct action_task without Safety Gate and approval path.

## Verification Targets

- Unit: stale/missing data policy after spec defines freshness windows.
- Integration: Advisor to Safety Gate handoff.
- E2E: missing pH/EC produces measurement request, not corrective dosing instruction.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Hydroponics Advisor, Safety Gate, and task-loop boundaries.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): recommendation, clarification, and safety route fields.
- [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md): Advisor input context rules.
- [.memory-bank/states/plant-state-trust.md](../states/plant-state-trust.md): stale/missing evidence and trust promotion guardrails.
- [.memory-bank/states/safety-action-lifecycle.md](../states/safety-action-lifecycle.md): physical-action routing and approval boundary.

## Feature-Local Design Pressure

- Exact advisor inputs, freshness policy, output contract, missing-data task
  handoff, Safety Gate handoff, and tests.

## Behavior specs

- `.memory-bank/behavior-specs/FT-010-BHV-001-missing-stale-measurements.behavior.json`
- `.memory-bank/behavior-specs/FT-010-BHV-002-fresh-evidence-pending-safety.behavior.json`
- `.memory-bank/behavior-specs/FT-010-BHV-003-current-authority-race.behavior.json`

## SDD Design Gate

- Feature-local status: complete. The canonical advisor runtime fixes the
  authorized input, independent 24-hour pH/EC freshness policy, strict result
  matrix, project-owned measurement-request wording, provider-neutral
  fake/spy verification, and pending MessageEnvelope handoff.
- No new storage or public HTTP contract is required: FT-010 reads current
  PostgreSQL authority and returns the existing transient envelope outcome.
- Safety classification, ordinary task persistence, action approval, and
  browser composition remain owned by FT-011, FT-012, and FT-016 respectively.
- No provider, credential, egress, network, or live smoke is a current
  code-phase closure condition; real response verification is deferred to the
  selected-endpoint milestone.

## Current W1 Boundary Evidence

- `TASK-036-T3-FT-010-W1` is scheduler-recorded `done` using only current
  ATTEMPT 02 evidence: bounded implementation `PASS`, independent functional
  `VERDICT: PASS`, separate `SEMANTIC_VERDICT: semantic-pass`, and immutable
  scheduler closure. ATTEMPT 01 remains history and is not combined with the
  current attempt to manufacture closure.
- Current evidence covers exact `CANONICAL_ROSTER_V1` Advisor composition,
  strict provider-neutral schemas, authorized PostgreSQL evidence assembly,
  independent 24-hour pH/EC freshness, deterministic missing-data wording,
  pending-only handoff, post-I/O authorization, redaction, fail-closed provider
  errors, and zero Safety/task/Bus/UI/state/action authority.
- The exact `HUMAN_CHECKPOINT: done` marker was not selected and remains an
  accepted advisory T3 confidence gap. No provider, model, base URL,
  credential, egress, network call, or live smoke was required, checked, or
  claimed for this code-phase boundary.
- This sync records evidence only and leaves `lifecycle: planned` unchanged
  pending an explicit owner feature-lifecycle decision. The dependent
  `TASK-037-T3-FT-011-W1` remains scheduler-owned `planned`; `/mb-sync` neither
  promotes nor selects it.

Evidence:
[implementation](../../.tasks/TASK-036-T3-FT-010-W1/TASK-036-T3-FT-010-W1-S-IMPL-final-report-code-02.md),
[functional verification](../../.tasks/TASK-036-T3-FT-010-W1/TASK-036-T3-FT-010-W1-S-VERIFY-final-report-docs-02.md),
[semantic verification](../../.tasks/TASK-036-T3-FT-010-W1/TASK-036-T3-FT-010-W1-S-RED-VERIFY-final-report-docs-02.md),
and [scheduler closure](../../.tasks/TASK-036-T3-FT-010-W1/TASK-036-T3-FT-010-W1-S-CLOSURE-final-report-docs-02.md).
