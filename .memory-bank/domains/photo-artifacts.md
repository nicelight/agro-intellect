---
description: Global photo artifact authority and data contract for MVP v2.
status: active
type: domain
last_updated: 2026-06-30
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/contracts/api-guidelines.md
---
# Photo Artifacts

## Scope

Photo artifacts are local files and artifact refs used as evidence for Plant
operations, Vision Observation, future dataset governance, and audit/export.
They are not mutable Plant state and cannot override PostgreSQL/read-model
authority.

The verified FT-000 executable baseline provides local artifact root settings
only. Exact storage layout, manifest schema, upload route contracts, recovery
behavior, and photo catalog migrations belong to `/prd-to-tasks FT-005`.

## Contract Scope

- Defines: global photo artifact authority boundary, accepted artifact identity,
  local-only privacy rules, and cross-feature reference requirements.
- Out of scope: exact directory layout, multipart endpoint schema, manifest
  field catalog, thumbnail/derivative policy, or Vision Observation payloads.
- Related specs:
  - [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md):
    defines upload/authz/error guardrails.
  - [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md):
    defines audit/export refs.
  - [.memory-bank/states/plant-state-trust.md](../states/plant-state-trust.md):
    defines trust/promotion rules for photo-derived observations.
  - [.memory-bank/states/dataset-governance.md](../states/dataset-governance.md):
    defines trainability state.

## Artifact Identity

Feature-local specs may refine fields, but every accepted photo artifact flow
must produce or reference:

- `photo_artifact_id`
- `farm_id`
- `plant_id`
- `captured_or_uploaded_at`
- `actor_ref`
- `original_file_ref`
- `sha256`
- `content_type`
- `size_bytes`
- `catalog_ref`
- `manifest_ref`
- `source_refs`
- `local_only=true`

The file path itself is not a public authority token. Runtime records should
store stable artifact refs and safe metadata.

## Rules

- Photo upload must validate ActorContext, PlantAccessGrant, content type, size,
  and path safety before accepting the artifact.
- Accepted artifact metadata lives in PostgreSQL/read model; the binary file
  lives on the local filesystem.
- A photo file or manifest can support evidence but cannot promote an agent
  hypothesis to confirmed Plant state by itself.
- A photo artifact can become Vision Observation input only through authorized
  context and real vision/model-backed processing.
- A photo artifact can become a dataset candidate only through dataset
  governance rules; it is non-trainable by default.
- Manifests, logs, timeline events, UI Feed, exports, and agent context must not
  include secrets or auth material.

## Edge Cases And Errors

- Unsupported content type, invalid file, unsafe path, missing Plant access, or
  missing ActorContext must fail closed.
- The applicable canonical subject spec must define the atomicity policy for file write,
  catalog row, manifest, and timeline refs before task creation.
- If cleanup is needed after partial failure, it must not delete unrelated local
  data or retained authorized history.
- Archived Plant photo access requires explicit retained-history authorization.

## Verification

Tests must prove:

- Upload accepts only authorized Plant photos and rejects unsafe files.
- Accepted photo flow produces `sha256`, catalog ref, manifest ref, and audit
  refs without leaking secrets.
- Photo artifacts cannot override PostgreSQL/read-model Plant state.
- Unauthorized or archived-normal-operation access is filtered correctly.
- Dataset trainability remains false unless dataset governance later changes it.
