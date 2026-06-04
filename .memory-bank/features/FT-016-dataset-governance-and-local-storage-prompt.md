---
description: Feature FT-016 for dataset governance fields, evidence refs, trainability guardrails, and 200 MB local storage prompt.
status: draft
lifecycle: planned
spec_design_status: needs_spec_improve
epic: EP-006
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
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

Global `/spec-design` is complete. Before `/prd-to-tasks FT-016`, run
`/spec-improve FT-016` using the completed backbone docs: [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md), [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md), [.memory-bank/states/core-lifecycles.md](../states/core-lifecycles.md), [.memory-bank/contracts/index.md](../contracts/index.md), and [.memory-bank/testing/index.md](../testing/index.md). `/spec-improve` must decide dataset fields, lifecycle,
evidence refs, trainability recomputation rules, local storage measurement, and prompt
behavior.
