---
description: EP-001 Local Farm Access And Admin.
status: draft
type: epic
epic_id: EP-001
lifecycle: planned
last_updated: 2026-07-10
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

- [FT-001 Local Accounts Sessions And ActorContext](../features/FT-001-local-accounts-sessions-actor-context.md): identity, session, and ActorContext boundary.
- [FT-002 Farm Plant Lifecycle And Access Grants](../features/FT-002-farm-plant-lifecycle-access-grants.md): Farm, Plant lifecycle, and access-grant boundary.
- [FT-003 Boss Admin Surface And Admin Audit](../features/FT-003-boss-admin-surface-admin-audit.md): Boss administration and audit boundary.

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

## Current Implementation State

- FT-001 tasks TASK-005 through TASK-011 are recorded `done`; independent
  verification and repeated feature-level adversarial review pass.
- FT-001 is synchronized as `verified` with the local PostgreSQL/`psql`
  environment gap and accepted missing hostile-provider regression recorded as
  residual risks.
- FT-002 tasks TASK-012 through TASK-015 are recorded `done`; TASK-015
  execution, independent verification, and per-task semantic verification pass
  with focused FT-002 `43/43` and full regression `151/151`. Feature-level
  `/red-verify --feature FT-002` returned `semantic-pass`, so FT-002 is
  synchronized as `verified`.
- FT-003 implementation evidence is now present for the backend Boss
  administration/audit boundary: first-Boss bootstrap, Boss login,
  Boss-created Engineer, Engineer login, canonical Plant API access grant,
  non-Boss denial, last-Boss guard, safe audit, password exclusion, and
  no-store response behavior. TASK-018 local gates passed focused FT-003
  `18/18`, EP-001 auth/admin/Farm regression `139/139`, and full regression
  `169/169`.
- EP-001 lifecycle remains `planned` until FT-003 independent verification,
  semantic review/owner closure, and feature-boundary synchronization are
  accepted. FT-003 does not claim FT-016 PWA/admin UI or downstream Plant
  operations, Safety Gate, agent, dataset, or first-demo completion.
