---
description: Feature-local SDD tech spec for FT-006 Vision Observation and plant state trust.
status: active
owner: architecture
last_updated: 2026-06-01
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/features/FT-006-vision-observation-plant-state-trust.md
  - .memory-bank/spec-index.md
---
# FT-006 Vision Observation and Plant State Trust Tech Spec

## Scope

This spec closes the feature-local SDD design gate for FT-006 before `/prd-to-tasks FT-006`.

FT-006 owns the MVP bridge from accepted photos to trusted plant-state updates:

- mock or real Vision Observation invocation through the existing agent adapter boundary;
- a small normalized vision observation report shape;
- observation-vs-diagnosis boundaries for vision output;
- source/evidence refs from photo catalog records, initial manifests, timeline events, and Bus/MessageEnvelope refs;
- confidence/status mapping into plant state;
- contradiction handling;
- human review and follow-up gates for confirmed plant state;
- dataset-governance handoff for agent-labeled evidence without setting `can_train_on=true`;
- API/service surfaces and verification targets needed for task decomposition.

FT-006 does not own photo upload, broad vision provider abstraction, disease/nutrient diagnosis, Hydroponics Advisor recommendations, Safety Gate physical-action policy, human approval for physical actions, UI layout, full dataset registry, real fine-tuning, or export package generation.

## Normative Inputs

- [.memory-bank/states/plant-state.md](../states/plant-state.md): confidence/status lifecycle and confirmed-state promotion rules.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): runtime decision and publishable agent output contract.
- [.memory-bank/tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md](FT-012-agent-runtime-decisions-message-envelope-output-contracts.md): adapter boundary, `AgentRuntimeResult`, `MessageEnvelope` validation, claim type mapping, and concise output.
- [.memory-bank/tech-specs/FT-004-agent-chat-bus-event-stream-publication-boundary.md](FT-004-agent-chat-bus-event-stream-publication-boundary.md): Bus publication boundary and `user_photo` / agent event payload minimums.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): PostgreSQL/read-model authority and required refs.
- [.memory-bank/domains/photo-artifacts.md](../domains/photo-artifacts.md): photo catalog, file artifact, manifest boundary, and MVP photo types.
- [.memory-bank/tech-specs/FT-002-photo-intake-catalog-capture-manifests.md](FT-002-photo-intake-catalog-capture-manifests.md): accepted photo fields, initial manifest v1, safe refs, and `user_photo` timeline event.
- [.memory-bank/tech-specs/FT-003-runtime-state-timeline-audit.md](FT-003-runtime-state-timeline-audit.md): runtime table boundaries, timeline append semantics, and current-state authority.
- [.memory-bank/states/dataset-governance.md](../states/dataset-governance.md): agent-labeled lifecycle, trainability prohibition, conflicts, and evidence refs.
- [.memory-bank/tech-specs/FT-009-dataset-governance-trainability.md](FT-009-dataset-governance-trainability.md): dataset item boundary, transition service, and trainability recomputation.
- [.memory-bank/states/task-follow-up.md](../states/task-follow-up.md): check/follow-up task evidence and outcome boundaries.
- [.memory-bank/tech-specs/FT-008-tasks-approvals-follow-up-outcomes.md](FT-008-tasks-approvals-follow-up-outcomes.md): missing-data check tasks and follow-up outcome refs.
- [.memory-bank/states/safety-approval.md](../states/safety-approval.md): physical-action wording boundary.
- [.memory-bank/tech-specs/FT-013-safety-gate-physical-action-advice.md](FT-013-safety-gate-physical-action-advice.md): final display/action wording checks when unsafe wording appears.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): API shape and structured errors.
- [.memory-bank/testing/first-demo.md](../testing/first-demo.md): first-demo gates and anti-cheat checks.
- [.memory-bank/invariants.md](../invariants.md): source-of-truth, agent, plant-state, safety, and trainability invariants.

## Design Decisions

### Vision Invocation Boundary

- Vision Observation may use a mock or real vision model for the first demo, but both modes must produce the same normalized adapter result and `MessageEnvelope` shape.
- Do not introduce a full provider plugin/abstraction for FT-006. A small configured adapter such as `mock` or `real` is enough as long as the domain-facing output is identical.
- Vision Observation can read accepted `photo_catalog` refs, safe initial manifest refs, latest relevant plant-state summary from PostgreSQL, and explicit source refs supplied by the workflow.
- Vision Observation must not treat photo manifests, export snapshots, `timeline.jsonl`, UI Feed, raw Agno output, or provider messages as current mutable state authority.
- Vision output is eligible for Agent Chat Bus only after FT-012 runtime-decision adaptation and FT-004 Bus publication.

### Accepted Inputs And Evidence Refs

Vision Observation runs only on accepted photos from the FT-002/FT-003 photo catalog.

Minimum invocation input:

| Field | Rule |
|---|---|
| `plant_id` | Required; MVP value `tomato_001`. |
| `photo_refs` | Non-empty list of accepted `photo:<photo_id>` refs. |
| `photo_types` | From the MVP photo types in photo artifacts. |
| `catalog_event_refs` | Timeline refs for accepted `user_photo` events when available. |
| `manifest_refs` | Initial capture manifest refs are allowed as immutable artifact evidence only. |
| `context_refs` | Optional refs to daily observations, manual measurements, previous plant-state records, or follow-up outcomes. |
| `adapter_mode` | `mock` or implementation-configured real mode; not a public provider contract. |

Evidence refs used by Vision Observation or Plant State must be stable refs, such as:

- `photo:<photo_id>`;
- `manifest:<manifest_ref>` for immutable initial capture artifact evidence;
- `timeline:<event_id>`;
- `bus:<bus_event_id>`;
- `message:<message_id>`;
- `observation:<observation_id>`;
- `measurement:<measurement_id>`;
- `task:<task_id>:outcome`;
- `review:<review_id>`;
- `plant_state:<state_record_id>`.

UI Feed event IDs and spoiler notes are forbidden as evidence refs for plant-state changes or dataset trainability.

### Vision Observation Report

The normalized vision report is an internal domain record or equivalent structured object. Exact ORM/Pydantic names belong to implementation tasks, but the report must preserve these facts:

| Field | Rule |
|---|---|
| `vision_report_id` | Backend-generated stable ID. |
| `plant_id` | Required; MVP value `tomato_001`. |
| `created_at` | Timezone-aware report time. |
| `agent_id` | Required, normally `vision_observation_agent`. |
| `adapter_mode` | `mock` or configured real mode. |
| `model_version` / `prompt_version` | Required; `mock` values allowed for mock mode. |
| `source_refs` | Non-empty stable evidence refs. |
| `photo_quality` | One of `usable`, `limited`, or `unusable`. |
| `visible_symptom_tags` | List from the MVP visual tag set below; empty only when quality/context is insufficient. |
| `missing_photo_types` | List of needed MVP photo types, when visual context is insufficient. |
| `observation_confidence` | `unknown`, `low`, `medium`, or `high`, aligned with `MessageEnvelope.confidence`. |
| `observation_summary` | Short visible-observation summary, not final diagnosis. |
| `diagnosis_boundary` | `observation_only`, `tentative_hypothesis`, or `invalid_diagnosis_or_action`. |
| `message_ref` | Required canonical `message:<message_id>` ref for publishable decisions. |
| `bus_event_ref` / `timeline_event_ref` | Refs when the report is published/audited. |

MVP `visible_symptom_tags` are intentionally small:

- `none_visible`
- `yellowing`
- `pale_leaf`
- `edge_discoloration`
- `spotting`
- `necrosis`
- `wilting`
- `curling`
- `deformation`
- `visible_damage`
- `unknown`

The tags describe visible pixels only. They are not disease, nutrient, pH/EC, or treatment labels.

### Observation vs Diagnosis Boundary

Allowed Vision Observation statements:

- photo quality and coverage;
- visible symptoms, such as yellowing, spotting, wilting, curling, deformation, or damage;
- missing visual context, such as `lower_leaf_closeup` under neutral light;
- confidence in the observation;
- tentative hypothesis language only when clearly marked as a hypothesis and backed by source refs.

Forbidden normal Vision Observation output:

- final disease, pest, or nutrient diagnosis;
- pH/EC correction, dosing, solution, pump, light, pruning, transplanting, root trimming, or other physical-action advice;
- action-task creation;
- `can_train_on=true`;
- direct mutation of confirmed plant state.

If the adapter receives final diagnosis wording without physical-action advice, it must either downgrade the content to `claim_type=hypothesis` with `can_train_on=false` and source refs, or reject the candidate as invalid when the boundary is ambiguous.

If the adapter receives physical-action wording, it must not publish it as normal Vision output. It must reject the report for plant-state update and route through FT-013 Safety Gate / FT-012 escalation behavior if a durable block is needed.

### MessageEnvelope Mapping

FT-006 uses only these Vision Observation claim routes:

| Runtime decision | Claim type | Allowed use |
|---|---|---|
| `speak` | `observation` | Photo quality, visible symptoms, and confidence. |
| `speak` | `hypothesis` | Tentative non-final interpretation from visible evidence. |
| `clarify` | `clarification_request` | Specific missing photo/context request. |
| `escalate` | `safety_block` | Only when unsafe physical-action wording must be blocked through Safety Gate. |

Vision Observation must not emit `recommendation` or `task_request` in FT-006. Missing photo/context asks use `clarification_request`; task creation, if needed, is a later FT-008 handoff.

All publishable Vision envelopes must have:

- `agent_id=vision_observation_agent`;
- `confidence` from `unknown|low|medium|high`;
- `requires_human_approval=false` unless the envelope is a Safety Gate escalation;
- `can_train_on=false`;
- non-empty `source_refs`;
- concise `consumable_output`;
- optional `ui_spoiler_note_ref` only as a pointer to non-consumable UI Feed.

### Plant State Field Set

FT-006 updates only a small visual plant-state surface for the MVP. Each field stores a value, status, confidence, source refs, and update time.

| Field | Allowed values / shape | Notes |
|---|---|---|
| `visual_condition_summary` | Short controlled text or null | Human-readable summary, not diagnosis. |
| `leaf_color_observation` | `normal_green`, `pale`, `yellowing`, `edge_yellowing`, `spotting`, `unknown`, `conflict` | Visible leaf color only. |
| `leaf_posture_observation` | `normal`, `wilting`, `curling`, `drooping`, `unknown`, `conflict` | Visible posture only. |
| `visible_damage_observation` | `none_visible`, `spots`, `necrosis`, `deformation`, `mechanical_damage`, `unknown`, `conflict` | No pest/disease conclusion. |
| `missing_visual_context` | List of MVP photo types | Used when state cannot be assessed. |
| `last_visual_observation_ref` | Ref to latest vision report/message | Traceability, not a state status by itself. |

Implementation may add display labels, but must not expand this into a diagnosis taxonomy or broad ML label set during FT-006.

### Confidence To State Status Mapping

The plant-state service maps normalized vision reports to plant-state records.

| Vision/report condition | Plant-state status |
|---|---|
| No usable photo, missing source refs, or insufficient visual context | `unknown` for affected fields; may produce `clarification_request`. |
| Usable observation with `low`, `medium`, or `high` confidence and no contradiction | `probable`. |
| Tentative `claim_type=hypothesis` with source refs | `probable` only; never confirmed. |
| New evidence contradicts existing field evidence | `conflict`. |
| Previous value carried forward with no fresh visual evidence | `assumed_unchanged`. |
| Human review confirms changed value | `confirmed_updated`. |
| Human review confirms no change | `confirmed_unchanged`. |
| Follow-up evidence confirms changed value | `confirmed_updated`, only through the follow-up gate below. |
| Follow-up evidence confirms no change | `confirmed_unchanged`, only through the follow-up gate below. |

High confidence from an agent is still agent-labeled evidence. It may increase priority for review or follow-up, but it must not promote a field to `confirmed_updated` or `confirmed_unchanged` by itself.

### Plant State Change Rules

- Plant-state writes must go through one plant-state application service or policy function; controllers and raw agent adapters must not write field statuses directly.
- Vision reports may create or update `probable`, `unknown`, or `conflict` field states.
- Agent-labeled output must not overwrite `confirmed_updated` or `confirmed_unchanged` with another confirmed status.
- If agent evidence conflicts with a confirmed field, the affected field becomes `conflict` or a separate conflict record is created, preserving both the confirmed source refs and the new agent source refs.
- `assumed_unchanged` is produced only by a current-state projection when there is no fresh evidence; Vision Observation does not directly claim it.
- Confirmed statuses require one of:
  - a `human_reviews` record with reviewer role/status, subject refs, decision, evidence refs, and event refs; or
  - follow-up evidence from a completed follow-up workflow with non-`no_data` outcome and stable evidence refs to new user-submitted observation/photo/measurement.
- Follow-up outcome `no_data` cannot confirm state. It preserves uncertainty.
- Contradictory follow-up evidence must set or keep `conflict` and may route to human review; it must not silently overwrite earlier evidence.

### Contradiction Handling

A contradiction exists when two non-empty evidence sets assert incompatible values for the same field and neither side is merely `unknown`.

Rules:

- Preserve both evidence sets in `source_refs` or conflict metadata.
- Do not choose the latest, highest-confidence, or most convenient value as confirmed.
- If the conflict involves human review or follow-up evidence, keep the agent evidence as hypothesis and require human review or later follow-up to resolve it.
- If the conflict is only between agent-labeled observations, mark `conflict` and request a targeted photo/check when a missing visual context can resolve it.
- Conflict records must keep enough refs to reproduce the disputed photo/report/state values.

### Dataset Governance Handoff

FT-006 may create dataset-governance metadata for the photo or agent output, but only through FT-009 rules.

Allowed handoff:

- accepted photo remains or initializes as `raw` when governance metadata is needed;
- validated Vision `MessageEnvelope` may create or transition an `agent_output` or photo-related dataset item to `agent_labeled`;
- conflicts, low confidence, rare examples, or high-impact labels may transition to `needs_review`;
- every handoff includes source refs, model/prompt version, confidence, report/message refs, and event refs where available.

Forbidden handoff:

- setting or implying `can_train_on=true`;
- choosing `dataset.split`;
- selecting `curator_decision=selected`;
- creating `confirmed` or `gold` dataset status from Vision output alone;
- using UI Feed, spoiler notes, stale export snapshots, or raw provider output as trainability evidence.

Any later trainability decision belongs to FT-009 dataset governance and must recompute `can_train_on` from the authoritative rule.

### Missing Visual Context

When photo quality or coverage is insufficient:

- Vision should return `runtime_decision=clarify` with `claim_type=clarification_request`;
- the request must name a specific MVP photo type when possible, for example `lower_leaf_closeup`, `whole_plant`, or `problem_area`;
- affected plant-state fields remain `unknown` or retain previous state with `assumed_unchanged` projection, depending on current-state read rules;
- a check/photo task may be requested through FT-008 later, but FT-006 itself does not create tasks directly.

### Timeline, Bus, And Authority

- Vision and plant-state workflows must preserve refs to accepted photo events and agent output events.
- Publishable Vision output uses FT-012 `MessageEnvelope` and FT-004 Bus publication.
- Timeline `agent_conclusion`, `agent_clarification_request`, or `safety_block` events may be appended for audit/export, but current plant state is read from PostgreSQL/read model.
- Photo manifests and export snapshots may include copies of vision reports and plant-state snapshots for export, but they do not define current mutable plant state.

## API And Service Surface

Feature tasks may implement these as internal services, HTTP endpoints, or both. Behavior is normative either way.

Service surface:

- `run_vision_observation(command)`
  - validates accepted photo refs and invokes mock/real configured adapter;
  - returns normalized `AgentRuntimeResult`, `MessageEnvelope` when publishable, and `vision_report_id`.
- `apply_vision_report_to_plant_state(vision_report_id)`
  - maps report fields to `probable`, `unknown`, or `conflict` state changes;
  - preserves source refs and writes timeline/event refs when emitted.
- `record_plant_state_review(command)`
  - records human review for plant-state fields and may promote to `confirmed_updated` or `confirmed_unchanged` when evidence refs are valid.
- `apply_follow_up_evidence_to_plant_state(command)`
  - consumes completed follow-up evidence with non-`no_data` outcome and source refs;
  - may promote or conflict affected fields according to the rules above.
- `handoff_vision_evidence_to_dataset_governance(command)`
  - optional handoff to FT-009 transition service with `can_train_on=false`.

Minimal HTTP surface for the PWA/backend boundary or local test workflows:

- `POST /api/plants/{plant_id}/vision-observations`
  - accepts a list of `photo_id` values and optional context refs;
  - uses configured mock/real adapter mode;
  - returns `vision_report_id`, runtime decision, `message_ref` and Bus refs when published, missing photo types, and plant-state candidate refs.
- `GET /api/plants/{plant_id}/vision-observations/{vision_report_id}`
  - returns the normalized report and source refs from PostgreSQL/read model.
- `GET /api/plants/{plant_id}/plant-state`
  - extends the FT-003 current-state read surface with field values, statuses, confidence, and source refs from PostgreSQL/read model.
- `POST /api/plants/{plant_id}/plant-state/reviews`
  - records human review for plant-state fields; this is not physical-action approval.

All API errors use the shared structured error envelope. Expected machine-readable codes include:

- `unsupported_plant`
- `photo_not_found`
- `photo_not_accepted`
- `missing_source_refs`
- `unsupported_photo_type`
- `vision_adapter_unavailable`
- `invalid_vision_output`
- `diagnosis_boundary_violation`
- `physical_action_wording_blocked`
- `invalid_state_field`
- `invalid_state_transition`
- `confirmation_requires_review_or_follow_up`
- `conflicting_evidence`
- `dataset_handoff_denied`

## Verification Targets

Required before FT-006 can be marked implemented:

- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- Schema tests for vision invocation input, normalized vision report fields, accepted photo refs, photo quality enum, visual symptom tags, missing photo types, source refs, model/prompt version, and timezone-aware timestamps.
- Adapter tests proving mock and real modes produce the same normalized domain output shape before MessageEnvelope/Bus publication.
- MessageEnvelope tests proving Vision uses only allowed claim routes, requires non-empty source refs, defaults `can_train_on=false`, and rejects `recommendation` / `task_request` for FT-006.
- Policy tests proving observations and hypotheses can update only `probable`, `unknown`, or `conflict` plant-state statuses.
- Promotion-gate tests proving `confirmed_updated` and `confirmed_unchanged` require human review or qualifying follow-up evidence.
- Conflict tests proving contradictory observations preserve both evidence sets and do not silently overwrite confirmed or probable values.
- Missing-context tests proving low-quality/incomplete photos return a targeted `clarification_request` such as `lower_leaf_closeup` and leave affected state unknown or assumed unchanged.
- Safety-boundary tests proving physical-action wording from Vision output is not published as normal Vision output, does not create tasks, and routes to Safety Gate/escalation when durable handling is required.
- Dataset-governance tests proving Vision handoff can create `agent_labeled` or `needs_review` metadata with evidence refs but cannot set split, selected curator decision, confirmed/gold status, or `can_train_on=true`.
- Runtime authority tests proving current plant state is read from PostgreSQL/read model, not photo manifests, export snapshots, `timeline.jsonl`, Agent Chat Bus replay, or UI Feed.
- Integration tests proving accepted photo refs flow through Vision adapter, FT-012 `MessageEnvelope`, FT-004 Bus publication, plant-state update service, timeline audit refs, and optional FT-009 handoff without bypassing boundaries.
- Anti-cheat tests proving raw provider output, raw Agno output, hidden reasoning, UI spoiler text, stale export snapshots, and local filenames cannot become plant state, confirmed facts, Bus context, or trainable labels.

## Gaps And Non-Goals

- No FT-006 blocker remains for `/prd-to-tasks FT-006`.
- A standalone `.memory-bank/contracts/vision-observation.md` is not required for the MVP because the feature-local tech spec plus FT-012/FT-004 contracts cover the current boundary.
- Exact ORM names, Alembic revision names, Pydantic class names, adapter function names, prompt parser details, and UI rendering belong to implementation tasks.
- Real disease diagnosis, nutrient diagnosis, treatment recommendations, physical-action advice, broad ML pipeline, full provider abstraction, image annotation tooling, export packaging, and training-data selection are outside FT-006 MVP scope.
