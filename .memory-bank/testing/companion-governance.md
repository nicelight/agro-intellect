---
description: Verification contract for FT-013 IssueStack governance, atomic DecisionRecord effects, projections, and explicit real Companion invocation.
status: active
type: testing_spec
last_updated: 2026-07-18
source_of_truth:
  - .memory-bank/features/FT-013-companion-issuestack-proposals-decisionrecords.md
  - .memory-bank/states/companion-governance.md
  - .memory-bank/domains/companion-governance.md
  - .memory-bank/contracts/companion-governance-http.md
  - .memory-bank/contracts/companion-runtime.md
  - .memory-bank/domains/plant-operations.md
  - .memory-bank/contracts/safety-gate-runtime.md
  - .memory-bank/domains/safety-action-routing.md
---
# Companion Governance Verification

## Scope

Defines deterministic, PostgreSQL, HTTP, concurrency, compatibility, runtime,
and credentialed product-agent evidence for FT-013 from explicit Companion run
through current proposal, human DecisionRecord, optional ordinary Task, and
retained IssueStack conclusion.

## Authorization and lifecycle matrix

- Boss and a granted Engineer with current `can_operate=true` may run,
  approve/reject, and close; Consultant, missing/revoked Plant grant, disabled
  identity, wrong Farm, or archived Plant fails closed. No governance-specific
  permission and no self-approval restriction exists.
- A successful new-issue run creates one focused `open` issue; an existing
  run requires exact open issue/version and focuses it without changing state.
  Partial uniqueness proves at most one focused issue per Plant.
- The only issue path is `open -> resolved -> closed`. Decision selects
  `keep_open|resolved`; close is a separate human command; resolved/closed
  issues reject new proposals and closed rows are immutable.
- Focus transfer preserves open issue state and readable conclusions. Tests
  cover open/unfocused `awaiting_human` with active attention/current pending
  proposal and open/unfocused `decided` with satisfied attention/latest
  keep-open DecisionRecord. Deciding an unfocused pending issue with
  `keep_open` atomically clears another focus and focuses the target; `resolved`
  leaves another issue's focus unchanged.
- One active HumanAttentionNeeded cycle points to one current pending proposal.
  A new accepted proposal supersedes the current proposal and reuses/updates
  active attention. Approve/reject satisfies it; a later explicit run may
  create a new attention sequence.
- CompanionConclusion is derived from retained authority on every read; tests
  prove no conclusion table, Bus row, UI row, Timeline event, or second
  confirmation command exists.

## Domain, migration, and concurrency matrix

- PostgreSQL inspection proves exact enums/checks, native UUID/FK parity,
  restrictive deletes, partial uniqueness, deferrable first attention/proposal
  relation, request ids/fingerprints, record versions, Timeline refs, and two
  ordered additive migrations: governance aggregate after the actual FT-012
  head, then decision-effect Task/Bus compatibility.
- Each FT-013 migration test advances every dependency-created exact-head
  assertion, including Safety Gate and Task Follow-Up migration-model tests;
  no required gate may leave them pinned to the preceding revision.
- Same-run, decision, and close duplicates return the first committed canonical
  result. Reused identity with different content, stale version, wrong current
  attention/proposal, or terminal row conflicts without replacement.
- Concurrent attempts with the same run id and concurrent decisions exercise
  unique-race re-read and commit exactly one product effect. Different run ids
  are independent commands: controlled-lock tests prove both may commit in
  serialization order, with the later existing-issue writer superseding the
  earlier pending proposal or the later new-issue writer becoming the sole
  focus. Provider finish time/requested time is not governance order, and no
  provider I/O is held inside a PostgreSQL transaction.
- Archive, membership, grant, issue-version, and proposal-supersede races are
  rechecked at the authoritative write boundary and write nothing on denial.
  Restore performs no replay.

## DecisionRecord and workflow-effect matrix

- The closed proposal/decision effect enum is exactly
  `discussion_only|check|measurement|follow_up|none`; `action`, unknown values,
  and mismatched persisted classification reject the whole decision.
- Approval copies the proposed effect; rejection records `none` regardless of
  proposal. `discussion_only|none` create no Task. Each operative effect
  creates exactly one same-kind ordinary Task with
  `source_type=governance_decision` and the unique DecisionRecord source.
- DecisionRecord, proposal/attention/issue transitions, ordinary Task,
  required Timeline events, and Bus/UI projections are one transaction.
  Injected Task, projection, audit, or persistence failure rolls everything
  back: no typed failed/no-effect DecisionRecord is retained.
- DecisionRecord never authorizes Safety approval, `action` Task, Plant-state
  mutation, device command, Task completion, or Outcome.
- The governance task effect uses the single canonical
  `OrdinaryTaskCreateCommandV1/source_branch=governance_decision` branch with
  exact sources, natural key, fingerprint, current guards, created/duplicate/
  conflict behavior, and caller-owned UoW. Tests prove the Task service does
  not commit/roll back that UoW and no competing Task writer exists. The
  proposal is locked pending/version 1 at decision start, then flushed
  approved/version 2 and linked to that same DecisionRecord before the Task
  call; committed duplicate succeeds, while pending-at-entry, rejected,
  superseded, or differently linked approved sources fail atomically.

## Timeline, Bus, UI, and context matrix

- Exact Timeline types, safe payload summaries, actor attribution, cardinality,
  persisted refs, and append failure behavior follow the registry. No raw
  issue/proposal/decision/Task text, auth data, prompt, or provider payload is
  emitted.
- Only a valid committed approved DecisionRecord reference enters Agent Chat
  Bus; a rejected DecisionRecord remains retained human governance history and
  produces no agent fact.
  Existing FT-008 variants remain valid; backend `domain_record` alone permits
  null authorization scope; actor-originated publication still requires it.
- Attention/proposal/decision UI projections use their exact authoritative ids,
  remain non-agent-consumable, update terminal state idempotently, and reject a
  canonical content conflict atomically. All three authorized roles may read
  them; Consultant still has zero run/decision/close authority.
- Context builders resolve the allowed DecisionRecord reference through the
  governance repository into exactly `ApprovedGovernanceSummaryV1`, including
  canonical ids/refs, approved proposal version, decision/effect/role/time,
  exact DecisionRecord source refs, and
  `safety_gate_authority=not_granted`. They never substitute
  `CompanionConclusionV1` or ingest UI rows, proposal/task text, rationale,
  HumanAttentionNeeded, raw provider output, or mutable governance authority.
  This is the Agent Chat Bus context rule; the explicit Companion provider
  request separately includes the selected Issue's typed `summary_text`.

## HTTP and archive matrix

- Generated OpenAPI and route tests prove the exact issue list/detail, explicit
  run, proposal decision, and close schemas, every field/ref, complete
  nullability matrix, closed enums, bounds, strict unknown-field/query
  rejection, stable errors, no-store, and redaction.
- List pagination proves canonical cursor identity and deterministic
  `(status_rank,created_at,issue_id)` ordering with exact
  `open=0|resolved=1|closed=2` rank continuation and filter/rank rejection.
  Unauthorized scope does not leak Plant/issue/proposal existence.
- Archived authorized reads expose retained human history and derived
  conclusion, while every run/decision/close/Task/provider path is denied.
- Caller cannot submit prompt, proposal text, effect, Task kind/text, provider,
  model, role, grant, classification, or authorization data.
- Detail reads prove active-else-latest attention, ascending proposal and
  DecisionRecord order, deterministic latest DecisionRecord, exact
  `awaiting_human|decided|closed` nullability for focused and unfocused open
  rows, canonical
  `companion_issue|companion_attention|companion_proposal|decision_record`
  refs, and no UI/Timeline fallback on an inconsistent authority graph.
- Parameterized error tests cover every common runtime, classifier, and domain
  branch in the total HTTP mapping, including distinct runtime-audit and
  governance-audit failures, output-invalid versus provider-failed, and
  successful persisted classifier uncertainty.
- Decision-route error tests cover reachable `TASK_COMMAND_FORBIDDEN`,
  `TASK_PLANT_NOT_ACTIVE`, `TASK_VERSION_CONFLICT`, `TASK_SOURCE_INVALID`,
  `TASK_AUDIT_FAILED`, and `TASK_PERSISTENCE_FAILED` translations plus the
  redacted internal fallback for Task codes forbidden to this branch; every
  injected failure rolls the complete decision UoW back.

## Runtime and trigger matrix

- Persisted Companion classification is consumed only through the exact
  server-derived `companion_governance_hold`; it is evidence, not dispatcher
  authority, and adds no persisted consumer-route field.
- Strict request/result tests cover record order and cardinality, new/existing
  target matrix, bounds, effect/task-text matrix, source-ref subset, unknown
  fields, pending MessageEnvelope mapping, classification match, and orchestration
  result nullability.
- Outbound spies prove only authorized PostgreSQL Plant, selected issue, the
  check-in selected by `(recorded_at DESC,check_in_id DESC)`, and the one
  manual-measurement row selected by
  `(measured_at DESC,measurement_id DESC)` cross provider egress. Tests cover
  empty/combined/one-value rows, different latest pH/EC rows, and timestamp
  ties; no values from two rows are merged. An authorized existing-issue
  request carries exactly the persisted matching `companion_issue.summary_text`
  unchanged, while a new-issue request carries no issue summary. Auth/UI/Bus/
  Timeline/attention/proposal/rationale/decision/caller data and every other
  field outside the registered Companion request allowlist are absent.
- Only `POST /api/plants/{plant_id}/companion/runs` invokes `agent_id=companion`.
  GET/detail/feed refresh, domain events, Task completion, startup, and
  reconciliation produce zero calls.
- Deterministic provider tests prove explicit DeepSeek/Gemini binding, no
  default/fallback/fake/canned result, no silent relabel of failures, and no
  governance write on classifier/runtime/guard failure.
- Negative compatibility proves Companion `safe_information` writes no FT-008
  candidate Bus/UI row, Companion `safe_task_request` writes no FT-012 Task,
  held physical/blocked/mismatch/failure writes no governance or ordinary row,
  and retry/restore/reconciliation never replays the held effect. Ordinary
  non-Companion flows remain unchanged.
- Sequential identical run retry returns the committed proposal/classification
  refs with `runtime_outcome=null`, no second provider call, and no transient
  MessageEnvelope reconstruction. No runtime receipt table is persisted.
  Conflicting same-id reuse fails before egress. Same-run concurrent calls may
  perform I/O but still commit one product effect and return duplicate refs
  without pretending the loser's outcome is the committed winner's outcome;
  different run ids follow the explicit serialized multi-effect rule above.

## Credentialed real-model UAT

The explicit smoke uses the production new-issue route, canonical `companion`
and `safety_gate` roster bindings, actual authorized PostgreSQL
Plant/check-in/measurement fixture, production provider factories,
`SafetyGateClassificationService`, classification repository, and governance
repository:

```bash
AGENT_REAL_COMPANION_SMOKE=1 .venv/bin/python -m pytest tests/backend/companion_governance/test_real_companion_smoke.py -m real_model -q
```

It makes exactly one real Companion provider call and one real Safety Gate
provider call, returns the committed strict non-silent proposal plus matching
strict classification, persists that classification and one current
proposal/active-attention result, and creates no Safety decision,
DecisionRecord, Task, action, Plant mutation, or device effect. Explicitly
requested skip/xfail, fake/canned executor or classifier, fallback, silence,
blocked/mismatched classification, either missing binding/call,
unconfigured/provider/output/guard/audit/persistence failure, or missing
persisted proposal fails UAT. Evidence stores only both safe model refs plus
run/event and issue/proposal/attention/classification refs, never prompts, raw
responses, proposal text, credentials, auth state, or hidden reasoning.

## Commands

```bash
.venv/bin/python -m pytest tests/backend/companion_governance -m "not real_model" -q
.venv/bin/python -m pytest tests/backend/api/test_ft013_companion_read_routes.py tests/backend/api/test_ft013_companion_decision_routes.py tests/backend/api/test_ft013_companion_run_route.py tests/backend/api/test_ft013_companion_app_registration.py -q
.venv/bin/python -m pytest tests/backend/safety_gate/test_classifier.py tests/backend/safety_gate/test_classification_persistence.py tests/backend/safety_gate/test_migration_models.py -m "not real_model" -q
.venv/bin/python -m pytest tests/backend/safety_gate/test_migration_models.py tests/backend/task_follow_up/test_migration_models.py tests/backend/companion_governance/test_migration_models.py -q
.venv/bin/python -m pytest tests/backend/access_admin tests/backend/agent_chat tests/backend/task_follow_up tests/backend/companion_governance -m "not real_model" -q
AGENT_REAL_COMPANION_SMOKE=1 .venv/bin/python -m pytest tests/backend/companion_governance/test_real_companion_smoke.py -m real_model -q
.venv/bin/python -m pytest tests -m "not real_model" -q
node scripts/mb-lint.mjs
git diff --check
```

The credentialed command is required for the feature's real-model acceptance;
deterministic task closure must not claim it from mocks or a deferred run.
