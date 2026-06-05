---
description: Feature FT-015 for approved governance summaries and strict exclusion of raw governance/chat/UI content from agent context.
status: active
owner: product
lifecycle: planned
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-015-approved-governance-summary-and-agent-context-isolation.md
epic: EP-005
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/contracts/boundary-map.md
  - .memory-bank/tech-specs/FT-015-approved-governance-summary-and-agent-context-isolation.md
---
# FT-015 Approved Governance Summary And Agent Context Isolation

## Use Cases

- After a valid DecisionRecord, agents receive compact approved governance summary facts and refs.
- Context builder filters out raw proposal text, rationale, raw chat, UI markdown, and unapproved discussion.
- Companion governance state informs workflow without granting Safety Gate authority.

## Acceptance Criteria

- Approved governance summary may include only decision id, Plant id, issue id,
  proposal id/version, decision, decision summary, allowed workflow effect, decider
  role, decided_at, source refs, and explicit `safety_gate_authority=not_granted`.
- Raw proposal text, raw rationale, raw chat, UI markdown, and unapproved discussion content remain non-consumable by agents.
- Approved summary cannot mutate Plant state or authorize physical action by itself.
- Context builder treats governance summaries as scoped typed facts with source refs.

## Edge Cases & Failure Modes

- Rejected or superseded proposals produce no operative agent facts.
- Governance summary cannot include hidden model reasoning.
- UI projection cannot alter what agents receive.
- Revoked Plant access blocks governance summary retrieval for that actor.

## Test Strategy Pointers

- `test:companion.approved-summary-context-filter`
- `test:harness.context-injection-boundary`
- `test:agent-output.bus-message-ui-isolation`

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): approved governance summary requirements.
- [.memory-bank/contracts/boundary-map.md](../contracts/boundary-map.md): Companion governance and context-builder boundaries.
- [.memory-bank/invariants.md](../invariants.md): UI Feed and raw chat exclusion rules.

## SDD Design Gate

Global `/spec-design` and feature-level `/spec-improve FT-015` are complete. Use
[.memory-bank/tech-specs/FT-015-approved-governance-summary-and-agent-context-isolation.md](../tech-specs/FT-015-approved-governance-summary-and-agent-context-isolation.md)
as the feature-local design hub before `/prd-to-tasks FT-015`.
