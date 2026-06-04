---
description: Feature FT-008 for permission-aware context building, scoped agent memory, retrieval, freshness, trust, and compaction boundaries.
status: draft
lifecycle: planned
spec_design_status: needs_spec_improve
epic: EP-003
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/contracts/boundary-map.md
---
# FT-008 Permission-Aware Context Builder And AgentMemoryRecord

## Use Cases

- Harness assembles context for one agent run from runtime state, evidence refs,
  approved governance summaries, and allowed AgentMemoryRecord refs.
- Plant State Agent retrieves prior scoped memory for long-running Plant analysis.
- Context compaction preserves active objective, permissions, approvals, source refs,
  and relevant memory without replaying raw chat or UI Feed.

## Acceptance Criteria

- AgentMemoryRecord is project-owned, durable, scoped, source-ref backed, auditable, and non-authoritative by itself.
- Memory retrieval is filtered by ActorContext, Farm/Plant scope, PlantAccessGrant,
  evidence provenance, freshness/trust semantics, Safety Gate boundaries, and dataset governance.
- Hidden provider memory, raw chat history, UI Feed replay, unapproved governance content,
  raw model reasoning, and provider/model memory cannot bypass the context builder.
- Context builder labels trusted instructions and untrusted/retrieved data distinctly.
- Compaction preserves active plan/approval/source state and cannot erase authority boundaries.

## Edge Cases & Failure Modes

- Stale memory is not treated as current Plant state.
- Revoked access blocks memory retrieval.
- Memory cannot promote hypotheses to confirmed Plant state.
- Memory cannot unlock Safety Gate or dataset trainability.
- Oversized context is compacted into structured handoff, not vague prose.

## Test Strategy Pointers

- `test:harness.memory-scope-permission-non-authority`
- `test:harness.context-injection-boundary`
- `test:harness.context-overflow-compaction-retention`

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): agent memory and context requirements.
- [.memory-bank/contracts/boundary-map.md](../contracts/boundary-map.md): context-builder and AgentMemoryRecord boundaries.
- [.memory-bank/states/lifecycle-map.md](../states/lifecycle-map.md): memory lifecycle hints.

## SDD Design Gate

Global `/spec-design` is complete. Before `/prd-to-tasks FT-008`, run
`/spec-improve FT-008` using the completed backbone docs: [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md), [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md), [.memory-bank/states/core-lifecycles.md](../states/core-lifecycles.md), [.memory-bank/contracts/index.md](../contracts/index.md), and [.memory-bank/testing/index.md](../testing/index.md). `/spec-improve` must decide AgentMemoryRecord schema,
lifecycle, retrieval order, trust labels, stale/supersede/archive handling,
compaction format, and permission filtering.
