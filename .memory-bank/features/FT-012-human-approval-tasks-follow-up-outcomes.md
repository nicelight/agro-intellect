---
description: FT-012 Human Approval Tasks And Follow-Up Outcomes.
status: draft
type: feature
feature_id: FT-012
epic: EP-004
lifecycle: planned
last_updated: 2026-07-20
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/states/lifecycle-map.md
spec_design_status: complete
spec_design_links:
  - .memory-bank/states/task-follow-up-lifecycle.md
  - .memory-bank/domains/task-approval-outcomes.md
  - .memory-bank/contracts/task-approval-http.md
  - .memory-bank/contracts/task-follow-up-runtime.md
  - .memory-bank/testing/task-follow-up.md
  - .memory-bank/domains/safety-action-routing.md
  - .memory-bank/states/safety-action-lifecycle.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
  - .memory-bank/states/plant-state-trust.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/contracts/safety-gate-runtime.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/contracts/agent-roster-bootstrap.md
  - .memory-bank/contracts/timeline-event.md
  - .memory-bank/runbooks/agent-runtime-providers.md
---
# FT-012 Human Approval Tasks And Follow-Up Outcomes

## Use Cases

- Authorized Boss or Engineer approves or rejects a physical-action proposal after Safety Gate pass.
- Approved physical action creates a human-performed `action_task`.
- Users complete checks, measurements, approved action tasks, and follow-up tasks.
- Follow-up outcome preserves evidence and audit trail.

## Acceptance Criteria

- Human approval unlocks only human-performed task tracking, never automated execution.
- `action_task`, `check_task`, measurement tasks, and follow-up outcomes are separated.
- A `safe_task_request` classification may create only its ordinary
  check/measurement/follow-up task through backend rules; it bypasses neither
  task authorization nor evidence checks and can never create `action_task`.
- A classified ordinary-message handoff is one-shot: its first current-guard
  evaluation is durably consumed or denied in PostgreSQL. A denial caused by
  current Plant/archive/authorization state cannot become operative after
  restore with the same `run_id` or `message_id`; a new Agent Runtime
  invocation with both new identities is required.
- A post-model `task_follow_up` current-guard decision is also one-shot before
  MessageEnvelope/classification: one immutable run/fingerprint disposition is
  either terminally denied or hands off exactly one post-guard message. It
  cannot conflict with the downstream classified-message disposition, and the
  same run never allocates another message after restore or retry.
- TASK-040 proves that boundary with one exact consumed-success lock-order
  fixture and four barrier-controlled orders. Eligible-first finishes consumed
  before its peer resolves `ALREADY_CONSUMED`; denied-first makes both peers
  return the same stored denial; late-denial-first returns classification-only
  `HANDOFF_INCOMPLETE` before the classified writer succeeds; classified-
  writer-first succeeds before the late peer resolves `ALREADY_CONSUMED`.
  These are exact outcomes, not scheduler-dependent alternatives; canonical
  row/call/audit/rollback counts live in the Task Follow-Up testing spec.
- Only successfully audited post-model guard denial or speak/envelope handoff
  owns that two-value row; context/config/provider/output/passing-guard silence/
  audit failures create none. Same-run handed-off conflict, incomplete,
  non-taskable, downstream denied/consumed, and replay-blocked states return the
  strict task-local disposition result without changing global Agent Runtime.
- Follow-up outcome captures exactly
  `improved|worsened|unchanged|no_data`; non-`no_data` values require evidence
  refs.
- Task and approval records preserve ActorContext, Plant scope, source refs, and audit refs.
- Archived Plant preserves task/approval/follow-up records but blocks their
  transitions until restore and current-guard revalidation.

## Edge Cases & Failure Modes

- Expired or stale approval cannot create action_task.
- Actor without `plant_approve_actions` cannot approve Plant physical action.
- Replayed or superseded approval cannot unlock action.
- Follow-up cannot mutate confirmed Plant state without required evidence/review rules.
- Archive must not complete, cancel, execute, or advance an open task; restore
  must not resume it automatically.
- Restore must not re-evaluate a terminally denied classified-message
  disposition or turn its retained envelope/classification into a Task.
- Restore must not turn a pre-classification runtime denial into an operative
  run. A conflicting same-run command fails closed; reevaluation requires a
  new command/run and then a new post-guard message.
- A committed handoff interrupted before classifier or Task writer is not
  replayed: exact retry resolves its persisted absent/non-taskable/denied/
  consumed downstream state without any model/classifier/Task call, then
  requires a new run for fresh evaluation.
- A consumed handoff is a duplicate only when an independent immutable
  classified-disposition commitment matches the Task create fingerprint and
  canonical text/kind/ordered-source preimage, while scope/agent/ActorContext
  attribution matches separately. PostgreSQL makes that commitment write-once:
  coordinated Task/classification plus both-digest replacement aborts and
  rolls back, while Task-only corruption remains a redacted null-ref failure.
  Missing legacy commitment or any corrupt graph fails with the existing
  error; raw candidate text and the full MessageEnvelope remain transient.

## Verification Targets

- Unit: approval authority and task state transitions after spec defines state model.
- Integration: approval creates action_task only through Safety Gate path.
- Integration: open task/approval/follow-up state is unchanged by archive,
  blocked while archived, and revalidated after restore.
- Integration: a classified ordinary message denied by a current guard remains
  denied after restore for the same run/message identities, while a new
  invocation with new identities may pass current guards.
- Integration: post-model archive/revoke denial persists before envelope
  creation; identical/conflicting/concurrent same-run calls, disposition
  commit failure, runtime-versus-classified race, and new-identity eligibility
  are deterministic PostgreSQL cases.
- Integration: Task text mutation with a recomputed Task-owned fingerprint,
  actor/source/classification/canonical-ref mutations, missing/wrong independent
  commitment, all three coordinated ATTEMPT 05 replacements rejected by the
  PostgreSQL write-once guard, no-self-derived legacy migration, rollback, and
  all prior groups 1-7 fail closed or preserve their exact accepted results.
- E2E: approved human-performed action creates follow-up and outcome evidence.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Safety & Task Loop module.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): Task, Approval, Outcome ownership.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): backend approval authority checks.
- [.memory-bank/states/safety-action-lifecycle.md](../states/safety-action-lifecycle.md): approval, human-performed action task, and follow-up boundary.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): audit/export refs for tasks, approvals, and outcomes.
- [.memory-bank/states/plants/plant-and-access-lifecycle.md](../states/plants/plant-and-access-lifecycle.md): global archived-Plant operational guard.

## Feature-Local Design Pressure

- Resolved by the linked Task/Approval/Outcome data, lifecycle, HTTP, provider-neutral
  `task_follow_up` runtime, Timeline, and verification subject specs.

## Behavior specs

- `.memory-bank/behavior-specs/FT-012-BHV-001-approval-follow-up-outcome.behavior.json`
- `.memory-bank/behavior-specs/FT-012-BHV-002-retry-conflict-archive.behavior.json`
- `.memory-bank/behavior-specs/FT-012-BHV-003-real-agent-ordinary-task.behavior.json`

## Current W1 Boundary Evidence

- `TASK-039-T3-FT-012-W1` is scheduler-recorded `done` using only current
  ATTEMPT 03 implementation `PASS`, independent functional `VERDICT: PASS`,
  separate `SEMANTIC_VERDICT: semantic-pass`, and immutable closure evidence.
  ATTEMPT 01 and ATTEMPT 02 remain preserved failed history.
- The implemented W1 boundary owns the authoritative PostgreSQL Approval,
  ordinary/action Task, automatic +48-hour follow-up, and Outcome loop; the
  immutable `ordinary_task_dispatch_dispositions` table records each
  classified ordinary handoff as terminal `consumed|denied`. Current
  ActorContext/Plant/evidence guards, archive/no-replay, idempotency,
  concurrency, rollback, strict HTTP/raw-path validation, branch-exact
  Timeline refs, and zero device or Plant-state effects are independently
  verified.
- The accepted W1 boundary remains `ft012_task_approval_outcomes` directly
  after `ft011_safety_action_decisions`. The current accumulated TASK-040 work
  has advanced the repository Alembic head and all eight exact-head consumers
  to the still-unclosed additive `ft012_runtime_dispositions` revision; this is
  implementation state, not TASK-040 closure evidence.
- `TASK-040-T3-FT-012-W2` is scheduler-recorded `failed` from the current
  ATTEMPT 05 semantic failure: the independent commitment was insert-correct
  but PostgreSQL still permitted coordinated replacement. Explicit owner
  recovery authorizes exactly ATTEMPT 06 with effective task limit `6`, one
  recovery attempt, and unchanged global maximum `5`. This reconciliation
  changes no lifecycle/status and does not consume ATTEMPT 06; planning review,
  failed-to-planned recovery, strict doctor, promotion, and selection remain
  scheduler-owned gates. FT-012 lifecycle remains `planned` pending the open
  wave and explicit owner decision.
- No provider/model/base URL/Gemini/credential/egress/network/live-smoke
  result was required, checked, or claimed for W1. The absent human checkpoint
  was accepted by the scheduler as an advisory T3 process gap.

## SDD Design Gate

- Global/shared status: complete; `AD-008` and Safety Action Lifecycle define the exact
  safe-task versus physical-action route; `AD-007` and Plant lifecycle define
  retained-but-frozen records and restore revalidation.
- Feature-local status: complete. The canonical design defines closed
  Task/Approval/Outcome states, exact FT-011 handoff and expiry reuse,
  transactional approval/action/follow-up/outcome uniqueness, persisted
  idempotency fingerprints, protected HTTP commands, Timeline refs, archive
  races, and the strict typed `task_follow_up` path. The runtime path now has a
  narrow immutable pre-classification disposition plus the existing downstream
  classified disposition, coordinated by one short run lock without model-I/O
  transaction. No scheduler, worker, outbox, device effect, generic run ledger,
  or second proposal state machine is introduced.
- Current code-phase closure uses test-only fake/spy Task Follow-Up and Safety
  classifier executors; production has no fake fallback and fails closed while
  unbound. Real endpoint calls are deferred to the shared future milestone.
