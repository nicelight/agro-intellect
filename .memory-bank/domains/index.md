---
description: Active domain and data specification router.
status: active
owner: architecture
last_updated: 2026-06-26
source_of_truth:
  - .memory-bank/spec-index.md
  - .memory-bank/spec-backbone.md
---
# Domains Index

## Active Domain Specs

- [Core Domain](core-domain.md): PRD-level vocabulary, entities, roles, business rules, and lifecycle hints.
- [Runtime Data Model](runtime-data-model.md): global runtime authority, shared entity ownership, and feature-local data-detail routing.
- [Foundation Data Substrate](foundation-data-substrate.md): FT-000 DB/session/Alembic/runtime-root substrate.
- [Photo Artifacts](photo-artifacts.md): local photo artifact authority, identity, privacy, and cross-feature evidence refs.

## Routing

Use this folder for durable domain/data ownership. Concrete feature schemas,
field catalogs, product migrations, state-machine fixtures, and endpoint payloads
belong to feature-level SDD specs unless a shared/global owner is explicitly
needed.
