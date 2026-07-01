---
description: Словарь терминов, сущностей и agreed vocabulary проекта.
status: active
last_updated: 2026-06-30
source_of_truth:
  - .memory-bank/constitution.md
  - .memory-bank/invariants.md
  - .memory-bank/spec-index.md
  - .memory-bank/spec-backbone.md
---
# Glossary

## Product Scope

- `Agro Intellect MVP`: local-first Web App/PWA and backend for a bounded Farm workspace, Plant care workflows, and AI-first agentic system development.
- `MVP v2`: planned bounded scope expansion that allows local Accounts, one local Farm workspace, role-scoped Plant access, multiple Plants, and Companion governance after PRD/spec promotion.
- `tomato_001`: initial canonical Plant for the MVP and expected migration seed into the Farm/Plant model; not a permanent product limit.
- `operator`: legacy shorthand for a human with operational Plant responsibilities; in MVP v2 usually maps to an Engineer or Boss with relevant Plant access.
- `Human Architect`: project owner role responsible for architecture direction and final scope/safety decisions.
- `AI Team Orchestrator`: project owner role coordinating AI development agents through Memory Bank workflows.
- `local-first`: default operating mode where runtime state, photos, manifests, and audit logs remain local unless the user explicitly approves upload/sync.
- `Web App/PWA`: first product surface for daily check-in, uploads, measurements, tasks, approvals, history, and recommendations.
- `MVP`: smallest useful local system for bounded Plant operations; not production SaaS, not broad farm management, and not automated control.

## Accounts, Farm Access, And Admin

- `Account`: local user identity used for login, authorization, attribution, and audit.
- `Farm`: bounded local workspace and data-ownership boundary containing Plants, memberships, access grants, and admin audit.
- `Plant`: farm-managed plant or crop unit; `tomato_001` is the initial Plant until migration details are specified.
- `Boss`: farm owner/admin role for personnel, role, Plant lifecycle, per-Plant access, and admin audit; cannot bypass Safety Gate.
- `Boss Admin Surface`: UI/workflow area where Boss manages personnel, roles, Plants, access, and admin audit.
- `Engineer`: operational role for assigned Plants, responsible for check-ins, photos, measurements, tasks, and action approvals only when granted.
- `Consultant`: advisory/read/comment role for assigned Plant context; no operational authority or binding decision authority by default.
- `FarmMembership`: relationship between an Account and a Farm that carries role and membership status for authorization.
- `PlantAccessGrant`: explicit per-Plant permission grant for an Account or FarmMembership.
- `Plant lifecycle`: creation, active use, archival, restoration, and history retention for a Plant.
- `ActorContext`: application/API boundary context that identifies the acting Account, Farm, role, Plant permissions, and session provenance for authorization.
- `admin audit`: durable trace of personnel, role, Plant lifecycle, access, and other admin changes.
- `role preset`: simple default permission bundle for Boss, Engineer, or Consultant before any narrow per-Plant override.
- `per-Plant access`: authorization model where a human may work only with Plants granted to their Account or membership.
- `local auth/authz baseline`: MVP security direction where local sessions/tokens and permission checks protect every farm/plant data route.

## Process And Memory Bank

- `Memory Bank`: durable project knowledge in `.memory-bank/`; chat context is temporary.
- `MBB`: Memory Bank Bible; rules for Memory Bank structure, links, frontmatter, and source-of-truth discipline.
- `Spec Before Code`: project discipline requiring relevant specs/source-of-truth checks before non-trivial implementation.
- `Docs First`: meaningful work updates Memory Bank before code is considered done.
- `SDD`: spec-driven development route where specs define normative decisions before task decomposition.
- `Design Specs`: normative SDD documents routed by [.memory-bank/spec-index.md](spec-index.md).
- `canonical subject spec`: the single registered path for one cohesive system
  concern, named by subject rather than feature ID and scoped without file-owner metadata.
- `feature composition root`: feature document that preserves product behavior
  and links applicable canonical specs without duplicating their contracts.
- `spec-index`: pure registry for authoritative and planned SDD specs; global
  backbone status lives in `spec-backbone`, and feature design status lives in
  feature frontmatter.
- `Foundation Runtime Substrate`: FT-000 runtime shape for app factory,
  entrypoint, dependency direction, settings/database injection, and smoke route
  mounting.
- `Foundation Smoke API`: substrate-level `/health` and `/ready` contract.
- `Foundation Data Substrate`: FT-000 DB/session/Alembic/runtime-root substrate
  that product features build on without defining product schemas.
- `Foundation Test Harness`: FT-000 test command, smoke targets, fixture
  expectations, and evidence requirements.
- `Evidence Redaction Contract`: rules for redacting Foundation logs, command
  output, tests, and handoff evidence.
- `Foundation Local Runtime Runbook`: local bootstrap, DB init, migration,
  start, smoke, and troubleshooting command path for the verified Foundation.
- `PRD`: product requirements document defining MVP scope, requirements, non-goals, and acceptance criteria.
- `RTM`: requirements traceability matrix linking requirements to epics, features, and verification targets.
- `epic`: C4 L2 product slice grouping related features.
- `feature`: C4 L3 functional slice whose feature-level SDD design is completed inside `/prd-to-tasks FT-<NNN>` before task slicing; `/spec-improve FT-<NNN>` is a repair or advanced refresh route.
- `task record`: schema-backed JSON `TASK-*` work item and the single
  authoritative task-scoped planning/execution/verification handoff.
- `Memory Bank greenfield flow`: canonical route from analysis/brief/PRD/specs to tasks, execute, verify, and sync.

## Architecture And Authority

- `PostgreSQL/read model`: runtime authority for mutable operational state.
- `timeline.jsonl`: append-only audit/export log, not primary mutable state.
- `Timeline Event`: append-only audit/export event record that references
  runtime/artifact authority but cannot mutate or rehydrate it.
- `photo manifest`: immutable JSON artifact next to a photo; either `initial_capture` or `export_snapshot`.
- `initial_capture`: manifest kind created at photo upload/capture time with identity and file metadata.
- `export_snapshot`: manifest kind created later for dataset/export context snapshots.
- `Agent Chat Bus`: domain-owned working event stream for agent-consumable events.
- `UI Feed`: human-facing presentation stream; never agent working context.
- `Agno`: execution SDK for agents/workflows; not source of truth and not Agent Chat Bus.
- `Agno Agent`: Agno execution unit wrapping model, tools, instructions, memory, HITL, and guardrails.
- `Agno Workflow`: Agno execution flow for predictable steps, routers, conditions, loops, or parallel steps.
- `Agno Team`: optional Agno grouping; not required for MVP and never a domain coordinator.
- `coordinate`: forbidden Agno Team mode for MVP domain coordination.
- `route`: allowed Agno Team mode only as a technical router to one executor when justified.
- `broadcast`: allowed Agno Team mode only for independent parallel checks when justified.
- `tasks`: allowed Agno Team mode only with bounded iterations and domain adapter output when justified.
- `step_completed`: Agno workflow event; execution trace only, not a domain fact.
- `Team synthesis`: Agno Team output; execution artifact until adapted through project contracts.
- `domain adapter`: project-owned boundary that turns execution output into validated domain output or audit-only records.
- `source of truth`: artifact authorized to define a specific decision, state, contract, or lifecycle.
- `runtime authority`: current mutable state authority; in MVP this is PostgreSQL/read model.
- `audit/export`: trace and portability layer, not current mutable state authority.
- `MessageEnvelope`: structured publishable agent output after runtime decision handling.
- `BusEventEnvelope`: required wrapper for Agent Chat Bus events.
- `UIFeedEvent`: required wrapper for human-facing UI presentation events;
  never runtime authority or agent working context.
- `source_refs`: references to evidence such as photos, timeline events, measurements, review, follow-up, or sensor windows.
- `InfluxDB`: future time-series authority for real sensor readings; not an MVP runtime dependency.
- `object storage`: future storage option for photos/artifacts after local MVP proves the workflow.
- `DuckDB`: future analytics option, not an MVP runtime dependency.

## Agent Runtime

- `single-competence agent`: agent constrained to one domain responsibility.
- `Competence Boundary`: explicit rule for what an agent may and may not do.
- `Companion Agent`: user dialogue and governance-coordination agent; may manage typed discussion state but does not replace domain specialists, backend rules, or Safety Gate.
- `Vision Observation Agent`: photo-quality and visual-observation agent; observes but does not diagnose or recommend physical actions.
- `Plant State Agent`: state-over-time agent; tracks trends, uncertainty, and conflicts without confirming agent hypotheses alone.
- `Hydroponics Advisor Agent`: hydroponic-parameter advisor; asks for missing critical data and cannot bypass Safety Gate.
- `Task & Follow-up Agent`: task and outcome agent for checks, measurements, approved actions, and 1-3 day follow-up.
- `Safety Gate Agent`: safety classifier/gate for physical-action wording and approval routing.
- `Dataset Governance Agent`: policy agent for dataset lifecycle, split restrictions, evidence, and trainability.
- `Training Data Curator Agent`: delayed dataset selection agent that usually stays silent and acts only with evidence refs.
- `runtime decision`: exactly one of `speak`, `silent`, `clarify`, or `escalate` after an agent invocation.
- `speak`: runtime decision to publish concise working output through `MessageEnvelope`.
- `silent`: decision that creates no `MessageEnvelope` and no Bus publication, but must leave audit evidence.
- `clarify`: runtime decision to publish a short missing-data request.
- `escalate`: runtime decision to publish a Team Signal or Safety Block route.
- `Silent Listener Mode`: agent mode where the agent reads Bus context but does not publish if it does not change the flow.
- `Conclusion / Agent Output`: concise structured agent result that other agents may consume when published.
- `Clarification Request`: short Bus event asking for missing data or a targeted detail.
- `Quoted Detail Reply`: slightly longer reply to a quoted/targeted request; still shorter than UI spoiler notes.
- `Concise-by-Default Protocol`: rule that ordinary agent outputs stay short unless a detail route is explicitly needed.
- `Team Signal`: rare strong working message intended to redirect shared agent flow.
- `Safety Block`: hard stop for physical-action flow until unlock conditions are satisfied.
- `Large-Font Team Message`: visually prominent team-level message reserved for Team Signals or Safety Blocks.
- `Global Flow`: current shared direction of the product workflow, formed by typed Bus events, tasks, safety rules, and valid governance or safety decisions.
- `Context Hygiene`: rule that agents consume only approved domain context, not UI Feed or raw reasoning.
- `ui_spoiler_note`: controlled user-facing explanation in UI Feed with `visible_to_agents=false` and `consumable_by_agents=false`.
- `raw reasoning`: hidden model reasoning; never stored as facts, labels, or agent working context.

## Companion Governance

- `IssueStack`: explicit structured state for findings, gaps, problems, open questions, and disagreements; not hidden LLM memory.
- `current_issue`: one IssueStack item receiving Companion primary attention with a short rationale.
- `CompanionConclusion`: Companion summary that an issue is resolved enough for discussion; not a binding system decision by itself.
- `IssueClosedByCompanion`: event recording Companion closure of a discussion issue; does not authorize backend action.
- `CompanionProposal`: typed human-visible proposal for process direction or decision; not operative until valid approval/rejection.
- `DecisionRecord`: typed binding governance record created from a valid human decision on a CompanionProposal.
- `HumanAttentionNeeded`: typed marker that Companion expects or requires human reaction before a governance path can proceed.
- `governance approval`: human approval/rejection of a CompanionProposal that may create a DecisionRecord; never authorizes physical action.
- `governance decision`: binding DecisionRecord for discussion, workflow, or domain direction within existing backend rules.
- `approved governance summary`: agent-consumable summary derived from an approved DecisionRecord, not from raw proposal discussion.
- `unapproved proposal`: CompanionProposal that remains human-visible only and must not enter agent working context as fact.

## Event And Envelope Fields

- `event_id`: unique event identifier.
- `event_type`: event kind such as `user_photo`, `agent_conclusion`, `task_created`, or `safety_block`.
- `created_at`: event creation timestamp.
- `source_type`: source category such as user, agent, system, task, sync, or safety.
- `source_id`: concrete source identifier.
- `topic`: routing/audit label; not a substitute for canonical IDs.
- `payload`: event-specific structured data.
- `audit_log`: technical trace of adapters, runtime decisions, and checks.
- `consumable_by_agents`: flag saying whether content may enter agent working context.
- `visible_to_agents`: UI Feed visibility flag; `false` for spoiler notes.
- `agent_id`: agent identifier inside `MessageEnvelope`.
- `claim_type`: output type such as observation, hypothesis, recommendation, safety block, task request, clarification, quoted detail, or team signal.
- `confidence`: stated certainty level for an output.
- `requires_human_approval`: flag showing whether a recommendation needs human approval before action.
- `consumable_output`: concise text intended for agent-consumable working context.
- `ui_spoiler_note_ref`: pointer to a UI Feed spoiler note; not permission for agents to consume it.
- `target_agent_id`: intended recipient on a clarification request; not a direct command.

## State And Safety

- `physical action`: plant-system intervention such as pH/EC change, solution change, pump/light/dosing change, pruning, transplanting, or root trimming.
- `Safety Gate`: policy boundary that blocks or routes physical-action advice before user display or task/action creation.
- `Safety Gate approval`: physical-action approval path requiring Safety Gate clearance, fresh data, and authorized human decision; distinct from governance approval.
- `Safety Action Lifecycle`: shared lifecycle from physical-action wording to
  Safety Gate, authorized human approval, human-performed action task, and
  follow-up outcome.
- `human approval`: explicit user approval/rejection for risky physical actions; unlocks only human-performed task tracking in MVP.
- `Human-in-the-loop`: pattern where important plant-impacting decisions require explicit human decision.
- `analysis freshness`: freshness requirement for using evidence in analysis;
  the applicable canonical subject spec defines the exact policy.
- `approval freshness`: freshness requirement for physical-action approval;
  the owning safety spec defines the exact policy.
- `fresh data`: measurement or evidence still inside the relevant freshness window.
- `pending action proposal`: blocked risky recommendation converted into a proposal awaiting approval.
- `pending approval task`: task representing required human decision before action tracking can start.
- `action_task`: approved human-performed checklist/task; never automated device execution in MVP.
- `check_task`: low-risk check/observation task that does not require approval.
- `measurement task`: task requesting missing or stale measurements.
- `follow-up`: later check, usually after 1-3 days, to capture outcome.
- `outcome`: follow-up result such as improved, worsened, unchanged, or no data.
- `confirmed_updated`: value explicitly updated now by human input, measurement, review, or follow-up evidence.
- `confirmed_unchanged`: human confirms the value did not change.
- `assumed_unchanged`: system carried a previous value forward without fresh confirmation.
- `probable`: hypothesis or incomplete-evidence value.
- `unknown`: value is not known.
- `conflict`: evidence contradicts other evidence.
- `Plant State Trust`: shared boundary that keeps observations, hypotheses,
  conflicts, and confirmed Plant state distinct.

## Data And Photo Artifacts

- `plant_id`: canonical Plant identifier; initial accepted Plant is `tomato_001` until multi-Plant migration is specified.
- `photo_catalog`: PostgreSQL/read-model catalog of accepted photo metadata and mutable refs.
- `photo_id`: globally unique photo identifier.
- `captured_at`: timestamp when the photo was captured.
- `photo_type`: controlled MVP photo category such as whole plant, leaf closeup, roots, or problem area.
- `sha256`: checksum for file identity/integrity.
- `photo file`: original local photo binary stored on disk.
- `photo JSON`: manifest/export artifact next to a photo file.
- `plant.json`: file-side plant snapshot/manifest; not primary runtime state.
- `dataset files`: paired photo and JSON artifacts used for future export/evaluation/training workflows.
- `photos/originals`: local folder concept for original photo files and adjacent JSON artifacts.
- `photos/derived`: local folder concept for thumbnails, annotated images, or processed derivatives.
- `sensor_window_ref`: future reference linking an item to a sensor-reading window.
- `sensor_window`: future time window around a photo/observation for sensor context.
- `sensor reading`: time-series measurement such as pH, EC, temperature, humidity, or light after sensors exist.
- `training export`: future artifact assembly from photo files, PostgreSQL snapshots, and later sensor windows.
- `schema_version`: version marker for JSON/schema-governed artifacts.

## Dataset Governance

- `dataset.status`: lifecycle field with values `raw`, `agent_labeled`, `needs_review`, `confirmed`, `rejected`, `gold`, `excluded`.
- `dataset.split`: `train`, `eval`, `holdout`, or null.
- `dataset.curator_decision`: curator field with `selected`, `deferred`, or `rejected`.
- `dataset.confirmation_source`: source of confirmation such as `curator_auto`, human, expert, or batch review.
- `dataset.evidence_refs`: refs supporting a dataset decision.
- `dataset.curator_notes_ref`: pointer to internal curator notes.
- `dataset.corrected`: flag that human/review corrected label or metadata.
- `dataset.follow_up_seen`: flag that follow-up outcome evidence exists.
- `human_review.status`: manual review lifecycle for a data item or label.
- `review_status`: export alias only when needed; not separate runtime authority.
- `curator_auto`: evidence-based curator confirmation source for ordinary train items, never for `gold`.
- `human review`: manual data or label review.
- `batch review`: batch-level review/approval for dataset decisions.
- `expert review`: domain expert review/approval.
- `evidence_refs`: references to follow-up, outcome, sensor window, repeated photo, review, or agreed observation.
- `can_train_on`: trainability flag allowed only by dataset governance rules.
- `gold`: high-quality reviewed example requiring human, expert, or batch review approval.
- `agent_labeled`: data labeled by an agent; not trainable by default.
- `fine-tuning`: future model training path; out of MVP unless evidence and governance gates exist.
- `evaluation`: future quality-check use of holdout/eval data.

## Sync And Deployment

- `sync.status`: mutable runtime sync state field.
- `local_only`: MVP sync status; data is local and no server sync is implied.
- `server_verified`: future sync status forbidden before a real server sync stage exists.
- `lazy sync`: future/lightweight upload prompt behavior; in MVP it is prompt-only.
- `200 MB prompt`: UI prompt shown when local dataset storage exceeds threshold; does not mutate sync status.
- `idempotency key`: future sync identity key, likely `plant_id + photo_id + sha256`.
- `loopback`: default backend binding to local machine only.
- `LAN mode`: explicit network-access mode requiring authentication, authorization, and token/session protection.
- `CORS allowlist`: explicit allowed origins list for API access.
- `secret redaction`: removing `.env`, tokens, API keys, credentials, and auth material from logs and export surfaces.

## Stack Terms

- `FastAPI`: backend framework selected for the MVP.
- `React / Next.js / PWA`: frontend stack selected for the MVP operator surface.
- `Capacitor`: possible future mobile wrapper after Web App/PWA.
- `LLM`: language model used for dialogue and structured outputs.
- `vision model`: real vision-capable model or real vision model integration used for photo observation in the MVP runtime/demo path.
- `test mock`: deterministic or fake dependency used only in automated tests; it is not an acceptable MVP runtime/demo agent path.
- `JSONL`: newline-delimited JSON format used for append-only timeline export.
- `Pydantic`: likely FastAPI schema layer; exact usage belongs to the applicable canonical subject spec and implementation.

## Notes
- Используй этот файл для устранения неоднозначностей в названиях и статусах.
- Глоссарий задаёт короткие meanings. Правила и контракты остаются в specs, states, contracts и runbooks.
