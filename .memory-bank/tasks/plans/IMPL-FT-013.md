---
description: Implementation plan for FT-013 Companion IssueStack governance, atomic DecisionRecord effects, and explicit provider-neutral Companion invocation.
status: active
last_updated: 2026-07-31
---
# IMPL-FT-013 — Companion IssueStack Proposals And DecisionRecords

## Goal

Implement one Plant-scoped Companion governance authority: explicit retained
issues, reusable human-attention cycles, superseding proposals, authorized
approve/reject DecisionRecords, atomic safe ordinary-task effects, derived
conclusions, guarded Bus/UI/Timeline projections, and one explicit provider-
neutral `companion` invocation over current PostgreSQL evidence.

## Scope

- closed IssueStack issue, focus, HumanAttentionNeeded, proposal, and
  DecisionRecord persistence and migration;
- Boss and granted-Engineer governance commands through existing
  `role_preset`, Plant grant, and `can_operate`, with no new permission;
- exact `open -> resolved -> closed` issue lifecycle, current focus, active
  attention reuse, proposal supersede, decision satisfaction, and separate
  close command;
- exact `discussion_only|check|measurement|follow_up|none` effect catalog;
- all-or-nothing approve/reject, optional ordinary Task, required Timeline,
  Bus, and UI projections;
- derived-only `CompanionConclusionV1`, exact non-persisted
  `ApprovedGovernanceSummaryV1`, and retained archive reads;
- strict protected IssueStack/detail, explicit run, decision, and close HTTP;
- exact HTTP view/ref/nullability/order schemas and total typed runtime,
  classifier, and governance error translation;
- idempotency fingerprints, row locking, uniqueness, conflicts, and current
  authorization/archive races;
- deterministic latest completed check-in plus exactly one latest manual-
  measurement row without cross-row pH/EC synthesis;
- strict `CompanionProviderRequestV1`/`CompanionModelResultV1`, one explicit
  trigger, MessageEnvelope/classification handoff, and proposal persistence;
- deterministic, PostgreSQL, HTTP, context-hygiene, compatibility, outbound-
  spy, and anti-cheat evidence.

## Non-goals

- a new permission envelope, `plant_approve_actions` reuse, self-approval ban,
  Farm-level IssueStack, time expiry, reopen, or hard delete;
- physical-action approval, `action` Task, target/quantity/device command,
  Plant-state mutation, automated actuation, Task completion, or Outcome;
- persisted CompanionConclusion, separate IssueStack table, acknowledgement
  command, arbitrary focus command, generic workflow-effect plugin, or typed
  failed/no-effect DecisionRecord;
- automatic domain-event, Task-completion, feed-refresh, startup, scheduler,
  worker, or reconciliation model triggers;
- public prompts/provider selection, raw chat, agent memory, Team/tools/RAG,
  fallback model, fake/canned production output, provider-result storage, or a
  persisted Companion runtime receipt/MessageEnvelope replay store;
- frontend/PWA components, owned by FT-016.

## Ordered implementation strategy

### 1. IssueStack and proposal authority

1. Add the cohesive `backend/app/companion_governance/` aggregate with strict
   ORM records, repository locks, fingerprints, IssueStack/conclusion read
   models, and the internal validated proposal-persistence transaction.
2. Add the first post-FT-012 migration for all four governance tables,
   restrictive/deferrable UUID relations, partial/natural uniqueness, exact
   checks, and strict Companion UI variants. Creating the DecisionRecord table
   here preserves terminal proposal/attention FKs; this wave exposes no
   decision command and creates no DecisionRecord row.
3. Reuse ActorContext and existing Plant access primitives. Internal proposal
   persistence allows Boss or a currently granted Engineer with
   `can_operate=true`; Consultant has authorized reads only; archive and
   current grant/version races fail closed.
4. Implement focus, new/existing issue targeting, active-attention reuse,
   proposal sequence/supersede, run fingerprint idempotency, same-run
   single-effect races, and distinct-run serialized supersede/refocus as one
   PostgreSQL transaction.
5. Persist exact attention/proposal UI projections and issue/proposal Timeline
   refs atomically. Add strict IssueStack/detail and retained feed reads with
   canonical status-rank pagination, no-store, redaction, and no public
   mutation route. Verify the Companion read router through an isolated test
   app; do not edit production `main.py` in this wave.
6. Verify PostgreSQL round trips, constraints, focus/supersede concurrency,
   projection rollback, archive/restore, and absence of run/decision/Task/Bus/
   provider/physical-action authority.

### 2. Simplify the implemented proposal aggregate

1. Add forward revision `ft013_simplify_companion` after
   `ft012_simplify_follow_up_runtime`; do not rewrite the applied aggregate
   migration. Drop only
   `companion_human_attention.current_proposal_id` and its cyclic FK while
   preserving all authority and projection rows.
2. Resolve the active current proposal through the existing unique pending
   proposal index plus `proposal.attention_id`. Reuse active attention without
   mutating its version during supersede; later satisfaction remains the only
   attention-version transition.
3. Replace retained full-graph equivalence validation with scope-filtered reads
   and strict public response serialization for supported application paths.
4. Rebuild and overwrite a proposal's derived UI projection from authoritative
   proposal state during supersede. Missing or stale presentation no longer
   blocks the authority transition; real projection persistence or Timeline
   failure still rolls the transaction back.
5. Preserve public issue/detail/OpenAPI shapes, authorization, archive/grant
   guards, proposal uniqueness, same-run idempotency, distinct-run
   serialization, Timeline redaction, and all Safety/Task authority boundaries.
6. Complete this repair before the DecisionRecord wave so TASK-042 implements
   only the simplified current-proposal semantics.

### 3. Binding DecisionRecords and atomic workflow effects

1. Add the next ordered FT-013 migration after the current repository head
   `ft008_lazy_introductions`, retaining `ft013_simplify_companion` in its
   ancestry, for the narrow TASK-039 `governance_decision` Task source,
   DecisionRecord Bus domain-ref constraints, and nullable authorization scope
   only for backend domain adapters.
2. Implement approve/reject with the Plant/current-focus/target lock order,
   expected proposal version, active-attention identity, canonical request
   fingerprint, exact closed effect, and optional issue resolution. Open
   unfocused proposals remain decidable: `keep_open` atomically transfers focus
   to the target, while `resolved` leaves another issue's focus unchanged.
   Unknown/mismatched effects reject the whole decision; rejection forces
   `none`.
3. Call the existing TASK-039 ordinary-task service inside the same Session/UoW
   for `check|measurement|follow_up` after the locked pending version-1 proposal
   has been transitioned and flushed as approved version 2 for the same
   DecisionRecord. The Task seam accepts that exact same-UoW or committed-retry
   graph and rejects every other terminal/link state without an intermediate
   commit. `discussion_only|none` create no Task; every effect/projection/audit
   failure rolls back the DecisionRecord and all transitions.
4. Implement the separate resolved-issue close command and complete the
   derived CompanionConclusion read cases without persisting a conclusion,
   including open/unfocused `awaiting_human` and `decided`. Close exact
   attention/proposal/DecisionRecord ordering, canonical refs, conclusion
   nullability, and the complete reachable nested Task-to-Companion HTTP error
   translation in the same slice.
5. Add decision/proposal UI updates, approved-only DecisionRecord Bus facts,
   repository-resolved exact `ApprovedGovernanceSummaryV1` agent context, exact
   decision/resolve/close Timeline events, and strict decision/close HTTP
   errors/OpenAPI behavior. The context DTO is derived, never persisted, and
   is not `CompanionConclusionV1`.
6. Verify all effects, authority, retries/concurrency, rollback injection,
   archive/no-replay, context hygiene, and FT-008/FT-012 compatibility.
   Decision/close route tests use an isolated test app; this wave also does not
   edit production `main.py`.

### 4. Explicit provider-neutral Companion invocation

1. Add competence-specific command, authorized PostgreSQL input assembler,
   provider request, strict model result, pending MessageEnvelope mapping,
   classifier route, and orchestration under the governance package. Do not
   widen generic `ProviderRequestV1`.
2. Send only the canonical Companion definition plus active Plant, selected
   open issue when present (including its exact persisted `summary_text`), the
   check-in selected by
   `(recorded_at DESC,check_in_id DESC)`, and exactly one measurement selected
   by `(measured_at DESC,measurement_id DESC)` in fixed order. Never merge
   latest pH and EC from different rows. Exclude Farm/auth/UI/Bus/Timeline/
   chat/proposal-history/prompt/provider internals and arbitrary fields.
3. Register the complete Companion router exactly once in production
   `backend/app/main.py` after both TASK-042 and TASK-040, then expose only the
   protected explicit run POST as an invocation trigger. GET, feed refresh,
   domain events, Task completion, startup, and reconciliation remain
   side-effect free.
4. Reuse the strict provider-neutral executor seam, no fallback, sanitized
   Agent Runtime audit, and the existing strict project classifier. Production
   remains unbound and fail-closed until a future endpoint choice; deterministic
   tests inject explicit Companion and Safety fakes/spies and prove exactly one
   call to each on a successful proposal path. Task effects require exact persisted
   `safe_task_request` kind; non-task effects require `safe_information`;
   physical/blocked/mismatched output writes no governance row.
5. Keep provider I/O outside transactions and repeat current session/grant/
   Plant/issue guards before proposal persistence. Use run id/fingerprint plus
   repository uniqueness for one product effect under retries/concurrency. An
   early committed duplicate returns only persisted proposal/classification
   refs with `runtime_outcome=null`; it performs no provider call, envelope
   reconstruction, or persisted runtime-receipt lookup.
6. Add deterministic schema/outbound/trigger/race/provider tests covering
   timeout/error, redaction, no fallback, and unbound production.

## Accepted provider-input policy

The owner removed the blanket prohibition on sending models unapproved
governance content. Registered agent-specific requests may include authorized
typed governance context that remains untrusted and non-authoritative. The
current FT-013 allowlist includes persisted open-Issue `summary_text` for an
authorized explicit Companion `existing_issue` request. The value is copied unchanged
from the exact current PostgreSQL issue after Plant/issue/version guards; a
`new_issue` request sends none. Sending it grants no downstream authority,
does not admit proposal/rationale/decision/history/caller content, and adds no
generic schema, persistence, permission, or approval pipeline. Deterministic
outbound spies own the positive field assertion and negative exclusion matrix.

## Dependencies and waves

- Global Planning Revision is 2. Fresh `/review-tasks-plan FT-013` review for
  that revision is `APPROVE`; task promotion and execution remain separate
  workflow actions.
- Foundation gate `TASK-004-T2-FT-000-W0` is satisfied transitively through
  the existing dependency chain.
- `TASK-041-T3-FT-013-W1` depends directly on
  `TASK-039-T3-FT-012-W1` for the implemented classifier persistence chain.
  TASK-041 implemented its aggregate migration after the historical
  `ft012_runtime_dispositions` head. Completed TASK-040 added
  `ft012_simplify_follow_up_runtime` after that aggregate migration and
  advanced the exact-head assertions without rewriting either applied
  revision.
- `TASK-044-T3-FT-013-W1` depends on TASK-041 and TASK-040. TASK-041 and
  TASK-044 are `done`; together they establish the simplified W1 proposal
  authority at revision `ft013_simplify_companion`. Terminal TASK-046 later
  advanced the repository migration head to `ft008_lazy_introductions`
  without changing the FT-013 authority.
- `TASK-042-T3-FT-013-W2` is `done`. It consumed TASK-044, TASK-041, and
  TASK-040, implemented the DecisionRecord/effect boundary, and added
  `ft013_decision_effects` after `ft008_lazy_introductions` while preserving
  Companion, Plant State, Agent Chat lazy-introduction, Safety Gate, Task
  Follow-Up, and older exact-head contracts.
- `TASK-043-T3-FT-013-W3` depends on TASK-042 and
  `TASK-040-T3-FT-012-W2`, because it composes the completed FT-013 governance
  boundary with the implemented competence-specific provider/classifier
  pattern and shared provider files. TASK-043 is `done`: its execution
  attempts implemented the strict runtime contracts, exact PostgreSQL input
  assembler, pending-envelope/classifier hold, guarded proposal handoff,
  protected run route, explicit unbound production bindings, and one complete
  production Companion router registration. Execution Attempt 02 repaired the
  bounded provenance wiring defect found by adversarial verification:
  MessageEnvelope keeps the model-selected subset while governance persistence
  receives the complete ordered provider-request refs.
- The feature lifecycle is `verified`: every indexed FT-013 task is terminal
  `done`, and TASK-043 Attempt 02 has fresh independent functional `PASS`,
  per-task `semantic-pass`, exact human checkpoint, and explicit owner closure.
- TASK-041/TASK-042 built and verified the Companion router in isolated test
  apps without touching `main.py`; TASK-043 is the only FT-013 production-
  registration owner. Its execution preserved the shared `main.py`/provider
  composition boundary and the FT-008 feed/lazy-introduction behavior already
  present after TASK-046.

## Expected touched files

These paths are advisory and non-exhaustive planning hints. They are not a
hard write allowlist; the task's semantic scope, direct canonical specs,
`forbidden_scope`, and `stop_conditions` govern execution.

IssueStack/proposal-authority slice:

- `backend/app/companion_governance/`
- `backend/app/agent_chat/contracts.py`
- `backend/app/agent_chat/models.py`
- `backend/app/agent_chat/publication.py`
- `backend/app/api/companion.py`
- `backend/app/api/feed.py`
- `backend/app/api/__init__.py`
- `backend/app/timeline/writer.py`
- `backend/migrations/versions/*_ft013_companion_governance_aggregate.py`
- focused proposal lifecycle/migration/projection/read-API tests plus all
  exact-head regressions, including Safety Gate and Task Follow-Up.

Aggregate-simplification slice:

- `backend/app/companion_governance/`
- `backend/migrations/versions/*_ft013_simplify_companion_aggregate.py`
- focused proposal lifecycle, projection, migration/model, and read-API tests;
- current exact-head regression tests across Access/Admin, Plant Operations,
  Photo Intake, Plant State, Agent Chat, Safety Gate, Task Follow-Up, and the
  Foundation database contract.

Decision/effect slice:

- `backend/app/companion_governance/`
- `backend/app/task_follow_up/`
- `backend/app/agent_chat/` strict DecisionRecord Bus/UI compatibility;
- `backend/app/access_admin/context_builders.py`
- `backend/app/api/companion.py`
- `backend/app/api/feed.py`
- `backend/app/timeline/writer.py`
- `backend/migrations/versions/*_ft013_companion_decision_effects.py`
- focused decision/effect/context/migration/API, Task Follow-Up, Agent Chat,
  and all exact-head regression tests, including Companion, Plant State,
  Agent Chat lazy introductions, Safety Gate classification/migration, and
  Task Follow-Up.

Explicit-runtime slice:

- `backend/app/companion_governance/` for competence-specific contracts,
  assembler, orchestration, and production composition;
- `backend/app/agent_runtime/providers.py`
- `backend/app/agent_runtime/__init__.py`
- `backend/app/api/companion.py`
- `backend/app/main.py`
- `tests/backend/companion_governance/test_runtime.py`
- `tests/backend/api/test_ft013_companion_run_route.py`
- `tests/backend/api/test_ft013_companion_app_registration.py`
- `tests/backend/api/test_ft008_feed_routes.py`
- `tests/backend/agent_chat/test_ft008_lazy_introductions.py`
- `tests/backend/agent_runtime/test_ft007_roster_providers.py`.

The runtime slice also executes the existing Plant Operations and direct
Safety classifier suites (`test_classifier.py`,
`test_classification_persistence.py`, and Safety migration compatibility) as
read-only regressions. It must not widen or silently repair their owning
contracts to make Companion pass.

The roster already contains `companion`. Generic runtime/envelope/classifier
contracts, Plant operations, Access/Admin, and completed FT-012 authority are
touched only for a narrowly proven compatibility edit; execution stops on a
public-contract widening need.

## Source artifacts

- `.memory-bank/features/FT-013-companion-issuestack-proposals-decisionrecords.md`
- `.memory-bank/epics/EP-005-companion-governance.md`
- `.memory-bank/requirements.md` (`REQ-003`, `REQ-004`, `REQ-010`, `REQ-011`,
  `REQ-013`, `REQ-016`, `REQ-017`, `REQ-018`, `REQ-022`)
- `.protocols/FT-013/decision-log.md`
- the three FT-013 behavior specs.

## Normative inputs and direct design links

- `.memory-bank/architecture/system-architecture.md`
- `.memory-bank/states/companion-governance.md`
- `.memory-bank/domains/companion-governance.md`
- `.memory-bank/contracts/companion-governance-http.md`
- `.memory-bank/contracts/companion-runtime.md`
- `.memory-bank/testing/companion-governance.md`
- `.memory-bank/domains/plant-operations.md`
- `.memory-bank/contracts/access/actor-context.md`
- `.memory-bank/states/plants/plant-and-access-lifecycle.md`
- `.memory-bank/states/task-follow-up-lifecycle.md`
- `.memory-bank/domains/task-approval-outcomes.md`
- `.memory-bank/contracts/task-approval-http.md`
- `.memory-bank/contracts/agent-chat-bus.md`
- `.memory-bank/contracts/ui-feed.md`
- `.memory-bank/domains/agent-chat-ui-feed-storage.md`
- `.memory-bank/contracts/plant-feed-http.md`
- `.memory-bank/contracts/timeline-event.md`
- `.memory-bank/states/safety-action-lifecycle.md`
- `.memory-bank/contracts/safety-gate-runtime.md`
- `.memory-bank/domains/safety-action-routing.md`
- `.memory-bank/testing/safety-gate.md`
- `.memory-bank/contracts/message-envelope.md`
- `.memory-bank/contracts/agent-runtime-adapter.md`
- `.memory-bank/contracts/agent-model-provider-profiles.md`
- `.memory-bank/contracts/agent-roster-bootstrap.md`
- `.memory-bank/runbooks/agent-runtime-providers.md`

## Constraints and invariants

- PostgreSQL governance records are mutable authority. Timeline, Bus, UI,
  MessageEnvelope, classification, model output, and derived conclusion cannot
  independently create, replay, or transition them. Derived proposal UI rows
  may be rebuilt from the owning proposal authority.
- Governance authority is Boss or granted Engineer with current
  `can_operate`; there is no extra permission and Consultant never decides.
- One Plant has at most one focused issue; one issue has at most one pending
  proposal and one active attention cycle. Active current proposal identity is
  derived from the unique pending row and `proposal.attention_id`;
  superseded/terminal proposals never become current or approvable.
- Focus is independent for open conclusion reads. Open/unfocused issues remain
  `awaiting_human` with an active/current pair or `decided` after keep-open;
  deciding an unfocused pending issue with `keep_open` transfers focus under
  the existing Plant lock.
- IssueStack order and continuation are exactly
  `(status_rank,created_at,issue_id)` with `open=0`, `resolved=1`, and
  `closed=2` in both repository and HTTP cursor semantics.
- DecisionRecord effects are closed, exact, current-authority checked, and
  atomic. No path grants Safety, action, Plant-state, device, completion, or
  Outcome authority.
- The operative Task call consumes only the flushed approved-version-2 proposal
  linked to the same DecisionRecord in the caller-owned UoW, or its identical
  committed retry; no source pre-commit or second Task writer exists.
- Only a valid approved DecisionRecord ref may enter Bus; UI rows stay
  human-facing and non-consumable; raw proposal/rationale/chat/provider data
  enters neither.
- Agent context reconstructs exactly `ApprovedGovernanceSummaryV1`; it does not
  expose mutable conclusion/focus/attention or proposal/task text.
- Archive retains rows and authorized reads but denies runs/transitions/
  publication/effects. Restore reopens no row and replays no denied work.
- Companion execution uses strict provider-neutral `companion` and
  `safety_gate` seams, typed requests, one explicit trigger, and no fallback.
  Production remains unbound and fail-closed; test fakes/spies are explicit
  and cannot become fake/silent production acceptance.
- A committed run duplicate is a governance/classification-ref result with
  `runtime_outcome=null`; it never replays a MessageEnvelope or requires a
  persisted runtime receipt.
- Different run ids are independent commands and may both commit in locked
  serialization order; only same-run identity is single-effect idempotency.
- FT-013 refs, source-ref arrays, detail ordering, and conclusion nullability
  use the one exact data/HTTP grammar. Public reads validate ownership and
  serialization; projections may be repaired only from authoritative proposal
  rows.

## Verification targets

- exact lifecycle/data/API/runtime matrices, restrictive migration/FKs,
  partial uniqueness, status-rank cursor ordering, request fingerprints, row
  locking, and retry conflicts;
- Boss/Engineer/Consultant, grants, archive/restore, focus, attention reuse,
  supersede, decide, resolve, and close;
- all five effects, matching classification, ordinary Task source/atomicity,
  same-UoW phase eligibility, nested Task failure translation, rollback
  injection, and zero action/Plant/device authority;
- exact Timeline cardinality/redaction, Bus/UI projection identity,
  exact ApprovedGovernanceSummary reconstruction, retained feed reads, and
  existing FT-008 compatibility;
- strict explicit-run HTTP/OpenAPI/no-store/no-leak behavior and proof that no
  non-trigger invokes a model;
- exact Companion outbound allowlist, deterministic one-row evidence
  selection, result matrix, pending envelope, null-outcome duplicate branch,
  same-run versus distinct-run races, classification, current-guard races,
  provider-neutral composition, single production router registration, and
  deterministic two-spy/two-call proposal evidence.

## Quality gates and UAT

- Run task-specific commands from
  `.memory-bank/testing/companion-governance.md`.
- Run exact-head compatibility tests after each ordered FT-013 migration,
  including current Companion, Plant State, Agent Chat lazy-introduction,
  Safety Gate classification/migration, Task Follow-Up, and older assertions.
- Run `node scripts/mb-lint.mjs` and `git diff --check` at applicable planning
  and wave boundaries.
- Run the full deterministic suite before handoff when the environment permits.
- Current acceptance uses deterministic Companion and Safety fake/spy evidence,
  including timeout, provider error, invalid output, post-I/O denial,
  redaction, and unbound production. It does not require a provider, model,
  base URL, credential, egress, network call, or non-skipped live smoke.
- Real image/request/response, error, timeout, redaction, and cost verification
  is deferred to the shared future selected-endpoint milestone and is not
  required by current deterministic acceptance.
- Browser Companion cards remain FT-016; backend JSON/OpenAPI behavior is
  verified here.

## Execution handoff

- Run fresh `/review-tasks-plan FT-013` for Global Planning Revision 2 before
  selecting either remaining card; the Planning Revision 1 approval is
  historical only.
- Planning does not select or promote the remaining `planned` cards.
- Execution and lifecycle handling follow each indexed task card and the
  canonical tier policy; task-specific evidence remains outside this plan.
- Durable state is reconciled at the applicable wave boundary.
- The cards intentionally omit a hard `write_boundary`: `touched_files` is
  advisory, while `forbidden_scope` and `stop_conditions` remain hard.
