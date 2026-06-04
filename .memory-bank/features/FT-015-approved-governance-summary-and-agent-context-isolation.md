---
description: Feature FT-015 for approved governance summaries and strict exclusion of raw governance/chat/UI content from agent context.
status: draft
lifecycle: planned
spec_design_status: needs_spec_improve
epic: EP-005
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/contracts/boundary-map.md
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

Global `/spec-design` is complete. Before `/prd-to-tasks FT-015`, run
`/spec-improve FT-015` using the completed backbone docs: [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md), [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md), [.memory-bank/states/core-lifecycles.md](../states/core-lifecycles.md), [.memory-bank/contracts/index.md](../contracts/index.md), and [.memory-bank/testing/index.md](../testing/index.md). `/spec-improve` must decide approved summary schema, context
filtering, source refs, retrieval permissions, and anti-leak tests.
