---
description: Global dataset governance and trainability lifecycle boundary for MVP v2.
status: active
type: state
last_updated: 2026-07-17
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

Exact persistence beyond the global fields below, lifecycle transitions,
evidence-policy details, derived-value materialization, endpoint schemas, and
UI behavior belong to `/prd-to-tasks FT-014`.

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

Dataset candidates use one lifecycle field, `candidate_status`, with exactly:

- `candidate`
- `needs_review`
- `confirmed`
- `rejected`
- `excluded`

`candidate_origin` is exactly `raw|agent_labeled` and describes provenance,
not lifecycle state. `quality_tier` is exactly `standard|gold` and describes
quality, not lifecycle state.

Every Dataset Candidate governance record must carry:

- `farm_id`
- `plant_id` when Plant-scoped
- `evidence_refs`
- nullable `confirmation_source`:
  `curator_auto|human_review|expert_review|batch_review`
- `candidate_status`
- `candidate_origin`
- `quality_tier`
- derived `can_train_on=false` by default
- `created_at`
- `updated_at`

## Rules

- Dataset Governance is the sole authority that derives `can_train_on`.
  Commands, agents, source artifacts, manifests, timeline events, UI Feed, and
  imports cannot set it directly.
- `can_train_on` is true only when `candidate_status=confirmed`, the canonical
  FT-014 evidence policy accepts non-empty `evidence_refs`, and an allowed
  `confirmation_source` is recorded. It is false for every other state.
- New candidates start with `candidate_status=candidate`,
  `quality_tier=standard`, nullable `confirmation_source=null`, and derived
  `can_train_on=false`.
- `curator_auto` may confirm an ordinary candidate only under the future exact
  FT-014 strong-evidence policy. A `gold` designation additionally requires
  human, expert, or batch review and can never be granted by `curator_auto`.
- Candidate provenance (`raw|agent_labeled`), dataset split, curator output, or
  a `gold` designation alone never grants trainability.
- `photo_catalog_items.can_train_on=false` is an immutable Photo Intake
  assertion: accepting a photo never grants trainability. It is not a second
  mutable trainability authority; a later Dataset Candidate is evaluated only
  by Dataset Governance.
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
- A request or agent result that supplies `can_train_on=true` is rejected;
  trainability is recomputed from canonical governance state.
- `quality_tier=gold` on a non-confirmed candidate, or with
  `confirmation_source=curator_auto|null`, is rejected.
- Unauthorized Plant evidence must not be mixed into a dataset candidate.
- Raw model/provider output must not be stored as trainable fact.
- Server sync/upload wording must not appear because MVP sync status is
  `local_only`.

## Verification

Tests must prove:

- New dataset candidates default to `can_train_on=false`.
- Tests cover the exact `candidate_status` enum and prove that provenance and
  `gold` are not lifecycle states.
- Tests prove `can_train_on` is derived, cannot be assigned by a request or
  agent, and remains false when state, evidence, or confirmation is missing.
- Tests prove `curator_auto` cannot grant `gold` and that `gold` requires a
  confirmed candidate plus human/expert/batch review.
- Photo Intake tests continue to prove its immutable source assertion remains
  `can_train_on=false` without becoming governance authority.
- UI Feed, timeline, manifests, and raw agent output cannot set trainability.
- Evidence refs and Plant scope are preserved.
- Unauthorized context cannot mix into dataset/export records.
- No MVP path triggers real fine-tuning or server upload.
