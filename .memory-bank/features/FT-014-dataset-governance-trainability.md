---
description: FT-014 Dataset Governance And Trainability.
status: active
type: feature
feature_id: FT-014
epic: EP-006
lifecycle: planned
last_updated: 2026-08-10
clarification_status: complete
last_clarified: 2026-08-10
clarification_questions: 1
spec_design_status: complete
spec_design_links:
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/contracts/boundary-map.md
  - .memory-bank/contracts/timeline-event.md
  - .memory-bank/contracts/agent-runtime-adapter.md
  - .memory-bank/contracts/agent-model-provider-profiles.md
  - .memory-bank/states/dataset-governance.md
  - .memory-bank/domains/dataset-governance.md
  - .memory-bank/contracts/dataset-agents-runtime.md
  - .memory-bank/testing/dataset-governance.md
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

### FT-014-AC-001 — Non-trainable default

- REQ: REQ-019
- Dataset candidates are non-trainable by default.

### FT-014-AC-002 — Sole trainability authority

- REQ: REQ-019
- `can_train_on=true` cannot be set or implied outside the Dataset Governance
  lifecycle.

### FT-014-AC-003 — Forbidden trainability sources

- REQ: REQ-019
- UI Feed, Timeline snapshots, manifests, and raw agent output never grant
  trainability by themselves.

### FT-014-AC-004 — Evidence requirement

- REQ: REQ-019
- Evidence refs are required before any trainability change.

### FT-014-AC-005 — Photo candidate creation

- REQ: REQ-019
- Accepted photo evidence automatically creates one `raw` non-trainable
  candidate with its typed ref, Farm/Plant scope, same-UoW rollback, and
  source-row idempotency.

### FT-014-AC-006 — Dataset Governance Agent remains advisory

- REQ: REQ-011, REQ-019
- Dataset Governance Agent uses the registered provider-neutral advisory-only
  route. Its assessment persists no Dataset field, cannot set evidence,
  lifecycle, quality, split, confirmation, or trainability, and creates no
  MessageEnvelope, Safety, Bus, or UI effect.

### FT-014-AC-007 — Multi-evidence association command

- REQ: REQ-019
- Internal Dataset-Governance-owned `associate_follow_up_evidence` derives
  eligible candidates from an authorized follow-up Outcome, adds its typed ref
  idempotently under current locks, and changes no lifecycle or trainability
  field.

### FT-014-AC-008 — Agent-labeled guard

- REQ: REQ-019
- `agent_labeled` candidates cannot be confirmed in MVP.

### FT-014-AC-009 — Daily check-in candidate creation

- REQ: REQ-019
- A completed daily check-in automatically creates one `raw` non-trainable
  candidate with its typed observation ref, Farm/Plant scope, same-UoW
  rollback, and source-row idempotency.

### FT-014-AC-010 — Manual measurement candidate creation

- REQ: REQ-019
- A recorded manual measurement automatically creates one `raw` non-trainable
  candidate with its typed measurement ref, Farm/Plant scope, same-UoW
  rollback, and source-row idempotency.

### FT-014-AC-011 — Follow-up Outcome candidate creation

- REQ: REQ-019
- A recorded follow-up Outcome automatically creates one `raw` non-trainable
  candidate with its typed Outcome ref, Farm/Plant scope, same-UoW rollback,
  and source-row idempotency.

### FT-014-AC-012 — Production follow-up evidence enrichment

- REQ: REQ-019
- `record_follow_up_outcome` invokes `associate_follow_up_evidence` in its
  existing UoW over already-authorized source refs, making canonical
  multi-evidence candidate state production-reachable without a new HTTP/UI or
  caller-selected association.

### FT-014-AC-013 — Training Data Curator remains advisory

- REQ: REQ-011, REQ-019
- Training Data Curator uses the registered provider-neutral advisory-only
  route. Deferred/rejected results persist only the exact current-run advisory
  allowlist, silence persists nothing, and no result directly changes evidence,
  lifecycle, quality, split, confirmation, or trainability.

### FT-014-AC-014 — Positive curator auto gate

- REQ: REQ-011, REQ-019
- A current-run `selected` curator result plus production-created canonical
  strong evidence may atomically confirm through `curator_auto`; weak/stale,
  `gold`, and `agent_labeled` paths fail without a reusable selected advisory
  or trainability change.

## Clarifications

### 2026-08-10 — Positive curator_auto reachability

- Positive `curator_auto` is required to be production-reachable in FT-014.
- `record_follow_up_outcome` calls the internal Dataset-Governance-owned
  `associate_follow_up_evidence` in its existing UoW. Dataset Governance
  derives eligible targets from the Outcome's authorized source refs and
  accepts no caller-selected candidate/lifecycle/trainability result.
- AD-011 selects the registered advisory-only route for both Dataset Agents;
  no generic MessageEnvelope/Safety/Bus/UI consumer is added.
- Governing requirements remain REQ-011 and REQ-019. REQ-003, REQ-010, and
  REQ-020 remain non-owning normative constraints.

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

- Global repair complete: AD-011 registers the advisory-only Dataset Agents
  route; the provider union, Agent Runtime exception, Dataset Timeline matrix,
  and canonical Boundary Map are authoritative at Planning Revision 3.
- Clarified: positive `curator_auto` must be production-reachable in FT-014.
  `record_follow_up_outcome` invokes the internal Dataset-Governance-owned
  `associate_follow_up_evidence` command inside its owning UoW. That command
  derives eligible candidates from already-authorized Outcome evidence refs,
  appends the Outcome ref idempotently, and accepts no caller-selected
  lifecycle or trainability result.
- Reconciled: the command, current-run identity, post-I/O authorization/archive
  races, normal source uniqueness, stable atomic AC ownership, and canonical
  verification matrices are defined in the linked specs.
- Operator decisions D1-D3 and provisional planner decisions D4-D9 remain in:
  [.protocols/FT-014/decision-log.md](../../.protocols/FT-014/decision-log.md).
- Deferred: any HTTP/review UI boundary (D1, including the FT-016
  dataset-fields read surface), agent-output evidence wiring (D2), export
  snapshots (D9).

## Behavior specs

- [.memory-bank/behavior-specs/FT-014-BHV-001-auto-created-candidate-non-trainable.behavior.json](../behavior-specs/FT-014-BHV-001-auto-created-candidate-non-trainable.behavior.json)
- [.memory-bank/behavior-specs/FT-014-BHV-002-curator-auto-evidence-gate.behavior.json](../behavior-specs/FT-014-BHV-002-curator-auto-evidence-gate.behavior.json)
- [.memory-bank/behavior-specs/FT-014-BHV-003-production-curator-auto-positive.behavior.json](../behavior-specs/FT-014-BHV-003-production-curator-auto-positive.behavior.json)

## SDD Design Gate

- Global Backbone is `complete` at Planning Revision 3; AD-011, the Dataset
  Timeline matrices, and the canonical Boundary Map close every shared FT-014
  blocker.
- Photo Intake's existing `can_train_on=false` remains an immutable source
  assertion and is not mutable trainability authority.
- Feature-local status: complete. The full rebuilt queue is execution-blocked
  only until fresh `/review-tasks-plan FT-014` APPROVE for Planning Revision 3;
  [.memory-bank/tasks/plans/IMPL-FT-014.md](../tasks/plans/IMPL-FT-014.md)
  records the exact resume gates. No FT-014 task may execute until a rebuilt
  queue passes `/review-tasks-plan FT-014` for the then-current positive
  Planning Revision.
