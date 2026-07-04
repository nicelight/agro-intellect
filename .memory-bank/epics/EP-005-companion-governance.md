---
description: EP-005 Companion Governance.
status: draft
type: epic
epic_id: EP-005
lifecycle: planned
last_updated: 2026-06-29
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/states/companion-governance.md
---
# EP-005 Companion Governance

## Value

Let Companion coordinate Plant-scoped discussion and workflow direction through explicit typed state without becoming hidden authority, Plant-state evidence, or Safety Gate approval.

## Features

- [FT-013 Companion IssueStack Proposals And DecisionRecords](../features/FT-013-companion-issuestack-proposals-decisionrecords.md)

## Success Metrics

- Companion can raise HumanAttentionNeeded and propose a Plant-scoped decision path.
- Only the current proposal for a Plant-scoped issue can be approved/rejected.
- DecisionRecord creates only allowed governance/workflow effects.
- Agents consume only compact approved governance summary facts and refs.

## Acceptance Criteria

- IssueStack, CompanionProposal, CompanionConclusion, HumanAttentionNeeded, and DecisionRecord are explicit typed concepts.
- A new pending proposal for the same Plant issue supersedes the previous pending proposal.
- DecisionRecord cannot mutate Plant state, create action_task, authorize physical action, replace Safety Gate approval, or turn raw chat into fact.

## Constraints / Invariants

- Companion governance is Plant-scoped in MVP.
- Farm-level issue governance and separate Farm-level chat are deferred.
- Raw proposal text, rationale, UI markdown, and chat discussion stay non-consumable by agents.

## Feature-Local Design Pressure

- Exact proposal/decision state machine.
- Exact allowed workflow-effect catalog.
- Exact compact approved governance summary schema.
