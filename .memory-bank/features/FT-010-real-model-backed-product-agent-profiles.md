---
description: Feature FT-010 for real model-backed product-agent profiles, including vision over actual uploaded photos.
status: draft
lifecycle: planned
spec_design_status: needs_spec_improve
epic: EP-003
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
---
# FT-010 Real Model-Backed Product Agent Profiles

## Use Cases

- Vision Observation Agent processes actual uploaded photo data through a real vision-capable model or real vision model integration.
- Plant State Agent, Hydroponics Advisor, Task & Follow-up Agent, Safety Gate Agent,
  Dataset Governance Agent, and Companion operate as real model-backed or deterministic
  policy-backed profiles where appropriate.
- First demo proves agent behavior over actual scoped Plant data, not fake/stubbed outputs.

## Acceptance Criteria

- MVP runtime/demo product-agent behavior is not satisfied by fake, mock, hardcoded, or stubbed outputs.
- Test-only mocks are allowed only in automated tests, not as MVP runtime/demo path.
- Each product agent has a single-competence AgentProfile with explicit competence boundary and allowed output types.
- Vision Observation observes photo quality and visual findings but does not diagnose or recommend physical actions.
- Real model-backed outputs still pass harness validation, permission policy, runtime decisions, and publication contracts.

## Edge Cases & Failure Modes

- Missing model/provider configuration fails clearly without pretending a fake agent succeeded.
- Vision model failure produces structured error/clarify/escalate path.
- Raw provider output does not become domain fact until adapted and validated.
- Model/provider memory cannot bypass project-owned context and memory rules.

## Test Strategy Pointers

- `test:agents.real-model-runtime-and-vision`
- `test:harness.loop-permission-observation-trace`
- `test:agent-output.bus-message-ui-isolation`

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): real model-backed MVP requirement.
- [.memory-bank/invariants.md](../invariants.md): NEVER fake/stub runtime/demo agent outputs.
- [.memory-bank/glossary.md](../glossary.md): product-agent vocabulary.

## SDD Design Gate

Global `/spec-design` is complete. Before `/prd-to-tasks FT-010`, run
`/spec-improve FT-010` using the completed backbone docs: [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md), [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md), [.memory-bank/states/core-lifecycles.md](../states/core-lifecycles.md), [.memory-bank/contracts/index.md](../contracts/index.md), and [.memory-bank/testing/index.md](../testing/index.md). `/spec-improve` must decide minimal provider/model adapters,
test-only mock boundaries, profile list, runtime failure behavior, and first-demo
evidence requirements.
