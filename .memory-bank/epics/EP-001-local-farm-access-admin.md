---
description: EP-001 Local Farm Access And Admin.
status: draft
type: epic
epic_id: EP-001
lifecycle: planned
last_updated: 2026-06-30
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/user-scenarios.md
  - .memory-bank/domains/core-domain.md
---
# EP-001 Local Farm Access And Admin

## Value

Establish the local Farm authority boundary so every human action and agent context is attributable, role-scoped, Plant-scoped, and auditable.

## Features

- [FT-001 Local Accounts Sessions And ActorContext](../features/FT-001-local-accounts-sessions-actor-context.md): complete identity/session/access subject-spec composition.
- [FT-002 Farm Plant Lifecycle And Access Grants](../features/FT-002-farm-plant-lifecycle-access-grants.md): bounded resolver dependency slice; full SDD pending.
- [FT-003 Boss Admin Surface And Admin Audit](../features/FT-003-boss-admin-surface-admin-audit.md): direct-account KISS direction; full SDD pending.

## Success Metrics

- Boss can use the single local Farm and administer at least one Engineer Account.
- Every Farm/Plant route and context builder can resolve ActorContext.
- Engineer sees only granted Plants.
- Plant archive/restore retains authorized history and audit.

## Acceptance Criteria

- Local Accounts, FarmMembership, role preset, PlantAccessGrant, and ActorContext are represented as active MVP concepts.
- Boss, Engineer, and Consultant role semantics are traceable to PRD requirements.
- Per-Plant access is backend-enforced; frontend visibility is presentation only.
- Admin changes create durable audit records.

## Constraints / Invariants

- Exactly one local Farm workspace in MVP.
- `tomato_001` is the initial Plant, not a permanent product limit.
- MVP permission overrides are limited to `plant_approve_actions`.
- No SaaS tenancy, enterprise identity, hosted recovery, or email delivery requirement.

## Spec Design Status

- FT-001 composition is complete; FT-002 has only the bounded permission seam
  needed by FT-001, and FT-003 records the direct-account KISS direction.
- Canonical subject specs are registered in [.memory-bank/spec-index.md](../spec-index.md); feature docs compose applicable paths.
- `/prd-to-tasks FT-001` is complete with [.memory-bank/tasks/plans/IMPL-FT-001.md](../tasks/plans/IMPL-FT-001.md) and active single-card task records `TASK-005-T3-FT-001-W1` through `TASK-011-T3-FT-001-W3`.
- Generated task-decomposition artifacts for FT-002 and FT-003 remain intentionally removed.
- Next EP-001 route is `/review-tasks-plan FT-001` before implementation.
