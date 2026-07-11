---
description: EP-002 Plant Operations Evidence Authority.
status: active
type: epic
epic_id: EP-002
lifecycle: verified
last_updated: 2026-07-11
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/user-scenarios.md
  - .memory-bank/domains/core-domain.md
---
# EP-002 Plant Operations Evidence Authority

## Value

Make authorized Plant care workflows useful and traceable while preserving the separation between mutable runtime state, local artifacts, and append-only audit/export.

## Features

- [FT-004 Authorized Plant Operations And Daily Check-In](../features/FT-004-authorized-plant-operations-daily-check-in.md)
- [FT-005 Photo Intake Catalog And Capture Manifests](../features/FT-005-photo-intake-catalog-capture-manifests.md)
- [FT-006 Runtime State Timeline And Plant History](../features/FT-006-runtime-state-timeline-plant-history.md)

## Success Metrics

- Boss and Engineer can complete the authorized backend/API Plant evidence
  workflow on `tomato_001`: check-in, observations, and manual pH/EC.
- Photo upload produces local file, catalog metadata, checksum, manifest, and audit refs.
- Runtime state remains separate from timeline/export artifacts.
- Authorized Plant card/history reads retain operational and photo evidence,
  including for archived Plants.

## Acceptance Criteria

- Plant operations are scoped by ActorContext and PlantAccessGrant.
- Daily check-in supports observations and manual pH/EC, with Plant-scoped
  seams to photo intake and Plant card/history.
- Photo intake persists accepted local artifacts, catalog metadata, checksum,
  capture manifest, and timeline refs.
- Plant history projects implemented operational/photo/admin evidence from
  runtime authority and may retain typed refs for future owning modules.
- Archived Plants are removed from normal operations but retained for authorized history/audit/export access.
- `timeline.jsonl` remains audit/export only.

## Constraints / Invariants

- PostgreSQL/read model remains mutable runtime authority until an active architecture spec changes it.
- Photo files and manifests are local artifacts, not mutable runtime authority.
- EP-002 applies strict secret/auth redaction to its timeline, manifests,
  Plant history, evidence refs, and audit/export surfaces. Cross-cutting
  redaction for Bus, UI Feed, and agent context remains mandatory under global
  specs and is implemented by EP-003/EP-006; it is not an EP-002 closure
  condition.

## Feature-Local Design Pressure

- Exact storage layout and manifest fields.
- Exact timeline event taxonomy.
- Exact daily check-in state model and persistence sequence.

## Current Implementation State

- FT-004, FT-005, and FT-006 task records `TASK-019` through `TASK-027` are
  recorded `done`; repair tasks TASK-025/026/027 have independent functional
  PASS and task-level `semantic-pass` evidence.
- FT-004, FT-005, and FT-006 are synchronized as `verified` after current
  feature-level `SEMANTIC_VERDICT: semantic-pass` reports. Historical
  feature-level failure/concern reports remain preserved.
- EP-002 is synchronized as `verified` for its independently closable
  backend/API evidence-authority scope. Tasks, approvals, follow-up, Safety
  Gate, agent/Vision behavior, and PWA/first-demo composition are not EP-002
  closure conditions.
- Existing TASK-019 through TASK-024 checkpoint waivers remain recorded.
  Missing exact `HUMAN_CHECKPOINT: done` markers for TASK-025 and TASK-027 are
  also explicitly accepted advisory waivers in their task records; no marker
  is fabricated. TASK-026 is T2.
- FT-006 follows the owner-approved URL-first/KISS best-effort local-path
  presentation policy; ambiguous paths/links may remain visible rather than
  reintroducing unstable parsing machinery, while secret/auth redaction stays
  strict.
- This verified EP-002 scope covers authorized check-in, observations, manual
  pH/EC, photo intake/manifests, PostgreSQL runtime authority, timeline
  audit/export refs, and retained Plant card/history. Future task, approval,
  follow-up, agent, and governance records may integrate through typed history
  refs only after their owning epics implement them; those implementations are
  not claimed here. Raw export packages, PWA UI, Vision, agents, Safety Gate,
  physical-action tasks, follow-up, Companion governance, dataset trainability
  transitions, remote sync, and automated actuation remain outside EP-002.
