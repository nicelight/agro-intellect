---
description: Feature-local SDD tech spec for FT-007 Hydroponics Advisor and missing data policy.
status: active
owner: architecture
last_updated: 2026-06-01
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/features/FT-007-hydroponics-advisor-missing-data-policy.md
  - .memory-bank/spec-index.md
---
# FT-007 Hydroponics Advisor and Missing Data Policy Tech Spec

## Scope

This spec closes the feature-local SDD design gate for FT-007 before `/prd-to-tasks FT-007`.

FT-007 owns the MVP Hydroponics Advisor boundary:

- advisor input context and evidence refs for `tomato_001`;
- missing/stale critical data policy for hydroponics analysis;
- pH/EC analysis freshness handling;
- cautious recommendation wording rules;
- MessageEnvelope claim mapping for advisor output;
- handoff to FT-008 for check/measurement task requests;
- handoff to FT-013 Safety Gate for physical-action wording or action candidates;
- service/API surface and verification targets needed for task decomposition.

FT-007 does not own task persistence, action-task creation, Safety Gate classification, human approval records, approval unlock, plant-state promotion, dataset trainability, sensor ingestion, automated device control, or a broad agronomic rule engine.

## Normative Inputs

- [.memory-bank/tech-specs/FT-001-daily-check-in-observations-manual-measurements.md](FT-001-daily-check-in-observations-manual-measurements.md): manual pH/EC fields, refs, provenance, and 24-hour analysis freshness projection.
- [.memory-bank/states/safety-approval.md](../states/safety-approval.md): physical-action list, 24-hour analysis and 2-hour approval freshness windows, fail-closed behavior, and approval requirements.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): runtime decisions, claim types, source-ref requirements, and concise output rules.
- [.memory-bank/tech-specs/FT-012-agent-runtime-decisions-message-envelope-output-contracts.md](FT-012-agent-runtime-decisions-message-envelope-output-contracts.md): adapter boundary, `AgentRuntimeResult`, `MessageEnvelope` validation, and decision-to-event mapping.
- [.memory-bank/states/task-follow-up.md](../states/task-follow-up.md): task types and creation rules.
- [.memory-bank/tech-specs/FT-008-tasks-approvals-follow-up-outcomes.md](FT-008-tasks-approvals-follow-up-outcomes.md): measurement/check task creation sources, source refs, due behavior, and action-task prohibition.
- [.memory-bank/tech-specs/FT-013-safety-gate-physical-action-advice.md](FT-013-safety-gate-physical-action-advice.md): physical-action taxonomy, `SafetyGateDecision`, display checks, task handoffs, and fail-closed outcomes.
- [.memory-bank/tech-specs/FT-014-human-approval-action-unlock-semantics.md](FT-014-human-approval-action-unlock-semantics.md): pending approval records, stale/replay prevention, and action unlock semantics.
- [.memory-bank/tech-specs/FT-006-vision-observation-plant-state-trust.md](FT-006-vision-observation-plant-state-trust.md): visual observation refs and observation-vs-diagnosis boundary.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): PostgreSQL/read-model authority and required refs.
- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): agent adapter, Safety Gate, task, Bus, and UI Feed module boundaries.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): API shape and structured error envelope.
- [.memory-bank/testing/first-demo.md](../testing/first-demo.md): first-demo pH/EC, Safety Gate, task/follow-up, and anti-cheat gates.
- [.memory-bank/invariants.md](../invariants.md): source-of-truth, agent boundary, human gate, and MVP exclusion rules.

## Design Decisions

### Advisor Invocation Boundary

- The MVP advisor identity is `hydroponics_advisor_agent`.
- The advisor may run through a mock, prompt-based, or real model adapter, but publishable output must pass through FT-012 `AgentRuntimeResult` / `MessageEnvelope` validation and FT-004 Bus publication where applicable.
- The advisor reads current mutable context from PostgreSQL/read model and stable source refs. It must not treat UI Feed, UI spoiler notes, raw Agno output, provider history, `timeline.jsonl` replay, or photo manifests as current authority.
- The advisor produces advice, missing-data requests, or Safety Gate handoff candidates. It never writes task records, approval records, plant-state confirmed values, or device commands directly.
- No autonomous hydroponic control is in scope. Any physical-action wording must route to FT-013 before user display or task/action routing.

### Advisor Input Context

The exact ORM/Pydantic names belong to implementation tasks, but every advisor invocation must be able to preserve these context facts:

| Field | Rule |
|---|---|
| `plant_id` | Required; MVP value `tomato_001`. |
| `created_at` | Timezone-aware invocation/context time. |
| `request_reason` | Short machine-readable reason such as `daily_checkin`, `user_question`, `missing_data_review`, or `safety_recheck`. |
| `analysis_goal` | Small enum or string describing the requested analysis, such as `general_hydroponics_review`, `solution_related_review`, `visual_symptom_context`, or `missing_data_only`. |
| `measurement_context` | Latest pH/EC refs and derived freshness from FT-001; includes independent pH and EC state. |
| `environment_context` | Optional temperature, humidity, and light refs/status when available; absent values remain unknown. |
| `solution_context` | Optional reservoir/solution refs such as solution notes, tank photo refs, volume/context notes, or last solution-change refs when available. |
| `visual_context_refs` | Optional refs to FT-006 vision reports, plant-state summaries, photo refs, or missing visual context. |
| `history_refs` | Optional recent observations, measurements, tasks, approvals, follow-up outcomes, and timeline refs used as evidence. |
| `source_refs` | Required non-empty stable refs used to build the advice or missing-data request. |

Allowed stable refs include `measurement:<measurement_id>`, `observation:<observation_id>`, `photo:<photo_id>`, `vision_report:<vision_report_id>`, `plant_state:<state_record_id>`, `task:<task_id>`, `approval:<approval_id>`, `timeline:<event_id>`, `bus:<bus_event_id>`, and canonical `message:<message_id>` refs.

If a value is missing, stale, unknown, or unsupported, the context must represent that state explicitly. The advisor must not infer pH/EC from photos, UI prose, old export snapshots, or agent hypotheses.

### pH/EC Missing And Stale Policy

pH and EC are evaluated independently for analysis freshness using FT-001 rules:

- fresh for analysis when the latest valid value age is less than or equal to 24 hours;
- stale for analysis when the latest valid value age is greater than 24 hours;
- missing when no valid plant-bound measurement ref exists;
- invalid when the ref lacks timestamp, provenance, plant binding, or syntactic validity.

Policy by advice type:

| Advice/request type | Required data behavior |
|---|---|
| General non-solution observation, such as "monitor trend" or "collect more context" | May proceed cautiously with explicit uncertainty and source refs. |
| Solution-related analysis, nutrient balance interpretation, pH/EC interpretation, or advice that depends on solution chemistry | Requires fresh pH and EC for analysis unless the user question explicitly depends on only one value. Missing/stale required fields must produce a missing-data request instead of solution advice. |
| pH-specific interpretation | Requires fresh pH for analysis; EC may be requested when needed to disambiguate nutrient/solution context. |
| EC/nutrient-strength interpretation | Requires fresh EC for analysis and should request pH too when uptake/solution chemistry is part of the rationale. |
| Physical-action candidate, such as changing pH, EC, solution, dosing, pumps, lights, or high-risk manual intervention | Must route to FT-013 Safety Gate. FT-013 owns the 2-hour approval freshness check and approval handoff. |

When pH/EC are fresh for analysis but older than the 2-hour physical-action approval window, FT-007 may produce cautious analysis, but any physical-action wording or proposal still routes to FT-013 and may become `needs_data` or `pending_approval`.

### Clarification Vs Measurement Task Request

FT-007 distinguishes user clarification from task handoff without creating task records directly.

Use `runtime_decision=clarify` with `claim_type=clarification_request` when:

- the missing input is a targeted question or context note, such as reservoir volume, nutrient mix name, recent solution change, light schedule, observed symptom location, or whether a photo shows a specific plant area;
- the system cannot yet decide a concrete task type safely;
- the request is a one-off chat clarification rather than a durable task;
- FT-008 task creation is unavailable and the safest fallback is a short targeted ask.

Use `runtime_decision=speak` with `claim_type=task_request` as a handoff to FT-008 when:

- missing/stale data maps to a low-risk `measurement_task` or `check_task`;
- the request should persist in the task list;
- source refs and missing fields are known;
- wording is non-intervention and contains no physical-action instruction.

The task handoff must be structured enough for FT-008 to validate source/task combinations. The handoff should preserve:

- requested task type: `measurement_task` or `check_task`;
- missing fields such as `ph`, `ec`, `ph_ec`, `temperature`, `humidity`, `light`, `solution_context`, or `photo_context`;
- reason code such as `missing_for_analysis`, `stale_for_analysis`, `insufficient_solution_context`, or `insufficient_visual_context`;
- source refs, including the advisor `message:<message_id>` ref and optional Bus ref when available;
- safe display summary.

FT-008 remains the only owner of task record creation and must reject any attempt by FT-007 to create `action_task`.

### Cautious Recommendation Wording

Advisor output must stay concise and cautious:

- ordinary recommendations are 1-3 short lines;
- uncertainty is explicit when evidence is partial;
- output uses hypothesis/review language such as "possible", "consistent with", "worth checking", or "needs confirmation";
- output names missing critical data instead of guessing;
- output avoids cleared dosage, target pH/EC, solution-change, pump, light, pruning, transplanting, or root-trimming instructions unless FT-013 has cleared the exact display wording in an approval context.

Forbidden normal advisor wording:

- mandatory dosing or immediate action commands;
- "raise/lower/change pH/EC to X" as cleared advice;
- nutrient amounts, schedules, or reservoir-change instructions as user-visible commands;
- pump/light/device commands;
- action-task creation;
- confirmed diagnosis or confirmed plant-state claims from advisor output alone;
- claims with missing `source_refs`;
- `can_train_on=true`.

The advisor may safely request low-risk checks, such as measuring pH/EC, taking a specific photo, recording solution temperature, or confirming recent reservoir context, as long as wording does not become an intervention.

### MessageEnvelope Mapping

Allowed Hydroponics Advisor claim routes:

| Runtime decision | Claim type | Allowed use |
|---|---|---|
| `speak` | `recommendation` | Cautious, non-action or already Safety-Gate-safe recommendation with source refs. |
| `speak` | `hypothesis` | Tentative hydroponic interpretation that is not final diagnosis and not action advice. |
| `speak` | `task_request` | Structured low-risk check/measurement task handoff to FT-008. |
| `clarify` | `clarification_request` | Short targeted missing-data question. |
| `escalate` | `safety_block` | Safety Gate block or fail-closed route for unsafe physical-action wording. |
| `silent` | none | No material advisor output; audit only through FT-012 rules. |

All publishable advisor envelopes must have:

- `agent_id=hydroponics_advisor_agent`;
- `confidence` from `unknown|low|medium|high`;
- `requires_human_approval=false` for ordinary advice, hypotheses, clarification requests, and measurement/check task requests;
- `requires_human_approval=true` only for Safety Gate / pending approval handoff content after FT-013 classifies it;
- `can_train_on=false`;
- non-empty `source_refs`;
- concise `consumable_output`;
- optional `ui_spoiler_note_ref` only as a pointer to UI Feed content that is not visible or consumable by agents.

`task_request` envelopes do not create tasks by themselves. They are a validated handoff input to FT-008.

### Safety Gate Handoff

Before any Hydroponics Advisor output is displayed to the user or converted into task/action routing, the workflow must check whether the wording instructs or implies physical action.

Physical-action wording includes changing pH, changing EC, changing solution, dosing, changing pumps, changing lights, pruning, transplanting, root trimming, target-setting, amount/schedule instructions, and similar intervention language.

Handoff rules:

- If no physical action is detected and the output is cautious/non-intervention, it may publish as normal advisor output.
- If physical action is detected or classification is uncertain, route the candidate text or structured action candidate to FT-013.
- If FT-013 returns `needs_data`, publish/request the missing measurement/check path and do not display the original action instruction.
- If FT-013 returns `pending_approval`, route to FT-014/FT-008 pending approval flow and do not display the original action as cleared advice.
- If FT-013 returns `block`, publish or display only the safe block/replacement text.
- If FT-013 is unavailable, malformed, or cannot classify, fail closed with no cleared action wording.

FT-007 may prepare a structured action candidate for Safety Gate evaluation, but it must not create a pending approval, approval task, action task, or automated command.

### Runtime Authority And Events

- Current measurements, tasks, approvals, plant state, and history come from PostgreSQL/read model or validated service projections.
- `timeline.jsonl` may be referenced for audit evidence only and is not current mutable authority.
- Agent Chat Bus events may influence advisor context only after FT-004 publication and context filtering.
- UI Feed and spoiler notes must not enter advisor working context.
- Timeline audit events for `agent_conclusion`, `agent_clarification_request`, `safety_block`, or task handoff may be appended by the owning workflow, but FT-007 does not make timeline replay authoritative.

## API And Service Surface

Feature tasks may implement these as internal services, HTTP endpoints, or both. Behavior is normative either way.

Service surface:

- `build_hydroponics_advisor_context(command)`
  - reads current PostgreSQL/read-model context and returns explicit known/missing/stale fields with source refs.
- `apply_hydroponics_missing_data_policy(context, analysis_goal)`
  - returns required fields, missing/stale fields, and whether advice may proceed.
- `run_hydroponics_advisor(command)`
  - invokes mock/real configured advisor adapter and returns normalized `AgentRuntimeResult`.
- `validate_hydroponics_advisor_output(result)`
  - applies FT-012 MessageEnvelope validation, cautious wording checks, source-ref rules, and `can_train_on=false`.
- `handoff_hydroponics_candidate_to_safety_gate(candidate, source_refs)`
  - routes physical-action candidate wording to FT-013 and consumes the resulting decision without creating action tasks.
- `build_hydroponics_task_request(policy_decision, source_refs)`
  - prepares an FT-008 task handoff for `measurement_task` or `check_task` only.

Minimal HTTP surface for local workflows/tests:

- `POST /api/plants/{plant_id}/hydroponics-advice`
  - accepts a bounded analysis request and optional explicit source refs;
  - returns runtime decision, `message_ref` and Bus refs when published, missing-data policy result, optional FT-008 task-request handoff refs, and optional FT-013 safety decision refs.
- `GET /api/plants/{plant_id}/hydroponics-context`
  - optional debug/test endpoint returning the advisor context projection from PostgreSQL/read model with no raw reasoning or UI Feed content.

Normal daily flow may call these services internally instead of exposing public routes.

All API errors use the shared structured error envelope. Expected machine-readable codes include:

- `unsupported_plant`
- `missing_source_refs`
- `missing_critical_data`
- `stale_measurement_for_analysis`
- `invalid_measurement_ref`
- `invalid_advisor_output`
- `unsafe_action_wording`
- `safety_gate_required`
- `safety_gate_unavailable`
- `task_handoff_denied`
- `action_task_forbidden`

## Verification Targets

Required before FT-007 can be marked implemented:

- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- Schema/model tests for advisor context fields, plant binding, source refs, measurement context, missing/stale status, and timezone-aware context time.
- Policy tests proving pH and EC analysis freshness are evaluated independently with the 24-hour window from FT-001.
- Missing-data tests proving missing/stale pH/EC blocks solution-related advice and produces a targeted clarification or FT-008 measurement-task handoff.
- Clarification-vs-task tests proving contextual questions use `clarification_request`, while durable low-risk pH/EC measurement asks use `task_request` handoff without direct task writes.
- MessageEnvelope tests proving Hydroponics Advisor uses only allowed claim routes, requires non-empty source refs, defaults `can_train_on=false`, and keeps ordinary output concise.
- Cautious wording tests proving recommendations preserve uncertainty and do not present confirmed diagnosis or cleared physical-action instructions.
- Safety-boundary tests proving pH/EC correction, dosing, solution change, pump/light changes, and high-risk manual intervention wording routes to FT-013 before display.
- Fail-closed tests for unavailable Safety Gate, uncertain physical-action classification, malformed advisor output, unsupported plant, missing source refs, stale required data, and prompt-injection attempts to bypass Safety Gate.
- Task handoff tests proving FT-007 can request only `measurement_task` or `check_task` through FT-008 and cannot create or request `action_task` directly.
- Integration test proving a daily-flow advisor invocation can use FT-001 freshness projection, FT-012 MessageEnvelope validation, FT-004 Bus publication, FT-008 task handoff, and FT-013 Safety Gate without bypassing ownership boundaries.
- Runtime authority tests proving advisor context is built from PostgreSQL/read model and validated Bus refs, not UI Feed, raw Agno output, raw reasoning, stale manifests, or timeline replay.
- Anti-cheat test proving no advisor output produces automated device commands, actuator payloads, approval records, approved action tasks, or `can_train_on=true`.

## Gaps And Non-Goals

- No FT-007 blocker remains for `/prd-to-tasks FT-007`.
- A standalone `.memory-bank/contracts/hydroponics-advisor.md` is not required for the MVP because this feature-local tech spec plus FT-012, FT-013, and FT-008 cover the current boundary.
- Exact prompt text, adapter function names, Pydantic class names, ORM table names, fixture shapes, and endpoint response field ordering belong to implementation tasks.
- Exact crop recipes, nutrient schedules, cultivar-specific thresholds, and reservoir dosing formulas are outside FT-007 MVP unless a later spec adds them.
- Automated pumps, dosing, lighting control, pH/EC correction, and device command execution are outside MVP scope.
