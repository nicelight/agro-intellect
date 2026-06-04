---
description: Epic EP-005 for Companion IssueStack, proposals, decisions, and approved governance summaries.
status: draft
lifecycle: planned
epic_id: EP-005
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/analysis/companion-issue-stack-decision-governance.md
  - .memory-bank/contracts/boundary-map.md
---
# EP-005 Companion Governance

## Value

Make Companion a transparent governance coordinator without hidden authority.
Discussion state, human attention, proposals, decisions, and agent-consumable summaries
are typed and auditable instead of living only in chat history or UI markdown.

## Features

- FT-014 Companion IssueStack, HumanAttention, Proposal, And DecisionRecord.
- FT-015 Approved Governance Summary And Agent Context Isolation.

## Success Metrics

- Companion can surface Plant-scoped issues and propose process direction.
- No parallel pending CompanionProposal exists for the same Plant issue.
- Valid human decisions create typed DecisionRecord records.
- Agents consume only compact approved governance summary facts, never raw proposal
  text, rationale, chat, UI markdown, or unapproved discussion.

## Acceptance Criteria

- Companion governance is Plant-scoped in MVP.
- Consultant input is advisory/read/comment only and does not create binding decisions.
- DecisionRecord may direct Plant-scoped workflow and safe check/measurement/follow-up
  task requests through backend rules.
- DecisionRecord cannot mutate Plant state, create `action_task`, authorize physical
  action, replace Safety Gate approval, or turn raw chat into fact.

## Constraints / Invariants

- Companion governance approval and Safety Gate approval are separate approval classes.
- Raw proposal content, discussion history, and UI projection remain presentation or
  audit data unless converted into allowed compact summary facts by a valid
  DecisionRecord.

## Verification Targets

- `test:companion.typed-plant-scoped-state`
- `test:companion.proposal-decision-authority`
- `test:companion.approved-summary-context-filter`
