---
description: Product Requirements Document.
status: draft
type: prd
clarification_status: complete
constitution_checked: true
last_updated: 2026-08-12
---
# PRD

## Source Inputs

- [project_dossier_v2.md](../project_dossier_v2.md): upstream MVP v2 dossier and detailed product/architecture context.
- [.memory-bank/constitution.md](constitution.md): governing policy for AI-first, low-maintenance, bounded local-first MVP scope.
- [.memory-bank/invariants.md](invariants.md): cross-cutting MUST/NEVER guardrails.
- [.memory-bank/glossary.md](glossary.md): agreed MVP v2 vocabulary.
- Operator decision on 2026-07-28 accepting the KISS outcome for Finding 4
  from [SIMPLIFICATION.md](../SIMPLIFICATION.md): retain the canonical
  eight-agent roster while materializing missing presentation-only
  introductions lazily on authorized active-Plant Feed access.
- Operator decisions on 2026-08-12 recorded in
  [FT-015 clarification](../.protocols/FT-015/clarification.md): storage
  pressure counts only accepted original photo binaries, the threshold is
  strictly over 200 MiB, and acknowledge/dismiss remain transient per-Account
  presentation actions with no durable state.

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
- Fake, mock, or stub product-agent outputs as a production fallback or
  user-visible substitute. Deterministic fake/spy executors remain test-only.

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
- The current code phase MUST implement provider-neutral, strict product-agent
  request/result boundaries over actual scoped Plant data. Closure is based on
  deterministic schema, authorization, media-integrity, failure, redaction,
  timeout, and no-authority evidence through explicit fake/spy executor seams.
- Production composition MUST fail closed when no endpoint is selected and
  MUST NOT use fake, mock, hardcoded, canned, or fallback output.
- Real external-provider integration is deferred until an owner selects an
  OpenAI-compatible endpoint and explicitly defines its provider, model, base
  URL, authentication, egress, and cost constraints. No provider, model, or
  base URL is selected by this PRD.
- Authorized typed Plant context MAY leave the local runtime for the explicitly
  selected provider. Credentials, auth material, raw UI/chat, provider history,
  and hidden reasoning remain forbidden outbound context.
- The canonical Plant agent roster MUST remain the same ordered eight-agent
  roster. Its deterministic introduction text is presentation metadata, not
  model output or evidence that a real model ran.
- Plant creation MUST keep its current commit and `201` response semantics and
  MUST NOT depend on introduction persistence.
- On the first authorized Feed open for an active Plant that is missing current
  roster introductions, the system MUST idempotently materialize only the
  missing presentation `UIFeedEvent` rows. Repeated Feed opens MUST NOT create
  duplicates. Introduction rows MUST remain unavailable to Agent Chat Bus and
  every other agent working-context path.
- Plant creation, process startup, and restore MUST NOT require an introduction
  batch, introduction sink, background scan, durable pending state, or
  reconciliation lifecycle. An archived retained-history Feed read MUST create
  no introduction rows. After restore, missing rows MAY be materialized only by
  a later authorized Feed open while the Plant is active.
- Lazy introduction materialization MUST preserve the current public Feed
  response and cursor schema. If persistence fails, the existing
  `FEED_PERSISTENCE_FAILED` response and a later client retry are sufficient
  recovery; no additional durable recovery mechanism is required.
- Vision Observation Agent MUST load and integrity-check actual uploaded photo
  bytes through its strict provider-neutral media boundary. Current code-phase
  acceptance uses an outbound spy for byte identity; a real image-capable
  endpoint run belongs to the deferred integration milestone.
- Agent-originated product output MUST pass project-owned runtime decision,
  pending MessageEnvelope, project-owned classification, and only then the
  applicable Agent Chat Bus/UI Feed/task/Safety boundary.
- UI Feed MUST remain presentation-only and unavailable as agent working context.
- Safety Gate MUST block or route physical-action wording until fresh data, Safety Gate pass, authorized human approval, and task/action tracking exist.
- Companion governance MUST use explicit typed Plant-scoped state for IssueStack, HumanAttentionNeeded, CompanionProposal, CompanionConclusion, and DecisionRecord.
- CompanionProposal MUST NOT be parallel for the same Plant-scoped issue. When Companion creates a new proposal for the same issue, the previous pending proposal automatically becomes superseded and non-operative.
- DecisionRecord MAY direct Plant-scoped discussion/workflow and safe task requests such as check, measurement, or follow-up tasks through backend rules.
- DecisionRecord MUST NOT change Plant state by itself, create `action_task`, authorize physical action, replace Safety Gate approval, or turn raw chat into a fact.
- Approved governance summary MAY become agent-consumable only as compact typed facts derived from a valid DecisionRecord: decision, decision summary, allowed workflow effect, role/time attribution, source refs, Plant/issue/proposal refs, and explicit `safety_gate_authority=not_granted`.
- Approved governance summary MUST NOT include raw proposal text, raw rationale, raw chat, or UI markdown. Separately, an owning agent-specific provider contract MAY supply authorized typed unapproved governance context as non-authoritative input.
- Dataset governance MUST keep candidates non-trainable by default and require evidence refs before any future trainability change.
- The local storage prompt MUST become eligible only when the Farm-wide sum of
  accepted original photo binary `size_bytes` is strictly greater than
  `209715200` bytes (200 MiB). Each accepted photo MUST be counted once from
  its authoritative Photo Catalog item. Manifests, PostgreSQL storage,
  Timeline, logs, caches, temporary/failed/orphan files, screenshots,
  application assets, derived/export artifacts, and Dataset Candidate refs
  MUST NOT contribute to this threshold.
- For the authenticated Account, both `acknowledge` and `dismiss` MUST close
  only the currently rendered storage prompt. Neither action creates durable
  backend state, upload approval, server availability, or sync-status change;
  the prompt MAY reappear on the next page or fresh status load while the
  threshold remains exceeded. Account/auth changes MUST discard this
  transient presentation state, and one Account's action MUST NOT affect
  another Account.

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
   On the first authorized Feed open for an active Plant with missing canonical
   roster introductions, the system idempotently adds only those missing
   presentation rows before returning the normal Feed view.
4. System starts a daily check-in.
5. User records observations, uploads a photo, and/or enters pH/EC measurements.
6. Backend stores photo file, catalog row, initial capture manifest, runtime state, and timeline audit.
7. Validated agent-consumable events are published through the Agent Chat Bus.
8. Provider-neutral product-agent adapters process actual scoped Plant data
   through strict schemas; deterministic code-phase flows use test-only
   fake/spy executors, while unconfigured production composition fails closed.
9. UI Feed shows human-facing messages, cards, prompts, tasks, approvals, and
   local storage status without becoming agent context. When accepted original
   photo bytes exceed 200 MiB, the current Account may acknowledge or dismiss
   the storage prompt for the current rendered instance; a later page or fresh
   status load may show it again while pressure remains above the threshold.
10. Safety Gate blocks or routes physical-action wording.
11. Boss or an Engineer with `plant_approve_actions` may approve a physical-action proposal only after fresh data and Safety Gate pass.
12. Approved physical action creates only a human-performed `action_task`, never automated execution.
13. Task and follow-up outcomes preserve evidence and audit trail.

First code-phase demo MUST include Boss and at least one Engineer path,
provider-neutral product-agent boundaries, real uploaded
photo/measurement/observation data, Plant State trust
statuses, Hydroponics Advisor missing-data behavior, Task & Follow-up Agent behavior,
Safety Gate behavior, and visible Companion HumanAttentionNeeded plus proposal/decision
path. Consultant remains in MVP v2 product scope, but Consultant UI/path may be deferred
from first demo.

## Integrations / Dependencies

- Backend: Python, FastAPI, Pydantic/schema validation, PostgreSQL/read model, local filesystem for photos/artifacts, JSONL timeline export.
- Frontend: Svelte 5/SvelteKit Web App/PWA with role-aware UI, Plant selector,
  chat/feed surface, task/approval cards, and minimal Boss Admin Surface.
- AI runtime: project-owned provider-neutral adapters and strict schemas; Agno
  may remain an execution dependency but is not integration evidence.
- Future model integration: one explicitly selected OpenAI-compatible endpoint
  behind the existing adapter boundary. Provider, model, base URL,
  authentication, egress, and cost policy are intentionally deferred.
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
- Sending governance content to a model does not approve it, turn it into a fact, or grant DecisionRecord, Plant-state, Task, Safety, or publication authority.
- Admin UI notices, UI markdown, UI cards, raw chat, and spoiler notes MUST NOT become agent facts.
- Archived retained-history Feed reads MUST NOT materialize missing roster
  introductions. Restore MUST NOT materialize them by itself; only a later
  authorized active-Plant Feed open may do so.
- A lazy introduction persistence failure MUST use the existing
  `FEED_PERSISTENCE_FAILED` response. A later authorized Feed retry MAY complete
  the idempotent materialization without a background repair lifecycle.
- Exactly `209715200` accepted original photo bytes MUST NOT make the storage
  prompt eligible; eligibility starts only above that value.
- Manifest, database, Timeline, log, cache, temporary/failed/orphan,
  screenshot, application, derived/export, and Dataset Candidate-ref growth
  MUST NOT make the photo-storage prompt eligible.
- Storage-prompt acknowledge/dismiss MUST remain transient to the current
  rendered instance and authenticated Account. It MUST NOT persist a
  preference, cooldown, storage episode, growth delta, Timeline event, upload
  approval, or sync mutation, and MUST NOT affect another Account.
- Local storage warnings MUST NOT imply upload or server availability.
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
- Current code-phase agent behavior is proven through strict deterministic
  fake/spy executor tests over actual scoped Plant data; production has no
  fake/canned fallback and fails closed without a selected endpoint. Real
  endpoint behavior is not claimed by this acceptance criterion.
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
- UI Feed is not consumed by agents; authorized typed governance context may be supplied only through an owning agent-specific provider contract and remains non-authoritative.
- The canonical ordered eight-agent roster remains visible through
  presentation-only introductions. Missing introduction rows are created
  idempotently on the first authorized active-Plant Feed open, repeated opens
  do not duplicate them, archived retained-history reads and restore create
  none, and a later authorized active Feed open after restore may fill them.
- Plant create commit/`201` and the public Feed response/cursor schema remain
  unchanged. Lazy persistence failure uses `FEED_PERSISTENCE_FAILED`, and retry
  is sufficient recovery without a batch, sink, startup scan, or durable
  reconciliation lifecycle.
- Physical-action wording is blocked or routed until fresh data, Safety Gate pass, and authorized human approval exist.
- Governance DecisionRecord remains separate from Safety Gate approval.
- DecisionRecord can route Plant-scoped workflow or safe check/measurement/follow-up task requests, but cannot mutate Plant state or unlock physical actions.
- Creating a new CompanionProposal for the same Plant issue supersedes the previous pending proposal; only the current proposal can be approved/rejected.
- After valid DecisionRecord, Agent Chat Bus consumers receive compact approved governance summary facts and refs. This approved Bus fact is separate from typed governance input supplied directly by an owning agent-specific provider contract.
- Dataset items are non-trainable by default.
- The local storage prompt is absent at or below `209715200` accepted original
  photo bytes and appears above that threshold without server/upload
  implication. Non-photo storage and duplicate refs do not affect eligibility.
- For each Account, acknowledge and dismiss close only the current prompt,
  persist no backend state, leave `sync.status=local_only`, may reappear after
  a fresh page/status load, and do not affect another Account.

## Verification Strategy

- Constitution check: confirm PRD remains bounded local-first MVP and does not introduce production SaaS, cloud sync, enterprise identity, automated actuation, or broad farm-management scope.
- Requirements decomposition readiness: verify all high-impact `NEEDS CLARIFICATION` items are resolved before `/prd-to-features`.
- Authorization tests later MUST cover Boss, Engineer, Consultant, missing PlantAccessGrant, archived Plant visibility, and context-builder filtering.
- Cross-feature archive tests later MUST cover open task, approval, follow-up,
  agent publication, and Companion proposal records, including no transition
  while archived and no automatic resume after restore.
- Safety tests later MUST cover stale data, missing approval authority, failed Safety Gate, governance-vs-safety approval separation, and action-task unlock semantics.
- UI/context hygiene tests later MUST prove UI Feed, spoiler notes, raw chat, and admin notices do not enter agent working context, while any agent-specific governance input matches its strict typed allowlist and remains non-authoritative.
- Roster-introduction tests later MUST prove lazy missing-row materialization on
  authorized active-Plant Feed open, idempotent retries, no writes from
  archived retained-history reads or restore, unchanged Plant-create and public
  Feed/cursor contracts, `FEED_PERSISTENCE_FAILED` recovery by retry, and no
  introduction path into agent context.
- Storage/export tests later MUST cover photo file/catalog/manifest/timeline refs and secret redaction.
- Storage-prompt tests later MUST cover below/exact/above `209715200` photo-byte
  boundaries, one-count-per-accepted-photo aggregation, exclusion of every
  non-photo/non-authoritative storage category named by the Functional
  Requirements, per-Account transient interaction isolation, reappearance
  after fresh load, and zero backend/sync mutation from acknowledge/dismiss.
- Agent runtime tests MUST keep fake/spy executors explicitly test-only and
  prove that production composition has no fake/canned/fallback path. A future
  integration milestone separately verifies a selected endpoint over real
  image/response, error, timeout, redaction, and cost scenarios.

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
- Q: What approved governance summary becomes agent-consumable? -> A: The Bus fact remains compact typed data derived from a valid DecisionRecord: decision id, Plant id, issue id, proposal id/version, decision, decision summary, allowed workflow effect, decider role, decided_at, source refs, and explicit `safety_gate_authority=not_granted`. This Bus projection is distinct from authorized typed governance input supplied directly by an owning agent-specific provider contract.
- Q: Is the first-demo boundary sufficient, and can any agent/model behavior be stubbed in MVP? -> A: Historical answer, superseded on 2026-07-19, required live LLM-backed acceptance. The active decision still forbids fake/mock/hardcoded/canned production output, but current code-phase closure uses explicit test fake/spy seams and unbound fail-closed production. Sensor runtime remains out of MVP until real sensors exist.

### Session 2026-07-11

- Q: Which provider families must Agent Runtime support? -> A: Historical
  answer, superseded on 2026-07-19, listed `chatgpt_oauth`, `deepseek`, and
  `gemini`. No provider family is currently required or targeted; Gemini is not
  planned. The active boundary is provider-neutral, production is unbound and
  fail-closed, and a future owner selection will define one OpenAI-compatible
  endpoint without reusing ChatGPT/Codex credentials.
- Q: May Plant context be sent to external providers? -> A: Yes, but only the
  typed authorized payload for the explicitly selected provider; credentials,
  raw UI/chat, provider history, and hidden reasoning remain excluded.
- Q: When do Plant agents start and appear in chat? -> A: Historical answer
  superseded on 2026-07-28. The active decision retains the canonical roster
  but materializes missing presentation-only introduction rows lazily through
  authorized active-Plant Feed access.

### Session 2026-07-18

- Q: May the current Companion model receive the selected open Issue summary
  before approval? -> A: Yes, as one narrow exception. The authorized explicit
  `existing_issue` request may include only the exact persisted
  `summary_text`; a `new_issue` request includes none. The field remains
  untrusted and non-authoritative and grants no fact, DecisionRecord,
  Plant-state, Task, Safety, Bus/general agent-context, or publication
  authority. The broader blanket prohibition remains until a later explicit
  documentation/product-policy change.

### Session 2026-07-19

- Q: Does current code-phase closure require a provider, credentials, egress,
  network access, or a non-skipped live smoke? -> A: No. Those inputs are not
  blockers or closure evidence for the current code phase.
- Q: Which provider is planned now? -> A: None. Gemini is not planned. Runtime
  contracts stay provider-neutral and point toward a future explicitly
  selected OpenAI-compatible endpoint without selecting provider, model, or
  base URL now.
- Q: Where is real integration accepted? -> A: One separate future integration
  milestone in the Agent Runtime provider runbook/testing concern covers real
  image, real response, errors, timeouts, redaction, and cost. Until that
  milestone is run, no real-provider integration is claimed.

### Session 2026-07-28

- Q: What is the accepted KISS outcome for roster introductions from
  `SIMPLIFICATION.md` Finding 4? -> A: Keep the canonical ordered eight-agent
  roster and its deterministic introduction metadata, but treat introductions
  solely as non-agent-consumable presentation. Missing `UIFeedEvent` rows are
  lazily and idempotently materialized only when an authorized user opens the
  Feed for an active Plant. Archived retained-history reads create nothing;
  restore creates nothing, and materialization is allowed only on a later
  authorized active-Plant Feed open.
- Q: What remains unchanged and how is failure recovered? -> A: Plant create
  commit and `201` semantics stay unchanged, as do the public Feed response and
  cursor schema. The product requires no post-create batch/sink, durable pending
  state, startup scan, or reconciliation lifecycle. Existing
  `FEED_PERSISTENCE_FAILED` behavior plus a later authorized Feed retry is
  sufficient recovery.

### Session 2026-08-12

- Q: What storage contributes to the local prompt threshold? -> A: Only the
  original binary of each accepted photo, counted once from authoritative
  Photo Catalog `size_bytes`. Manifests, PostgreSQL, Timeline, logs, caches,
  temporary/failed/orphan files, screenshots, application assets,
  derived/export artifacts, and Dataset Candidate refs are excluded.
- Q: What is the exact threshold? -> A: The Farm-wide total must be strictly
  greater than `209715200` bytes (200 MiB). Equality does not show the prompt.
- Q: How are acknowledge and dismiss scoped? -> A: Apply KISS: for the current
  authenticated Account, both close only the currently rendered prompt and
  persist nothing. A page or fresh status load may show it again while pressure
  remains above threshold; Account/auth changes discard transient state, and
  one Account's action never affects another. Neither action implies upload,
  server availability, or a change from `sync.status=local_only`.
- Constitution check: passed. The decision narrows an existing local warning,
  adds no sync lifecycle or infrastructure, preserves private-by-default and
  `local_only` constraints, and follows the low-maintenance KISS principle.

## Unresolved Blockers

None.
