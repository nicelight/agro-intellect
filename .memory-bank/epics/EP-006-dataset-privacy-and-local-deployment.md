---
description: Epic EP-006 for dataset governance, trainability, local storage prompts, privacy, local deployment, and secret redaction.
status: active
owner: product
lifecycle: planned
epic_id: EP-006
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/testing/index.md
---
# EP-006 Dataset Privacy And Local Deployment

## Value

Preserve evidence for future learning without turning MVP data into a training system
or cloud product. Local privacy, `local_only` sync, storage prompts, dataset
trainability, and secret redaction stay explicit and testable.

## Features

- FT-016 Dataset Governance And Local Storage Prompt.
- FT-017 Local Privacy, Deployment Controls, And Secret Redaction.

## Success Metrics

- Dataset candidates remain non-trainable by default.
- Trainability cannot be granted by UI Feed, timeline snapshots, manifests, or raw
  agent output alone.
- Local storage prompt appears at the 200 MB threshold without implying upload/server
  availability.
- Loopback is default; LAN mode requires explicit auth/session, authorization,
  token/session protection, and CORS/origin controls.
- Secrets and auth material are absent from logs, timeline, manifests, Bus, UI Feed,
  screenshots, exports, and agent context.

## Acceptance Criteria

- `sync.status` remains `local_only`; `server_verified` and server upload semantics are
  forbidden until a later server-sync stage exists.
- Dataset lifecycle fields and evidence refs exist without introducing a full dataset
  registry or real fine-tuning in MVP.
- Local artifacts are private by default and no upload/sync is implied.

## Constraints / Invariants

- Full dataset registry, real fine-tuning, object storage, server sync, and production
  SaaS remain out of MVP.
- Secret redaction is mandatory across product, audit, export, screenshot, and agent
  context surfaces.

## Verification Targets

- `test:dataset.non-trainable-by-default`
- `test:storage.200mb-local-prompt-no-upload`
- `test:privacy.local-only-loopback-lan-controls`
- `test:privacy.secret-redaction-surfaces`
