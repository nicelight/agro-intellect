---
description: Active state and lifecycle spec router for MVP v2.
status: active
owner: architecture
last_updated: 2026-06-26
source_of_truth:
  - .memory-bank/spec-index.md
  - .memory-bank/spec-backbone.md
---
# States Index

## Active State Specs

- [Lifecycle Map](lifecycle-map.md): pre-PRD lifecycle hints retained as context.
- [Plant State Trust](plant-state-trust.md): global trust and promotion boundary
  for observations, hypotheses, conflicts, and confirmed Plant state.
- [Safety Action Lifecycle](safety-action-lifecycle.md): global Safety Gate,
  approval, action task, and follow-up authority boundary.
- [Companion Governance](companion-governance.md): global IssueStack,
  proposal, DecisionRecord, and approved summary lifecycle boundary.
- [Dataset Governance](dataset-governance.md): global trainability and evidence
  lifecycle boundary.

## Routing

Exact feature-local state machines, DB fields, endpoint payloads, and task
records belong to `/prd-to-tasks FT-<NNN>` unless a state rule is shared across
multiple features. Shared safety, governance, trainability, and Plant trust
rules live here and must be linked from dependent T2/T3 tasks.
