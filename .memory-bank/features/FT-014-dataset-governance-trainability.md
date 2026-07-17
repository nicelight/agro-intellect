---
description: FT-014 Dataset Governance And Trainability.
status: draft
type: feature
feature_id: FT-014
epic: EP-006
lifecycle: planned
last_updated: 2026-06-26
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
---
# FT-014 Dataset Governance And Trainability

## Use Cases

- Photo, measurement, follow-up, review, and agent-output evidence create dataset candidates or dataset-related fields.
- Candidate remains non-trainable by default.
- Future trainability changes require evidence refs and governance lifecycle rules.
- Dataset/export refs remain Plant-scoped and permission-aware.

## Acceptance Criteria

- Dataset candidates are non-trainable by default.
- `can_train_on=true` cannot be set or implied outside dataset governance lifecycle.
- UI Feed, timeline snapshots, manifests, and raw agent output never grant trainability by themselves.
- Evidence refs are required before any future trainability change.

## Edge Cases & Failure Modes

- Agent-labeled data is not trainable by default.
- Raw Companion content cannot become dataset fact.
- Unauthorized Farm/Plant context cannot mix into dataset/export context.
- Full dataset registry and real fine-tuning are out of MVP.

## Verification Targets

- Unit: trainability default and transition policy after spec defines lifecycle.
- Integration: evidence refs and Plant scope are preserved.
- Anti-cheat: UI Feed/raw agent output cannot set trainability.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Dataset Governance module and non-goals.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): dataset fields and authority invariants.
- [.memory-bank/domains/photo-artifacts.md](../domains/photo-artifacts.md): local photo evidence refs.
- [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md): evidence consumability boundaries.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md): audit/export refs that cannot grant trainability.
- [.memory-bank/states/dataset-governance.md](../states/dataset-governance.md): trainability default, evidence gates, and lifecycle boundary.

## Feature-Local Design Pressure

- Exact dataset fields, lifecycle, transition authority, evidence refs,
  trainability recomputation, export constraints, and tests.

## SDD Design Gate

- Global/shared status: complete. The canonical Dataset Governance state uses
  one `candidate_status` lifecycle, separates `candidate_origin` and
  `quality_tier`, and makes `can_train_on` a derived result owned only by
  Dataset Governance.
- Photo Intake's existing `can_train_on=false` remains an immutable source
  assertion and is not mutable trainability authority.
- Feature-local status: pending `/prd-to-tasks FT-014` for exact persistence,
  evidence-policy, confirmation, agent I/O, API/export, and test contracts.
