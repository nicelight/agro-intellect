---
description: Feature FT-014 for Companion IssueStack, HumanAttentionNeeded, CompanionProposal, CompanionConclusion, and DecisionRecord.
status: draft
lifecycle: planned
spec_design_status: needs_spec_improve
epic: EP-005
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/analysis/companion-issue-stack-decision-governance.md
---
# FT-014 Companion IssueStack, HumanAttention, Proposal, And DecisionRecord

## Use Cases

- Companion tracks Plant-scoped issues in explicit IssueStack state.
- Companion raises HumanAttentionNeeded when human reaction is expected.
- Companion creates a CompanionProposal for process direction or decision.
- Valid human approval/rejection creates a DecisionRecord.

## Acceptance Criteria

- IssueStack, HumanAttentionNeeded, CompanionProposal, CompanionConclusion, and DecisionRecord are typed Plant-scoped state.
- CompanionProposal is not parallel for the same Plant-scoped issue; a new proposal supersedes the previous pending one.
- Superseded proposals cannot be approved and cannot become agent facts.
- DecisionRecord can direct Plant-scoped discussion/workflow and safe check/measurement/follow-up task requests through backend rules.
- DecisionRecord cannot mutate Plant state, create `action_task`, authorize physical action, replace Safety Gate approval, or turn raw chat into fact.

## Edge Cases & Failure Modes

- Consultant input remains advisory and does not approve governance decisions by default.
- Raw proposal text/rationale/chat stays non-consumable before and after decision.
- UI markdown cannot become governance authority.
- Governance approval controls workflow direction only inside backend rules.

## Test Strategy Pointers

- `test:companion.typed-plant-scoped-state`
- `test:companion.proposal-decision-authority`
- `test:safety-gate.fail-closed-approval-boundary`

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): Companion governance requirements.
- [.memory-bank/analysis/companion-issue-stack-decision-governance.md](../analysis/companion-issue-stack-decision-governance.md): governance analysis source.
- [.memory-bank/states/lifecycle-map.md](../states/lifecycle-map.md): proposal and decision lifecycle hints.

## SDD Design Gate

Global `/spec-design` is complete. Before `/prd-to-tasks FT-014`, run
`/spec-improve FT-014` using the completed backbone docs: [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md), [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md), [.memory-bank/states/core-lifecycles.md](../states/core-lifecycles.md), [.memory-bank/contracts/index.md](../contracts/index.md), and [.memory-bank/testing/index.md](../testing/index.md). `/spec-improve` must decide state machine, supersede policy,
approval roles, DecisionRecord workflow effects, audit refs, and UI controls.
