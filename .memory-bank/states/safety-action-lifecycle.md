---
description: Global Safety Gate and physical-action lifecycle boundary for MVP v2.
status: active
owner: architecture
type: state
last_updated: 2026-06-26
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/architecture/system-architecture.md
---
# Safety Action Lifecycle

## Scope

Safety Action Lifecycle defines the global authority boundary from
physical-action wording to Safety Gate decision, authorized human approval,
human-performed action task, and follow-up outcome. It is not an automated
device-control spec.

Exact action taxonomy, freshness windows, API route schemas, task table fields,
and UI prompts belong to `/prd-to-tasks FT-011` and `/prd-to-tasks FT-012`.

## Ownership

- Owns: global Safety Gate authority separation, lifecycle phases, allowed
  approval roles, no-actuation rules, and verification requirements.
- Does not own: detailed classifier implementation, exact pH/EC freshness
  windows, endpoint schemas, task UI, or follow-up form fields.
- Related specs:
  - [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md):
    owns physical-action implication and `safety_gate_route` fields.
  - [.memory-bank/contracts/ui-feed.md](../contracts/ui-feed.md): owns human
    prompt projection.
  - [.memory-bank/states/companion-governance.md](companion-governance.md):
    owns governance decisions that must not replace Safety Gate approval.

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
  `requires_human_approval=true`, and Bus publication are not Safety Gate
  approval.
- Superseded, stale, or replayed approvals cannot create an action task.

## Edge Cases And Errors

- Missing/stale evidence routes to `needs_fresh_evidence` or blocked output.
- Missing approver authority fails closed.
- Governance approval cannot be converted into physical-action approval.
- Unsafe classifier uncertainty must prefer block/clarify over cleared wording.
- Any implementation path that would issue pump, dosing, pH/EC correction,
  light-control, autowatering, or autodosing commands is out of MVP.

## Verification

Tests must prove:

- Safety Gate, human approval, action task creation, and follow-up are separate
  records or explicit phases.
- Boss/Engineer/Consultant approval rules are enforced.
- Governance DecisionRecord does not unlock physical action.
- UI prompt display does not unlock physical action.
- No code path performs automated actuation.
