---
description: Feature FT-010 for real model-backed product-agent profiles, including vision over actual uploaded photos.
status: active
owner: product
lifecycle: planned
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-010-real-model-backed-product-agent-profiles.md
epic: EP-003
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/tech-specs/FT-010-real-model-backed-product-agent-profiles.md
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

Global `/spec-design` and feature-level `/spec-improve FT-010` are complete. Use
[.memory-bank/tech-specs/FT-010-real-model-backed-product-agent-profiles.md](../tech-specs/FT-010-real-model-backed-product-agent-profiles.md)
as the feature-local design hub before `/prd-to-tasks FT-010`.
