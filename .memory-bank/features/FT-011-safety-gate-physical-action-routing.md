---
description: FT-011 Safety Gate Physical-Action Routing.
status: draft
type: feature
feature_id: FT-011
epic: EP-004
lifecycle: planned
last_updated: 2026-07-12
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
---
# FT-011 Safety Gate Physical-Action Routing

## Use Cases

- Agent/advisor output includes or implies physical-action wording.
- The project-owned classifier produces the strict shared
  `SafetyClassificationResultV1`, independently of model-selected labels, and
  blocks or routes the output.
- The classifier analyzes candidate wording only as untrusted data; markup- or
  prompt-looking content cannot instruct it or alter its closed result matrix.
- System requires fresh evidence, Safety Gate pass, and authorized human approval before cleared user-visible action wording or action-task tracking.
- Safety block is visible to humans without authorizing action.

## Acceptance Criteria

- Physical-action advice fails closed when data is stale/missing, Safety Gate fails, or actor approval authority is absent.
- Safe information and check/measurement/follow-up requests are distinguished
  from physical action; ordinary safe tasks never require physical-action
  approval and never become `action_task`.
- Candidate formatting syntax alone is neither `output_invalid` nor a safety
  class; semantic physical-action/uncertainty handling and every existing
  Safety/current-guard rule remain unchanged.
- Safety Gate approval is distinct from Companion governance approval.
- Boss may approve for Farm Plants only after Safety Gate rules pass.
- Engineer may approve only with `plant_approve_actions` for that Plant.
- Consultant never approves physical actions in MVP.
- Archived Plant blocks Safety Gate progression and physical-action approval;
  retained records do not resume automatically after restore.

## Edge Cases & Failure Modes

- Governance DecisionRecord cannot be treated as Safety Gate approval.
- Superseded CompanionProposal cannot unlock action flow.
- Safety Gate cannot authorize automated actuation.
- High-risk non-pH/EC actions require later exact freshness/action taxonomy in specs.
- Archive leaves open safety/approval records unchanged and non-operative;
  restore requires current authorization, record-version, evidence freshness,
  and Safety Gate checks.

## Verification Targets

- Unit: exact shared classification matrix, adversarial model-label bypass, and
  fail-closed policy, including prompt-like candidate data that cannot override
  classifier results; feature design later adds the domain action taxonomy.
- Integration: stale/missing data and missing authority block approval path.
- Integration: archive blocks an already-open approval without mutating it;
  restore cannot bypass current freshness, replay, or authority checks.
- E2E: risky advice routes to pending approval or safety block, not immediate instruction.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Safety & Task Loop boundaries and no-actuation rule.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): pending candidate output and model-untrusted claim fields before project-owned classification.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): authorization, errors, and safety route API guardrails.
- [.memory-bank/states/safety-action-lifecycle.md](../states/safety-action-lifecycle.md): global Safety Gate and physical-action lifecycle boundary.
- [.memory-bank/states/companion-governance.md](../states/companion-governance.md): DecisionRecord separation from Safety Gate approval.
- [.memory-bank/states/plants/plant-and-access-lifecycle.md](../states/plants/plant-and-access-lifecycle.md): global archived-Plant operational guard.

## Feature-Local Design Pressure

- Exact action taxonomy, freshness rules, Safety Gate decision contract,
  approval routing, replay/stale handling, and tests.

## SDD Design Gate

- Global/shared status: complete; strict shared classification ownership, exact result
  matrix, opaque untrusted candidate semantics, archived approval behavior, and
  restore revalidation are defined by `AD-008`, Plant lifecycle, and Safety
  Action Lifecycle.
- Feature-local status: pending `/prd-to-tasks FT-011` for exact taxonomy,
  freshness, decision, route, replay, and error contracts.
