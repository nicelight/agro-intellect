---
description: Product Requirements Document.
status: draft
type: prd
clarification_status: complete
constitution_checked: true
last_updated: 2026-07-06
---
# PRD

## Source Inputs

- [project_dossier_v2.md](../project_dossier_v2.md): upstream MVP v2 dossier and detailed product/architecture context.
- [.memory-bank/constitution.md](constitution.md): governing policy for AI-first, low-maintenance, bounded local-first MVP scope.
- [.memory-bank/invariants.md](invariants.md): cross-cutting MUST/NEVER guardrails.
- [.memory-bank/glossary.md](glossary.md): agreed MVP v2 vocabulary.

## Product Summary

Agro Intellect MVP v2 is a local-first Farm workspace and AI-first agentic development
training ground for safe, traceable Plant operations. The MVP starts with one local
Farm, local Accounts, Boss/Engineer/Consultant role presets, multiple Plants, and
`tomato_001` as the initial Plant.

The product is a Web App/PWA backed by a local modular monolith. It lets authorized
humans perform daily Plant care workflows, upload photos, record pH/EC measurements,
receive cautious agent-assisted outputs, handle Safety Gate prompts, manage tasks and
follow-up outcomes, and preserve evidence for future dataset governance.

Companion governance is included in MVP v2 as explicit typed state and human decision
flow. Companion may coordinate discussion and proposals, but it is not hidden authority,
does not replace backend rules, and cannot authorize physical actions.

## Goals

- Provide a useful local Farm workspace for bounded Plant operations.
- Support one local Farm, local Accounts, role-scoped Plant access, and multiple Plants.
- Migrate `tomato_001` into the Farm/Plant model as the initial Plant.
- Give Boss a minimal admin surface for personnel, roles, Plant archive/restore, Plant access, and admin audit, while allowing Boss and Engineer to create Plants.
- Let Boss and Engineer complete the first authorized Plant workflow end to end.
- Keep every Farm/Plant workflow actor-scoped through ActorContext and backend authorization.
- Preserve strict authority boundaries between runtime state, audit/export, UI presentation, agent context, governance decisions, and physical-action approval.
- Exercise AI-first architecture patterns: single-competence product agents, Agent Chat Bus boundaries, UI Feed isolation, Safety Gate, task/follow-up loop, and dataset evidence hygiene.

## Non-goals

- Production SaaS or hosted cloud sync as an MVP requirement.
- Billing, subscription boundaries, enterprise identity, email delivery, hosted account recovery, or SaaS tenancy.
- Multi-Farm tenancy or multi-Farm membership in MVP.
- Broad commercial farm-management scope.
- Microservices instead of a local modular monolith.
- Automated physical actuation, pumps, dosing, pH/EC correction, light-control commands, autowatering, or autodosing.
- Agno as source of truth, Agent Chat Bus replacement, or domain coordinator.
- Complex RAG, mandatory expert panels, full dataset registry, real fine-tuning, or sensor runtime dependency before real sensors exist.
- Hard delete for Plant removal in MVP.
- Fake, mock, or stub product-agent flows as the MVP runtime/demo path.

## Users / Actors

- `Boss`: first local Account and Farm owner/admin. Boss manages Accounts, role presets, Plant archive/restore, PlantAccessGrant records, and admin audit, and may create Plants. Boss can approve Safety Gate physical-action proposals for Farm Plants, but cannot bypass fresh data, Safety Gate pass, or backend approval rules.
- `Engineer`: operational user who may create a Plant in the single Farm and otherwise operates only on granted Plants. Engineer performs check-ins, uploads photos, records pH/EC and observations, manages allowed tasks/follow-up, sees recommendations, and may approve physical-action proposals only when granted `plant_approve_actions` for that Plant.
- `Consultant`: advisory/read/comment user for granted Plant context. Consultant may participate in discussion and give advice, but does not create domain task/recommendation records, does not approve Companion governance decisions by default, and never approves physical actions in MVP.
- Project owner / AI-first development operator: uses the product to validate Memory Bank workflow, source-of-truth boundaries, product-agent architecture, and safety governance.

## Functional Requirements

- The system MUST support exactly one local Farm workspace in MVP.
- The system MUST support local Accounts and a local login/session baseline sufficient for authorization and audit attribution.
- The system MUST support Boss, Engineer, and Consultant role presets.
- The system MUST support FarmMembership and ActorContext for every Farm/Plant read, mutation, context-builder path, task, approval, and audit record.
- The system MUST support multiple Plants inside the local Farm, with `tomato_001` as the initial Plant.
- Active Boss and Engineer memberships MUST be allowed to create Plants. An
  Engineer-created Plant and an active creator PlantAccessGrant with
  `plant_approve_actions=false` MUST commit atomically so the creator can read
  and operate the Plant immediately; failed creation MUST persist neither
  record.
- The system MUST support Plant create, archive, and restore. Archive is the only MVP removal action; history, photos, tasks, outcomes, timeline audit, and admin audit remain retained and accessible to authorized roles.
- Plant archive/restore MUST preserve PlantAccessGrant records unchanged.
  Active grants are non-operative while archived and resume after restore;
  revoked grants remain revoked.
- Plant archive MAY proceed with open tasks, approvals, follow-ups, agent work,
  or Companion governance records. Archive MUST retain those records unchanged
  while making every state-advancing command/publication non-operative; restore
  MUST NOT replay or resume work without current authorization and owning
  freshness, safety, version, and governance checks.
- The system MUST support PlantAccessGrant for per-Plant visibility and work authorization.
- The system MUST limit MVP permission overrides to `plant_approve_actions`; other MVP permissions come from Boss/Engineer/Consultant role presets plus PlantAccessGrant.
- Boss Admin Surface MUST support direct local Account creation with an initial
  password, personnel list, role assignment, Plant list, Plant archive/restore,
  Plant access management, durable admin audit records, and minimal admin audit
  view. Account, membership, and one safe creation audit record are atomic.
- Authorized users MUST be able to select only authorized Plants.
- Daily Plant operations MUST support check-in, observations, photo upload, manual pH/EC, Plant card/history, cautious agent-assisted outputs, tasks, approvals, and follow-up outcomes.
- Photo intake MUST store local photo files, accepted catalog metadata, `sha256`, initial capture manifest, export-ready refs, and timeline audit refs.
- Product agents MUST operate with single-competence boundaries and permission-aware context.
- MVP product agents MUST run as real LLM-backed agents or real model-backed adapters over actual Plant data entered or uploaded by users.
- MVP MUST NOT satisfy agent acceptance criteria with fake, mock, hardcoded, or stubbed agent outputs.
- Vision Observation Agent MUST process actual uploaded photo data through a real vision-capable model or real vision model integration; it MUST NOT be replaced by a mock/fake adapter in MVP.
- Agent-originated product output MUST pass project-owned runtime decision, MessageEnvelope, Agent Chat Bus, and UI Feed boundaries as applicable.
- UI Feed MUST remain presentation-only and unavailable as agent working context.
- Safety Gate MUST block or route physical-action wording until fresh data, Safety Gate pass, authorized human approval, and task/action tracking exist.
- Companion governance MUST use explicit typed Plant-scoped state for IssueStack, HumanAttentionNeeded, CompanionProposal, CompanionConclusion, and DecisionRecord.
- CompanionProposal MUST NOT be parallel for the same Plant-scoped issue. When Companion creates a new proposal for the same issue, the previous pending proposal automatically becomes superseded and non-operative.
- DecisionRecord MAY direct Plant-scoped discussion/workflow and safe task requests such as check, measurement, or follow-up tasks through backend rules.
- DecisionRecord MUST NOT change Plant state by itself, create `action_task`, authorize physical action, replace Safety Gate approval, or turn raw chat into a fact.
- Approved governance summary MAY become agent-consumable only as compact typed facts derived from a valid DecisionRecord: decision, decision summary, allowed workflow effect, role/time attribution, source refs, Plant/issue/proposal refs, and explicit `safety_gate_authority=not_granted`.
- Approved governance summary MUST NOT include raw proposal text, raw rationale, raw chat, UI markdown, or unapproved discussion content.
- Dataset governance MUST keep candidates non-trainable by default and require evidence refs before any future trainability change.
- Local storage prompt MUST appear when local dataset/photo storage exceeds 200 MB and MUST NOT imply upload or server availability.

## Non-functional Requirements

- The MVP MUST remain local-first and private by default.
- Default exposure boundary is loopback. LAN mode MAY exist only when explicitly enabled and protected by authentication, authorization, session/token protection, and CORS/origin controls.
- MVP sync status MUST be `local_only`; `server_verified` and server upload semantics are forbidden until a later server-sync stage exists.
- Backend authorization MUST enforce every Farm/Plant route and context builder; frontend visibility is presentation only.
- PostgreSQL/read model remains runtime authority for mutable operational state unless a later active architecture spec replaces it.
- `timeline.jsonl` remains append-only audit/export, not mutable runtime authority.
- Photo files and manifests are local artifacts, not mutable runtime authority.
- Sessions, tokens, credentials, `.env` values, API keys, and auth material MUST NOT enter logs, timeline, manifests, Bus, UI Feed, screenshots, exports, or agent context.
- The MVP MUST preserve KISS and avoid speculative enterprise abstractions.

## Data / Domain Model

The PRD-level domain model includes:

- `Account`: local user identity for login, authorization, attribution, and audit.
- `Farm`: single local workspace and data-ownership boundary.
- `FarmMembership`: Account-to-Farm relationship with role preset and membership status.
- `ActorContext`: application/API boundary context containing Account, Farm, role/membership, Plant permissions, and session/auth provenance.
- `Plant`: Farm-managed Plant or crop unit. `tomato_001` is the initial Plant.
- `PlantAccessGrant`: explicit per-Plant access and authorization grant.
- `AdminAuditRecord`: durable record for Account, role, Plant lifecycle, membership, and access changes.
- `PhotoCatalogItem`: accepted photo metadata and refs, backed by local photo file and manifest artifacts.
- `TimelineEvent`: append-only audit/export event.
- `BusEventEnvelope`, `MessageEnvelope`, and `UIFeedEvent`: high-level contract areas for agent working context and human-facing presentation.
- `Task`, `Approval`, and `Outcome`: operational loop records for checks, measurements, approved human-performed actions, and follow-up.
- `IssueStack`, `CompanionProposal`, `CompanionConclusion`, `HumanAttentionNeeded`, and `DecisionRecord`: Companion governance records scoped to a Plant in MVP.
- Dataset governance fields: lifecycle status, evidence refs, confirmation source, split, and `can_train_on`.

Detailed schemas, payload fields, state machines, and event matrices belong to
the applicable canonical subject specs, not to this PRD.

## UX / Interaction Flow

First working flow:

1. User logs in or opens a local session.
2. System resolves Account, Farm, role preset, PlantAccessGrant, and ActorContext.
3. User selects an authorized Plant, initially `tomato_001`.
4. System starts a daily check-in.
5. User records observations, uploads a photo, and/or enters pH/EC measurements.
6. Backend stores photo file, catalog row, initial capture manifest, runtime state, and timeline audit.
7. Validated agent-consumable events are published through the Agent Chat Bus.
8. Real LLM/model-backed product agents process actual scoped Plant data and produce concise, permission-aware outputs or remain silent.
9. UI Feed shows human-facing messages, cards, prompts, tasks, approvals, and local storage status without becoming agent context.
10. Safety Gate blocks or routes physical-action wording.
11. Boss or an Engineer with `plant_approve_actions` may approve a physical-action proposal only after fresh data and Safety Gate pass.
12. Approved physical action creates only a human-performed `action_task`, never automated execution.
13. Task and follow-up outcomes preserve evidence and audit trail.

First demo MUST include Boss and at least one Engineer path, real LLM/model-backed
product agents, real uploaded photo/measurement/observation data, Plant State trust
statuses, Hydroponics Advisor missing-data behavior, Task & Follow-up Agent behavior,
Safety Gate behavior, and visible Companion HumanAttentionNeeded plus proposal/decision
path. Consultant remains in MVP v2 product scope, but Consultant UI/path may be deferred
from first demo.

## Integrations / Dependencies

- Backend: Python, FastAPI, Pydantic/schema validation, PostgreSQL/read model, local filesystem for photos/artifacts, JSONL timeline export.
- Frontend: Web App/PWA with role-aware UI, Plant selector, chat/feed surface, task/approval cards, and minimal Boss Admin Surface.
- AI runtime: Agno SDK as execution layer only, real LLM-backed product agents, real vision-capable model or real vision model integration for photos, and project-owned domain adapters.
- Future/non-MVP options: InfluxDB, object storage, DuckDB, Capacitor wrapper, server sync/cloud deployment, full dataset registry, and real fine-tuning.

## Edge Cases / Failure Handling

- Unauthorized users MUST NOT see or mutate unauthorized Plants, photos, measurements, tasks, approvals, admin audit, or agent context.
- Consultant, disabled membership, and unauthorized-role Plant creation MUST
  fail before persistence. Engineer Plant creation MUST NOT grant Plant
  archive/restore or PlantAccessGrant management authority.
- Archived Plants MUST disappear from normal operational flows but remain retained for authorized history/audit/export access.
- Archive/restore MUST NOT create, activate, revoke, replace, or otherwise
  mutate a PlantAccessGrant.
- Archive MUST NOT automatically complete, cancel, delete, execute, approve,
  reject, supersede, publish, or otherwise transition an open Plant-scoped
  record. Restore removes only the archive deny and cannot bypass current
  guards.
- Physical-action advice MUST fail closed when pH/EC or required evidence is stale/missing, Safety Gate fails, or actor approval authority is missing.
- Governance approval MUST NOT be treated as Safety Gate approval.
- Superseded CompanionProposal records MUST NOT be approvable and MUST NOT become agent facts.
- DecisionRecord MUST NOT be treated as Plant-state evidence or action approval by itself.
- Raw CompanionProposal content, rationale, discussion history, and UI projection MUST NOT become agent-consumable even after approval.
- Admin UI notices, UI markdown, UI cards, raw chat, unapproved Companion proposals, and spoiler notes MUST NOT become agent facts.
- Local storage warnings MUST allow acknowledge/dismiss and MUST NOT imply upload/server availability.
- LAN mode, if enabled, MUST add exposure controls and MUST NOT weaken local auth/authz.
- Agent output MUST NOT promote hypotheses to confirmed Plant state without human review or follow-up evidence.
- Dataset candidates MUST remain non-trainable until dataset governance rules allow otherwise.

## Acceptance Criteria

- Boss can create or use one local Farm workspace, directly create at least one
  active Engineer Account, and grant Plant access.
- Boss and an active Engineer can create a Plant. Engineer creation atomically
  creates an active creator grant with `plant_approve_actions=false`; the
  Engineer can then read, select, and operate the Plant but still cannot
  archive/restore it or manage access.
- Boss and Engineer can complete the first authorized Plant workflow on `tomato_001`.
- First demo agent behavior is produced by real LLM/model-backed agents over actual scoped Plant data, not fake, mock, hardcoded, or stubbed outputs.
- Engineer sees only assigned Plants and cannot approve physical actions without `plant_approve_actions`.
- Consultant, when present, is limited to authorized advisory/read/comment context.
- Every Farm/Plant route and agent context builder can identify Account, Farm, role preset, Plant permission, and session provenance.
- Plant archive/restore works without hard deletion and retains authorized history/audit.
- Existing grant identity, status, and `plant_approve_actions` values remain
  unchanged across archive/restore; active grants regain effect only after
  restore.
- Open operational/governance records remain unchanged and cannot transition
  or publish while archived; after restore they advance only through a new
  request that passes all current guards.
- Photo upload produces a local file, catalog row, `sha256`, initial capture manifest, and audit/export refs.
- UI Feed and unapproved proposal content are not consumed by agents.
- Physical-action wording is blocked or routed until fresh data, Safety Gate pass, and authorized human approval exist.
- Governance DecisionRecord remains separate from Safety Gate approval.
- DecisionRecord can route Plant-scoped workflow or safe check/measurement/follow-up task requests, but cannot mutate Plant state or unlock physical actions.
- Creating a new CompanionProposal for the same Plant issue supersedes the previous pending proposal; only the current proposal can be approved/rejected.
- After valid DecisionRecord, agents can receive only compact approved governance summary facts and refs, not raw proposal text, rationale, UI markdown, or chat discussion.
- Dataset items are non-trainable by default.
- Local storage prompt appears at the 200 MB threshold without server/upload implication.

## Verification Strategy

- Constitution check: confirm PRD remains bounded local-first MVP and does not introduce production SaaS, cloud sync, enterprise identity, automated actuation, or broad farm-management scope.
- Requirements decomposition readiness: verify all high-impact `NEEDS CLARIFICATION` items are resolved before `/prd`.
- Authorization tests later MUST cover Boss, Engineer, Consultant, missing PlantAccessGrant, archived Plant visibility, and context-builder filtering.
- Cross-feature archive tests later MUST cover open task, approval, follow-up,
  agent publication, and Companion proposal records, including no transition
  while archived and no automatic resume after restore.
- Safety tests later MUST cover stale data, missing approval authority, failed Safety Gate, governance-vs-safety approval separation, and action-task unlock semantics.
- UI/context hygiene tests later MUST prove UI Feed, spoiler notes, raw chat, admin notices, and unapproved proposals do not enter agent working context.
- Storage/export tests later MUST cover photo file/catalog/manifest/timeline refs and secret redaction.
- Agent runtime tests later MUST distinguish real LLM/model-backed MVP flows from test-only mocks; mocks may be used only in tests, not as the MVP runtime/demo path.

## Clarifications

### Session 2026-06-02

- Q: How should MVP deployment boundary be fixed? -> A: Loopback is the default and first-demo boundary. LAN mode may exist only as explicitly enabled MVP capability with auth/session/CORS controls; LAN is not required for the first demo.
- Q: How should MVP permission model be fixed? -> A: Use Boss/Engineer/Consultant role presets plus PlantAccessGrant. The only MVP per-permission override is `plant_approve_actions`.
- Q: Who can approve Safety Gate physical-action proposals? -> A: Boss can approve for Farm Plants. Engineer can approve only with per-Plant `plant_approve_actions`. Consultant never approves. Approval still requires fresh data and Safety Gate pass.
- Q: What can Consultant do in MVP? -> A: Consultant is read/comment/advice only in granted Plant context and does not create domain task/recommendation records or approvals.
- Q: What are Plant removal semantics? -> A: Use KISS archive/restore only. No hard delete in MVP. Retain history, audit, photos, tasks, outcomes, and evidence for authorized access.
- Q: What is the MVP `IssueStack` scope? -> A: `IssueStack` is scoped to a Plant. Farm-level issues and separate Farm-level chat are deferred beyond MVP PRD.
- Q: What may a `DecisionRecord` control in MVP? -> A: DecisionRecord may direct Plant-scoped discussion/workflow and safe task requests such as check, measurement, or follow-up tasks through backend rules. It must not change Plant state by itself, create `action_task`, authorize physical action, replace Safety Gate approval, or turn raw chat into a fact.
- Q: What is the high-level CompanionProposal supersede/expiry policy? -> A: No parallel proposals for the same Plant-scoped issue. When Companion creates a new proposal for the same issue, the previous pending proposal automatically becomes superseded and non-operative. No time-based expiry is required in PRD.
- Q: What approved governance summary becomes agent-consumable? -> A: Only compact typed facts derived from a valid DecisionRecord: decision id, Plant id, issue id, proposal id/version, decision, decision summary, allowed workflow effect, decider role, decided_at, source refs, and explicit `safety_gate_authority=not_granted`. Raw proposal text, raw rationale, UI markdown, raw chat, and unapproved discussion content remain non-consumable.
- Q: Is the first-demo boundary sufficient, and can any agent/model behavior be stubbed in MVP? -> A: MVP must use real LLM-backed agents or real model-backed adapters over actual Plant data entered or uploaded by users. Fake, mock, hardcoded, or stubbed agent outputs are not acceptable as the MVP runtime/demo path. Sensor runtime remains out of MVP until real sensors exist.

## Unresolved Blockers

None.
