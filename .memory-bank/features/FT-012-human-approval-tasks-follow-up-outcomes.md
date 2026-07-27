---
description: FT-012 Human Approval Tasks And Follow-Up Outcomes.
status: draft
type: feature
feature_id: FT-012
epic: EP-004
lifecycle: planned
last_updated: 2026-07-27
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
- `task_follow_up` has no pre-classification runtime ledger or durable delivery
  contract in the current MVP. Each injected invocation follows the linear
  path `invoke -> post-I/O current guard -> sanitized audit -> transient
  MessageEnvelope -> classify -> canonical Task writer`.
  A denied or interrupted invocation may be called again and may repeat model,
  audit, or classification work; it cannot bypass the current guards or create
  a second ordinary Task for an already consumed run/message identity.
- Action completion exclusively owns the action's deterministic +48-hour
  follow-up. A `task_follow_up` invocation triggered by an `action` may propose
  `check|measurement`, but never an ordinary `follow_up`, regardless of whether
  completion occurs before, during, or after provider I/O.
- Runtime command fingerprints remain deterministic inputs and the classified
  ordinary-task writer retains its transaction, natural keys, run-key
  serialization, Task FK, and `consumed|denied` disposition. No runtime-stage
  row, replay result union, or exact crash-window recovery is required before a
  real worker/scheduler and delivery identity exist.
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
- A pre-classification denial or interruption is not durable runtime state.
  Re-invocation re-runs the normal provider/current-guard/classifier path; this
  may repeat non-authoritative work but never weakens authorization or the sole
  Task writer.
- A consumed classified handoff retry resolves only through the immutable
  classified disposition and Task's unique classification link, then repeats
  current read/task authority before exposing the Task. It does not depend on a
  pre-classification runtime row, reconstruct the original Task
  text/kind/source preimage, or add an independent Task-create commitment.
  Coordinated direct PostgreSQL row corruption is outside the current product
  threat model; raw candidate text and the full MessageEnvelope remain
  transient.

## Verification Targets

- Unit: approval authority and task state transitions after spec defines state model.
- Integration: approval creates action_task only through Safety Gate path.
- Integration: open task/approval/follow-up state is unchanged by archive,
  blocked while archived, and revalidated after restore.
- Integration: a classified ordinary message denied by a current guard remains
  denied after restore for the same run/message identities, while a new
  invocation with new identities may pass current guards.
- Integration: post-I/O archive/revoke denial creates no envelope or Task;
  repeated internal invocation rechecks current authority and may repeat model
  work because no durable runtime delivery/replay contract exists.
- Integration: ordinary-task write races prove at most one Task and one
  classified `consumed|denied` disposition per run/message identity, atomic
  rollback, current-authority duplicate reads, and no runtime-ledger,
  direct-corruption, or exact crash-window acceptance matrix.
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

## Current W1/W2 Boundary Evidence

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
  after `ft011_safety_action_decisions`. Historical TASK-040 added
  `ft012_runtime_dispositions`; later feature work may already own the current
  repository head. The reopened repair adds only a forward cleanup revision
  after the executor-confirmed head and rewrites neither history.
- `TASK-040-T3-FT-012-W2` is explicit-owner `done` from ATTEMPT 08
  functional `PASS`, `semantic-pass`, and `HUMAN_CHECKPOINT: done`; prior
  attempt history remains preserved.
- No live-provider result is claimed.

## SDD Design Gate

- Global/shared status: complete; `AD-008` and Safety Action Lifecycle define the exact
  safe-task versus physical-action route; `AD-007` and Plant lifecycle define
  retained-but-frozen records and restore revalidation.
- Feature-local status: complete. The canonical design defines closed
  Task/Approval/Outcome states, exact FT-011 handoff and expiry reuse,
  transactional approval/action/follow-up/outcome uniqueness, persisted
  idempotency fingerprints, protected HTTP commands, Timeline refs, archive
  races, and the strict typed `task_follow_up` path. The runtime path is linear
  and best-effort with no pre-classification persistence; the downstream
  classified disposition remains the sole one-shot Task-write authority. No
  scheduler, worker, outbox, device effect, runtime ledger, or second proposal
  state machine is introduced.
- Current code-phase closure uses test-only fake/spy Task Follow-Up and Safety
  classifier executors; production has no fake fallback and fails closed while
  unbound. Real endpoint calls are deferred to the shared future milestone.
