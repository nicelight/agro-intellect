---
description: EP-003 - Learning governance and trainability for future datasets.
status: draft
lifecycle: planned
---
# EP-003 Learning Governance

## Value

Protect future training and evaluation data from raw agent hypotheses by making dataset lifecycle, provenance, evidence refs, split restrictions, and `can_train_on` eligibility explicit from the MVP start.

## Success metrics

- Dataset lifecycle fields are present for evidence items without introducing a full dataset registry.
- Raw and agent-labeled items cannot become trainable.
- `can_train_on=true` is allowed only when curator decision, split, evidence refs, status, and confirmation source rules permit it.
- `gold` examples require human, expert, or batch review approval.
- Dataset decisions stay traceable to source, model/prompt version, reviewer role when reviewed, timestamps, and evidence/outcome refs.

## Acceptance criteria

- The system tracks `dataset.status`: `raw`, `agent_labeled`, `needs_review`, `confirmed`, `rejected`, `gold`, `excluded`.
- The system tracks `dataset.split`, `dataset.curator_decision`, `dataset.confirmation_source`, `dataset.evidence_refs`, `dataset.curator_notes_ref`, `dataset.corrected`, and `dataset.follow_up_seen`.
- Dataset and agent-report provenance includes source, `model_version`, `prompt_version`, reviewer role when reviewed, `created_at`, and outcome/evidence refs when available.
- The MVP includes key lifecycle fields but does not implement a full dataset registry.
- `dataset.split=eval` and `dataset.split=holdout` are never used for fine-tuning/train.
- `curator_auto` may confirm ordinary train items only when strong `evidence_refs` exist.
- `curator_auto` cannot create `gold`.

## Source artifacts

- [.memory-bank/prd.md](../prd.md): FR-016, dataset governance acceptance criteria, edge cases, and verification strategy.
- [project_dossier.md](../../project_dossier.md): sections 8.7, 8.8, 15.1, 18, 19, 28, and 33 for compressed learning-loop context.
- [.memory-bank/requirements.md](../requirements.md): REQ-011 and RTM link.
- [.memory-bank/features/FT-009-dataset-governance-trainability.md](../features/FT-009-dataset-governance-trainability.md): included feature scope.

## Normative inputs

- [.memory-bank/constitution.md](../constitution.md): bounded agent autonomy, evidence-based dataset curation, KISS, and low-maintenance constraints.
- [.memory-bank/spec-index.md](../spec-index.md): SDD route map for planned dataset governance lifecycle, runtime data model, Training Data Curator policy, and export snapshot interaction.
- [.memory-bank/testing/index.md](../testing/index.md): dataset governance risk-surface gates.

## Constraints / invariants

- Agent hypotheses are not confirmed facts and default to non-trainable.
- Dataset governance starts with required lifecycle fields, not a broad dataset registry.
- PostgreSQL/read model remains authority for mutable dataset/review/sync status.
- Photo JSON manifests are export snapshots and cannot define current mutable dataset status.
- Training data curation may be mostly autonomous only with strong `evidence_refs`.

## Features included

- [FT-009 Dataset Governance and Trainability](../features/FT-009-dataset-governance-trainability.md): dataset lifecycle fields, provenance, split restrictions, curator decisions, evidence refs, `gold` restrictions, and `can_train_on` eligibility.
