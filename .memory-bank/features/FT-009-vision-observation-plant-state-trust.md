---
description: FT-009 Vision Observation And Plant State Trust.
status: draft
type: feature
feature_id: FT-009
epic: EP-003
lifecycle: planned
last_updated: 2026-06-26
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

- Low-confidence vision output remains probable/unknown and does not become confirmed.
- Contradictory evidence is represented as conflict, not silently resolved.
- Missing photo data prevents vision processing and produces safe clarification/follow-up behavior.
- Unauthorized photo context cannot enter vision context.

## Verification Targets

- Integration: real photo input reaches real vision/model-backed path.
- Unit: trust status and promotion gate rules after spec defines states.
- E2E: uploaded `tomato_001` photo produces visible observation/trust status without unsafe action wording.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): real model/vision integration and Plant state authority boundaries.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): Plant state authority and evidence refs.
- [.memory-bank/domains/photo-artifacts.md](../domains/photo-artifacts.md): authorized local photo artifact input refs.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): observation/hypothesis output boundary.
- [.memory-bank/states/plant-state-trust.md](../states/plant-state-trust.md): trust status and promotion guardrails.

## SDD Design Gate

Global `/spec-design` is complete for shared backbone/spec routing. Then run `/prd-to-tasks FT-009`; it must define exact vision input refs, observation schema, trust statuses, promotion gates, contradiction handling, real vision/provider configuration, and tests during its feature-level SDD design phase before writing tasks. Use standalone `/spec-improve FT-009` only for repair or advanced refresh without task generation.
