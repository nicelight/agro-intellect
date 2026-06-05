---
description: Feature FT-014 for Companion IssueStack, HumanAttentionNeeded, CompanionProposal, CompanionConclusion, and DecisionRecord.
status: active
owner: product
lifecycle: planned
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-014-companion-issue-stack-human-attention-proposal-and-decision-record.md
epic: EP-005
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/analysis/companion-issue-stack-decision-governance.md
  - .memory-bank/tech-specs/FT-014-companion-issue-stack-human-attention-proposal-and-decision-record.md
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

Global `/spec-design` and feature-level `/spec-improve FT-014` are complete. Use
[.memory-bank/tech-specs/FT-014-companion-issue-stack-human-attention-proposal-and-decision-record.md](../tech-specs/FT-014-companion-issue-stack-human-attention-proposal-and-decision-record.md)
as the feature-local design hub before `/prd-to-tasks FT-014`.
