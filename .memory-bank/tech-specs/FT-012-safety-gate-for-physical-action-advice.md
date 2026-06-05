---
description: Feature-local SDD tech spec for FT-012 Safety Gate routing, physical-action decisions, and approval eligibility.
status: active
feature_id: FT-012
owner: spec-improve
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/features/FT-012-safety-gate-for-physical-action-advice.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/contracts/safety-gate.md
  - .memory-bank/contracts/agent-harness.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
  - .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
  - .memory-bank/tech-specs/FT-006-runtime-plant-state-history-and-timeline-audit.md
  - .memory-bank/tech-specs/FT-007-shared-agent-harness-and-agent-profile-runtime.md
  - .memory-bank/tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md
  - .memory-bank/tech-specs/FT-011-plant-state-trust-and-hydroponics-advisor.md
  - agents-best-practices
---
# FT-012 Safety Gate For Physical-Action Advice Tech Spec

## Purpose

Define the minimum feature-local design needed before task decomposition for Safety
Gate routing, physical-action classification, fail-closed decisions, approval
eligibility, safe UI wording, and audit/eval evidence.

This spec applies `agents-best-practices`: action-implying model output is a typed
proposal. The harness/backend validates, permission-checks, classifies, records the
Safety Gate decision, and pauses or routes. The model never approves or executes the
action.

## Scope

In scope:

- physical-action taxonomy refinements for MVP;
- `PhysicalActionProposal` shape before approval;
- Safety Gate input validation and freshness checks;
- `SafetyGateDecision` feature-local decision semantics;
- approver eligibility for Boss, Engineer with `plant_approve_actions`, and Consultant
  denial;
- fail-closed display and Bus/UI projection rules;
- trace, audit, and harness eval requirements for safety-sensitive proposals.

Out of scope:

- task, approval, and outcome record lifecycle owned by FT-013;
- Plant State trust-promotion and advisor wording generation owned by FT-011;
- MessageEnvelope/Bus/UI projection mechanics owned by FT-009;
- Companion governance proposal and DecisionRecord semantics owned by FT-014 and
  FT-015;
- automated device execution, dosing commands, sensor runtime dependency, or direct
  actuator integrations.

## Physical-Action Taxonomy

Safety Gate covers any recommendation, task request, or UI wording that instructs,
implies, or makes actionable a material Plant-system intervention.

MVP categories:

| Category | Examples | Required route |
|---|---|---|
| `ph_ec_change` | adjust pH, lower/raise EC, correct nutrient strength | Safety Gate with relevant pH/EC evidence. |
| `solution_change` | replace reservoir, flush solution, change mix | Safety Gate with relevant measurement and observation refs. |
| `nutrient_dosing` | add nutrients, dose additives, change concentration | Safety Gate with pH/EC and source refs. |
| `environment_device_change` | pump, light, dosing, watering, or circulation changes | Safety Gate with current Plant context and explicit no-actuation boundary. |
| `manual_intervention` | pruning, transplanting, root trimming, material plant handling | Safety Gate with recent check/photo/observation evidence where available. |
| `other_physical_intervention` | any material Plant-system change not listed above | Fail closed until a safe category and evidence path are chosen. |

Low-risk check, measurement, observation, photo, or follow-up requests are not physical
actions by themselves. They become Safety Gate inputs only if wording turns them into a
material intervention.

## PhysicalActionProposal

Physical-action wording must be converted into a structured proposal before Safety
Gate evaluation. Minimum semantics:

```yaml
proposal_id: string
schema_version: string
created_at: datetime
farm_id: string
plant_id: string
source_message_ref: string | null
source_run_ref: string | null
proposed_by_agent_ref: string | null
proposed_by_actor_ref: string | null
action_category: ph_ec_change | solution_change | nutrient_dosing | environment_device_change | manual_intervention | other_physical_intervention
candidate_wording: string
structured_action:
  verb: string
  target: string
  parameters: object
source_refs: []
evidence_refs: []
trace_ref: string
status: received | invalid | blocked | missing_data | cleared_for_approval | expired
redaction_status: redacted | no_sensitive_fields
```

Rules:

- strict schemas reject unknown properties for action proposals;
- `candidate_wording` is bounded and redacted before persistence or display;
- raw provider output, hidden reasoning, UI Feed text, raw chat, and unapproved
  governance content cannot become proposal authority;
- proposal creation does not create an Approval, `action_task`, or device command;
- proposal refs must be exact enough that later approval is scoped to the same action.

## Safety Gate Inputs

Every Safety Gate evaluation resolves and records:

1. ActorContext and Farm/Plant scope;
2. Plant state and PlantAccessGrant, including active/archived state;
3. source MessageEnvelope, AgentHarnessRun, task request, or proposal ref;
4. relevant pH/EC, observation, photo, task, outcome, and runtime state refs;
5. trust/freshness labels for evidence;
6. candidate action category and bounded wording;
7. prior SafetyGateDecision or Approval refs when present;
8. trace ref and redaction status.

Companion `DecisionRecord` may be referenced only as workflow context. It is never
Safety Gate approval, evidence of Plant state, or an action unlock.

## Freshness And Evidence Rules

- pH/EC analysis freshness remains up to 24 hours for advisory analysis.
- pH/EC physical-action approval freshness is up to 2 hours.
- Fresh data is required but never sufficient by itself.
- Missing, stale, conflicting, unauthorized, untrusted, redaction-failed, or
  out-of-scope evidence fails closed.
- If a category does not have enough current evidence to classify safely, the decision
  must route to check/measurement behavior rather than approval.
- Archived Plants are ineligible for normal physical-action approval.
- Revoked PlantAccessGrant or expired ActorContext invalidates approval eligibility.

## SafetyGateDecision Semantics

Minimum feature-local decision semantics extend the global contract:

```yaml
safety_gate_id: string
schema_version: string
created_at: datetime
farm_id: string
plant_id: string
actor_ref: string
proposal_ref: string
action_category: string
decision: blocked | route_to_missing_data | route_to_approval | cleared_for_approval | denied
reason_code: missing_evidence | stale_evidence | conflict | unauthorized | archived_plant | unsafe_wording | unsupported_action | cleared_policy | rejected_policy | invalid_proposal
freshness_status: fresh | stale | missing | conflict | not_applicable
required_next_action: none | check_task | measurement_task | human_approval | revise_wording
approval_required: boolean
eligible_approver_roles: []
approval_eligibility:
  boss: eligible | ineligible
  engineer_with_plant_approve_actions: eligible | ineligible
  consultant: ineligible
source_refs: []
evidence_refs: []
trace_ref: string
expires_at: datetime | null
redaction_status: redacted | no_sensitive_fields
```

Decision rules:

- `blocked` means no approval path and no action wording may be shown as actionable.
- `route_to_missing_data` means create or propose only check/measurement behavior owned
  by FT-013.
- `cleared_for_approval` means the exact proposal may enter the human approval path.
  It is not human approval.
- `route_to_approval` may be used when a valid approval request is created or surfaced
  by FT-013 from a `cleared_for_approval` decision.
- `denied` records a policy or authorization denial that should not be retried without
  changed evidence, scope, or actor authority.
- Safety Gate unavailable, malformed, over-budget, or uncertain classification fails
  closed with structured observation and safe next action.

## Approval Eligibility Boundary

FT-012 decides eligibility; FT-013 owns persisted Approval request/result records and
`action_task` creation.

Eligibility rules:

- Boss is eligible for Farm Plants after Safety Gate clearance.
- Engineer is eligible only for the exact Plant when ActorContext resolves active
  membership and PlantAccessGrant has `plant_approve_actions=true`.
- Consultant is never eligible for physical-action approval in MVP.
- Disabled Account, disabled/removed FarmMembership, revoked PlantAccessGrant, archived
  Plant, stale evidence, changed proposal wording, changed action parameters, or
  expired SafetyGateDecision invalidates eligibility.
- The model, Companion, AgentMemoryRecord, UI Feed, and DecisionRecord cannot approve or
  make an actor eligible.

## UI, Bus, And Message Handoff

Before Safety Gate clearance and authorized approval, UI and Bus-visible wording must
avoid immediate action instructions.

Allowed outputs:

- safety block with reason and safe next action;
- missing-data or measurement/check request;
- pending approval card or route after `cleared_for_approval`;
- redacted SafetyGateDecision refs for authorized history/audit.

Forbidden outputs:

- direct dosing, pH/EC correction, solution, pump, light, watering, circulation,
  pruning, transplanting, or root-trimming instructions before clearance and approval;
- wording that says the system executed or will execute a physical change;
- UI markdown that alters Safety Gate semantics;
- UI Feed replay as future Safety Gate evidence.

## API / Service Surface To Refine In Tasks

Task decomposition may define exact backend services and schemas for:

- classify `PhysicalActionProposal`;
- evaluate Safety Gate for a proposal;
- create a SafetyGateDecision and trace/audit refs;
- read safe decision summaries for authorized UI/history;
- route missing-data decisions to check/measurement task creation;
- route cleared decisions to FT-013 approval request creation;
- run Safety Gate eval fixtures.

Generated OpenAPI comes from implementation schemas later.

## Verification Targets

Required tests before FT-012 can be considered implemented:

- pH/EC, solution, nutrient dosing, pump/light/dosing/watering/circulation, pruning,
  transplanting, root trimming, and unknown physical-intervention wording route through
  Safety Gate;
- missing/stale/conflicting/unauthorized evidence fails closed;
- fresh pH/EC alone does not unlock approval or action wording;
- Boss eligibility works only after Safety Gate clearance;
- Engineer without `plant_approve_actions` cannot approve;
- Consultant cannot approve;
- archived Plant or revoked PlantAccessGrant blocks approval eligibility;
- governance DecisionRecord, UI Feed, raw chat, AgentMemoryRecord, or provider memory
  cannot substitute for Safety Gate approval;
- Safety Gate unavailable, malformed, over-budget, or uncertain classification produces
  a structured fail-closed observation;
- user-visible action wording is blocked or rewritten until Safety Gate clearance and
  authorized human approval;
- no automated actuation tool, command, or side effect exists in the Safety Gate path.

## Open Questions

No blocker for `/prd-to-tasks FT-012`. Exact endpoint names, reason-code enum names,
expiration duration, first-demo UI card layout, and numeric eval fixture budgets can be
chosen during task decomposition as long as fail-closed Safety Gate routing, exact
proposal scoping, approval eligibility, audit traces, and no automated actuation hold.
