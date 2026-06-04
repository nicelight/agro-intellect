---
description: Safety Gate contract for physical-action advice, approval, and human-performed action task unlock.
status: active
owner: safety
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/constitution.md
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/invariants.md
---
# Safety Gate Contract

## Purpose

Safety Gate prevents model or UI wording from turning into unsafe Plant-system action.
It is a backend/harness policy boundary, not a prompt convention.

Physical actions in MVP can become only human-performed `action_task` records after
fresh evidence, Safety Gate pass, authorized human approval, and task/action tracking.
They never trigger automated device execution.

## Physical Action Taxonomy

Physical actions include, at minimum:

- pH/EC change;
- solution change;
- nutrient dosing;
- pump, light, dosing, watering, or circulation change;
- pruning;
- transplanting;
- root trimming;
- other interventions that materially change the Plant system.

Feature specs may refine taxonomy, but must not narrow it enough to bypass the gate.

## Safety Gate Inputs

Minimum inputs:

- ActorContext and PlantAccessGrant;
- Plant id and Farm id;
- proposed action wording or structured proposal;
- source MessageEnvelope or task/proposal ref;
- latest relevant runtime state;
- pH/EC evidence and freshness labels where relevant;
- photo/observation/task/outcome refs when used;
- prior approval refs if any;
- Companion governance refs only as workflow context, never Safety approval.

## Freshness Defaults

Until feature specs refine exact windows:

- analysis freshness for pH/EC is up to 24 hours;
- physical-action approval freshness for pH/EC is up to 2 hours;
- fresh data is required but never sufficient by itself for physical action.

Stale, missing, conflicting, unauthorized, or untrusted evidence must fail closed or
route to missing-data/check/measurement behavior.

## SafetyGateDecision

Minimum global fields:

```yaml
safety_gate_id: string
schema_version: string
created_at: datetime
farm_id: string
plant_id: string
actor_ref: string
proposal_ref: string
decision: blocked | route_to_missing_data | route_to_approval | cleared_for_approval | denied
reason_code: string
freshness_status: fresh | stale | missing | conflict | not_applicable
required_next_action: none | check_task | measurement_task | human_approval | revise_wording
approval_required: boolean
eligible_approver_roles: []
source_refs: []
trace_ref: string
```

`cleared_for_approval` does not mean approved. It means the proposal may enter the
human approval path.

## Approver Rules

- Boss may approve physical-action proposals for Farm Plants.
- Engineer may approve only with `plant_approve_actions` for that Plant.
- Consultant never approves physical actions in MVP.
- Companion cannot approve physical actions.
- A governance DecisionRecord cannot replace Safety Gate approval.
- Approval is scoped to the exact proposal/action and cannot be replayed after evidence
  becomes stale or scope changes.

## Action Task Unlock

Human approval can create only a human-performed `action_task`.

Rules:

- no automated device command is emitted;
- rejected approval creates no action_task;
- missing/revoked PlantAccessGrant blocks approval and task mutation;
- stale approval context blocks replay;
- follow-up task/outcome should be created or requested where feature specs require it;
- outcome without data must be represented explicitly, not backfilled as success.

## UI Wording Rules

- Before Safety Gate clearance and authorized approval, UI must not imply immediate
  physical action.
- Blocked advice should display a safe next step, missing-data request, or explanation.
- UI markdown cannot alter Safety Gate semantics.
- Safety Gate output may be projected to UI Feed, but UI Feed content cannot become
  future Safety Gate evidence by itself.

## Verification

Feature specs must test:

- missing/stale pH/EC fails closed for physical actions;
- fresh pH/EC alone does not unlock action;
- Boss approval path works only after Safety Gate path permits it;
- Engineer without `plant_approve_actions` cannot approve;
- Consultant cannot approve;
- governance DecisionRecord cannot substitute for Safety approval;
- approved action creates human-performed action_task only;
- no automated actuation command exists in MVP path;
- stale approval cannot be replayed;
- blocked advice produces safe next action or missing-data request.
