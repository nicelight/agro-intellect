---
description: FT-011 Safety Gate Physical-Action Routing.
status: draft
type: feature
feature_id: FT-011
epic: EP-004
lifecycle: planned
last_updated: 2026-07-17
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
spec_design_status: complete
spec_design_links:
  - .memory-bank/contracts/safety-gate-runtime.md
  - .memory-bank/domains/safety-action-routing.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/contracts/agent-roster-bootstrap.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/domains/plant-operations.md
  - .memory-bank/states/safety-action-lifecycle.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/ui-feed.md
  - .memory-bank/domains/agent-chat-ui-feed-storage.md
  - .memory-bank/contracts/plant-feed-http.md
  - .memory-bank/testing/safety-gate.md
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
- The MVP approval route supports only human-performed pH adjustment, EC
  adjustment (including manual nutrient addition/top-up), and complete solution
  change; every supported kind requires both pH and EC fresh within the
  existing two-hour approval-input window.
- Boss may approve for Farm Plants only after Safety Gate rules pass.
- Engineer may approve only with `plant_approve_actions` for that Plant.
- Consultant never approves physical actions in MVP.
- Archived Plant blocks Safety Gate progression and physical-action approval;
  retained records do not resume automatically after restore.

## Edge Cases & Failure Modes

- Governance DecisionRecord cannot be treated as Safety Gate approval.
- Superseded CompanionProposal cannot unlock action flow.
- Safety Gate cannot authorize automated actuation.
- Pump/light/device-dosing commands, pruning, transplanting, root trimming, and
  other physical actions remain explicitly unsupported and cannot reach
  approval.
- Archive leaves open safety/approval records unchanged and non-operative;
  restore requires current authorization, record-version, evidence freshness,
  and Safety Gate checks.

## Verification Targets

- Unit: exact shared classification matrix, adversarial model-label bypass, and
  fail-closed policy, including prompt-like candidate data that cannot override
  classifier results, plus the linked exact domain action taxonomy.
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

- Resolved by the linked Safety Gate Runtime, Safety Action Routing, UI Feed,
  and Safety Gate Verification subject specs.

## Behavior specs

- `.memory-bank/behavior-specs/FT-011-BHV-001-supported-manual-action.behavior.json`
- `.memory-bank/behavior-specs/FT-011-BHV-002-device-action-blocked.behavior.json`
- `.memory-bank/behavior-specs/FT-011-BHV-003-stale-approval-input.behavior.json`

## SDD Design Gate

- Global/shared status: complete; strict shared classification ownership, exact result
  matrix, opaque untrusted candidate semantics, archived approval behavior, and
  restore revalidation are defined by `AD-008`, Plant lifecycle, and Safety
  Action Lifecycle.
- Feature-local status: complete. The canonical design defines the real
  model-backed candidate, backend-owned durable classification, exact supported
  and unsupported action kinds, independent `approval_input=2h` evidence,
  immutable decision/proposal rows, safe feed projection, replay/concurrency
  behavior, and executable verification. FT-011 stops at
  `pending_human_approval`; FT-012 owns every later human decision and task.
