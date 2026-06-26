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
- [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md): evidence consumability boundaries.

## SDD Design Gate

Run global `/spec-design` before this feature is task-decomposed. Then run `/prd-to-tasks FT-014`; it must define exact dataset fields, lifecycle, transition authority, evidence refs, trainability recomputation, and tests during its feature-level SDD design phase before writing tasks. Use standalone `/spec-improve FT-014` only for repair or advanced refresh without task generation.
