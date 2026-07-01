---
description: Global dataset governance and trainability lifecycle boundary for MVP v2.
status: active
type: state
last_updated: 2026-06-30
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/domains/runtime-data-model.md
---
# Dataset Governance

## Scope

Dataset Governance defines the global evidence and trainability boundary for
photo, measurement, follow-up, review, and agent-output evidence. It does not
create a full dataset registry or real fine-tuning path in MVP.

Exact dataset fields, lifecycle transitions, recomputation rules, endpoint
schemas, and UI behavior belong to `/prd-to-tasks FT-014`.

## Scope Boundaries

- Defines: global non-trainable default, evidence-ref requirement, allowed
  trainability authority, forbidden sources, and verification requirements.
- Out of scope: full registry schema, ML training jobs, model evaluation,
  export packaging, or fine-tuning workflows.
- Related specs:
  - [.memory-bank/domains/photo-artifacts.md](../domains/photo-artifacts.md):
    defines local photo evidence refs.
  - [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md):
    defines audit/export event refs.
  - [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md):
    defines agent-consumable evidence boundaries.

## Lifecycle Shape

Feature-local specs may refine states, but dataset candidates must distinguish:

- `candidate`
- `needs_review`
- `confirmed`
- `rejected`
- `excluded`

Every dataset-related record must carry:

- `farm_id`
- `plant_id` when Plant-scoped
- `evidence_refs`
- `confirmation_source`
- `candidate_status`
- `can_train_on=false` by default
- `created_at`
- `updated_at`

## Rules

- `can_train_on` is false by default.
- Evidence refs are required before any future transition that could make data
  trainable.
- UI Feed, timeline snapshots, manifests, raw agent output, raw Companion
  content, and unreviewed model labels never grant trainability by themselves.
- Agent-labeled evidence remains non-trainable until a future explicit review
  path allows a transition.
- Full dataset registry, real fine-tuning, and production learning loops are
  out of MVP.
- Dataset/export context must stay Farm/Plant scoped and permission-aware.

## Edge Cases And Errors

- Missing evidence refs block any trainability transition.
- Unauthorized Plant evidence must not be mixed into a dataset candidate.
- Raw model/provider output must not be stored as trainable fact.
- Server sync/upload wording must not appear because MVP sync status is
  `local_only`.

## Verification

Tests must prove:

- New dataset candidates default to `can_train_on=false`.
- UI Feed, timeline, manifests, and raw agent output cannot set trainability.
- Evidence refs and Plant scope are preserved.
- Unauthorized context cannot mix into dataset/export records.
- No MVP path triggers real fine-tuning or server upload.
