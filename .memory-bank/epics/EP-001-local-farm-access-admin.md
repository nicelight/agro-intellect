---
description: EP-001 Local Farm Access And Admin.
status: draft
type: epic
epic_id: EP-001
lifecycle: planned
last_updated: 2026-06-26
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

- [FT-001 Local Accounts Sessions And ActorContext](../features/FT-001-local-accounts-sessions-actor-context.md): `/spec-improve` complete; current normative feature design is [.memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md](../tech-specs/FT-001-local-accounts-sessions-actor-context.md).
- [FT-002 Farm Plant Lifecycle And Access Grants](../features/FT-002-farm-plant-lifecycle-access-grants.md): `/spec-improve` complete; current normative feature design is [.memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md](../tech-specs/FT-002-farm-plant-lifecycle-access-grants.md).
- [FT-003 Boss Admin Surface And Admin Audit](../features/FT-003-boss-admin-surface-admin-audit.md): `/spec-improve` complete; current normative feature design is [.memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md](../tech-specs/FT-003-boss-admin-surface-admin-audit.md).

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

- First-wave `/spec-improve` is complete for FT-001, FT-002, and FT-003.
- Current normative feature designs are registered in [.memory-bank/spec-index.md](../spec-index.md).
- `/prd-to-tasks FT-001` is complete and was refreshed on 2026-06-26 with [.memory-bank/tasks/plans/IMPL-FT-001.md](../tasks/plans/IMPL-FT-001.md) and active task records `TASK-005-T3-FT-001-W1` through `TASK-011-T3-FT-001-W3`; the latest refresh linked task records and packets to expanded SDD owners without creating new tasks.
- A later `/spec-improve FT-001` repair on 2026-06-26 closed concrete
  security primitive, cookie transport, and PlantPermissionContext ownership
  gaps in the linked feature specs.
- `/prd-to-tasks FT-001` then refreshed `TASK-006` through `TASK-011` and their
  packets against the repaired contracts without creating new tasks.
- Generated task-decomposition artifacts for FT-002 and FT-003 remain intentionally removed.
- Next EP-001 route is `/review-tasks-plan FT-001` before implementation.
