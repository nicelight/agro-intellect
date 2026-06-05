---
description: Feature FT-016 for dataset governance fields, evidence refs, trainability guardrails, and 200 MB local storage prompt.
status: active
owner: product
lifecycle: planned
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-016-dataset-governance-and-local-storage-prompt.md
epic: EP-006
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/tech-specs/FT-016-dataset-governance-and-local-storage-prompt.md
---
# FT-016 Dataset Governance And Local Storage Prompt

## Use Cases

- Photo/measurement/outcome evidence becomes a future dataset candidate with non-trainable default.
- Dataset Governance Agent records evidence refs without granting trainability.
- UI shows local storage prompt after local dataset/photo storage exceeds 200 MB.

## Acceptance Criteria

- Dataset candidates are non-trainable by default.
- Evidence refs are required before any future trainability change.
- UI Feed, timeline snapshots, manifests, raw agent output, and agent-labeled content never grant trainability by themselves.
- MVP includes dataset lifecycle fields, evidence refs, confirmation source, split, and `can_train_on` guardrails without full dataset registry or real fine-tuning.
- Local storage prompt appears at 200 MB and does not imply upload/server availability.

## Edge Cases & Failure Modes

- Unauthorized Farm/Plant evidence cannot enter another actor's dataset context.
- `can_train_on=true` cannot be set outside dataset governance lifecycle.
- Storage prompt acknowledge/dismiss cannot change sync status.
- Server upload and `server_verified` semantics remain forbidden.

## Test Strategy Pointers

- `test:dataset.non-trainable-by-default`
- `test:storage.200mb-local-prompt-no-upload`
- `test:privacy.local-only-loopback-lan-controls`

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): dataset governance and local storage prompt requirements.
- [.memory-bank/invariants.md](../invariants.md): trainability and sync guardrails.
- [.memory-bank/glossary.md](../glossary.md): dataset lifecycle vocabulary.

## SDD Design Gate

Global `/spec-design` and feature-level `/spec-improve FT-016` are complete. Use
[.memory-bank/tech-specs/FT-016-dataset-governance-and-local-storage-prompt.md](../tech-specs/FT-016-dataset-governance-and-local-storage-prompt.md)
as the feature-local design hub before `/prd-to-tasks FT-016`.
