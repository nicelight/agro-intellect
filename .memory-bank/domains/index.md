---
description: Active domain and data specification router.
status: active
owner: architecture
last_updated: 2026-06-29
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
- [Local Identity And Session Data](local-identity-session-data.md): exact FT-001 Account/FarmMembership/LocalSession relational contract.

## Routing

Use this folder for durable domain/data ownership. Concrete feature schemas and
product migrations may live here when a dedicated data owner is clearer than a
feature hub. Endpoint payloads and lifecycle state machines stay with their
natural contract/state owners.
