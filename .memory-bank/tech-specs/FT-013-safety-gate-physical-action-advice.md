---
description: Feature-local SDD tech spec for FT-013 Safety Gate for physical-action advice.
status: active
owner: architecture
last_updated: 2026-05-31
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/features/FT-013-safety-gate-physical-action-advice.md
  - .memory-bank/spec-index.md
---
# FT-013 Safety Gate for Physical-Action Advice Tech Spec

## Scope

This spec closes the feature-local SDD design gate for FT-013 before `/prd-to-tasks FT-013`.

FT-013 owns:

- deterministic physical-action detection for user-visible and agent-originated wording;
- action taxonomy and risk classes for the MVP;
- Safety Gate decision shape;
- 2-hour pH/EC approval freshness checks where relevant;
- fail-closed behavior when data, classifier confidence, Safety Gate availability, or approval context is missing;
- conversion of risky advice into safe block / needs-data / pending-approval handoff;
- final display check for Companion responses, UI spoiler notes, quoted details, and approval prompt wording.

FT-013 does not own human approval record lifecycle, action-task unlock semantics, task execution, Hydroponics Advisor reasoning, or automated device control.

## Normative Inputs

- [.memory-bank/states/safety-approval.md](../states/safety-approval.md): physical-action list, freshness windows, outcomes, fail-closed behavior, and approval semantics.
- [.memory-bank/tech-specs/FT-001-daily-check-in-observations-manual-measurements.md](FT-001-daily-check-in-observations-manual-measurements.md): manual pH/EC refs and computed approval freshness.
- [.memory-bank/tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md](FT-012-agent-runtime-decisions-message-envelope-output-contracts.md): `safety_block` MessageEnvelope and escalation route.
- [.memory-bank/tech-specs/FT-004-agent-chat-bus-event-stream-publication-boundary.md](FT-004-agent-chat-bus-event-stream-publication-boundary.md): `safety_block` Bus publication boundary.
- [.memory-bank/tech-specs/FT-005-ui-feed-context-hygiene.md](FT-005-ui-feed-context-hygiene.md): UI Feed display safety and spoiler-note behavior.
- [.memory-bank/states/task-follow-up.md](../states/task-follow-up.md): pending approval task handoff and no automated device execution.
- [.memory-bank/testing/index.md](../testing/index.md): safety, freshness, and user-visible action-advice gates.
- [.memory-bank/invariants.md](../invariants.md): human gate and no immediate physical-action instruction rules.

## Design Decisions

### Deterministic Gate First

- Safety Gate is a deterministic domain policy first, not a prompt-only advisor.
- The gate may use simple pattern/rule matching and structured action candidates from upstream agents.
- A model may help propose a classification only if deterministic validation still decides the final outcome.
- If classification is uncertain, unavailable, malformed, or unsupported, the outcome is fail-closed.

### MVP Action Taxonomy

Physical-action categories:

| Action category | Examples | MVP risk class |
|---|---|---|
| `ph_change` | lower/raise/change pH, add pH up/down | `physical_action` |
| `ec_change` | raise/lower/change EC, add nutrients to target EC | `physical_action` |
| `solution_change` | replace/change reservoir solution, flush solution | `physical_action` |
| `dosing` | add fertilizer/nutrient/additive by amount or schedule | `physical_action` |
| `pump_change` | turn pump on/off, change pump timing/flow | `physical_action` |
| `light_change` | change light duration, intensity, distance, schedule | `physical_action` |
| `high_risk_manual` | pruning, transplanting, root trimming | `physical_action` |
| `low_risk_check` | observe, photograph, measure pH/EC, inspect leaves, record water level | `check_only` |

Rules:

- `check_only` actions do not require human approval unless wording turns them into an intervention.
- Physical-action wording includes commands, imperatives, target-setting, dosage amounts, schedule changes, or "you should do X now" phrasing.
- Negative/blocking wording that tells the user not to perform an unsafe action is allowed only as Safety Gate block/pending-review wording.
- Automated device command wording is forbidden in MVP regardless of approval.

### Freshness Requirements

pH/EC approval freshness is evaluated from PostgreSQL/read-model measurement refs, using FT-001 semantics:

- pH-changing advice requires fresh pH within 2 hours.
- EC-changing, nutrient dosing, and solution-change advice require fresh pH and fresh EC within 2 hours unless a later feature spec narrows the needed measurements.
- Pump, light, and high-risk manual intervention advice require Safety Gate and human approval; pH/EC freshness is required only when the action rationale depends on pH/EC or solution chemistry.
- If required measurement refs are missing, stale, ambiguous, or not bound to `tomato_001`, the gate returns `needs_data` or `block`.

Fresh pH/EC is necessary where relevant, but never sufficient without Safety Gate pass and human approval.

### SafetyGateDecision Shape

Safety Gate decisions are domain records or structured outputs that can be audited and referenced by Bus/UI/task/approval flows.

Minimum decision fields:

| Field | Rule |
|---|---|
| `safety_decision_id` | Globally unique decision ID. |
| `plant_id` | Mandatory when plant-bound; MVP value `tomato_001`. |
| `created_at` | Timezone-aware decision time. |
| `source_refs` | Non-empty refs to MessageEnvelope, Bus event, UI event candidate, observation, measurement, or task/proposal. |
| `surface` | `bus`, `ui_feed`, `companion_response`, `quoted_detail_reply`, `task_handoff`, or `api`. |
| `input_text_ref` / `input_text_hash` | Ref/hash of checked wording; do not store secrets or raw reasoning. |
| `detected_action_category` | One taxonomy value or `none`. |
| `risk_class` | `none`, `check_only`, or `physical_action`. |
| `outcome` | `pass`, `block`, `pending_approval`, or `needs_data`. |
| `required_measurement_refs` | pH/EC refs required for the candidate action, when relevant. |
| `missing_requirements` | Missing/stale data, safety uncertainty, approval missing, unsupported action, or automated-command attempt. |
| `safety_check_passed` | Boolean; true only when deterministic safety checks passed. |
| `human_approval_required` | Boolean; true for physical actions. |
| `approval_ref` | Optional future FT-014 approval ref; absent in normal pending flows. |
| `safe_display_text` | Optional safe replacement/blocking text. |
| `expires_at` | Optional; for chemistry-related decisions, no later than the earliest required measurement freshness expiry. |

`SafetyGateDecision` is not human approval. FT-014 owns approval/rejection records and action unlock semantics.

### Outcome Semantics

| Outcome | Meaning |
|---|---|
| `pass` | No physical action detected, low-risk check only, or a future approved context is valid; may display/publish the checked wording. |
| `needs_data` | Required fresh measurement/context is missing or stale; request measurement/check rather than action. |
| `pending_approval` | Physical action candidate is structured enough for human decision, but cannot be presented as cleared action. |
| `block` | Unsafe, unsupported, automated, unclassifiable, or immediate action wording must not display as action advice. |

Physical-action advice without a valid human approval context must not result in cleared action wording. It may become pending-approval wording or a pending approval task/proposal handoff.

### Display Check

Every user-visible surface that may contain action wording must call Safety Gate before display:

- Companion response;
- UI spoiler note;
- quoted detail reply;
- approval prompt;
- task/action wording;
- local debug-lite card when visible to the user.

If the gate returns `block`, `needs_data`, or `pending_approval`, the unsafe original wording must not be displayed as an instruction. The system may display safe replacement text such as:

```text
Это действие требует свежих измерений, проверки безопасности и подтверждения человека. Сначала зафиксируй недостающие данные.
```

The replacement text must not include dosage, target pH/EC, pump/light commands, or other actionable parameters unless those parameters are framed as an unapproved proposal requiring review.

### Bus, UI, And Task Handoff

- `block` and `pending_approval` may publish a `safety_block` Bus event through FT-004.
- `needs_data` may route to a measurement/check task handoff owned by FT-008.
- `pending_approval` may route to a pending approval task/proposal handoff owned by FT-008/FT-014.
- `action_task` creation is forbidden until FT-014 records a valid human approval and the task feature applies its transition rules.
- Safety Gate never issues automated device commands.

## API Surface

FT-013 primarily owns internal policy functions. Minimal useful surfaces:

- `POST /api/safety/check-text`
  - local/internal or authenticated endpoint for checking user-visible candidate wording;
  - returns `SafetyGateDecision`;
  - must not create approval or action tasks by itself.
- `POST /api/safety/evaluate-action`
  - accepts structured action candidate/source refs;
  - returns `SafetyGateDecision` and optional pending proposal/task handoff refs when owning features exist.

Implementation tasks may keep these as internal services instead of public routes if product workflows can call them directly. The behavior and tests remain required.

## Verification Targets

Required before FT-013 can be marked implemented:

- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- Policy tests for action taxonomy: pH change, EC change, solution change, dosing, pump change, light change, pruning, transplanting, root trimming, and low-risk checks.
- Freshness tests proving pH/EC-dependent physical actions require measurement refs fresh within 2 hours.
- Fail-closed tests for missing/stale measurements, unsupported plant, uncertain classifier, unavailable gate, malformed action candidate, unsupported action type, and automated command wording.
- Display tests proving Companion output, UI spoiler notes, quoted detail replies, approval prompts, and task wording cannot display physical-action instructions without Safety Gate clearance.
- Routing tests proving unsafe wording becomes `block`, `needs_data`, or `pending_approval`, not cleared action advice.
- Bus integration test proving `safety_block` routes through FT-004 Bus publication and uses FT-012 MessageEnvelope shape when agent-originated.
- Task handoff tests proving Safety Gate may create pending proposal/approval handoff refs but cannot create `action_task` without FT-014 approval.
- Anti-cheat tests proving Safety Gate output is not treated as human approval and no automated device execution command can be produced.

## Gaps And Non-Goals

- No FT-013 blocker remains for `/prd-to-tasks FT-013`.
- Exact regex/pattern lists, classifier helper names, and Pydantic class names belong to implementation tasks.
- Human approval record fields, approval expiry/replay policy, approval rejection, and action unlock semantics are owned by FT-014.
- Hydroponics Advisor input reasoning and cautious recommendation generation are owned by FT-007.
- Automated pumps, dosing, lighting control, and device command execution are outside MVP scope.
