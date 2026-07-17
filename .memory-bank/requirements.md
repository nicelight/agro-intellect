---
description: Требования (REQ-IDs) + traceability matrix (RTM).
status: active
type: requirements
owner: product
last_updated: 2026-07-17
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/constitution.md
  - .memory-bank/invariants.md
  - .memory-bank/user-scenarios.md
  - .memory-bank/domains/core-domain.md
  - .memory-bank/foundation.md
---
# Requirements

## Status model
- Document `status`: `draft|active|deprecated|archived`
- RTM `Lifecycle`: `planned|implemented|verified`

## REQ list

- `REQ-000` Verified executable foundation: project MUST have a verified executable baseline before product feature implementation starts, including task schema/protocol alignment, backend scaffold anchors, Linux Mint local bootstrap, PostgreSQL init, migration baseline, DB readiness, local runtime roots, and redaction baseline.
- `REQ-001` Single local Farm workspace: MVP MUST support exactly one local Farm workspace and keep multi-Farm tenancy out of scope.
- `REQ-002` Local Accounts and sessions: MVP MUST support local Accounts and a local login/session baseline sufficient for authorization and audit attribution.
- `REQ-003` ActorContext authority: every Farm/Plant read, mutation, context-builder path, task, approval, and audit record MUST resolve Account, Farm, role/membership, Plant permissions, and session/auth provenance through ActorContext.
- `REQ-004` Role presets and PlantAccessGrant: MVP MUST support Boss, Engineer, and Consultant role presets plus per-Plant PlantAccessGrant; the only MVP permission override is `plant_approve_actions`.
- `REQ-005` Boss Admin Surface and admin audit: Boss MUST directly create local
  active Accounts with an initial password, manage personnel and roles, the
  Plant list, Plant access, Plant archive/restore, and durable admin audit records; Account,
  membership, and exactly one safe creation audit record MUST commit atomically.
- `REQ-006` Multiple Plants and `tomato_001`: MVP MUST support multiple Plants
  in the local Farm, with `tomato_001` as the initial Plant. Active Boss and
  Engineer memberships MUST be allowed to create Plants; Engineer creation
  MUST atomically create an active creator PlantAccessGrant with
  `plant_approve_actions=false`, giving immediate read/operate authority for
  the new active Plant. Plant archive/restore and PlantAccessGrant management
  remain Boss-only.
- `REQ-007` Plant lifecycle retention: MVP MUST support create, archive, and
  restore; archive is the only removal action, and Plant history, photos,
  timeline audit/export refs, and admin audit remain retained for authorized
  access. Archive/restore MUST preserve PlantAccessGrant records unchanged:
  active grants resume after restore and revoked grants remain revoked.
- `REQ-008` Authorized Plant operations: authorized users MUST select only
  authorized Plants and complete daily check-in with observations and manual
  pH/EC while retaining authorized Plant card/history access.
- `REQ-009` Photo intake and local artifacts: photo intake MUST store local photo files, accepted catalog metadata, `sha256`, initial capture manifest, export-ready refs, and timeline audit refs.
- `REQ-010` Runtime authority and timeline audit: PostgreSQL/read model MUST remain mutable operational state authority unless a later active architecture spec replaces it; `timeline.jsonl` remains append-only audit/export only.
- `REQ-011` Real model-backed product agents: MVP runtime/demo product-agent outputs MUST come from real LLM/model-backed agents or real model-backed adapters over actual scoped Plant data; fake, mock, hardcoded, or stubbed outputs are test-only and do not satisfy MVP runtime/demo acceptance. Runtime MUST support explicit `chatgpt_oauth`, `deepseek`, and `gemini` provider profiles with deploy-time model ids, no hardcoded model default, and no silent cross-provider fallback. DeepSeek/Gemini use native bindings; `chatgpt_oauth` MUST fail closed without a project-approved broker and MUST NOT reuse ChatGPT browser or Codex credentials.
- `REQ-012` Vision observation and Plant state trust: Vision Observation MUST process actual uploaded photo data through a real vision-capable model or real vision integration, and agent hypotheses MUST NOT become confirmed Plant state without human review or follow-up evidence.
- `REQ-013` Agent publication and context hygiene:
  - agent output MUST pass runtime decision, pending MessageEnvelope, project-owned classification, and the applicable guarded downstream boundary;
  - UI Feed, raw chat/UI content, admin notices, and unapproved proposals MUST NOT become agent working context;
  - archived Plants deny state-advancing publication; restore requires current authorization and does not replay denied work;
  - after Plant commit, the system submits one deterministic eight-item introduction batch without rolling back or falsely failing Plant creation on delivery failure;
  - FT-008 MUST reconcile exactly one non-agent-consumable `UIFeedEvent` per introduction for every active Plant; the Plant chat/feed UI renders that event, Agent Chat Bus does not consume it, archive pauses projection, and restore requires current-state reconciliation.
- `REQ-014` Hydroponics Advisor missing-data behavior: advisory output MUST remain cautious, permission-aware, and request missing/stale critical data instead of bypassing Safety Gate or inventing evidence.
- `REQ-015` Safety Gate physical-action routing: physical-action wording MUST be blocked or routed until fresh evidence, Safety Gate pass, authorized human approval, and task/action tracking exist.
- `REQ-016` Human tasks, approval, and follow-up loop: safe check or
  measurement requests MUST create traceable task records; approved physical
  actions MUST create only human-performed `action_task` records, never
  automated device execution; and follow-up outcomes MUST preserve evidence
  and audit refs. Tasks, approvals, and outcomes MUST remain retained and
  non-operative while their Plant is archived, and restore MUST NOT resume
  them without current authorization and owning safety/lifecycle checks.
- `REQ-017` Companion typed governance: Companion MUST use explicit Plant-scoped state for IssueStack, HumanAttentionNeeded, CompanionProposal, CompanionConclusion, and DecisionRecord; parallel pending proposals for the same Plant issue are forbidden. Archived-Plant governance records MUST remain retained but non-operative until a new request passes current owning guards after restore.
- `REQ-018` DecisionRecord authority boundary: DecisionRecord MAY direct Plant-scoped workflow or safe task requests through backend rules but MUST NOT mutate Plant state, create `action_task`, authorize physical action, replace Safety Gate approval, or turn raw chat/proposal content into fact. Any allowed workflow effect MUST respect the current Plant lifecycle and MUST NOT replay automatically after restore.
- `REQ-019` Dataset governance: dataset candidates MUST be non-trainable by default and require evidence refs before any future trainability change.
- `REQ-020` Local privacy, exposure, and storage: MVP data/artifacts MUST remain local/private by default; sync status MUST be `local_only`; secrets/auth material MUST NOT enter logs, timeline, manifests, Bus, UI Feed, screenshots, exports, or agent context; local storage prompt MUST appear over 200 MB without implying upload/server availability.
- `REQ-021` Web App/PWA first demo: first demo MUST include Boss and Engineer paths, `tomato_001`, Plant selector access checks, daily check-in, photo upload, pH/EC, real agent outputs, Vision Observation, Plant State trust statuses, Hydroponics Advisor missing-data behavior, Task & Follow-up behavior, Safety Gate, Companion HumanAttentionNeeded/proposal/decision path, dataset fields, timeline audit/export, and local storage prompt.
- `REQ-022` Consultant advisory scope: Consultant, when present, MUST remain limited to authorized advisory/read/comment context and MUST NOT create domain task/recommendation records, governance approvals by default, or physical-action approvals.

## Out of scope

- Production SaaS, hosted cloud sync as an MVP requirement, billing, subscription boundaries, enterprise identity, email delivery, hosted recovery, or SaaS tenancy.
- Multi-Farm tenancy or multi-Farm membership in MVP.
- Broad commercial farm-management scope.
- Microservices instead of a local modular monolith.
- Automated physical actuation, pumps, dosing, pH/EC correction, light-control commands, autowatering, or autodosing.
- Agno as source of truth, Agent Chat Bus replacement, or domain coordinator.
- Complex RAG, mandatory expert panels, full dataset registry, real fine-tuning, or sensor runtime dependency before real sensors exist.
- Hard delete for Plant removal in MVP.
- Fake, mock, hardcoded, or stubbed product-agent flows as the MVP runtime/demo path.

## Traceability (RTM)
| REQ | Epic | Feature | Test | Lifecycle |
|---|---|---|---|---|
| REQ-000 | Foundation | FT-000 | gate: final Foundation Dev Path build/start/bootstrap/db/migration/test/MB checks | verified |
| REQ-001 | EP-001 | FT-002 | verified: canonical single local Farm workspace via FT-002 bootstrap/API integration; first-Boss setup remains FT-003/first-demo scope | verified |
| REQ-002 | EP-001 | FT-001 | unit: session model; integration: login/session attribution | verified |
| REQ-003 | EP-001, EP-004 | FT-001, FT-002, FT-003, FT-012 | integration: ActorContext on every Farm/Plant route, context builder, task, approval, and outcome mutation | planned |
| REQ-004 | EP-001, EP-004 | FT-001, FT-002, FT-012 | unit: role/permission matrix; integration: PlantAccessGrant filtering and current action-approval authority | planned |
| REQ-005 | EP-001 | FT-003 | implemented: first-Boss bootstrap plus Boss personnel/Plant access/admin audit flow through canonical HTTP boundaries | implemented |
| REQ-006 | EP-001 | FT-002 | integration: multiple Plants, `tomato_001` bootstrap, Boss/Engineer create policy, atomic Engineer creator grant; FT-004 is a non-owning consumer | planned |
| REQ-007 | EP-001, EP-002 | FT-002, FT-005, FT-006 | integration: archive/restore preserves Plant/grants and authorized history/photo/timeline/admin-audit evidence | planned |
| REQ-008 | EP-002 | FT-004, FT-006 | verified: authorized daily check-in with observations/manual pH/EC plus Plant card/history access | verified |
| REQ-009 | EP-002 | FT-005 | verified: photo file/catalog/sha256/manifest/timeline refs plus stable complete catalog continuation | verified |
| REQ-010 | EP-002 | FT-006 | verified: PostgreSQL authority vs append-only timeline audit/export, retained history, and strict cursor behavior | verified |
| REQ-011 | EP-003, EP-004, EP-005, EP-006 | FT-007, FT-009, FT-010, FT-011, FT-012, FT-013, FT-014 | integration: real provider-backed runtime adapter plus every owning product-agent flow; anti-cheat: no fake runtime path | planned |
| REQ-012 | EP-003 | FT-009 | integration: real vision input; unit: Plant trust-state promotion gates | planned |
| REQ-013 | EP-003 | FT-007, FT-008 | verified: pending MessageEnvelope/classification handoff, guarded typed Bus/literal UI publication, archived-Plant deny, restore revalidation, protected feed reads, and anti-cheat agent-context hygiene | verified |
| REQ-014 | EP-003, EP-004 | FT-010, FT-011 | unit: missing/stale data policy; integration: Safety Gate handoff | planned |
| REQ-015 | EP-004 | FT-011, FT-012 | unit: Safety Gate fail-closed policy; integration: current human approval and human action-task authority checks | planned |
| REQ-016 | EP-004 | FT-012 | e2e: check/measurement tasks, approval-to-human-action task, follow-up evidence, and archived-Plant transition guards | planned |
| REQ-017 | EP-005 | FT-013 | unit: proposal supersede/archive state; integration: retained non-operative governance records and DecisionRecord creation | planned |
| REQ-018 | EP-005, EP-004 | FT-013, FT-011, FT-012 | integration: governance approval separated from Safety Gate approval and workflow effects revalidated after restore | planned |
| REQ-019 | EP-006 | FT-014 | unit: trainability default false; integration: evidence refs required | planned |
| REQ-020 | EP-006 | FT-015 | integration: loopback/LAN controls, secret redaction, storage prompt | planned |
| REQ-021 | EP-006 | FT-016 | e2e: first-demo PWA composition over available backend/agent/safety/governance seams plus safety/context checks | planned |
| REQ-022 | EP-001, EP-004, EP-006 | FT-001, FT-012, FT-016 | integration: Consultant read/comment scope and no task mutation, governance approval, or physical-action approval authority | planned |

## Current FT-001 Evidence Note

- TASK-005 through TASK-011 completion evidence covers the FT-001-owned
  portions of REQ-002, REQ-003, REQ-004, REQ-020, and REQ-022, and provides
  identity/session/ActorContext seams consumed by FT-016 for REQ-021.
- TASK-011 independent verification passes, repeated feature-level red-verify
  returns `semantic-pass`, and the full non-environment suite reports
  `105/105`; one PostgreSQL and two `psql`-dependent checks remain an explicit
  environment gap backed by earlier task-scoped evidence.
- REQ-002 is synchronized as `verified`. REQ-003/004/020/022 remain `planned`
  because their complete outcomes also depend on later features or deferred
  cross-feature E2E. REQ-021 remains `planned` under its sole owner
  EP-006/FT-016; FT-001 is an integration provider, not a co-owner.

## Current FT-002 Evidence Note

- TASK-012 through TASK-015 are recorded `done`; TASK-015 evidence adds
  integrated Engineer/Boss API flows, direct BHV-001..004 traceability,
  focused FT-002 `43/43`, full regression `151/151`, independent
  `/verify PASS`, and per-task `/red-verify semantic-pass`.
- REQ-001 is synchronized as `verified` for the FT-002-owned single local Farm
  workspace boundary after feature-level `/red-verify --feature FT-002`
  returned `semantic-pass`.
- REQ-003, REQ-004, REQ-006, and REQ-007 retain `planned` RTM lifecycle.
  REQ-006 is owned by EP-001/FT-002; FT-004 consumes its Plant selection and
  operate authority without co-owning it. REQ-007 now tracks only the shared
  Plant/grant and retained evidence baseline across EP-001/EP-002; downstream
  agent, task/approval/follow-up, and governance archive guards are traced by
  REQ-013, REQ-016, REQ-017, and REQ-018.
- FT-002 is synchronized as `verified` for its owned Farm/Plant lifecycle and
  access boundary. This does not close shared/downstream portions of
  REQ-003/004/006/007.

## Current FT-003 Evidence Note

- TASK-016 and TASK-017 are recorded `done`; TASK-018 implementation evidence
  adds integrated Boss setup, Engineer creation/login, `tomato_001` access
  grant through the canonical Plant API, non-Boss denial, last-Boss guard,
  safe audit, password exclusion, and no-store checks.
- Local TASK-018 gates passed: focused FT-003 `18/18`, EP-001 auth/admin/Farm
  regression `139/139`, and full regression `169/169`.
- REQ-005 is synchronized as `implemented` for the FT-003-owned backend admin
  and audit boundary. It remains short of `verified` until the owner/scheduler
  accepts independent verification and semantic-review evidence.
- REQ-003 and REQ-004 remain `planned` because complete outcomes still depend
  on shared/downstream features. FT-003 supplies Boss/admin backend seams to
  FT-016; REQ-021 remains solely owned by EP-006/FT-016.

## Current FT-004/FT-005/FT-006 Evidence Note

- TASK-019 through TASK-027 are recorded `done`. Repair tasks TASK-025/026/027
  have independent `VERDICT: PASS`, task-level
  `SEMANTIC_VERDICT: semantic-pass`, focused regressions, full `238/238`, and
  owner closure evidence in the authoritative task records.
- Current feature-level reports for FT-004, FT-005, and FT-006 each contain
  exact `SEMANTIC_VERDICT: semantic-pass`; historical failure/concern reports
  remain preserved. The three feature lifecycles are synchronized as
  `verified`.
- Existing TASK-019 through TASK-024 checkpoint waivers remain warnings.
  TASK-025 and TASK-027 also record explicit advisory acceptance of their
  absent exact `HUMAN_CHECKPOINT: done` markers; this sync does not fabricate
  either marker. TASK-026 is T2.
- REQ-009 is synchronized as `verified` for the FT-005-owned local photo
  file/catalog/checksum/manifest/timeline-ref boundary and truthful complete
  catalog continuation.
- REQ-010 is synchronized as `verified` for the FT-006-owned PostgreSQL/read
  model authority, append-only timeline separation, retained-history
  authorization, and strict history cursor boundary, with FT-004 evidence also
  preserving canonical PostgreSQL/timeline measurement agreement.
- FT-006 retains the owner-approved URL-first/KISS best-effort local-path
  policy: ambiguous path/link content may remain visible when exact
  discrimination would require unstable complexity; strict secret/auth
  redaction remains separate and unchanged.
- REQ-008 is synchronized as `verified` for the EP-002-owned authorized
  check-in, observations, manual pH/EC, and Plant card/history outcome.
  Task/approval/follow-up creation and transitions are traced by REQ-016 under
  EP-004; agent/Vision behavior remains with EP-003; first-demo/PWA composition
  remains solely with REQ-021 under EP-006/FT-016.
- REQ-006 ownership is corrected to EP-001/FT-002 with FT-004 as a non-owning
  consumer. REQ-007 retains its existing `planned` lifecycle but now covers
  only the Plant/grant and retained evidence baseline; downstream archive
  guards are traced by REQ-013/016/017/018.
- EP-002 is synchronized as `verified` from its three verified features and
  owned REQ-008/009/010 outcomes. Other REQ lifecycles remain unchanged; this
  decomposition repair does not infer lifecycle promotion for EP-003, EP-004,
  EP-006, or REQ-021.

## Current FT-008 Completion Evidence Note

- `TASK-032-T3-FT-008-W1` is recorded `done` with independent functional
  `VERDICT: PASS` and per-task `SEMANTIC_VERDICT: semantic-pass`. Evidence
  covers one durable canonical batch plus exactly eight non-agent-consumable
  introduction UI rows, atomic failure, idempotent retry, current-state
  restart reconciliation, archive-race denial, restore without replay, and
  unchanged Plant-create semantics.
- The exact `HUMAN_CHECKPOINT: done` marker is absent. Scheduler closure records
  an explicit process-only waiver; this note preserves that warning and does
  not weaken safety, authorization, data integrity, source-of-truth, privacy,
  or scope rules.
- `TASK-033-T3-FT-008-W2` is recorded `done` after one bounded repair, fresh
  independent `VERDICT: PASS`, and per-task
  `SEMANTIC_VERDICT: semantic-pass`. Evidence covers strict Bus/UI identity and
  source unions, atomic guarded safe-information publication, current
  ActorContext/Plant/grant checks, fail-closed persisted Bus reconstruction,
  UI/raw/provider/governance context exclusion, literal candidate data, and
  backend-authorized retained-history feed reads.
- FT-008 and the FT-007/FT-008-owned REQ-013 outcome are synchronized as
  `verified`. This does not satisfy FT-007's deferred live-provider UAT or
  promote REQ-011, FT-009, FT-010, or EP-003.
- REQ-020 remains `planned`: FT-008 verifies only its applicable local/privacy,
  no-secret, and context-exclusion boundary; complete local security, exposure,
  and operator-surface ownership remains downstream with FT-015/FT-016.
- Both FT-008 tasks are T3. Their per-task semantic evidence is the applicable
  semantic basis; no feature-level T2 red gate is claimed or invented.
