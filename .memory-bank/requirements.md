---
description: Требования (REQ-IDs) + traceability matrix (RTM).
status: active
type: requirements
owner: product
last_updated: 2026-07-09
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
  restore; archive is the only removal action and
  history/photos/tasks/outcomes/timeline/admin audit remain retained for
  authorized access. Archive/restore MUST preserve PlantAccessGrant records
  unchanged: active grants resume after restore and revoked grants remain
  revoked. Open Plant-scoped operational/governance records MUST remain
  unchanged and non-operative while archived; restore MUST NOT resume or replay
  them without current authorization and owning lifecycle checks.
- `REQ-008` Authorized Plant operations: authorized users MUST select only authorized Plants and complete daily check-in, observations, manual pH/EC, Plant card/history, tasks, approvals, and follow-up workflows.
- `REQ-009` Photo intake and local artifacts: photo intake MUST store local photo files, accepted catalog metadata, `sha256`, initial capture manifest, export-ready refs, and timeline audit refs.
- `REQ-010` Runtime authority and timeline audit: PostgreSQL/read model MUST remain mutable operational state authority unless a later active architecture spec replaces it; `timeline.jsonl` remains append-only audit/export only.
- `REQ-011` Real model-backed product agents: MVP runtime/demo product-agent outputs MUST come from real LLM/model-backed agents or real model-backed adapters over actual scoped Plant data; fake, mock, hardcoded, or stubbed outputs are test-only and do not satisfy MVP runtime/demo acceptance.
- `REQ-012` Vision observation and Plant state trust: Vision Observation MUST process actual uploaded photo data through a real vision-capable model or real vision integration, and agent hypotheses MUST NOT become confirmed Plant state without human review or follow-up evidence.
- `REQ-013` Agent publication and context hygiene: agent-originated output MUST pass project-owned runtime decision, MessageEnvelope, Agent Chat Bus, and UI Feed boundaries; UI Feed, raw chat, UI markdown, spoiler notes, admin notices, and unapproved proposals MUST NOT become agent working context.
- `REQ-014` Hydroponics Advisor missing-data behavior: advisory output MUST remain cautious, permission-aware, and request missing/stale critical data instead of bypassing Safety Gate or inventing evidence.
- `REQ-015` Safety Gate physical-action routing: physical-action wording MUST be blocked or routed until fresh evidence, Safety Gate pass, authorized human approval, and task/action tracking exist.
- `REQ-016` Human approval and follow-up loop: approved physical actions MUST create only human-performed `action_task` records, never automated device execution, and follow-up outcomes MUST preserve evidence and audit trail.
- `REQ-017` Companion typed governance: Companion MUST use explicit Plant-scoped state for IssueStack, HumanAttentionNeeded, CompanionProposal, CompanionConclusion, and DecisionRecord; parallel pending proposals for the same Plant issue are forbidden.
- `REQ-018` DecisionRecord authority boundary: DecisionRecord MAY direct Plant-scoped workflow or safe task requests through backend rules but MUST NOT mutate Plant state, create `action_task`, authorize physical action, replace Safety Gate approval, or turn raw chat/proposal content into fact.
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
| REQ-003 | EP-001 | FT-001, FT-002, FT-003 | integration: ActorContext on every Farm/Plant route and context builder | planned |
| REQ-004 | EP-001 | FT-001, FT-002 | unit: role/permission matrix; integration: PlantAccessGrant filtering | planned |
| REQ-005 | EP-001 | FT-003 | e2e: Boss personnel/role/Plant/access/admin audit flow | planned |
| REQ-006 | EP-001, EP-002 | FT-002, FT-004 | integration: multiple Plants, `tomato_001` bootstrap, Boss/Engineer create policy, atomic Engineer creator grant | planned |
| REQ-007 | EP-001, EP-002, EP-003, EP-004, EP-005 | FT-002, FT-006, FT-007, FT-008, FT-011, FT-012, FT-013 | integration: archive/restore retention, unchanged grants/records, denied transitions/publication while archived, current-guard revalidation after restore, and authorized history | planned |
| REQ-008 | EP-002, EP-004 | FT-004, FT-012 | e2e: Engineer authorized daily workflow and follow-up | planned |
| REQ-009 | EP-002 | FT-005 | integration: photo file/catalog/sha256/manifest/timeline refs | planned |
| REQ-010 | EP-002 | FT-006 | integration: PostgreSQL authority vs append-only timeline audit/export | planned |
| REQ-011 | EP-003 | FT-007 | integration: real model-backed runtime adapter; anti-cheat: no fake runtime path | planned |
| REQ-012 | EP-003 | FT-009 | integration: real vision input; unit: Plant trust-state promotion gates | planned |
| REQ-013 | EP-003 | FT-007, FT-008 | contract: MessageEnvelope/Bus/UI Feed filters; anti-cheat context hygiene | planned |
| REQ-014 | EP-003, EP-004 | FT-010, FT-011 | unit: missing/stale data policy; integration: Safety Gate handoff | planned |
| REQ-015 | EP-004 | FT-011 | unit: Safety Gate fail-closed policy; integration: approval authority checks | planned |
| REQ-016 | EP-004 | FT-012 | e2e: approval creates human-performed action task and follow-up outcome | planned |
| REQ-017 | EP-005 | FT-013 | unit: proposal supersede state; integration: DecisionRecord creation | planned |
| REQ-018 | EP-005, EP-004 | FT-013, FT-011, FT-012 | integration: governance approval separated from Safety Gate approval | planned |
| REQ-019 | EP-006 | FT-014 | unit: trainability default false; integration: evidence refs required | planned |
| REQ-020 | EP-006 | FT-015 | integration: loopback/LAN controls, secret redaction, storage prompt | planned |
| REQ-021 | EP-006, EP-001, EP-002, EP-003, EP-004, EP-005 | FT-016, FT-001, FT-004, FT-005, FT-007, FT-009, FT-010, FT-011, FT-012, FT-013, FT-014, FT-015 | e2e: first-demo happy path plus safety/context checks | planned |
| REQ-022 | EP-001, EP-006 | FT-001, FT-016 | integration: Consultant read/comment scope and no approval/action authority | planned |

## Current FT-001 Evidence Note

- TASK-005 through TASK-011 completion evidence covers the FT-001-owned
  portions of REQ-002, REQ-003, REQ-004, REQ-020, REQ-021, and REQ-022.
- TASK-011 independent verification passes, repeated feature-level red-verify
  returns `semantic-pass`, and the full non-environment suite reports
  `105/105`; one PostgreSQL and two `psql`-dependent checks remain an explicit
  environment gap backed by earlier task-scoped evidence.
- REQ-002 is synchronized as `verified`. REQ-003/004/020/021/022 remain
  `planned` because their complete outcomes also depend on later features or
  deferred cross-feature E2E.

## Current FT-002 Evidence Note

- TASK-012 through TASK-015 are recorded `done`; TASK-015 evidence adds
  integrated Engineer/Boss API flows, direct BHV-001..004 traceability,
  focused FT-002 `43/43`, full regression `151/151`, independent
  `/verify PASS`, and per-task `/red-verify semantic-pass`.
- REQ-001 is synchronized as `verified` for the FT-002-owned single local Farm
  workspace boundary after feature-level `/red-verify --feature FT-002`
  returned `semantic-pass`.
- REQ-003, REQ-004, REQ-006, and REQ-007 retain `planned` RTM lifecycle because
  each has shared or downstream acceptance outside FT-002: FT-001/FT-003
  ActorContext/admin scope, FT-004 Plant operations, retained-history
  payloads, task/approval/governance/archive integrations, UI/PWA, and first
  demo flows remain with their owning features.
- FT-002 is synchronized as `verified` for its owned Farm/Plant lifecycle and
  access boundary. This does not close shared/downstream portions of
  REQ-003/004/006/007.
