---
description: Product Requirements Document.
status: draft
type: prd
clarification_status: complete
constitution_checked: true
---
# PRD

## Source Inputs

- [Archived Product Brief](analysis/product-brief.md): Product Brief input contract for this PRD.
- [.memory-bank/constitution.md](constitution.md): governing policy for AI-first, KISS, Memory Bank, task execution, risk-based DoD, human safety gates, and low maintenance.
- [.memory-bank/spec-index.md](spec-index.md): future routing layer for SDD Design Specs. After `/spec-init` and `/spec-design`, linked specs become normative.
- [.memory-bank/testing/index.md](testing/index.md): baseline verification strategy.

## Product Summary

Agro Intellect MVP is a personal hydroponic tomato monitoring assistant and an AI-first training ground for designing, implementing, testing, and governing agentic agricultural monitoring systems.

The MVP focuses on one plant, `tomato_001`, and turns daily observations, photos, manual pH/EC inputs, agent conclusions, safety decisions, follow-up tasks, approvals, outcomes, and dataset metadata into traceable evidence. The system must be useful as a personal tomato assistant now while preserving reusable architectural patterns for a future farm-scale agentic monitoring system.

The first product surface is a Web App/PWA. The user performs a daily check-in, uploads photos, enters manual observations and pH/EC values, receives cautious agent conclusions, approves risky physical actions, and tracks follow-up tasks.

## Goals

- Practice AI-first product development with explicit specs, Memory Bank routing, task records, evidence, and verification gates.
- Provide a working daily monitoring loop for one hydroponic tomato as the constrained product vehicle for that learning goal.
- Validate single-competence agent boundaries and structured inter-agent communication.
- Preserve source-of-truth discipline across PostgreSQL runtime state, `timeline.jsonl`, file photos, JSON photo manifests, Agent Chat Bus, UI Feed, and future SDD specs.
- Keep all plant-impacting physical actions behind fresh data, Safety Gate checks, and human approval.
- Build dataset governance foundations so future training/evaluation data is based on evidence rather than raw agent hypotheses.
- Keep the MVP low-maintenance and small enough to implement as a local monolith.

## Non-goals

- Production SaaS.
- Multi-user support.
- Commercial farm-management product scope.
- Autopilot control, pumps, dosing, pH/EC adjustment, light control, or any direct physical actuation.
- Automatic pH/EC correction or mandatory dosing instructions without approval.
- Complex RAG, expert panel, full dataset registry, or real model fine-tuning.
- Storing photo binaries in PostgreSQL or InfluxDB.
- Making InfluxDB a runtime dependency before real sensors exist.
- Treating Agno, Agno Team, Agno Workflow events, Agno memory, or Agno storage as domain source of truth.
- Using Agno Team `coordinate` mode as a domain coordinator.
- Treating agent hypotheses, UI explanations, or raw model reasoning as confirmed facts or trainable labels.

## Users / Actors

- Primary user: the project owner acting as Human Architect, Product Owner, Safety Owner, QA Gatekeeper, Domain Learner, and operator of one hydroponic tomato.
- Product user role: one person caring for `tomato_001` through daily observation and decision support.
- Future reference user: farm operators or agronomists in a future farm-scale system; not an MVP user.

Product agents:

- Companion Agent: user dialogue, daily flow, plain-language synthesis, missing-data prompts.
- Vision Observation Agent: photo quality and visual observations; not final diagnosis or pH/EC correction.
- Plant State Agent: state over time, trends, uncertainty statuses, conflicts; cannot confirm agent-labeled hypotheses without human review or follow-up evidence.
- Hydroponics Advisor Agent: hydroponic parameters and cautious recommendations; cannot bypass Safety Gate.
- Task & Follow-up Agent: check tasks, approved action tasks, follow-up tracking, outcomes.
- Safety Gate Agent: blocks or converts risky physical-action recommendations into pending approval flows.
- Dataset Governance Agent: dataset lifecycle rules, train/eval/holdout constraints, `can_train_on` eligibility.
- Training Data Curator Agent: delayed dataset selection using evidence refs; mostly silent in Agent Chat Bus.

## Functional Requirements

### FR-001 Daily Check-in

- The system MUST support a daily check-in flow for `tomato_001`.
- The system MUST allow the user to record textual observations for the day.
- The system SHOULD initiate or guide the daily ritual with a short prompt such as "Как томат сегодня?"
- The daily check-in MUST be recorded as traceable state/event data.

### FR-002 Photo Capture and Catalog

- The system MUST allow the user to upload photos for `tomato_001`.
- Every photo MUST have `plant_id`, `photo_id`, `captured_at`, `photo_type`, file path, and `sha256`.
- `photo_catalog.photo_id` MUST be globally unique.
- `photo_catalog.plant_id` MUST be mandatory and canonical for runtime plant binding.
- The system MUST support MVP photo types: `whole_plant`, `leaf_closeup`, `lower_leaf_closeup`, `top_view`, `stem`, `roots`, `solution_tank`, `problem_area`.
- Photo binaries MUST be stored as files, not PostgreSQL or InfluxDB blobs.

### FR-003 Photo JSON Manifest and Export Snapshot

- Each photo MUST have an initial generated JSON manifest snapshot next to the photo file at upload/capture time.
- The system MUST distinguish initial capture manifests from later export snapshot manifests.
- `photo_manifest.plant_id` MUST be mandatory and immutable for export.
- Initial capture manifests MUST include schema version, photo identity, file identity, `plant_id`, `captured_at`, `photo_type`, file reference, and `sha256`.
- Export snapshot manifests MAY include plant context, relevant system state, agent reports, review/dataset/sync status snapshots, and sensor window references when those data exist.
- Export snapshot manifests MUST include `manifest_kind`, `snapshot_at`, and `snapshot_version` or `export_id`.
- Photo JSON manifests are dataset/export artifacts and MUST NOT become runtime authority for mutable state.
- Mutable review, dataset, sync, and plant state MUST be read from PostgreSQL/read model, not from a previous manifest snapshot.

### FR-004 Manual pH/EC and Observation Input

- The system MUST allow manual pH and EC entry.
- Manual measurements MUST include timestamp/provenance.
- Hydroponics recommendations that depend on pH/EC MUST request fresh measurements when missing or stale.
- pH/EC measurements are fresh for analysis for up to 24 hours.
- pH/EC measurements are fresh for physical action approval for up to 2 hours.

### FR-005 Runtime State in PostgreSQL

- PostgreSQL MUST be part of the MVP.
- PostgreSQL/read model MUST be runtime authority for mutable operational state.
- Minimal runtime state MUST include plants, photo catalog, tasks, human approvals, review statuses, dataset statuses, `can_train_on`, event refs, sync status, and future `sensor_window_ref`.
- The MVP schema SHOULD remain minimal and avoid broad farm-scale abstractions before needed.

### FR-006 Timeline Audit Export

- The system MUST maintain `timeline.jsonl` as an append-only audit/export log.
- Each line MUST represent one event.
- Timeline events MUST include enough identifiers to trace daily observations, photo uploads, agent conclusions, task creation, approvals, safety blocks, and sync events.
- For `event_type=user_photo`, `payload.plant_id` MUST be mandatory and MUST NOT be inferred only from `topic`.
- `timeline.jsonl` MUST NOT be treated as primary mutable state.

### FR-007 Agent Chat Bus

- The system MUST use a domain-owned Agent Chat Bus for consumable agent events.
- Agno invocation MUST NOT equal Agent Chat Bus publication.
- Bus events MUST pass through `BusEventEnvelope`.
- Agent work outputs published to the Bus MUST pass through `MessageEnvelope`.
- Agent Chat Bus events MUST include `consumable_by_agents`.
- MVP event types MUST include `user_message`, `user_photo`, `agent_conclusion`, `agent_clarification_request`, `agent_quoted_detail_reply`, `agent_team_signal`, `safety_block`, `task_created`, `human_confirmation`, `system_event`, and `sync_event`.

### FR-008 Agent Runtime Decision

- Each invoked agent MUST return one runtime decision: `speak`, `silent`, `clarify`, or `escalate`.
- `silent` MUST NOT create a `MessageEnvelope` or publish to Agent Chat Bus.
- `silent` MUST still leave an audit record.
- `speak` MUST publish a concise consumable conclusion through `MessageEnvelope`.
- `clarify` MUST publish a short missing-data request.
- `escalate` MUST publish a Team Signal or Safety Block.

### FR-009 UI Feed Separation

- The system MUST maintain UI Feed as a presentation layer separate from Agent Chat Bus.
- UI Feed events MUST NOT be passed to agents as working context.
- `ui_spoiler_note` MUST have `consumable_by_agents=false` and `visible_to_agents=false`.
- UI-only explanations MUST be controlled summaries for the user, not raw chain-of-thought.
- `ui_spoiler_note_ref` MAY be included in `MessageEnvelope`, but it MUST refer only to a UI Feed event.

### FR-010 Concise Agent Communication

- Ordinary agent conclusions SHOULD be 1-3 lines.
- Clarification requests MUST be short and targeted.
- Quoted detail replies SHOULD be 3-7 lines and remain shorter than UI Spoiler Notes.
- Large team messages MUST be reserved for Team Signals or Safety Blocks.

### FR-011 Vision Observation

- The system MUST support mock or real Vision Observation Agent for the first demo.
- Vision Observation Agent MUST describe photo quality, visible symptoms, missing visual context, and observation confidence.
- Vision Observation Agent MUST distinguish observation from diagnosis.
- Vision Observation Agent MUST NOT recommend pH/EC correction, dosing, or physical plant-system actions.
- The first working demo MAY default to mock Vision if output contracts match the future real vision model.

### FR-012 Plant State

- Plant State Agent MUST track plant state over time.
- Important fields MUST carry confidence/status metadata such as `confirmed_updated`, `confirmed_unchanged`, `assumed_unchanged`, `probable`, `unknown`, or `conflict`.
- Agent-labeled conclusions MAY update probable, unknown, or conflict states.
- Agent-labeled conclusions MUST NOT promote state to confirmed without human review or follow-up evidence.

### FR-013 Hydroponics Advisor

- Hydroponics Advisor Agent MUST reason over pH, EC, temperature, humidity, light, solution context, visual observations, and history when available.
- Hydroponics Advisor Agent MUST issue cautious recommendations and ask for missing critical data.
- Hydroponics Advisor Agent MUST NOT create action tasks directly.
- Hydroponics Advisor Agent MUST NOT bypass Safety Gate or issue mandatory dosing/action commands.

### FR-014 Safety Gate and Human Approval

- The system MUST block any immediate physical-action command without fresh data, safety check, and human approval.
- Physical actions include changing pH, changing EC, changing solution, changing pumps, changing dosing, changing light regime, and similar plant-system interventions.
- In the first demo, Safety Gate MUST also cover high-risk manual interventions such as pruning, transplanting, and root trimming.
- Low-risk manual observations or checks do not require approval unless they become physical interventions.
- Safety Gate MAY convert risky recommendations into pending action proposals or pending approval tasks.
- MVP `action_task` means human-performed checklist/task tracking, not automated device command or physical actuation.
- Approval unlocks task tracking/status transition for a human-performed `action_task`; it MUST NOT authorize automatic device execution in MVP.
- User-visible outputs, including Companion responses and UI spoiler notes, MUST pass a final safety check before display when they contain or imply a physical action.
- Any user-visible phrase that instructs or implies a physical action MUST fail closed into Safety Gate review.

### FR-015 Tasks and Follow-up

- Task & Follow-up Agent MUST create check/measurement tasks without approval when additional data is needed.
- Task & Follow-up Agent MUST create action tasks only from approved action proposals.
- The system MUST support follow-up after 1-3 days.
- Follow-up outcome MUST record whether the situation improved, worsened, stayed unchanged, or has no data.

### FR-016 Dataset Governance

- The system MUST track `dataset.status`: `raw`, `agent_labeled`, `needs_review`, `confirmed`, `rejected`, `gold`, `excluded`.
- The system MUST track separate fields for `dataset.split`, `dataset.curator_decision`, `dataset.confirmation_source`, `dataset.evidence_refs`, `dataset.curator_notes_ref`, `dataset.corrected`, and `dataset.follow_up_seen`.
- Dataset and agent-report provenance MUST include source, `model_version`, `prompt_version`, `reviewer_role` when reviewed, `created_at`, and outcome/evidence refs when available.
- The MVP MUST include the full set of key dataset lifecycle fields from the start, but MUST NOT implement a full dataset registry before the MVP needs it.
- `can_train_on=true` MUST be allowed only when:
  - `dataset.curator_decision=selected`;
  - `dataset.split=train`;
  - `dataset.evidence_refs` is not empty;
  - and status/source rules allow either confirmed training item or gold item as defined by the dossier.
- `dataset.split=eval` and `dataset.split=holdout` MUST NOT be used for fine-tuning/train.
- `gold` MUST require human, expert, or batch review approval.
- `curator_auto` MAY confirm ordinary train items only when strong `evidence_refs` exist.

### FR-017 Lazy Sync

- MVP sync status MUST support `local_only`.
- If local dataset storage exceeds 200 MB, the UI SHOULD show a local storage prompt only.
- Server/upload sync is TODO for a later version and MUST NOT be implied or triggered in the MVP.
- The 200 MB prompt MUST NOT imply that a server/upload target exists or that sync status changed.
- `server_verified` MUST NOT appear before a server sync stage exists.

## Non-functional Requirements

- Safety: physical plant-system changes require fresh data, Safety Gate, and human approval.
- Traceability: photos, observations, agent outputs, tasks, approvals, outcomes, and dataset decisions must be traceable via IDs and event refs.
- Source-of-truth discipline: PostgreSQL owns mutable runtime state; photo JSON is export snapshot; `timeline.jsonl` is audit/export; Agent Chat Bus is domain event context; UI Feed is presentation; Agno is execution SDK.
- KISS: use the smallest verifiable MVP slices; avoid production SaaS, multi-user architecture, full dataset registry, complex sync, and unnecessary abstractions.
- Testability: schemas, safety rules, context filtering, dataset eligibility, and critical workflow rules must be testable.
- Local-first operation: MVP can run locally without sensor runtime dependencies or server sync.
- Local security baseline: backend MUST bind to loopback by default; LAN mode requires explicit enablement and authentication/token protection.
- Local security baseline: API CORS MUST use an allowlist; uploads MUST validate size, MIME/content type, and safe paths; path traversal MUST be rejected.
- Secrets baseline: `.env` values, API keys, tokens, and credentials MUST NOT be written to logs, `timeline.jsonl`, photo manifests, UI Feed, Agent Chat Bus, or screenshots.
- Privacy baseline: local plant photos and manifests are private project data by default and MUST NOT be uploaded or synced without explicit user approval.
- Context hygiene: agents consume only domain-approved Bus events and structured outputs, not UI Feed or raw reasoning.
- Maintainability: Memory Bank remains durable project knowledge; meaningful changes must update relevant Memory Bank navigation/source-of-truth docs.

## Data / Domain Model

Core runtime entities:

- Plant: initial scope is `tomato_001`.
- Photo catalog item: `photo_id`, `plant_id`, `captured_at`, `photo_type`, file path, `sha256`, review/dataset/sync references.
- Photo manifest snapshot: immutable file-side JSON artifact next to the photo, with `manifest_kind=initial_capture|export_snapshot`.
- Timeline event: append-only audit/export event.
- Bus event envelope: working domain event for Agent Chat Bus.
- Message envelope: structured working output from an agent.
- UI Feed event: presentation-only event for UI status/spoiler/debug-lite display.
- Task: check task, measurement task, pending approval task, approved action task, follow-up task.
- Human approval: approval/rejection for physical actions and selected data decisions.
- Human review: manual data item/label review lifecycle.
- Dataset item/status: future learning-loop metadata and train/eval/holdout eligibility.
- Sensor window reference: future link to sensor readings; initially manual measurement or placeholder reference, not InfluxDB runtime dependency.

Authority model:

- Design Specs: normative truth after `/spec-init` and `/spec-design`.
- PostgreSQL/read model: runtime authority for mutable operational state.
- `timeline.jsonl`: append-only audit/export log.
- Photo files and JSON manifests: dataset/export artifacts.
- Agent Chat Bus: working domain communication stream for agents.
- UI Feed: human-facing presentation stream.
- Agno: execution SDK only.
- InfluxDB: future time-series authority after real sensors exist.

## UX / Interaction Flow

Primary MVP flow:

1. System asks the daily check-in question for `tomato_001`.
2. User replies with observation text and uploads one or more photos.
3. User enters pH/EC if measured.
4. System stores photo files, photo catalog records, initial capture manifest snapshots, and timeline events.
5. Vision Observation Agent returns photo quality and visual observation conclusion.
6. Plant State Agent updates probable/unknown/conflict state and compares with history.
7. Hydroponics Advisor checks pH/EC context and risk.
8. Safety Gate blocks risky recommendations when required inputs/approval are missing.
9. Companion Agent produces a short user-facing response with next useful actions.
10. Task & Follow-up Agent creates missing-data, follow-up, or approved action tasks.
11. Outcomes and follow-up evidence are recorded later.

Minimum UI:

- chat;
- photo upload;
- plant card;
- daily check-in;
- manual pH/EC input;
- task list;
- day history;
- photo history;
- recommendations;
- human approval prompt;
- controlled "поразмыслил" spoiler notes for educational explanation.

## Integrations / Dependencies

- Backend: Python + FastAPI.
- Frontend: React / Next.js / PWA.
- AI runtime: Agno SDK for agents/workflows inside the monolith.
- LLM: dialogue and structured outputs.
- Vision model: real or mock at MVP start, preserving the same output contract.
- Storage: PostgreSQL plus local file storage, JSON manifests, and JSONL export.
- Future sensors: InfluxDB or equivalent time-series authority after real sensors exist.
- Future scale: DuckDB/object storage/dataset registry/server sync only after MVP proves the core workflow.

## Edge Cases / Failure Handling

- Missing pH/EC: request measurement; block solution correction recommendations.
- Stale pH/EC for analysis: request a new measurement when the latest pH/EC is older than 24 hours.
- Stale pH/EC for physical action approval: block the action and request a new measurement when the latest pH/EC is older than 2 hours.
- Low-quality or incomplete photo: request a specific photo type, such as `lower_leaf_closeup` under neutral light.
- Photo without `plant_id`: reject or fail validation.
- Photo manifest without existing photo file: fail validation.
- Duplicate `photo_id`: fail validation.
- Agent returns long/unstructured output: reject or adapt to concise `MessageEnvelope`.
- Agent returns `silent`: no Bus event; audit record required.
- UI Feed event accidentally passed to agent context: fail context-filtering tests.
- Safety Gate identifies physical action without approval: block and create pending approval flow.
- User-visible physical-action advice without Safety Gate clearance: block display or replace with safe pending-approval wording.
- Unsafe model output, prompt-injection attempt to bypass Safety Gate, or unavailable Safety Gate: fail closed and do not create an action task.
- Secret or credential detected in output/log/export candidate: redact and fail the export/logging operation.
- Conflicting plant-state evidence: mark status `conflict` rather than confirmed.
- Agent diagnosis without evidence: keep as hypothesis and `can_train_on=false`.
- Dataset item without evidence refs: cannot become trainable.
- `eval` or `holdout` item selected for fine-tuning: reject.
- Local storage over 200 MB: show local storage prompt only; keep `sync.status=local_only`; server/upload sync remains TODO for a later version.

## Acceptance Criteria

- A complete daily flow can run for `tomato_001`: check-in, photo upload, optional pH/EC handling, agent conclusions, safety review, task/follow-up, and timeline entry.
- The daily flow succeeds with fresh pH/EC or with missing/stale pH/EC converted into a clarification/measurement task and Safety Gate block for solution-related actions.
- Every photo has `plant_id`, `photo_id`, file reference, JSON manifest snapshot, `sha256`, and traceable event refs.
- Initial capture and export snapshot manifests are distinguishable and do not act as mutable runtime authority.
- `user_photo.payload.plant_id` is mandatory.
- PostgreSQL is runtime authority for mutable operational state.
- `timeline.jsonl` is append-only and not primary mutable state.
- Photo JSON manifests are generated as export snapshots and are not runtime authority.
- Agent outputs published to Agent Chat Bus use `MessageEnvelope`.
- Agent Chat Bus events use `BusEventEnvelope`.
- UI Feed events use `UIFeedEvent` and are not consumable by agents.
- `ui_spoiler_note` is visible to the user but has `consumable_by_agents=false` and `visible_to_agents=false`.
- `silent` agent decisions do not create Bus messages and do leave audit records.
- Dangerous recommendations are blocked or converted into pending approval tasks.
- No physical action can proceed without fresh data, Safety Gate pass, and human approval.
- MVP action tasks are human-performed task records, not automated device commands.
- High-risk manual interventions such as pruning, transplanting, and root trimming are blocked or converted into pending approval tasks.
- User-visible Companion responses and UI notes cannot display physical-action instructions without Safety Gate clearance.
- Dataset items cannot become trainable unless status, split, confirmation source, and evidence rules are satisfied.
- `gold` examples require human/expert review or batch review approval.
- Core schemas and boundary rules have tests before feature decomposition is considered done.
- First end-to-end demo Definition of Done includes schema tests, backend/API integration tests, and workflow smoke.
- UI/e2e smoke is required when the UI flow exists, but it is not mandatory for the first backend/workflow demo.

## Verification Strategy

- Schema validation tests for `BusEventEnvelope`, `MessageEnvelope`, `UIFeedEvent`, `photo_manifest`, `timeline_event`, agent report, plant state, task, and human review where applicable.
- Tests that Agno Agent/Workflow output cannot enter Agent Chat Bus without runtime decision and domain adapter.
- Tests that Agno Team output, if Team is configured/enabled, passes through the same adapter and does not use `coordinate`.
- Tests that `silent` creates no Bus event/`MessageEnvelope` and leaves audit evidence.
- Tests that workflow events and `step_completed` are not treated as domain facts.
- Photo flow tests for required `plant_id`, unique `photo_id`, existing photo file, JSON manifest, and schema version.
- Photo manifest tests for `manifest_kind=initial_capture|export_snapshot`, snapshot versioning, and no runtime reads from stale export snapshots.
- Timeline tests for append-only behavior and mandatory `payload.plant_id` on `user_photo`.
- Context-filtering tests that UI Feed and `ui_spoiler_note` are not passed to agents.
- Safety tests that dangerous pH/EC/solution/pump/light/dosing commands and high-risk manual interventions require fresh data where relevant, safety check, and approval.
- Safety tests that Companion responses and UI notes cannot display physical-action instructions without Safety Gate clearance.
- Security tests for loopback default binding, explicit authenticated LAN mode, CORS allowlist, upload size/MIME/path validation, path traversal rejection, and secret redaction from logs/timeline/manifests/UI.
- Dataset governance tests for provenance fields, `can_train_on`, split restrictions, confirmation source rules, and `gold` restrictions.
- Workflow smoke test for daily check-in through task/follow-up.
- Backend/API integration tests for first-demo critical endpoints and state transitions.
- UI/e2e smoke test for the critical daily flow once a UI exists.

## Clarifications

### Session 2026-05-27

- Q: What freshness window should apply to pH/EC measurements for analysis and physical action approval? -> A: Analysis up to 24 hours; physical action approval up to 2 hours.
- Q: Should first-demo Safety Gate cover manual interventions such as pruning/transplanting or only pH/EC/dosing/light/pumps/solution actions? -> A: Cover pH/EC, solution, dosing, pumps, light, plus high-risk manual interventions such as pruning, transplanting, and root trimming.
- Q: What Definition of Done should apply to the first end-to-end demo workflow? -> A: Schema tests, backend/API integration tests, and workflow smoke; UI/e2e smoke once a UI flow exists.
- Q: Should dataset governance start with full lifecycle fields or a minimal subset? -> A: Include the full key lifecycle fields immediately, but keep implementation simple and avoid a full dataset registry.

## Unresolved Blockers

- None.
