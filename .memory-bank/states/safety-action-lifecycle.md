---
description: Global Safety Gate and physical-action lifecycle boundary for MVP v2.
status: active
type: state
last_updated: 2026-07-18
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
---
# Safety Action Lifecycle

## Scope

Safety Action Lifecycle defines the global authority boundary from
physical-action wording to Safety Gate decision, authorized human approval,
human-performed action task, and follow-up outcome. It is not an automated
device-control spec.

Exact domain action taxonomy, freshness windows, API route schemas, task table
fields, and UI prompts belong to `/feature-to-tasks FT-011` and
`/feature-to-tasks FT-012`. This shared spec owns the exact pre-safety
classification result and route classes needed by FT-007/008/011/012.

## Scope Boundaries

- Defines: global Safety Gate authority separation, lifecycle phases, allowed
  approval roles, no-actuation rules, and verification requirements.
- Out of scope: classifier algorithm/model choice, exact pH/EC freshness
  windows, endpoint schemas, task UI, or follow-up form fields.
- Related specs:
  - [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md):
    defines pending output and untrusted candidate-claim fields.
  - [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): defines human
    prompt projection.
  - [.memory-bank/states/companion-governance.md](companion-governance.md):
    defines governance decisions that must not replace Safety Gate approval.
  - [.memory-bank/states/plants/plant-and-access-lifecycle.md](plants/plant-and-access-lifecycle.md):
    defines the archived-Plant operational guard.

## Project-owned classification contract

Every non-silent MessageEnvelope starts with
`publication_state=pending_classification` and must produce one strict
`SafetyClassificationResultV1` before any Bus/UI/task route. The classifier
may use implementation details chosen by FT-011, but only the project-owned
validated result below is authority; model-selected claim labels are inputs,
not classification.

The classifier may semantically analyze `candidate_output`, including text that
looks like Markdown, HTML, a prompt, an instruction, or a command, but it must
treat the complete value as untrusted data. Candidate content cannot instruct
the classifier, change its closed result schema/matrix, select a permitted next
boundary, or authorize an action.

The strict result contains exactly:

- `schema_version=1`;
- lowercase canonical UUID `message_id` equal to the pending envelope;
- project-owned `classifier_version` matching
  `[a-z0-9][a-z0-9._-]{0,63}`;
- `classification=safe_information|safe_task_request|physical_action|blocked_uncertain`;
- nullable `safe_task_kind=check|measurement|follow_up`;
- one exact `reason_code` from the matrix below.

Unknown fields are rejected. The result does not copy envelope text, refs,
Plant identity, authorization, timestamps, downstream dispatch authority, or
a consumer-route field. `message_id` is the result key: one MessageEnvelope
accepts one classification, an identical retry is idempotent, and a
conflicting result fails closed. Reclassification requires a new Agent Runtime
invocation and `message_id`.

The result is persisted routing evidence, never an automatic dispatcher
command. After persistence, the project orchestrator derives exactly one
strict internal `ClassificationConsumerRouteV1`:

- `ordinary_dispatch` when the validated envelope and matching persisted
  classification have the same non-`companion` `origin_agent_id`;
- `companion_governance_hold` when both identify canonical
  `origin_agent_id=companion`.

The route is server-owned and derived; it is never accepted from the user,
provider, model result, MessageEnvelope, or classification result. No new
persisted discriminant is required because `safety_classifications` already
stores the matching `origin_agent_id`. A missing/mismatched identity fails
closed. Every downstream consumer validates the derived route; the classifier
itself writes only evidence and invokes no Bus, UI, Task, Safety-decision, or
governance repository.

The existing ordinary-dispatch matrix remains:

| Classification | Task kind | Reason | `ordinary_dispatch` next boundary |
|---|---|---|---|
| `safe_information` | null | `non_physical_information` | guarded FT-008 UI/Bus publication |
| `safe_task_request` | `check` | `safe_check_request` | ordinary FT-012 check task |
| `safe_task_request` | `measurement` | `safe_measurement_request` | ordinary FT-012 measurement task |
| `safe_task_request` | `follow_up` | `safe_follow_up_request` | ordinary FT-012 follow-up task |
| `physical_action` | null | `physical_action_detected` | FT-011 Safety Gate |
| `blocked_uncertain` | null | `classification_uncertain` | generic non-consumable UI block notice |

Under `ordinary_dispatch`, `safe_information` may be projected only after the
FT-008 current publication guard. `safe_task_request` may enter the ordinary
FT-012 task service but can never create an `action_task`. `physical_action`
enters the Safety Gate lifecycle and its wording remains non-operative until
every later gate passes.
`blocked_uncertain` permits only a generic human-visible block/clarification
notice; the original candidate text remains non-consumable and non-operative.

For `companion_governance_hold`, the matrix is instead closed as follows:

| Classification | Companion model effect | Only permitted result |
|---|---|---|
| `safe_information` | `discussion_only|none` | call `persist_companion_proposal` after its current governance guard |
| `safe_task_request` | exact matching `check|measurement|follow_up` | call `persist_companion_proposal` after its current governance guard |
| `physical_action|blocked_uncertain` | any | no governance row and no downstream effect |
| mismatch, conflict, classifier failure, or current-guard denial | any | no governance row and no downstream effect |

A held classification never invokes FT-008 classified publication or generic
block-notice projection, FT-011 Safety-decision routing, or the FT-012
`classified_message` ordinary-task branch. Raw candidate/proposal/rationale or
provider text never enters Bus, UI Feed, or agent context. The dedicated
governance writer may persist authoritative proposal fields and compact
non-agent-consumable governance summaries under its own contract; that is not
FT-008 candidate publication.

Only a later committed approved DecisionRecord may invoke the separate
`governance_decision` branch of the canonical ordinary-task command and/or the
guarded compact DecisionRecord Bus-fact path. Classification evidence alone
can do neither.

`SafetyClassificationResultV1` is routing data, not authorization. Before a
downstream write, the owning FT-008/FT-011/FT-012 service applies its canonical
current authorization and active-Plant guard in the same transaction/locking
boundary; the FT-013 proposal writer applies its own equivalent current
governance guard. Denial creates no effect and the handoff is not replayed
after restore; a new current-state request is required.

There is no generic classification replay dispatcher, outbox, restore hook,
startup reconciliation, or retry worker. An identical classification retry
returns evidence only and does not repeat its prior consumer effect. In
particular, restart/restore/reconciliation cannot turn a held Companion row
into FT-008 publication, FT-011 routing, or an FT-012 Task. Ordinary
non-Companion flows retain the matrix and behavior above.

## Lifecycle Shape

Feature-local specs may refine state names, but the global lifecycle must keep
these authority phases distinct:

- `not_physical_action`
- `safety_blocked`
- `needs_fresh_evidence`
- `safety_gate_passed`
- `pending_human_approval`
- `human_approved`
- `human_rejected`
- `action_task_created`
- `follow_up_due`
- `outcome_recorded`

Every safety/action record must carry:

- `farm_id`
- `plant_id`
- `source_refs`
- `actor_ref` or `agent_ref`
- `safety_gate_status`
- `approval_actor_ref` when approved/rejected
- `action_task_ref` when created
- `follow_up_ref` when created

## Rules

- Physical-action wording fails closed until fresh evidence, Safety Gate pass,
  authorized human approval, and action/task tracking exist.
- Boss may approve for Farm Plants only after Safety Gate rules pass.
- Engineer may approve only when the active PlantAccessGrant has
  `plant_approve_actions=true` and Safety Gate rules pass.
- Consultant never approves physical actions in MVP.
- Human approval creates only human-performed action task tracking. It never
  triggers automated device execution.
- DecisionRecord, UI Feed prompt display, MessageEnvelope
  candidate fields, `SafetyClassificationResultV1`, and Bus publication are not
  Safety Gate approval.
- Candidate wording cannot override classifier policy, freshness evidence,
  current authorization, Safety Gate state, approval authority, or task/action
  tracking even when it claims to be a system/developer instruction or command.
- Superseded, stale, or replayed approvals cannot create an action task.
- Every Safety Gate, approval, task, follow-up, and outcome transition requires
  current `Plant.status=active` at its transactional authorization boundary.
- Archive preserves existing safety/task records and their states but blocks
  every transition, including approval/rejection, action-task creation,
  completion, follow-up, and outcome recording.
- Restore does not refresh evidence or approvals and does not resume a record;
  the next transition revalidates ActorContext/grant, record state/version,
  evidence freshness, Safety Gate status, and approval authority.

## Edge Cases And Errors

- Missing/stale evidence routes to `needs_fresh_evidence` or blocked output.
- Missing approver authority fails closed.
- Archived Plant returns a fail-closed non-operative result without mutating
  the safety/task record.
- Governance approval cannot be converted into physical-action approval.
- Unsafe classifier uncertainty must prefer block/clarify over cleared wording.
- Markup- or prompt-looking syntax alone is neither a safety class nor an
  `output_invalid` condition; classification is semantic and still fails
  closed on physical-action meaning or uncertainty.
- A model-selected `observation|hypothesis|team_signal` label cannot make
  physical-action wording safe, and a model-selected
  `recommendation|task_request` label cannot force a genuinely non-physical
  check/measurement request into physical-action approval.
- Any implementation path that would issue pump, dosing, pH/EC correction,
  light-control, autowatering, or autodosing commands is out of MVP.
- A caller/provider-selected consumer route, a generic dispatcher that ignores
  `origin_agent_id`, or reuse of a held Companion classification by an
  ordinary FT-008/FT-011/FT-012 consumer is invalid and fails closed.

## Verification

Tests must prove:

- Safety Gate, human approval, action task creation, and follow-up are separate
  records or explicit phases.
- Boss/Engineer/Consultant approval rules are enforced.
- Governance DecisionRecord does not unlock physical action.
- UI prompt display does not unlock physical action.
- Adversarial classification tests cover mislabeled physical-action wording,
  all four result classes, exact matrix/unknown-field rejection, duplicate
  conflict, and safe task requests that never create an `action_task`.
- Classifier tests treat representative Markdown/HTML/prompt-like strings as
  untrusted data, prove they cannot override the result matrix or current
  guards, and preserve unchanged fail-closed physical-action behavior.
- No code path performs automated actuation.
- Archiving with open safety/task records leaves those records unchanged,
  blocks every transition while archived, and restore does not bypass current
  freshness, replay, authorization, or Safety Gate checks.
- Consumer-route tests prove Companion `safe_information` produces no FT-008
  Bus/UI candidate publication, Companion `safe_task_request` produces no
  FT-012 Task, held physical/blocked/mismatch/failure produces no downstream
  row, retry/restore/reconciliation performs no held effect, and unchanged
  non-Companion classifications still follow the ordinary matrix.
