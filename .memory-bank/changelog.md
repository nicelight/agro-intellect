---
description: Лог изменений Memory Bank.
status: active
---
# Changelog

## [2026-07-13] FT-008 human checkpoint confirmation
- Recorded the user's confirmation of `HUMAN_CHECKPOINT: done` for TASK-032
  and TASK-033 after the completed results were checked.
- Replaced the temporary scheduler waiver state in the authoritative task
  cards; historical verification and review reports remain unchanged.

## [2026-07-13] Wave W2 — FT-008 guarded publication and context isolation
- Reconciled the scheduler-written `TASK-033-T3-FT-008-W2` `done` decision
  after one bounded repair, fresh independent functional PASS, and per-task
  semantic-pass evidence.
- Recorded strict Bus/UI value-object validation, atomic guarded
  safe-information publication, current ActorContext/Plant/grant enforcement,
  fail-closed persisted Bus reconstruction, presentation/raw/provider/
  governance exclusion from agent context, literal candidate data, and the
  protected retained-history Plant feed API.
- Synchronized FT-008 and REQ-013 as `verified`; EP-003, REQ-011, and REQ-020
  remain `planned`, and FT-009/FT-010 plus FT-015/FT-016 retain their existing
  downstream ownership. No frontend rendering, Safety/task, governance,
  dataset, provider-UAT, or mutable Plant-authority outcome is claimed.
- Both T3 FT-008 checkpoints were subsequently confirmed by the user; no
  feature-level T2 red gate applies to this T3-only feature.
- Confirmed the authoritative indexed queue contains 34 tasks, all `done`.
  Final `/review-tasks-plan FT-008` remains a separately delegated scheduler
  gate and was not run by this sync.

## [2026-07-12] Wave W1 — FT-008 durable introduction reconciliation
- Reconciled the scheduler-written `TASK-032-T3-FT-008-W1` `done` decision with
  independent functional PASS and per-task semantic-pass evidence for durable
  PostgreSQL introduction delivery and current-state reconciliation.
- Recorded exactly-eight-or-zero persistence, retry/conflict idempotency,
  restart convergence, archive-race denial, restore without replay, guarded
  rollback, and unchanged post-commit Plant creation as the completed W1
  outcome.
- Preserved the absent `HUMAN_CHECKPOINT: done` marker as an explicit warning;
  scheduler accepted only the process requirement and did not waive safety,
  authorization, data integrity, source-of-truth, privacy, or scope rules.
- Kept FT-008, REQ-013, and REQ-020 lifecycle `planned` because guarded Bus/UI
  publication, context reads, the Plant feed API, and broader privacy/operator
  outcomes remain downstream. TASK-033 stays `planned`; promotion remains a
  separate scheduler decision after strict readiness gates.

## [2026-07-12] FT-008 SDD closure and task queue
- Completed FT-008 feature-local design for strict Bus/UI v1 envelopes,
  PostgreSQL storage, atomic safe-information publication, protected Plant
  feed reads, context filtering, and restart/archive-safe roster-introduction
  reconciliation.
- Extended the existing Agent Chat Bus and UI Feed canonical contracts; added
  subject-based storage, HTTP, and testing specs plus three behavior examples.
- Selected one local current-state reconciliation service and an atomic strict
  eight-item sink instead of a broker, distributed worker, or outbox.
- Preserved FT-011 classifier, FT-012 task effects, and FT-016 Svelte/PWA
  rendering ownership. The current tree has no frontend scaffold, so FT-008
  defines the exact backend event/API handoff without claiming DOM evidence.
- Added and indexed `TASK-032-T3-FT-008-W1` for durable introduction delivery
  and `TASK-033-T3-FT-008-W2` for guarded Bus/UI publication, context reads,
  and the Plant feed API.
- JSON/schema/link/dependency checks, `mb-lint`, `mb-doctor`, and diff check
  pass. Doctor reports only historical checkpoint advisories plus the expected
  planned W1 ready-candidate warning. Next: `/review-tasks-plan FT-008`.

## [2026-07-12] Opaque candidate-output contract decision
- Ratified the owner decision that schema-valid `candidate_output` is opaque
  untrusted normalized text within the existing 1..2000 Unicode-code-point
  bound; Markdown/HTML/prompt-like syntax is data and is not by itself
  `output_invalid`.
- Extended AD-004/AD-008 and the existing MessageEnvelope, Agent Runtime,
  UI Feed, Agent Chat Bus, Safety Action Lifecycle, and testing contracts:
  authorized UI rendering is literal/escaped, Bus propagation uses typed
  quotation rather than instruction channels, and candidate content gains no
  routing, Safety, task, action, or runtime authority.
- Kept the classifier matrix, current authorization/archive guards, Safety
  Gate, human approval, redaction, pending/non-consumable envelope state, and
  raw-provider/history/reasoning exclusions unchanged.
- Preserved TASK-028 failure, TASK-029 blocked state, BUG-001, protocols, and
  scheduler evidence as correct historical records under the superseded
  syntax-rejection contract; no lifecycle artifact was edited.
- Foundation remains verified and unaffected. Next route is bounded
  `/prd-to-tasks FT-007`, then fresh `/review-tasks-plan FT-007`; no execution.

## [2026-07-12] FT-007 shared/global SDD repair
- Closed D1-D6/E1 in canonical Agent I/O, MessageEnvelope, Timeline,
  classification, Plant Operations, provider-smoke, and roster/bootstrap specs.
- Fixed strict UUIDv5 eight-item batch/result semantics and assigned durable
  exactly-once `UIFeedEvent` reconciliation to FT-008.
- Returned backbone and FT-007 design to `complete`; the verified Foundation
  gate remains sufficient and downstream feature design stays feature-owned.
- Reconciled `IMPL-FT-007`, TASK-028, and TASK-029 without changing task ids,
  T3 tiers, W1/W2 order, dependencies, or `planned` states. Added direct
  identity/session, Plant Operations, and Plant-create inputs plus exact
  request/outcome/classification/batch/smoke assertions.
- Next: `/review-tasks-plan FT-007`; no execution before fresh `APPROVE`.

## [2026-07-11] FT-007 SDD closure and task queue
- Finalized the project-owned Agent Runtime, strict MessageEnvelope v1,
  sanitized runtime-decision timeline audit, exact PostgreSQL typed-input
  assembler, and fresh post-model authorization/archive guard.
- Added canonical provider-profile, eight-agent roster/post-commit bootstrap,
  focused verification, provider runbook, and three behavior specifications.
- Recorded explicit DeepSeek and Gemini native bindings, per-agent deploy-time
  model ids, typed external egress, no fallback, and a recognized fail-closed
  `chatgpt_oauth` broker port that never reuses ChatGPT/Codex credentials.
- Defined Plant agent activation as a restart-safe derived roster and one
  deterministic non-agent-consumable introduction handoff per agent after
  Plant commit, without model I/O inside creation or false durable-chat claims.
- Added and indexed `TASK-028-T3-FT-007-W1` and
  `TASK-029-T3-FT-007-W2`; the direct W1 dependency is the completed canonical
  Plant-operations baseline `TASK-025-T3-FT-004-W3`.
- Preserved Bus/chat/UI persistence as a downstream boundary and created no
  FT-008 task after the owner's explicit scope reduction.
- JSON/task-schema/link checks and `mb-lint` passed. `mb-doctor` passed with
  zero errors; its 12 advisories are 11 historical T3 checkpoint warnings plus
  the intentionally planned W1 ready-candidate warning pending
  `/review-tasks-plan FT-007`. Global diff-check still reports only the
  unrelated pre-existing `notes_agro-prj.md:51` whitespace finding.

## [2026-07-11] EP-002 ownership correction boundary sync
- Reconciled the already-written owner decision: EP-002 is `active` and
  `verified` for authorized check-in/observations/manual pH/EC, photo intake
  and manifests, PostgreSQL authority, timeline audit/export refs, and
  retained Plant card/history.
- Confirmed REQ-008/009/010 as `verified`; REQ-006/007, EP-003/004/006,
  REQ-016, and REQ-021 remain lifecycle-unchanged and `planned` where
  applicable.
- Confirmed routing ownership without further edits: agents/Vision remain with
  EP-003, Safety/tasks/approvals/follow-up with EP-004, and PWA/first-demo
  composition with EP-006/FT-016.
- Confirmed the epic/feature routers, RTM evidence, boundary map, verified
  FT-004/005/006 state, and 28/28 `done` task registry are mutually consistent.
- Preserved the PRD, user scenarios, task records and links, canonical
  contracts, code/tests, feature lifecycles, and all historical sync reports
  and changelog entries.
- Post-sync RTM/ownership/link assertions, `mb-lint`, and scoped whitespace
  checks passed. Strict doctor passed with `0 errors, 11 warnings, 2 info`;
  warnings remain the already-recorded advisory checkpoint findings. Global
  diff hygiene retains only the unrelated `notes_agro-prj.md:51` warning.
- Post-sync review corrected the operational run status from mixed active/run
  chronology to one compact terminal snapshot: no task is selected or running,
  the queue remains `28/28 done`, and historical step-by-step evidence routes
  to per-task protocols/reports instead of being duplicated as current state.

## [2026-07-11] EP-002 decomposition ownership repair
- Corrected the L1-L3 ownership cut so EP-002 closes independently around
  authorized check-in/observations/manual pH/EC, photo intake/manifests,
  PostgreSQL runtime authority, timeline audit/export refs, and retained Plant
  card/history.
- Narrowed REQ-008 to that owned outcome and synchronized REQ-008 plus EP-002
  to `verified` from the already-verified FT-004/FT-005/FT-006 evidence.
- Activated the EP-002 document after its decomposition questions closed and
  scoped its local redaction criterion to timeline/manifests/history/evidence/
  export refs; mandatory Bus/UI Feed/agent-context redaction remains governed
  by global specs and implemented by EP-003/EP-006.
- Routed agent/Vision behavior to EP-003, Safety Gate/tasks/approvals/follow-up
  to EP-004/REQ-016, and first-demo PWA composition solely to
  EP-006/REQ-021/FT-016; these downstream areas remain lifecycle-unchanged.
- Corrected REQ-006 to primary EP-001/FT-002 ownership with FT-004 as a
  non-owning consumer, without changing the REQ-006 lifecycle.
- Split the REQ-007 base retention mapping from downstream archived-Plant
  guards now traced by REQ-013/016/017/018; REQ-007 lifecycle remains
  unchanged.
- Rephrased FT-004/005/006 criteria as owned backend/API behavior plus typed
  integration seams and moved task/approval/outcome authority in the boundary
  map to the Safety & Task Loop.
- Preserved the PRD and user scenarios as composite product flows, all task
  records/links, historical reports and sync entries, unrelated specs, code,
  and tests. No new product IDs or `/mb-sync` run was introduced.

## [2026-07-11] Wave W3 - FT-004/FT-005/FT-006 repair verification sync
- Reconciled owner-written `done` decisions and preserved functional/semantic
  evidence for repair tasks TASK-025, TASK-026, and TASK-027 without changing
  task identity, tier, dependencies, status, or historical reports.
- Synchronized FT-004, FT-005, and FT-006 from `implemented` to `verified`
  after current feature-level reports each recorded exact
  `SEMANTIC_VERDICT: semantic-pass`; EP-002 remains `implemented` so downstream
  epic/product scope is not inferred.
- Synchronized REQ-009 and REQ-010 to `verified`; kept REQ-007 and REQ-008
  `planned` and left other shared requirements unchanged.
- Recorded TASK-025/TASK-027 missing human-checkpoint markers as explicit
  advisory owner waivers, without fabricating either marker.
- Recorded the controlling FT-006 URL-first/KISS policy: obvious local paths
  are best-effort redaction targets, ambiguous paths/links may remain visible
  rather than reintroducing unstable parser/matrix complexity, and strict
  secret/auth redaction remains unchanged.
- Confirmed task/index and canonical spec-link consistency through TASK-027;
  no spec, lifecycle model, dependency promotion, or unrelated feature was
  created or changed.

## [2026-07-10] Wave W2 - FT-004/FT-005/FT-006 scheduler sync
- Reconciled scheduler-written `TASK-019` through `TASK-024` records as `done`
  without changing closure decisions or promoting dependents inside
  `/mb-sync`.
- Synchronized FT-004, FT-005, FT-006, and EP-002 lifecycles as
  `implemented`, not `verified`, with direct implementation/verify/red-verify
  evidence links.
- Synchronized RTM lifecycles for REQ-009 and REQ-010 to `implemented`; kept
  REQ-008 and REQ-007 `planned` because downstream task/approval/follow-up,
  Safety Gate, PWA/first-demo, agent, Companion, and governance scope remains
  with later features.
- Recorded scheduler-waived missing exact `HUMAN_CHECKPOINT: done` markers for
  TASK-019 through TASK-024 as warnings, not blockers, under the advisory T2/T3
  process override.
- Confirmed the indexed queue is reconciled through `TASK-024`; no new specs,
  principles, lifecycle models, or future-work task records were created.

## [2026-07-10] FT-006 SDD closure and task queue
- Created subject-based SDD specs for Plant history projections, retained-
  history HTTP reads, and focused verification.
- Added three FT-006 behavior specs for active history projection, archived
  retained history, and timeline replay non-authority.
- Created implementation plan `IMPL-FT-006` and indexed T3 task records
  `TASK-023` and `TASK-024`.
- Kept raw timeline export packages, PWA UI, Vision, agents, Safety Gate,
  tasks/follow-up, Companion, and dataset history entries outside FT-006.

## [2026-07-10] FT-004/FT-005 task-plan repair
- Repaired rejected FT-004 and FT-005 task-plan gates by creating indexed
  schema-backed T3 task records `TASK-019` through `TASK-022`.
- Extended the Timeline Event contract with the minimal append writer seam and
  registered current event types for Plant operations and photo intake emitters.
- Resolved FT-005 photo identity ambiguity: `photo_id` is the storage/API name
  for the same UUID as `photo_artifact_id`.
- Left all new FT-004/FT-005 task records `planned`; no implementation or
  execution evidence was produced by this planning repair.

## [2026-07-10] FT-003 admin internal refactor
- Split the Boss admin API adapter into router, schemas, backend, and mapping
  modules without changing HTTP routes, response models, OpenAPI names,
  no-store behavior, or error envelopes.
- Split admin service helpers into typed results/projections, policy/input
  guards, and safe-summary builders while keeping existing public imports from
  `backend.app.access_admin.admin_service` available.
- Moved admin audit offset pagination behind the AdminService/AdminRepository
  boundary and removed the admin API layer's direct audit SQL/query bypass.
- Preserved FT-003 behavior and contract specs; this is an internal
  no-contract-change refactor.

## [2026-07-10] Wave W3 — FT-003 integrated implementation evidence
- Added integrated FT-003 API flow coverage for canonical Farm/`tomato_001`
  bootstrap, first Boss bootstrap, Boss login, Boss-created Engineer, Engineer
  login, Boss Plant access grant through the canonical Plant API, non-Boss
  denial, last-Boss protection, safe audit, password exclusion, and no-store
  responses.
- Ran TASK-018 local gates: focused FT-003 `18/18`, EP-001 auth/admin/Farm
  regression `139/139`, and full regression `169/169`.
- Synchronized FT-003 and REQ-005 as `implemented`, not `verified`; scheduler
  closure, independent `/verify`, per-task `/red-verify`, and recommended
  feature-level semantic review remain owner/scheduler decisions.
- Kept FT-016 PWA/admin UI, Plant operations, Safety Gate, agent runtime,
  dataset, and downstream first-demo scopes open.

## [2026-07-09] FT-003 SDD closure and task queue
- Closed FT-003 planning for Boss admin, first-Boss bootstrap, direct Account
  creation, role changes, Plant admin projection, and admin audit reads.
- Extended the Boss Admin HTTP and Boss Admin verification specs with concrete
  response shapes, error behavior, OpenAPI, rollback, and redaction checks.
- Added the First Boss Local Bootstrap runbook as the exact one-shot local CLI
  contract and linked it from the spec registry and FT-003 feature composition.
- Added three FT-003 behavior specs for first-Boss bootstrap, Boss-created
  Engineer atomic audit, and non-Boss/last-Boss guard.
- Created implementation plan `IMPL-FT-003` and indexed dependency-ordered T3
  tasks `TASK-016` through `TASK-018`.
- Kept PWA/admin UI implementation with FT-016 and reused FT-002 Plant
  lifecycle/access semantics instead of redefining them in FT-003.

## [2026-07-09] Wave W4 — FT-002 integrated execution handoff
- Added integrated FT-002 API flow tests for Engineer create/select/rename and
  Boss archive/grant/restore permission behavior.
- Added executable BHV-001..004 traceability so behavior specs point to
  concrete passing tests instead of prose-only evidence.
- Ran local `/execute` gates for TASK-015: focused FT-002 `43/43` and full
  regression `151/151` passed.
- Initially synchronized FT-002 and REQ-001 as `implemented` while leaving
  shared REQ-003/004/006/007, FT-003 admin, downstream archive integrations,
  UI/PWA, Safety Gate, Companion, and agent scopes open.
- Recorded independent `/verify TASK-015` `PASS`, per-task `/red-verify`
  `semantic-pass`, user-approved `HUMAN_CHECKPOINT: done`, and TASK-015
  closure as `done`.
- Recorded feature-level `/red-verify --feature FT-002`
  `SEMANTIC_VERDICT: semantic-pass`; synchronized FT-002 lifecycle to
  `verified` and REQ-001 to `verified`.
- Kept shared/downstream REQ-003/004/006/007, FT-003 admin, retained-history,
  UI/PWA, Safety Gate, Companion, and agent scopes open.
- Ran wave-boundary `/mb-sync`; Memory Bank lint, doctor, strict doctor, and
  diff whitespace checks pass with no warnings.

## [2026-07-06] FT-002 SDD closure and task queue
- Confirmed completed Foundation gate `TASK-004-T2-FT-000-W0` and the full
  completed FT-001 chain through `TASK-011-T3-FT-001-W3` as the brownfield
  prerequisite for FT-002.
- Closed exact Farm/Plant/grant persistence, legacy Farm-ID reconciliation,
  canonical `local_farm`/`tomato_001` bootstrap, lifecycle, stable grant,
  AdminAuditRecord, HTTP/error, and verification contracts.
- Added three behavior specs for idempotent bootstrap, atomic Engineer create
  with immediate access, and archive/grant/restore semantics.
- Marked FT-002 feature design `complete` and created implementation plan plus
  indexed dependency-ordered T3 tasks `TASK-012` through `TASK-015`.
- Kept first-Boss/Account administration in FT-003 and retained-history,
  downstream archive integration, UI, agents, tasks, approvals, and governance
  behavior with their owning features.

## [2026-07-06] FT-002-triggered archived-Plant backbone repair
- Added Architecture Spine `AD-007`: archived Plant is a global operational
  deny for new and already-open Plant-scoped workflows.
- Preserved open task, approval, follow-up, agent, and Companion governance
  records without automatic completion, cancellation, deletion, execution, or
  supersede on archive.
- Required current transactional Plant status for state-advancing commands and
  full owning-guard revalidation after restore; restore never auto-resumes work.
- Kept Boss lifecycle/grant administration and authorized retained-history
  reads as explicit exceptions, with archived grants remaining non-operative.
- Synchronized FT-002, FT-011, FT-012, FT-013, global lifecycle specs, testing,
  spec registry/backbone, and Foundation sufficiency without creating tasks or
  changing the verified FT-000 gate.

## [2026-07-06] Wave W3 — FT-001 completion sync
- Reconciled authoritative TASK-005 through TASK-011 records as `done` without
  rewriting their closure decisions or promoting any dependent task.
- Recorded repeated feature-level `SEMANTIC_VERDICT: semantic-pass` after the
  safe-repr and standard protected-route composition repairs; the owner accepts
  the missing dedicated hostile-provider regression test as residual risk.
- Synchronized FT-001 document status/lifecycle to `active` / `verified` and
  REQ-002 RTM lifecycle to `verified`.
- Kept EP-001 and cross-feature REQ-003/004/020/021/022 `planned`; FT-002,
  FT-003, FT-007, and FT-008 boundaries remain deferred to their owning work.
- Preserved the explicit PostgreSQL/`psql` environment gap and prior
  task-scoped evidence; no unavailable check is represented as newly passing.
- Updated the FT-001 feature router and current evidence notes. No SDD registry
  or global backbone decision changed.

## [2026-07-05] Wave W3 — TASK-011 execution handoff
- Applied the owner-requested code-only repr hardening for ActorContext and its
  Plant snapshot provider; verification remains pending by explicit request.
- Fixed default protected-route composition by registering the existing denial
  handler in `create_app()`; protected-route tests now exercise the standard app
  without manual fixture registration.
- Integrated FT-001 evidence across TASK-005 through TASK-010 and mapped the
  security, session HTTP, ActorContext, context-builder, and behavior-spec
  coverage into the TASK-011 protocol.
- Ran the focused FT-001 suite with `77 passed` and one PostgreSQL check
  deselected; ran the complete non-environment suite with `105 passed` and
  three local PostgreSQL/`psql` checks deselected.
- Recorded the unavailable database/tooling checks as an environment gap and
  retained prior PostgreSQL evidence without representing it as rerun.
- Updated FT-001, EP-001, and RTM evidence notes without changing their
  `planned` lifecycles or claiming FT-002/FT-003 completion.
- Left TASK-011 independent `/verify`, optional semantic review, explicit owner
  closure, and wave-boundary `/mb-sync` as separate next-owner actions.

## [2026-07-04] Testing router and strategy separation
- Reduced `.memory-bank/testing/index.md` to annotated navigation links.
- Moved stable quality gates, test-level guidance, anti-cheat rules, and risk
  surfaces to the canonical `.memory-bank/testing/strategy.md` document.
- Registered the strategy in `spec-index.md`, updated the testing backbone
  route, and redirected active testing-policy references without rewriting
  historical task records.

## [2026-07-03] Advisory T2/T3 execution policy
- Amended Constitution version 3 so T2/T3 tiers classify risk and recommend
  rigor without creating automatic closure gates.
- Made protocol depth, task gates, `/verify`, `/red-verify`, feature semantic
  review, human checkpoints, strict doctor, and `/mb-sync` advisory for T2/T3.
- Preserved binding product safety, authorization, source-of-truth, scope, and
  destructive-operation rules; only process ceremony became owner-controlled.
- Kept completed-task evidence as history. Legacy `required` wording in T2/T3
  cards is interpreted as a strong recommendation unless an explicit owner
  makes a concrete gate mandatory for the current run.

## [2026-07-01] Wave W1 — completion
- Closed `TASK-006-T3-FT-001-W1` after recorded functional PASS,
  adversarial `semantic-pass`, and the explicit owner human checkpoint.
- Completed the final W1 Memory Bank sync for TASK-005 and TASK-006, including
  FT-001 feature/epic/plan state, active routing, closure evidence, and
  changelog reconciliation.
- Left `TASK-007-T3-FT-001-W2` as `planned`: all dependencies are done, but
  promotion remains a separate owner decision after the strict readiness gate.

## [2026-07-01] T3 closure policy optimization
- Synchronized the deployed DevRails T3 command/workflow runtime in both
  `.agents/skills/` and `.claude/skills/` plus generated project policy and
  doctor surfaces.
- Removed tier-generated rollback/recovery closure boilerplate from active
  `TASK-006` through `TASK-011`, the FT-001 implementation plan, and the FT-001
  execution protocol.
- Preserved functional `/verify`, per-task `/red-verify`, exact human
  checkpoint, explicit owner closure, and wave-boundary `/mb-sync` gates.
- Left TASK-005-specific closure artifacts, historical completed evidence,
  migration downgrade checks, product recovery non-goals, and unrelated
  implementation/test changes unchanged.

## [2026-07-01] Wave W1 — TASK-005 closure and TASK-006 readiness
- Closed `TASK-005-T3-FT-001-W1` in manual mode after recorded
  `VERDICT: PASS`, `SEMANTIC_VERDICT: semantic-pass`, explicit owner human
  checkpoint, and verified Alembic rollback/recovery evidence.
- Synchronized the TASK-005 authoritative record, closure handoff, FT-001
  feature/epic/plan state, and active Memory Bank routing.
- Ran the strict T3/dependency readiness gate, then applied the separate manual
  owner promotion decision for `TASK-006-T3-FT-001-W1`; its status is `ready`.
- This owner-requested early W1 sync enables a clean-agent TASK-006 handoff and
  does not replace the final W1 boundary sync after TASK-006 closes.

## [2026-07-01] KISS Account creation and bounded FT-002 dependency repair
- Replaced local invite/activation with direct Boss-created active Account and
  active FarmMembership semantics; removed invite entity/state/API specs and
  reconciled FT-001 session/storage/task cards without changing task topology.
- Recorded the local MVP trust model: Boss knows the initial password, no
  mandatory first-login change, and no compatibility route or fallback state.
- Defined `POST /api/admin/accounts` as a future FT-003 atomic boundary for
  Account, membership, Argon2id password hash, and exactly one safe
  `account_created` audit record; exact first-Boss one-shot CLI remains deferred
  until FT-002/FT-003 design.
- Narrowed FT-002 inputs to the minimum PlantPermissionContext dependency slice
  needed by FT-001 and removed prematurely detailed Plant API, migration, seed,
  mutation, and verification specs. No FT-002 plan/tasks/code were created.
- Reconciled FT-001 subject specs, implementation plan, protocols, and
  `TASK-005`, `TASK-007`, `TASK-008`, `TASK-009`, and `TASK-010`; task IDs,
  tiers, waves, dependencies, statuses, and outcomes remain unchanged.
- Re-ran `/prd-to-tasks FT-001` canonical discovery/link audit: no new spec was
  needed; the existing session/access verification spec is now direct in all
  applicable cards, `TASK-010` directly links session lifecycle/API, and
  `TASK-008` explicitly owns only the bounded archived permission effect.

## [2026-07-01] Post-migration review repairs
- Restored mandatory exactly-one same-transaction admin audit writes and the
  exact PlantAccessGrant response shape from the removed hubs.
- Restored FT-001/FT-002/FT-003 feature non-goals and removed stale active
  packet/file-routing wording.
- Added the missing Account/FarmMembership spec link to `TASK-007`.
- Split executable FT-001 verification from deferred FT-002/FT-003 E2E and
  added the full project test-suite gate to `TASK-011`.
- Added missing router annotations. Remaining ambiguous findings are deferred
  explicitly rather than resolved by invention.

## [2026-06-30] Single-card and subject-based SDD migration
- Deployed current generated workflows/scripts and migrated the task schema to
  the framework single-card contract.
- Confirmed packet success checks were already represented in task cards, then
  removed persisted packets and `packet_required`/`packet_ref` fields without
  changing task IDs, tiers, waves, dependencies, statuses, or outcomes.
- Replaced FT-001/FT-002/FT-003 tech-spec hubs with canonical subject specs for
  identity, sessions, ActorContext, Farm/Plant access, local invite, admin
  audit, HTTP boundaries, lifecycles, and verification.
- Converted feature docs to composition roots, rebuilt `spec-index.md` around
  canonical paths and `Change route`, and linked FT-001 tasks directly to the
  applicable spec subset.
- Removed obsolete compatibility hubs after active references were switched;
  historical references below describe the state at their original date.

## [2026-06-29] FT-001 SDD ownership split
- Replaced the 735-line FT-001 all-in-one tech spec with a stable feature hub
  plus atomic data, session-security, session-API, ActorContext, and
  verification owners.
- Preserved the original hub path as a compatibility facade for existing task,
  packet, plan, and adjacent-feature references; no behavioral contract changed.
- Updated the spec registry, feature metadata, contracts/domains/testing
  routers, runtime-data routing, and FT-002/FT-003 dependencies.
- Added `ANALISYS_REPORT.md` with root-cause analysis for the monolithic spec and
  duplicated FT-001 workflow status.

## [2026-06-29] Memory Bank garden cleanup
- Removed promoted active analysis artifacts and replaced their remaining
  project-doc references with current PRD and owning specs.
- Removed exact freshness windows and duplicate `UIFeedEvent` vocabulary from
  the glossary.
- Reconciled the FT-001 handoff with the completed targeted refresh and current
  `/review-tasks-plan FT-001` gate.
- Added a concise Explorer role to the project worker-role copies.
- Removed unresolved legacy dossier references and trimmed MVP v1 history
  from the active changelog.

## [2026-06-28] /prd-to-tasks FT-001 targeted TASK-005 relational refresh
- Updated only `TASK-005-T3-FT-001-W1` and its canonical packet for native UUID
  identity, exact nullability/timestamps, DB domain checks, normalized login
  uniqueness, non-cascading Account FKs, deferred Farm FK ownership, exact
  indexes, and PostgreSQL evidence targets.
- Preserved the task ID, T3 tier, W1 dependency on the completed Foundation
  gate, implementation write scope, and queue ordering.
- Updated feature/implementation/protocol handoff notes. No new task, behavior
  spec, runtime code, migration, or changes to `TASK-006` through `TASK-011`
  and their packets were made.
- Next gate: `/review-tasks-plan FT-001`, then conditional `/mb-doctor` before
  `TASK-005` execution.

## [2026-06-28] /spec-improve FT-001 relational storage repair
- Added a shared PostgreSQL native UUID/Python `uuid.UUID` identity contract
  with application UUIDv4 generation and non-cascading authority relations to
  Runtime Data Model.
- Completed the authoritative TASK-005 relational schema for `accounts`,
  `farm_memberships`, and `local_sessions`: exact types/nullability/timestamps,
  string-domain checks, active-account password invariant, normalized login
  uniqueness, required Account FKs, and exact indexes.
- Kept `farm_memberships.farm_id` required but temporarily without FK so FT-001
  does not create the FT-002-owned Farm authority. FT-002 now owns deterministic
  zero/one/multiple-ID reconciliation and final `ON DELETE RESTRICT` FK closure.
- No runtime code, migrations, task records, packets, or new spec files were
  created. Next route is targeted `/prd-to-tasks FT-001` for `TASK-005` and its
  packet, then `/review-tasks-plan FT-001`.

## [2026-06-27] /spec-improve FT-001 KISS storage repair
- Added only the security-derived `TASK-005` storage contract needed before the
  first FT-001 migration: unbounded Argon2id PHC `password_hash`, exact
  64-character lowercase SHA-256 `token_hash`, nullability/status rules, unique
  lookup behavior, raw-token prohibition, edge cases, and verification targets.
- Reconciled FT-001 with FT-003 invite revocation: an Account disabled before
  activation may have `password_hash=null`, while every active Account requires
  a credential.
- Did not add broader identifier/timestamp schemas, API DTO, event, callable
  interface, runtime code, migration, task-record, or packet decisions.
- Next route: `/prd-to-tasks FT-001` refreshes the existing `TASK-005` record and
  packet, followed by `/review-tasks-plan FT-001`.

## [2026-06-26] /prd-to-tasks FT-001 task-card refresh after spec repair
- Refreshed existing FT-001 task cards and packets after `/spec-improve FT-001`
  closed concrete security primitive, cookie/session transport, and
  PlantPermissionContext ownership gaps.
- Updated `TASK-006-T3-FT-001-W1` to own `argon2-cffi` Argon2id dependency,
  256-bit opaque session tokens, SHA-256 `token_hash`, constant-time digest
  comparison, and related evidence.
- Updated `TASK-007-T3-FT-001-W2`, `TASK-008-T3-FT-001-W2`,
  `TASK-009-T3-FT-001-W2`, `TASK-010-T3-FT-001-W3`, and
  `TASK-011-T3-FT-001-W3` for session lifecycle, exact cookie transport,
  PlantPermissionContext compatibility, denial filtering, and integration
  evidence.
- Left `TASK-005-T3-FT-001-W1` unchanged because no schema-level column,
  nullability, index, or migration constraint changed.
- Refreshed required FT-001 packets, implementation plan, feature protocol, and
  routing docs. No new task records, behavior specs, runtime code, migrations,
  or FT-002/FT-003 product tasks were created.

## [2026-06-26] /spec-improve FT-001 finding repair
- Evaluated the three `todo.md` FT-001 findings as objective against the
  current FT-001/FT-002 specs and T3 task requirements.
- Updated historical path `.memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md`
  (removed during the 2026-06-30 subject-spec migration)
  with concrete Argon2id/password, opaque session token, `token_hash`,
  constant-time verification, cookie transport, bearer-mode, and verification
  targets.
- Updated historical path `.memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md`
  (removed during the 2026-06-30 subject-spec migration)
  with explicit Ownership and canonical concrete PlantPermissionContext
  resolver semantics aligned to the FT-001 interface envelope.
- Refreshed routing docs so the next FT-001 step is rerun
  `/prd-to-tasks FT-001`, then `/review-tasks-plan FT-001`; no task records,
  packets, implementation plan, runtime code, DB migrations, or dependencies
  were changed in this repair.

## [2026-06-26] /prd-to-tasks FT-001 expanded protocol refresh
- Reran the FT-001 planning surface through the expanded `/prd-to-tasks`
  protocol without creating new task records.
- Added explicit ownership and concrete contract readiness routing to
  historical path `.memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md`
  (removed during the 2026-06-30 subject-spec migration).
- Refreshed [.memory-bank/tasks/plans/IMPL-FT-001.md](tasks/plans/IMPL-FT-001.md),
  `TASK-005-T3-FT-001-W1` through `TASK-011-T3-FT-001-W3`, and their required
  packets to link current Foundation runtime/data substrate,
  evidence-redaction, and testing owners.
- Confirmed the FT-001 queue shape, statuses, and dependencies are unchanged;
  next gate remains `/review-tasks-plan FT-001`.

## [2026-06-26] Foundation post-hoc audit remediation
- Clarified FT-000 local command wording so pytest, install, and uvicorn checks
  use the project `.venv` created by `scripts/bootstrap-local.sh`.
- Updated completed FT-000 task metadata and required packet spec refs to link
  the new Foundation substrate specs: runtime substrate, smoke API, data
  substrate, test harness, local runtime runbook, and evidence redaction.
- Refreshed FT-000 required packet revisions and `source_task_hash` values after
  task metadata link updates.

## [2026-06-26] /foundation-to-tasks substrate spec audit
- Ran the updated `/foundation-to-tasks` substrate spec audit against the
  already verified FT-000 Foundation baseline and current backend code.
- Added scaffold-level SDD owners for Foundation runtime shape, smoke API,
  DB/session/Alembic/runtime roots, test harness, local runtime runbook, and
  evidence redaction.
- Registered the new owners in `.memory-bank/spec-index.md` and linked them
  from Foundation, FT-000, backbone, architecture, contracts, domains, testing,
  and Memory Bank navigation.
- Did not create or edit task records, packets, implementation plans, backend
  code, product schemas, generated OpenAPI, or feature-local `FT-*` tech specs.

## [2026-06-26] /spec-design expanded shared SDD refresh
- Reran global `/spec-design` after strengthening shared SDD formation rules.
- Kept the backbone status `complete`, corrected the mode to
  `standard_architecture_scaffold`, and preserved the verified FT-000
  Foundation closure.
- Added shared global SDD owners for UI Feed, timeline audit/export, photo
  artifacts, Plant state trust, Safety action lifecycle, Companion governance,
  and dataset governance.
- Updated existing API, Agent Chat Bus, MessageEnvelope, runtime data,
  architecture, testing, spec registry, backbone, feature routing, and Memory
  Bank navigation docs to link the new owners.
- Did not create product task records, implementation plans, packets, generated
  OpenAPI, DB migrations, or feature-local `FT-*` tech specs.

## [2026-06-26] /prd-to-tasks FT-001 refresh
- Refreshed the existing FT-001 task planning surface against the brownfield
  global SDD backbone, verified FT-000 Foundation evidence, and current
  FT-001/FT-002/FT-003 feature specs.
- Confirmed no new global/shared or feature-local design spec is required for
  FT-001 before task-plan review.
- Updated FT-001 implementation plan, feature routing, EP/index routing,
  `.protocols/FT-001/`, task records, and execution packets so the next gate is
  `/review-tasks-plan FT-001`.
- Preserved the existing FT-001 task queue shape: `TASK-005-T3-FT-001-W1`
  through `TASK-011-T3-FT-001-W3`; no runtime code was implemented.

## [2026-06-26] /spec-design review repair
- Repaired overbroad ActorContext wording after brownfield review.
- Clarified that protected product endpoints must resolve ActorContext before
  business logic, while `/health`, `/ready`, and explicitly public auth
  endpoints such as login/bootstrap endpoints are exceptions that must not
  expose Farm/Plant data or auth material.
- Replaced Foundation `route registration convention` wording with an app
  factory extension point for future route registration; owning feature tasks
  establish concrete product route registration.
- Updated global contracts, runtime data model, Foundation wording, and the
  FT-001 feature design/implementation-plan wording; did not edit task records
  or packets.
- Swept remaining active routing docs after the brownfield refresh so
  `analysis`, `testing`, `FT-000`, `EP-001`, `skills`, `glossary`, and PRD
  handoff language point to `/prd-to-tasks FT-001` refresh and no longer claim
  product route/module anchors from the verified FT-000 baseline.
- Added protocol notes so PRD bootstrap and FT-001 planning artifacts do not
  send execution directly from stale pre-refresh task assumptions.

## [2026-06-26] /spec-design --all brownfield refresh
- Ran `/spec-design --all` as a brownfield-aware global SDD backbone refresh.
- Read verified FT-000 evidence and current backend code before changing global
  contracts; preserved `FT-000`/`TASK-004-T2-FT-000-W0` closure because no real
  executable baseline gap was found.
- Added explicit brownfield precedence in the global architecture: verified code
  and FT-000 evidence constrain refreshed contracts below Constitution/user
  decisions and above older speculative specs or generated task assumptions.
- Refreshed global SDD routing so `/prd-to-tasks FT-<NNN>` owns feature-level
  SDD design before task slicing, while `/spec-improve FT-<NNN>` remains
  repair/advanced refresh without task generation.
- Corrected Foundation wording so FT-000 proves shared app/settings/database,
  bootstrap, readiness, runtime-root, and redaction anchors, but does not claim
  product module/package anchors that current code has not created.
- Routed existing FT-001 generated tasks/packets through `/prd-to-tasks FT-001`
  refresh before `/review-tasks-plan FT-001` and implementation.
- Did not create or edit product task records, packets, implementation plans, or
  feature-local FT tech specs.

## [2026-06-26] /prd refresh check
- Ran `/prd` refresh check against the updated command contract after the
  `/spec-init` refresh passed.
- Confirmed PRD frontmatter, Constitution gate, pre-PRD framing gate, and pure
  `spec-index` gate are valid for L1-L3 decomposition.
- Kept the existing 6 epic / 16 product feature decomposition plus reserved
  `FT-000` Foundation pseudo-feature; no product scope, REQ IDs, task records,
  implementation plans, packets, or feature-local tech specs were created.
- Refreshed routing text in derived PRD artifacts so `/prd-to-tasks FT-<NNN>`
  owns feature-level SDD design before task slicing, while standalone
  `/spec-improve FT-<NNN>` remains repair/advanced refresh only.
- Next workflow focus is `/spec-design --all` for global/shared SDD refresh.

## [2026-06-26] /spec-init refresh check
- Ran `/spec-init` refresh check against the updated command contract.
- Confirmed active PRD and pre-PRD framing artifacts still cover actors,
  scenarios, domain, constraints, non-goals, risks, boundary hints, and
  lifecycle hints sufficiently for `/prd` decomposition.
- Updated [.memory-bank/spec-backbone.md](spec-backbone.md) `Pre-PRD Spec Status`
  timestamp and notes; no new pre-PRD specs, feature docs, task records, or
  implementation plans were created.
- Next workflow focus remains `/prd` refresh check, then `/spec-design --all`
  for global/shared SDD gaps.

## [2026-06-25] FT-001 task decomposition
- Ran `/prd-to-tasks FT-001` after verified Foundation closure.
- Added [.memory-bank/tasks/plans/IMPL-FT-001.md](tasks/plans/IMPL-FT-001.md) and `.protocols/FT-001/` planning notes.
- Added behavior specs for login success, no-leak login failure, and ActorContext permission filtering under `.memory-bank/behavior-specs/`.
- Added T3 task records `TASK-005-T3-FT-001-W1` through `TASK-011-T3-FT-001-W3` and indexed them in [.memory-bank/tasks/index.json](tasks/index.json).
- Added required execution packets for every FT-001 task under `.memory-bank/packets/`.
- Updated FT-001, EP-001, feature router, and Memory Bank index routing so the next gate is `/review-tasks-plan FT-001`.

## [2026-06-25] Wave W0 - TASK-004 final gate failed
- Ran `TASK-004-T2-FT-000-W0` final Foundation gate evidence collection.
- Passed local bootstrap, venv install, DB init, DB migration, full pytest suite, `mb-lint`, `mb-doctor`, `git diff --check`, and TASK-004 evidence secret-pattern scan.
- Failed the app start gate because `.venv` does not contain `uvicorn`, so `/health` and `/ready` could not be checked.
- Recorded `VERDICT: FAIL` evidence under `.protocols/TASK-004-T2-FT-000-W0/` and `.tasks/TASK-004-T2-FT-000-W0/`.
- Did not run W0 red-verification because functional verification did not pass.

## [2026-06-25] Wave W0 - TASK-004 dependency fix and verify PASS
- Added `uvicorn>=0.30` to `pyproject.toml` so the documented local app start command is executable.
- Recreated `.venv` from scratch through `scripts/bootstrap-local.sh`; fresh bootstrap installed `uvicorn 0.49.0`.
- Reran the final Foundation gate: install, DB init, DB migration, app start, `/health`, `/ready`, full pytest suite, `mb-lint`, `git diff --check`, and evidence secret-pattern scan all passed.
- Updated `TASK-004-T2-FT-000-W0` to `done` with latest `VERDICT: PASS` evidence.

## [2026-06-25] Wave W0 - semantic red-verification PASS
- Ran W0-level semantic red-verification for `FT-000` without using forbidden `--feature FT-000` mode.
- Recorded `SEMANTIC_VERDICT: semantic-pass` in `.protocols/FT-000/red-verification-W0.md`.
- Added final W0 red-verification report at `.tasks/FT-000/FT-000-W0-S-RED-VERIFY-final-report-docs-01.md`.
- Confirmed the Foundation wave proves platform anchors only and does not close product features or generate product tasks.

## [2026-06-25] Wave W0 - Foundation MB-SYNC
- Marked `REQ-000` RTM lifecycle as `verified`.
- Marked `FT-000` lifecycle as `verified`.
- Updated Memory Bank routers and Foundation docs so product tasking is unblocked for features with completed feature-level SDD designs.
- Recorded the next route as `/prd-to-tasks FT-001` followed by `/review-tasks-plan FT-001` before implementation.
- Synchronized dependency wording after removing Python package upper bounds from `pyproject.toml` and generated package metadata.

## [2026-06-25] Wave W0 - TASK-003 closed
- Updated `TASK-003-T3-FT-000-W0` to `done` after `/verify` PASS,
  `/red-verify` semantic-pass, and user-confirmed human checkpoint.
- Recorded exact T3 closure markers `HUMAN_CHECKPOINT: done` and
  `ROLLBACK_RECOVERY_NOTE: present` in closure evidence.
- Refreshed `.memory-bank/packets/TASK-003-T3-FT-000-W0.packet.json` to R5 so
  its `source_task_hash` matches the closed task record.
- Updated [.memory-bank/index.md](index.md) and
  [.memory-bank/tasks/plans/IMPL-FT-000.md](tasks/plans/IMPL-FT-000.md) so the
  next route is `TASK-004-T2-FT-000-W0`, the final Foundation gate.

## [2026-06-24] Wave W0 - TASK-001 verified and synced
- Updated [.memory-bank/tasks/plans/IMPL-FT-000.md](tasks/plans/IMPL-FT-000.md) to reflect `TASK-000-T1-FT-000-W0` and `TASK-001-T2-FT-000-W0` as `done`.
- Recorded current routing in [.memory-bank/index.md](index.md): `TASK-002-T2-FT-000-W0` remains `planned` but has all direct dependencies done and is eligible for a separate scheduler/owner promotion pass.
- Left `REQ-000` and `FT-000` lifecycle as planned because the final Foundation gate `TASK-004-T2-FT-000-W0` is not done yet.
- Did not promote dependent tasks from `/mb-sync`; promotion remains a separate scheduler/owner action.

## [2026-06-23] Foundation retargeted to Linux Mint local
- Updated the active `FT-000` Foundation Dev Path from Windows 10/PowerShell to Linux Mint/Bash local setup.
- Replaced planned bootstrap, DB init, and migration commands with `bash scripts/bootstrap-local.sh`, `bash scripts/db-init-local.sh`, and `bash scripts/db-migrate-local.sh`.
- Updated `TASK-001-T2-FT-000-W0` through `TASK-004-T2-FT-000-W0` and their packets so the next Foundation implementation task targets Linux Mint.
- Left product feature scope unchanged; product tasking still waits for final `FT-000` gate closure.

## [2026-06-23] /foundation-to-tasks queue created
- Added `REQ-000` and reserved pseudo-feature [.memory-bank/features/FT-000-foundation.md](features/FT-000-foundation.md).
- Added Foundation implementation plan [.memory-bank/tasks/plans/IMPL-FT-000.md](tasks/plans/IMPL-FT-000.md), `.protocols/FT-000/` planning notes, and schema-backed `TASK-000-T1-FT-000-W0` through `TASK-004-T2-FT-000-W0`.
- Set [.memory-bank/foundation.md](foundation.md) final gate to `TASK-004-T2-FT-000-W0`.
- Added required packets for T2/T3 Foundation tasks under `.memory-bank/packets/`.
- Updated routing so the next gate is `node scripts/mb-doctor.mjs`, then execute/verify `FT-000` until the final gate is done.

## [2026-06-23] Compact Foundation Dev Path restored
- Added a new compact [.memory-bank/foundation.md](foundation.md) focused on task schema/protocol alignment, backend scaffold anchors, Windows 10 local bootstrap, PostgreSQL init, migration baseline, DB readiness, local runtime roots, and redaction baseline.
- Updated [.memory-bank/schemas/task.schema.json](schemas/task.schema.json) to match the current `TASK-<NNN>-T<N>-FT-<NNN>-W<N>` task protocol, optional `runtime_context`, and FT-000/W0 flow.
- Updated routing in spec backbone, spec index, Memory Bank index, analysis/features routers, and testing so product tasking waits for `/foundation-to-tasks` and the final `FT-000` gate.
- Kept the old broad Bus -> Agent -> Message/UI -> Safety -> timeline/photo export Foundation Critical Path out of active routing; those concerns remain global or feature-local specs.

## [2026-06-23] Foundation artifacts removed
- Removed project-specific Foundation Dev Path artifacts: `.memory-bank/foundation.md`, `.memory-bank/contracts/foundation-critical-path.md`, `.protocols/FT-000/`, and the Foundation-only root `todo.md`.
- Restored active routing to the pre-Foundation state: task queue empty, no `REQ-000`, no `FT-000`, and no final Foundation gate requirement.
- Kept generic task/workflow tooling intact; no product runtime code was changed.

## [2026-06-22] Generated task artifacts removed after rollback
- Reset the active task queue to an empty [.memory-bank/tasks/index.json](tasks/index.json).
- Removed generated first-wave task records and implementation plans for FT-001, FT-002, and FT-003.
- Removed local ignored `.tasks/` task evidence/review artifacts and task/feature protocol state tied to old task generation.
- Updated active routing docs so the Memory Bank no longer points to `/execute TASK-001` or stale `TASK-*` records.
- Kept PRD, product, requirements, epics, features, global SDD backbone, and FT-001..FT-003 feature-local specs.

## [2026-06-17] Task registry cleanup
- Removed the obsolete standalone foundation task from the active task registry and project navigation.
- Kept the executable backend scaffold as part of the active TASK-001 implementation evidence.
- Updated current routing and verification notes so Memory Bank doctor no longer trips on the retired foundation task shape.

## [2026-06-17] TASK-001 DB/test scaffold implemented
- Extended the backend baseline with a minimal database settings primitive, a SQLAlchemy-backed engine/session/test harness, and a migration entrypoint package under `backend/migrations`.
- Added backend fixtures/tests that prove the app imports, can be created with an explicit test database handle, and can open a clean rollback-safe test session boundary.
- Updated `.env.example`, `pyproject.toml`, and the `backend/app` package exports to surface the new reusable scaffold without implementing FT-001 auth/session behavior.
- Captured T2 protocol notes and evidence under `.protocols/TASK-001/` and `.tasks/TASK-001/evidence/`.

## [2026-06-16] First-wave task artifacts verified
- Verified generated `/prd-to-tasks` artifacts for FT-001, FT-002, and FT-003: implementation plans, TASK-001..TASK-015 records, task index, dependencies, tiers, SDD links, requirement coverage, and T3 closure evidence requirements.
- Added verification evidence at `.tasks/TASK-ARTIFACT-VERIFY/FT-001-003-task-artifacts-verification.md`.
- Fixed stale per-feature routing text that still pointed to `/prd-to-tasks` after task generation.
- Updated Memory Bank routing so the next route is `/execute TASK-001`.
- No application code was implemented.

## [2026-06-14] /prd-to-tasks first wave completed
- Created feature protocols for FT-001, FT-002, and FT-003 under `.protocols/FT-001/`, `.protocols/FT-002/`, and `.protocols/FT-003/`.
- Added implementation plans `.memory-bank/tasks/plans/IMPL-FT-001.md`, `.memory-bank/tasks/plans/IMPL-FT-002.md`, and `.memory-bank/tasks/plans/IMPL-FT-003.md`.
- Created schema-backed TASK-001..TASK-015 records for FT-001..FT-003 and indexed them in `.memory-bank/tasks/index.json`.
- Marked only TASK-001 `ready`; dependent tasks remain `planned` with explicit dependencies.
- Updated Memory Bank routing in `.memory-bank/index.md`, `.memory-bank/features/index.md`, `.memory-bank/analysis/index.md`, and `.memory-bank/epics/EP-001-local-farm-access-admin.md`.
- Did not implement application code or create task records for FT-004..FT-016.

## [2026-06-14] /spec-improve first wave integrated
- Registered active/current normative `feature_design` specs for FT-001, FT-002, and FT-003 in `.memory-bank/spec-index.md`.
- Updated shared navigation for EP-001, features, analysis, and main Memory Bank routing to show first-wave `/spec-improve` completion.
- Recorded that TASK records and task decomposition have not been created yet; next route is `/prd-to-tasks FT-001`, `/prd-to-tasks FT-002`, and `/prd-to-tasks FT-003`.
- Did not edit feature docs, feature-local tech specs, TASK records, implementation plans, generated OpenAPI, DB migrations, or code.

## [2026-06-14] /spec-design global backbone completed
- Added global architecture backbone at `.memory-bank/architecture/system-architecture.md` with local modular monolith, source-of-truth hierarchy, module boundaries, data flow, storage, API/contract, security/safety, testing, deployment, risks, and open-question routing.
- Added `.memory-bank/domains/runtime-data-model.md` for runtime authority layers and shared entity ownership.
- Added active contract router and global contracts: `.memory-bank/contracts/index.md`, `.memory-bank/contracts/api-guidelines.md`, `.memory-bank/contracts/agent-chat-bus.md`, and `.memory-bank/contracts/message-envelope.md`.
- Updated `.memory-bank/spec-backbone.md` to `Global Backbone Status: complete`, `Mode: standard_ai_first`, `Architecture artifact strategy: single-file`, with all required backbone matrix areas authoritative.
- Updated `.memory-bank/spec-index.md`, feature SDD gate notes, epic open-question routing, testing router, Memory Bank index, and analysis router for the post-`/spec-design` state.
- Did not create TASK records, implementation plans, generated OpenAPI, DB migrations, or feature-local tech specs.

## [2026-06-14] /prd MVP v2 decomposition completed
- Filled active `.memory-bank/product.md` from the clarified MVP v2 PRD.
- Rebuilt `.memory-bank/requirements.md` with REQ-001..REQ-022 and an MVP v2 traceability matrix.
- Added active MVP v2 L2/L3 decomposition: 6 epics under `.memory-bank/epics/` and 16 features under `.memory-bank/features/`.
- Added feature SDD Design Gate notes that require global `/spec-design`, then per-feature `/spec-improve FT-<NNN>`, before `/prd-to-tasks FT-<NNN>`.
- Updated `.memory-bank/testing/index.md`, `.memory-bank/index.md`, `.memory-bank/analysis/index.md`, `.memory-bank/spec-backbone.md`, and `.protocols/PRD-BOOTSTRAP/` routing for the post-`/prd` state.
- Did not create TASK records, implementation plans, global architecture specs, or feature-local tech specs.

## [2026-06-03] /spec-init pre-PRD framing completed
- Marked `.memory-bank/spec-backbone.md` `Pre-PRD Spec Status` as `ready_for_prd`.
- Added active pre-PRD framing artifacts for MVP v2: `.memory-bank/user-scenarios.md`, `.memory-bank/domains/core-domain.md`, `.memory-bank/contracts/boundary-map.md`, and `.memory-bank/states/lifecycle-map.md`.
- Updated `.memory-bank/spec-index.md` as a pure registry and `.memory-bank/index.md` routing so the next command is `/prd`.
- Kept architecture contracts, state machines, schemas, routes, and verification strategy routed to `/spec-design` after `/prd`.

## [2026-06-02] MVP v2 PRD completed and source docs synced
- Created clarified MVP v2 PRD at `.memory-bank/prd.md` with `clarification_status: complete` and Constitution gate passed.
- Synchronized Product Brief, dossier, glossary, invariants, analysis router, spec-index, and Memory Bank index with PRD decisions.
- Fixed MVP runtime/demo boundary: product-agent flows must use real LLM/model-backed agents over actual scoped Plant data; fake/mock/stub outputs are test-only and do not satisfy MVP runtime acceptance.
- Updated routing so the next possible workflow step is `/spec-init` after explicit user instruction; `/prd-to-tasks` remains blocked until `/spec-init`, `/prd`, `/spec-design`, and feature-level `/spec-improve` complete.

## [2026-06-01] MVP v1 spec-layer archived for MVP v2 migration
- Hard-archived the MVP v1 PRD, requirements, epics, features, SDD backbone, contracts, states, domains, runbooks, tech specs, testing docs, and v1 analysis inputs under `.memory-bank/archive/mvp-v1/`.
- Archived old root-level MVP v1 planning/onboarding artifacts `epic_list.md`, `features_list.md`, and `schemas_mermaid.md` under `.memory-bank/archive/mvp-v1/root/`.
- Kept active governance and planning docs for MVP v2: Constitution, invariants, glossary, analysis inputs, migration plan, and routing stubs.
- Replaced active Memory Bank and SDD routing with MVP v2 migration stubs that block `/prd-to-tasks` until `/write-prd`, `/spec-init`, `/prd`, `/spec-design`, and feature-level `/spec-improve` are rerun.
- Updated the active glossary for Accounts/Farm/Admin and Companion governance vocabulary while keeping MVP v1 vocabulary available in the archive.
