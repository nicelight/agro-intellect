---
description: FT-011 Safety Gate Physical-Action Routing.
status: draft
type: feature
feature_id: FT-011
epic: EP-004
lifecycle: planned
last_updated: 2026-06-26
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
---
# FT-011 Safety Gate Physical-Action Routing

## Use Cases

- Agent/advisor output includes or implies physical-action wording.
- Safety Gate classifies the output and blocks or routes it.
- System requires fresh evidence, Safety Gate pass, and authorized human approval before cleared user-visible action wording or action-task tracking.
- Safety block is visible to humans without authorizing action.

## Acceptance Criteria

- Physical-action advice fails closed when data is stale/missing, Safety Gate fails, or actor approval authority is absent.
- Safety Gate approval is distinct from Companion governance approval.
- Boss may approve for Farm Plants only after Safety Gate rules pass.
- Engineer may approve only with `plant_approve_actions` for that Plant.
- Consultant never approves physical actions in MVP.

## Edge Cases & Failure Modes

- Governance DecisionRecord cannot be treated as Safety Gate approval.
- Superseded CompanionProposal cannot unlock action flow.
- Safety Gate cannot authorize automated actuation.
- High-risk non-pH/EC actions require later exact freshness/action taxonomy in specs.

## Verification Targets

- Unit: physical-action classifier and fail-closed policy after spec defines taxonomy.
- Integration: stale/missing data and missing authority block approval path.
- E2E: risky advice routes to pending approval or safety block, not immediate instruction.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Safety & Task Loop boundaries and no-actuation rule.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): physical-action implication and Safety Gate route fields.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): authorization, errors, and safety route API guardrails.

## SDD Design Gate

Run global `/spec-design` before this feature is task-decomposed. Then run `/prd-to-tasks FT-011`; it must define exact action taxonomy, freshness rules, Safety Gate decision contract, approval routing, and tests during its feature-level SDD design phase before writing tasks. Use standalone `/spec-improve FT-011` only for repair or advanced refresh without task generation.
