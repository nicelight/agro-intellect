---
description: Testing and verification router for MVP v2 migration.
status: active
owner: quality
last_updated: 2026-06-01
source_of_truth:
  - .memory-bank/constitution.md
  - .memory-bank/invariants.md
  - .memory-bank/spec-index.md
---
# Testing Index

## Current State

The active product/spec testing strategy is pending MVP v2 PRD and global SDD design.

MVP v1 testing docs are archived under
[.memory-bank/archive/mvp-v1/testing/](../archive/mvp-v1/testing/).

## Migration Gates

After Memory Bank routing or spec-layer changes, run:

```bash
node scripts/mb-lint.mjs
node scripts/mb-doctor.mjs
git diff --check
```

After `/prd` and `/spec-design`, run fresh-context Memory Bank review before task decomposition.

## Future MVP v2 Testing Areas

The MVP v2 testing strategy must be rebuilt from the new PRD and SDD backbone. Expected risk surfaces include:

- local account/session/authentication behavior;
- farm/plant authorization and per-Plant access;
- admin audit and Boss admin workflows;
- ActorContext propagation through APIs and workflows;
- Agent Chat Bus and UI Feed permission/context hygiene;
- Companion governance state and `DecisionRecord` semantics;
- Safety Gate approval roles and no automated physical actuation;
- dataset/export isolation by Farm/Plant context.
