---
description: Требования (REQ-IDs) + traceability matrix (RTM).
status: active
type: requirements
owner: product
last_updated: 2026-07-20
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
| REQ-011 | EP-003, EP-004, EP-005, EP-006 | FT-007, FT-009, FT-010, FT-011, FT-012, FT-013, FT-014 | deterministic integration: strict provider-neutral schemas, fake/spy timeout/error paths, pre/post-I/O authorization, redaction, no production fake/fallback, and zero direct authority; future milestone: selected OpenAI-compatible endpoint | planned |
| REQ-012 | EP-003 | FT-009 | integration: actual photo-byte integrity through outbound spy; unit: Plant trust-state promotion gates; future milestone: selected endpoint real-image run | planned |
| REQ-013 | EP-003 | FT-007, FT-008 | verified: pending MessageEnvelope/classification handoff, guarded typed Bus/literal UI publication, archived-Plant deny, restore revalidation, protected feed reads, and anti-cheat agent-context hygiene | verified |
| REQ-014 | EP-003, EP-004 | FT-010, FT-011 | verified FT-010 missing/stale-data policy plus completed FT-011 deterministic classification and Safety routing through pending human approval; lifecycle awaits explicit owner reconciliation | planned |
| REQ-015 | EP-004 | FT-011, FT-012 | unit: Safety Gate fail-closed policy; integration: current human approval and human action-task authority checks | planned |
| REQ-016 | EP-004 | FT-012 | e2e: check/measurement tasks, approval-to-human-action task, follow-up evidence, and archived-Plant transition guards | planned |
| REQ-017 | EP-005 | FT-013 | unit: focus/attention/proposal lifecycle and derived conclusion; integration: retained non-operative governance records, DecisionRecord creation, and explicit real Companion proposal | planned |
| REQ-018 | EP-005, EP-004 | FT-013, FT-011, FT-012 | integration: closed atomic governance effects separated from Safety Gate/action authority and revalidated after restore | planned |
| REQ-019 | EP-006 | FT-014 | unit: trainability default false; integration: evidence refs required | planned |
| REQ-020 | EP-006 | FT-015 | integration: loopback/LAN controls, secret redaction, storage prompt | planned |
| REQ-021 | EP-006 | FT-016 | e2e: first-demo PWA composition over available backend/agent/safety/governance seams plus safety/context checks | planned |
| REQ-022 | EP-001, EP-004, EP-005, EP-006 | FT-001, FT-012, FT-013, FT-016 | integration: Consultant read/comment scope and no task mutation, governance approval, Companion invocation, or physical-action approval authority | planned |

## Current FT-013 Planning Note

- FT-013 shared repair is complete for the single ordinary-task source union,
  its exact pending-v1 to flushed-approved-v2 caller-UoW phase, and the
  classification-only Companion governance hold. Existing-access authority,
  lifecycle, closed effects, and atomic rollback decisions remain accepted.
- Deterministic feature-local repairs are complete: open/unfocused conclusion
  and focus behavior, exact derived `ApprovedGovernanceSummaryV1`, reachable
  nested Task error translation, HTTP/ref/read rules, evidence selection,
  distinct-run serialization, and provider-neutral Companion+Safety-classifier
  composition are closed in registered subject specs.
- The shared provider-policy decision is closed: the blanket prohibition on
  sending models unapproved governance content is removed. Registered
  agent-specific requests may carry their authorized typed governance subsets
  without granting fact or downstream authority semantics. The current
  Companion `existing_issue` request includes persisted open-Issue
  `summary_text`.
- `TASK-041-T3-FT-013-W1`, `TASK-042-T3-FT-013-W2`, and
  `TASK-043-T3-FT-013-W3` are indexed `planned` behind the existing planned
  FT-012 chain; TASK-042 now also depends directly on TASK-040 to serialize the
  shared Task Follow-Up package. Global and feature design are complete; run a
  fresh `/review-tasks-plan FT-013` before execution selection. No
  implementation, real-provider result, or RTM lifecycle promotion is claimed.

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
  `verified`. This does not satisfy the deferred future provider-integration milestone or
  promote REQ-011, FT-009, FT-010, or EP-003.
- REQ-020 remains `planned`: FT-008 verifies only its applicable local/privacy,
  no-secret, and context-exclusion boundary; complete local security, exposure,
  and operator-surface ownership remains downstream with FT-015/FT-016.
- Both FT-008 tasks are T3. Their per-task semantic evidence is the applicable
  semantic basis; no feature-level T2 red gate is claimed or invented.

## Current FT-009 W2 Boundary Evidence Note

- `TASK-034-T3-FT-009-W1` is recorded `done` through the scheduler's
  evidence-preserving administrative closure under the owner-accepted
  provider-neutral deterministic code-phase acceptance. Its historical
  live-provider blocker remains preserved and does not become a fabricated
  verification pass.
- `TASK-035-T3-FT-009-W2` is recorded `done` using only current ATTEMPT 04
  implementation `PASS`, independent functional `VERDICT: PASS`, and separate
  `SEMANTIC_VERDICT: semantic-pass` evidence. The bounded PostgreSQL matrix
  includes authoritative retained-session photo-ownership refresh, canonical
  zero-write provenance failures, classified-only trust persistence, explicit
  conflict/human review, strict cursor handling, and no downstream authority.
- The W2 checkpoint marker and real provider/image result remain absent and are
  preserved as advisory/deferred evidence gaps. No credential, egress, network,
  or live-provider claim is made.
- RTM lifecycles remain unchanged. REQ-003 and REQ-011 remain `planned` because
  their complete cross-feature/future-provider outcomes are open; REQ-012
  remains `planned` because its future selected-endpoint real-image verification
  is explicitly deferred. REQ-010 and the FT-007/FT-008-owned REQ-013 remain
  `verified` on their existing owning evidence; FT-009 contributes guarded
  consumer evidence without re-owning or reopening those outcomes.
- FT-009 and EP-003 lifecycle values remain `planned` pending explicit owner
  feature/epic decisions. At the FT-009 boundary,
  `TASK-036-T3-FT-010-W1` was scheduler-recorded `planned` after dependency
  recovery; its later completion is recorded in the FT-010 note below.

## Current FT-010 W1 Boundary Evidence Note

- `TASK-036-T3-FT-010-W1` is scheduler-recorded `done` using only current
  ATTEMPT 02 implementation `PASS`, independent functional `VERDICT: PASS`,
  separate `SEMANTIC_VERDICT: semantic-pass`, and immutable closure evidence.
  ATTEMPT 01 is retained as history and is not mixed into current closure.
- Current deterministic evidence covers canonical Advisor roster composition,
  strict provider-neutral request/result boundaries, authorized PostgreSQL
  input assembly, independent closed-interval pH/EC freshness, exact
  project-owned missing-data requests, pending-only handoff, post-I/O denial,
  redaction, unbound-production failure, and zero direct downstream authority.
- RTM lifecycles remain unchanged. REQ-014 remains `planned` because FT-011 W2
  Safety decision/projection remains open after W1 classification completion.
  REQ-003 and REQ-011 remain
  `planned` for their broader cross-feature/future-milestone outcomes;
  FT-010 contributes guarded consumer evidence without re-owning REQ-008 or
  the FT-007/FT-008-owned verified REQ-013 outcome.
- The absent human-checkpoint marker remains an accepted advisory T3 warning.
  Provider/model/base URL/credential/egress/network/live-smoke evidence remains
  deferred and unverified; no such result is claimed.
- FT-010 and EP-003 lifecycle values remain `planned` pending explicit owner
  feature/epic decisions. The later FT-011 note records the scheduler-owned
  TASK-037 completion; this earlier FT-010 boundary did not promote or select
  it.

## Current FT-011 W1/W2 Boundary Evidence Note

- `TASK-037-T3-FT-011-W1` is scheduler-recorded `done` using only current
  ATTEMPT 03 implementation `PASS`, independent functional `VERDICT: PASS`,
  separate `SEMANTIC_VERDICT: semantic-pass`, and immutable closure evidence.
  ATTEMPT 01 and ATTEMPT 02 remain preserved failed history.
- `TASK-038-T3-FT-011-W2` is scheduler-recorded `done` using only current
  ATTEMPT 01 implementation `PASS`, independent functional `VERDICT: PASS`,
  separate `SEMANTIC_VERDICT: semantic-pass`, and immutable closure evidence.
- Current provider-neutral PostgreSQL evidence covers strict backend-owned
  classification, first-write-wins persistence, exact action/authority/
  evidence routing, atomic immutable decision plus inert UI projection,
  fail-closed archive/revoke races, restore without replay, redaction, and zero
  downstream authority. The product migration head is
  `ft011_safety_action_decisions` directly after
  `ft011_safety_classifications` and `ft009_plant_state`.
- RTM lifecycles remain unchanged. REQ-003, REQ-011, REQ-014, REQ-015, and
  REQ-018 remain `planned` pending explicit owner RTM decisions and because
  their broader cross-feature, human-approval/task, governance, or future
  provider-milestone outcomes remain open.
  REQ-008 and the FT-007/FT-008-owned REQ-013 outcome remain `verified`; FT-011
  consumes those seams without reopening or re-owning them.
- FT-011 and EP-004 lifecycle values remain `planned`. The later FT-012 note
  records scheduler-owned TASK-039 completion; this earlier FT-011 boundary
  did not promote or select it.
- No provider/model/base URL/Gemini/credential/egress/network/live-smoke result
  is claimed. The absent task checkpoint markers remain owner-accepted
  advisory process gaps and do not amend canonical policy.

## Current FT-012 W1 Boundary Evidence Note

- `TASK-039-T3-FT-012-W1` is scheduler-recorded `done` using only current
  ATTEMPT 03 implementation `PASS`, independent functional `VERDICT: PASS`,
  separate `SEMANTIC_VERDICT: semantic-pass`, and immutable closure evidence.
  ATTEMPT 01 and ATTEMPT 02 remain preserved failed history and are not mixed
  into current closure.
- Current provider-neutral PostgreSQL/HTTP evidence covers immutable
  classified-message `consumed|denied` dispositions, current ActorContext,
  Plant, grant, Safety-decision, version, expiry, and pH/EC guards; atomic
  approval/action Task, action-completion/+48-hour follow-up, and
  Outcome/follow-up completion; exact retries/conflicts, archive/no-replay,
  rollback, redaction, branch-exact Timeline events, and zero device or
  Plant-state authority.
- The product migration head is `ft012_task_approval_outcomes` directly after
  `ft011_safety_action_decisions`. All eight exact-head compatibility
  consumers pass; current selected evidence also records `22` focused,
  `210` current-guard/Safety, `47` migration-compatibility, and `489`
  full-deterministic passes with `2` intentional `real_model` deselections.
- RTM lifecycles remain unchanged. REQ-003, REQ-004, REQ-015, REQ-016,
  REQ-018, and REQ-022 remain `planned` because their broader cross-feature,
  provider-runtime, governance, Consultant, or deferred E2E outcomes remain
  open. REQ-010 and the FT-007/FT-008-owned REQ-013 outcome remain `verified`;
  FT-012 W1 consumes those authority/publication seams without re-owning them.
- FT-012 and EP-004 lifecycle values remain `planned` pending the open W2 and
  explicit owner feature/epic decisions. TASK-040 remains scheduler-owned
  `in_progress` after ATTEMPT 01 verification FAIL and ATTEMPT 02
  implementation BLOCKED; this sync makes no retry/resume selection, ATTEMPT
  03 consumption, lifecycle transition, unblock, or block decision and does
  not touch TASK-041/TASK-042/TASK-043.
- No provider/model/base URL/Gemini/credential/egress/network/live-smoke result
  was required, checked, or claimed. The absent human checkpoint remains a
  scheduler-accepted advisory T3 process gap.
