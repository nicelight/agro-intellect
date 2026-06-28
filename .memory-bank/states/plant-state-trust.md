---
description: Global Plant state trust and promotion boundary for MVP v2.
status: active
owner: architecture
type: state
last_updated: 2026-06-26
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/domains/runtime-data-model.md
---
# Plant State Trust

## Scope

Plant State Trust defines how observations, measurements, photo-derived
hypotheses, model outputs, and follow-up evidence may move toward confirmed
Plant state. It is a global guardrail; exact state fields, freshness windows,
and UI labels belong to feature-level SDD design.

## Ownership

- Owns: global promotion rules, trust categories, conflict handling, and
  verification requirements for keeping agent hypotheses out of confirmed state
  without review/evidence.
- Does not own: exact Plant state table schema, measurement freshness windows,
  Vision Observation payload fields, UI labels, or first-demo view layout.
- Related specs:
  - [.memory-bank/domains/photo-artifacts.md](../domains/photo-artifacts.md):
    owns photo artifact refs.
  - [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md):
    owns observation/hypothesis output boundary.
  - [.memory-bank/states/safety-action-lifecycle.md](safety-action-lifecycle.md):
    owns physical-action routing after Plant state evidence is evaluated.

## Trust Shape

Feature-local specs may refine names, but Plant evidence must distinguish:

- `unknown`
- `observed`
- `hypothesis`
- `conflicting`
- `confirmed`
- `rejected`

Every Plant-state-affecting record must carry:

- `plant_id`
- `source_refs`
- `evidence_kind`
- `observed_at` or `recorded_at`
- `trust_status`
- `confirmation_source` when confirmed
- `actor_ref` or `agent_ref`

## Rules

- Agent/model output may create observations, hypotheses, clarifications, or
  task requests, but cannot directly create confirmed Plant state.
- Confirmed Plant state requires human review, measurement evidence, follow-up
  evidence, or another feature-defined confirmation source.
- Contradictory evidence must be represented as `conflicting` or routed for
  review; it must not be silently collapsed into confirmed state.
- Fresh pH/EC or photo evidence is not enough by itself to clear physical-action
  wording; Safety Gate rules still apply.
- UI Feed display of a trust status does not change runtime state.
- Timeline events and photo manifests can reference trust state but cannot be
  the mutable authority for it.

## Edge Cases And Errors

- Missing source refs block promotion to confirmed state.
- Low-confidence or unsupported model output remains hypothesis/unknown.
- Unauthorized evidence cannot be considered for Plant state.
- Archived Plant state reads require retained-history authorization.

## Verification

Tests must prove:

- Vision/model hypotheses are not promoted to confirmed state without explicit
  review/evidence.
- Conflicting evidence remains visible as conflict/review state.
- UI Feed and timeline refs cannot mutate trust status.
- Unauthorized Plant evidence is excluded from trust computation.
- Safety Gate checks still run even when evidence is fresh.
