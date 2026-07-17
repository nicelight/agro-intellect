---
description: FT-009 Vision Observation And Plant State Trust.
status: draft
type: feature
feature_id: FT-009
epic: EP-003
lifecycle: planned
last_updated: 2026-07-16
spec_design_status: complete
spec_design_links:
  - .memory-bank/contracts/vision-observation-runtime.md
  - .memory-bank/contracts/plant-state-runtime.md
  - .memory-bank/domains/plant-state-observations.md
  - .memory-bank/contracts/plant-state-http.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/domains/photo-artifacts.md
  - .memory-bank/states/plant-state-trust.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
  - .memory-bank/testing/vision-observation-plant-state.md
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
---
# FT-009 Vision Observation And Plant State Trust

## Use Cases

- Vision Observation Agent processes actual uploaded photo data.
- Agent publishes visual observations with source refs and confidence/trust status.
- Plant State behavior tracks trends, uncertainty, conflicts, and unknowns without promoting hypotheses to confirmed state by itself.
- First demo shows Plant State trust statuses.

## Acceptance Criteria

- Vision Observation uses a real vision-capable model or real vision integration.
- Mock/fake adapter cannot satisfy MVP runtime/demo acceptance.
- Vision output observes and may hypothesize but does not diagnose as confirmed state or recommend physical actions directly.
- Confirmed Plant state requires human review, measurement, or follow-up evidence.

## Edge Cases & Failure Modes

- Low-confidence or uncertain vision output remains `unknown` and does not become confirmed.
- Contradictory evidence is represented as conflict, not silently resolved.
- Missing or unavailable photo data prevents vision processing and returns
  `context_denied/input_contract_violation` before provider I/O. FT-009 creates
  no clarification envelope or follow-up task for this branch; FT-016 may show
  an upload/reselect prompt, and FT-012 owns any later follow-up task.
- Unauthorized photo context cannot enter vision context.

## Verification Targets

- Integration: real photo input reaches real vision/model-backed path.
- Integration: missing/unavailable photo data returns the exact fail-closed
  denial with no provider call, runtime audit, envelope, or state candidate.
- Unit: trust status and promotion gate rules after spec defines states.
- E2E: uploaded `tomato_001` photo produces visible observation/trust status without unsafe action wording.

## Behavior specs

- `.memory-bank/behavior-specs/FT-009-BHV-001-real-photo-vision.behavior.json`
- `.memory-bank/behavior-specs/FT-009-BHV-002-classified-trust-mapping.behavior.json`
- `.memory-bank/behavior-specs/FT-009-BHV-003-conflict-human-promotion.behavior.json`

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): real model/vision integration and Plant state authority boundaries.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): Plant state authority and evidence refs.
- [.memory-bank/domains/photo-artifacts.md](../domains/photo-artifacts.md): authorized local photo artifact input refs.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): observation/hypothesis output boundary.
- [.memory-bank/states/plant-state-trust.md](../states/plant-state-trust.md): trust status and promotion guardrails.

## Feature-Local Design Pressure

- Exact vision input refs, observation schema, trust statuses, promotion gates,
  contradiction handling, real vision/provider configuration, and tests.

## Feature-Local Not Applicable

- Browser/PWA rendering is downstream FT-016 work; FT-009 owns the protected
  backend trust-record API and does not invent a frontend scaffold.
- Safety classification policy, physical-action approval, and action-task
  effects remain FT-011/FT-012 work. FT-009 consumes only a matching successful
  `safe_information` classification and grants no Safety authority.
- Automatic background orchestration is not required: model invocation remains
  an internal application command until the owning workflow/UI composes it.
