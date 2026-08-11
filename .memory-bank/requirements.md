---
description: Требования (REQ-IDs) + traceability matrix (RTM).
status: active
type: requirements
owner: product
last_updated: 2026-08-11
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
- `REQ-011` Provider-neutral product-agent runtime: the current code phase MUST
  implement strict competence-specific request/result schemas, test-only
  fake/spy executor seams, pre/post-I/O authorization, redaction, timeout/error
  handling, no-fallback/no-fake production behavior, and no direct domain,
  Safety, task, or actuation authority from model output. Production MUST fail
  closed while no endpoint is selected. Real integration is deferred to one
  future milestone after explicit selection of an OpenAI-compatible endpoint;
  no provider, model, base URL, credential, egress, or live smoke is required
  for current code-phase closure.
- `REQ-012` Vision observation and Plant state trust: Vision Observation MUST
  load actual uploaded photo bytes through a strict integrity-checked
  provider-neutral media boundary, and agent hypotheses MUST NOT become
  confirmed Plant state without human review or follow-up evidence. A future
  selected endpoint must verify real image processing separately.
- `REQ-013` Agent publication and context hygiene:
  - agent output MUST pass runtime decision, pending MessageEnvelope, project-owned classification, and the applicable guarded downstream boundary;
  - UI Feed, raw chat/UI content, and admin notices MUST NOT become agent working context;
  - authorized typed governance content MAY be supplied by an owning agent-specific provider contract, but it remains untrusted context and grants no DecisionRecord, Plant-state, Task, Safety, or publication authority;
  - archived Plants deny state-advancing publication; restore requires current authorization and does not replay denied work;
  - the canonical ordered eight-agent roster and deterministic introduction metadata MUST remain available without making Plant creation or its `201` response depend on introduction persistence;
  - on an authorized Feed open for an active Plant, FT-008 MUST idempotently materialize only missing non-agent-consumable introduction `UIFeedEvent` rows; repeated opens MUST NOT duplicate them, and neither Agent Chat Bus nor any agent-context path may consume them;
  - Plant creation, process startup, restore, and archived retained-history Feed reads MUST NOT run an introduction batch, sink, background scan, durable pending state, or reconciliation lifecycle;
  - the public Feed response/cursor schema MUST remain unchanged; `FEED_PERSISTENCE_FAILED` plus a later authorized active-Plant Feed retry is sufficient recovery.
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

## Durable requirement clarifications

- For REQ-017 and REQ-018, the registered Companion `existing_issue` request
  may include persisted open-Issue `summary_text` as typed, untrusted,
  non-authoritative context. It grants no fact, Task, Safety, publication, or
  DecisionRecord authority.
- Governance-driven ordinary Task creation uses the canonical closed source
  union and caller-owned unit-of-work phase. Classification-only Companion
  output remains held for governance and does not dispatch an ordinary Task.
- REQ-010 and REQ-020 retain the URL-first, best-effort local-path policy:
  ambiguous path/link content may remain visible when reliable discrimination
  would require unstable complexity; strict secret and auth redaction remains
  mandatory.

## Out of scope

- Production SaaS, hosted cloud sync as an MVP requirement, billing, subscription boundaries, enterprise identity, email delivery, hosted recovery, or SaaS tenancy.
- Multi-Farm tenancy or multi-Farm membership in MVP.
- Broad commercial farm-management scope.
- Microservices instead of a local modular monolith.
- Automated physical actuation, pumps, dosing, pH/EC correction, light-control commands, autowatering, or autodosing.
- Agno as source of truth, Agent Chat Bus replacement, or domain coordinator.
- Complex RAG, mandatory expert panels, full dataset registry, real fine-tuning, or sensor runtime dependency before real sensors exist.
- Hard delete for Plant removal in MVP.
- Fake, mock, hardcoded, or stubbed product-agent outputs as a production
  fallback; deterministic fake/spy executors are test-only.

## Traceability (RTM)
| REQ | Epic | Feature | Test | Lifecycle |
|---|---|---|---|---|
| REQ-000 | Foundation | FT-000 | gate: final Foundation Dev Path build/start/bootstrap/db/migration/test/MB checks | verified |
| REQ-001 | EP-001 | FT-002 | verified: canonical single local Farm workspace via FT-002 bootstrap/API integration; first-Boss setup remains FT-003/first-demo scope | verified |
| REQ-002 | EP-001 | FT-001 | unit: session model; integration: login/session attribution | verified |
| REQ-003 | EP-001, EP-004, EP-005 | FT-001, FT-002, FT-003, FT-012, FT-013 | integration: ActorContext on every Farm/Plant route, context builder, task, approval, outcome, and Companion governance mutation | planned |
| REQ-004 | EP-001, EP-004, EP-005 | FT-001, FT-002, FT-012, FT-013 | unit: role/permission matrix; integration: PlantAccessGrant filtering plus current action-approval and governance authority | planned |
| REQ-005 | EP-001 | FT-003 | implemented: first-Boss bootstrap plus Boss personnel/Plant access/admin audit flow through canonical HTTP boundaries | implemented |
| REQ-006 | EP-001 | FT-002 | integration: multiple Plants, `tomato_001` bootstrap, Boss/Engineer create policy, atomic Engineer creator grant; FT-004 is a non-owning consumer | planned |
| REQ-007 | EP-001, EP-002 | FT-002, FT-005, FT-006 | integration: archive/restore preserves Plant/grants and authorized history/photo/timeline/admin-audit evidence | planned |
| REQ-008 | EP-002 | FT-004, FT-006 | verified: authorized daily check-in with observations/manual pH/EC plus Plant card/history access | verified |
| REQ-009 | EP-002 | FT-005 | verified: photo file/catalog/sha256/manifest/timeline refs plus stable complete catalog continuation | verified |
| REQ-010 | EP-002 | FT-006 | verified: PostgreSQL authority vs append-only timeline audit/export, retained history, and strict cursor behavior | verified |
| REQ-011 | EP-003, EP-004, EP-005, EP-006 | FT-007, FT-009, FT-010, FT-011, FT-012, FT-013, FT-014 | deterministic integration: strict provider-neutral schemas, fake/spy timeout/error paths, pre/post-I/O authorization, redaction, no production fake/fallback, and zero direct authority; future milestone: selected OpenAI-compatible endpoint. FT-014 full implementation adds the advisory-only Dataset Governance Agent and Training Data Curator runtimes; the remaining FT-007/FT-009/FT-010/FT-011/FT-012 mapped features keep this row `planned` | planned |
| REQ-012 | EP-003 | FT-009 | integration: actual photo-byte integrity through outbound spy; unit: Plant trust-state promotion gates; future milestone: selected endpoint real-image run | planned |
| REQ-013 | EP-003 | FT-007, FT-008 | verified: pending MessageEnvelope/classification, guarded Bus/UI publication, protected Feed reads, context isolation, and TASK-046 lazy missing-introduction materialization on authorized active-Plant Feed open with no create/startup/restore/archived-read writes, unchanged Feed/cursor schema, and retry after `FEED_PERSISTENCE_FAILED` | verified |
| REQ-014 | EP-003, EP-004 | FT-010, FT-011 | verified FT-010 missing/stale-data policy plus completed FT-011 deterministic classification and Safety routing through pending human approval; lifecycle awaits explicit owner reconciliation | planned |
| REQ-015 | EP-004 | FT-011, FT-012 | unit: Safety Gate fail-closed policy; integration: current human approval and human action-task authority checks | planned |
| REQ-016 | EP-004 | FT-012 | e2e: check/measurement tasks, approval-to-human-action task, follow-up evidence, and archived-Plant transition guards | planned |
| REQ-017 | EP-005 | FT-013 | verified: focus/attention/proposal lifecycle, derived conclusion, retained non-operative governance records, DecisionRecord creation, and explicit provider-neutral Companion proposal through deterministic fake/spy executors; real-provider tests remain a separate explicit future request | verified |
| REQ-018 | EP-005, EP-004 | FT-013, FT-011, FT-012 | integration: closed atomic governance effects separated from Safety Gate/action authority and revalidated after restore | planned |
| REQ-019 | EP-006 | FT-014 | unit: trainability default false; integration: evidence refs required. FT-014 fully implemented (candidate aggregate + sole creation seam, transition/trainability authority, photo/check-in/measurement/outcome candidate wiring, advisory Dataset Governance Agent, follow-up evidence association, Outcome composition, Training Data Curator with atomic selected gate); feature-level verification awaits the applicable feature/owner gate | implemented |
| REQ-020 | EP-006 | FT-015 | integration: loopback/LAN controls, secret redaction, storage prompt | planned |
| REQ-021 | EP-006 | FT-016 | e2e: first-demo PWA composition over available backend/agent/safety/governance seams plus safety/context checks | planned |
| REQ-022 | EP-001, EP-004, EP-005, EP-006 | FT-001, FT-012, FT-013, FT-016 | integration: Consultant read/comment scope and no task mutation, governance approval, Companion invocation, or physical-action approval authority | planned |
