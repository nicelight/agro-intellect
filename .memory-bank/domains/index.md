---
description: Router for active canonical domain, persistence, migration, and internal data specifications.
status: active
last_updated: 2026-06-30
source_of_truth:
  - .memory-bank/spec-index.md
  - .memory-bank/spec-backbone.md
---
# Domains Index

## Global domain specs

- [Core Domain](core-domain.md): PRD-level vocabulary and rules.
- [Runtime Data Model](runtime-data-model.md): runtime authority and shared identity.
- [Foundation Data Substrate](foundation-data-substrate.md): DB/session/Alembic/runtime roots.
- [Photo Artifacts](photo-artifacts.md): local artifact authority.

## Subject data specs

- [Account And FarmMembership](identity/account-membership.md): local identity and membership persistence.
- [Session Storage](auth/session-storage.md): digest-only LocalSession persistence.
- [Farm Plant And Access Storage](farm/farm-plant-access-storage.md): bounded Plant/grant identity and status assumptions for the permission seam.
- [Admin Audit](admin/admin-audit.md): durable audited mutation records.

## Routing

Use `domains/` for internal models, storage, migrations, retention, and runtime
data rules. Payload compatibility belongs in `contracts/`; transitions belong
in `states/`. Discover existing canonical paths before creating a spec.
