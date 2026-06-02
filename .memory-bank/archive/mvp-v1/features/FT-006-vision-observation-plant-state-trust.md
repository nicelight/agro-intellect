---
description: FT-006 - Vision observation and plant state trust.
status: draft
lifecycle: planned
parent_epic: EP-002
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-006-vision-observation-plant-state-trust.md
---
# FT-006 Vision Observation and Plant State Trust

## Parent Epic

- [EP-002 Agent Advisory and Safety Loop](../epics/EP-002-agent-advisory-safety-loop.md): agent advisory, communication boundaries, and safety loop.

## Purpose

Support mock or real visual observation for the first demo while keeping a hard boundary between visual observations, diagnoses, plant state confidence/status values, and confirmed facts.

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): FR-011, FR-012, plant-state edge cases, acceptance criteria, and verification strategy.
- [project_dossier.md](../../project_dossier.md): sections 8.2, 8.3, 16, 17, 22, 23, and 28 for vision/plant-state context.
- [.memory-bank/requirements.md](../requirements.md): REQ-008.
- [.memory-bank/constitution.md](../constitution.md): bounded agent autonomy, dataset evidence discipline, and no speculation.
- [.memory-bank/spec-index.md](../spec-index.md): route map for vision observation, plant state lifecycle, runtime data model, and first-demo verification areas.
- [.memory-bank/testing/index.md](../testing/index.md): vision-to-plant-state and hypothesis-not-confirmed verification.

## Use Cases

- A mock or real Vision Observation Agent evaluates photo quality and visible symptoms.
- Vision Observation requests a specific missing photo type when visual context is insufficient.
- Vision Observation publishes observation confidence without final diagnosis.
- Plant State compares current observations with history.
- Plant State records probable, unknown, or conflict states from agent-labeled evidence.
- Human review or follow-up evidence can later promote state to confirmed.

## Acceptance Criteria

- The first demo supports mock or real Vision Observation Agent.
- Vision Observation describes photo quality, visible symptoms, missing visual context, and observation confidence.
- Vision Observation distinguishes observation from diagnosis.
- Vision Observation does not recommend pH/EC correction, dosing, or physical plant-system actions.
- Plant State tracks plant state over time.
- Important fields carry confidence/status metadata such as `confirmed_updated`, `confirmed_unchanged`, `assumed_unchanged`, `probable`, `unknown`, or `conflict`.
- Agent-labeled conclusions may update probable, unknown, or conflict states.
- Agent-labeled conclusions do not promote state to confirmed without human review or follow-up evidence.

## Edge Cases / Failure Modes

- Low-quality or incomplete photo: request a specific photo type, such as `lower_leaf_closeup` under neutral light.
- Vision output includes final diagnosis or physical-action advice: block or reroute to the appropriate specialist and Safety Gate.
- Plant state evidence conflicts: mark `conflict` instead of confirmed.
- Agent diagnosis without evidence: keep as hypothesis and `can_train_on=false`.
- Follow-up contradicts previous state: preserve traceability and do not silently overwrite confirmed state.
- Real vision adapter is unavailable: mock vision may be used if output contracts match future real vision output.

## Test Strategy Pointers

- `workflow:vision-to-plant-state` for observation-to-probable/unknown/conflict state updates.
- `policy:agent-hypothesis-not-confirmed` for confirmed-state promotion requiring human review or follow-up evidence.
- `schema:agent-report` for source refs, confidence, model/prompt version, and output refs when applicable.
- `policy:vision-no-physical-action-advice` for preventing pH/EC correction, dosing, and physical-action recommendations from Vision Observation.
- `workflow:missing-photo-request` for low-quality or incomplete photo cases.

## Constraints / Invariants

- Vision Observation observes; it does not diagnose or recommend physical actions.
- Plant State preserves uncertainty and conflicts.
- Confirmed state requires human review or follow-up evidence.
- Agent-labeled conclusions are hypotheses and default to non-trainable.
- Mock vision is allowed only if it preserves future output contracts.

## SDD Design Gate

Feature-local `/spec-improve FT-006` is complete. Normative design inputs and feature-local handoff:

- [.memory-bank/tech-specs/FT-006-vision-observation-plant-state-trust.md](../tech-specs/FT-006-vision-observation-plant-state-trust.md): feature-local tech spec for Vision Observation reports, observation-vs-diagnosis boundary, source refs, confidence/status mapping, plant-state promotion gates, dataset handoff, API/service surface, and verification targets.
- [.memory-bank/states/plant-state.md](../states/plant-state.md): confidence/status lifecycle and promotion rules.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): observation/hypothesis output envelope.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): plant state refs and future sensor-window refs.
- [.memory-bank/states/dataset-governance.md](../states/dataset-governance.md): hypotheses are not trainable labels by default.
- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): mock/real vision output must pass the same adapter boundary.

No FT-006 design blocker remains for `/prd-to-tasks FT-006`.
