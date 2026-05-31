---
description: FT-009 - Dataset governance and trainability.
status: draft
lifecycle: planned
parent_epic: EP-003
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-009-dataset-governance-trainability.md
  - .memory-bank/states/dataset-governance.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/domains/photo-artifacts.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/testing/first-demo.md
---
# FT-009 Dataset Governance and Trainability

## Parent Epic

- [EP-003 Learning Governance](../epics/EP-003-learning-governance.md): dataset lifecycle, provenance, and trainability governance.

## Purpose

Define the MVP learning-governance slice that records dataset lifecycle fields and provenance from the start while preventing raw agent hypotheses from becoming trainable data.

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): FR-016, non-goals, dataset acceptance criteria, edge cases, and verification strategy.
- [project_dossier.md](../../project_dossier.md): sections 8.7, 8.8, 15.1, 18, 19, 28, and 33 for trainability and curator-source rules.
- [.memory-bank/requirements.md](../requirements.md): REQ-011.
- [.memory-bank/constitution.md](../constitution.md): bounded autonomy, dataset evidence discipline, KISS, and low-maintenance constraints.
- [.memory-bank/spec-index.md](../spec-index.md): route map for dataset governance lifecycle, runtime data model, Training Data Curator policy, export snapshot interaction, and first-demo verification.
- [.memory-bank/testing/index.md](../testing/index.md): dataset governance tests.

## Use Cases

- The system records dataset lifecycle metadata for photos, observations, agent reports, outcomes, and future export candidates.
- Dataset Governance checks whether an item is raw, agent-labeled, review-needed, confirmed, rejected, gold, or excluded.
- Training Data Curator selects, defers, or rejects candidate items using evidence refs and curator notes.
- The system prevents eval and holdout examples from being used for fine-tuning/train.
- The system allows `curator_auto` only for ordinary confirmed train items with strong evidence refs.
- The system escalates conflict, low-confidence, rare valuable, gold-candidate, or high-impact labels for human, expert, batch, or sampling review.

## Acceptance Criteria

- `dataset.status` supports `raw`, `agent_labeled`, `needs_review`, `confirmed`, `rejected`, `gold`, and `excluded`.
- The system tracks separate fields for `dataset.split`, `dataset.curator_decision`, `dataset.confirmation_source`, `dataset.evidence_refs`, `dataset.curator_notes_ref`, `dataset.corrected`, and `dataset.follow_up_seen`.
- Dataset and agent-report provenance includes source, `model_version`, `prompt_version`, reviewer role when reviewed, `created_at`, and outcome/evidence refs when available.
- `can_train_on=true` requires `dataset.curator_decision=selected`, `dataset.split=train`, non-empty `dataset.evidence_refs`, and allowed status/source rules.
- Allowed trainability status/source rules are confirmed items with `curator_auto`, `human`, `expert`, or `batch_review`, or gold items with `human`, `expert`, or `batch_review`.
- `dataset.split=eval` and `dataset.split=holdout` are rejected for fine-tuning/train.
- `gold` requires human, expert, or batch review approval.
- `curator_auto` cannot create `gold`.
- The MVP includes the key lifecycle fields but does not introduce a full dataset registry.

## Edge Cases / Failure Modes

- Agent diagnosis or raw hypothesis attempts to set `can_train_on=true`: reject.
- Dataset item has no evidence refs: keep non-trainable.
- Item is selected but split is `eval` or `holdout`: reject for train/fine-tuning.
- Item is `gold` with `curator_auto`: reject.
- Confirmation source is missing for confirmed or gold status: reject trainability.
- Evidence conflicts or follow-up contradicts the label: mark needs review, conflict, rejected, or excluded according to later design.
- Export snapshot contains stale dataset status: read current mutable status from PostgreSQL/read model instead.

## Test Strategy Pointers

- `schema:dataset-provenance` for lifecycle fields, source, model/prompt version, reviewer role, timestamps, and evidence/outcome refs.
- `schema:dataset-transition-audit` for actor, reason, evidence, review, curator, and event refs on trainability-affecting transitions.
- `policy:dataset-lifecycle-transitions` for allowed/forbidden lifecycle transitions.
- `policy:dataset-trainability` for the full `can_train_on=true` eligibility rule.
- `policy:split-restrictions` for eval/holdout never entering train/fine-tuning.
- `policy:gold-review-restriction` for human/expert/batch-review-only `gold`.
- `policy:agent-hypothesis-not-trainable` for raw and agent-labeled items.
- `policy:conflict-resets-trainability` for contradictory follow-up, correction, or conflict resetting `can_train_on=false`.
- `integration:postgres-dataset-authority` for mutable dataset status read from PostgreSQL/read model rather than stale manifests.
- `workflow:curator-decision` for selected/deferred/rejected decisions with evidence refs and curator notes.

## Constraints / Invariants

- Agent-labeled conclusions are hypotheses, not trainable labels.
- Dataset governance fields exist from the start, but full dataset registry scope is deferred.
- PostgreSQL/read model owns mutable dataset/review/sync state.
- Photo manifests are export snapshots only.
- Training data selection needs evidence refs.
- `gold` requires stronger review than `curator_auto`.

## SDD Design Gate

Feature-level `/spec-improve FT-009` is complete. Normative design inputs for `/prd-to-tasks FT-009`:

- [.memory-bank/tech-specs/FT-009-dataset-governance-trainability.md](../tech-specs/FT-009-dataset-governance-trainability.md): feature-local decisions for dataset item boundary, transition service, trainability recomputation, evidence refs, curator rules, API/service surface, and verification targets.
- [.memory-bank/states/dataset-governance.md](../states/dataset-governance.md): lifecycle fields, transition matrix, actor/source rules, trainability side effects, split restrictions, and gold constraints.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): mutable dataset/review/sync fields in PostgreSQL/read model.
- [.memory-bank/domains/photo-artifacts.md](../domains/photo-artifacts.md): export snapshots are artifacts, not current dataset authority.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): agent outputs default to non-trainable hypotheses unless governance allows otherwise.
- [.memory-bank/testing/first-demo.md](../testing/first-demo.md): dataset trainability anti-cheat gates.

A standalone Training Data Curator contract is not required for FT-009 task decomposition. The MVP curator/source rules are owned by the dataset governance state spec; a later public agent contract can be added only if agent runtime work needs a separate boundary.
