---
description: FT-003 Boss Admin Surface And Admin Audit.
status: draft
type: feature
feature_id: FT-003
epic: EP-001
lifecycle: planned
last_updated: 2026-06-16
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/user-scenarios.md
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md
---
# FT-003 Boss Admin Surface And Admin Audit

## Use Cases

- Boss manages a personnel list.
- Boss adds or invites a local-only Account without email delivery or hosted recovery.
- Boss assigns role presets.
- Boss manages Plant list, archive/restore, and Plant access.
- Boss views minimal durable admin audit records.

## Acceptance Criteria

- Boss Admin Surface supports personnel, local-only add/invite, role assignment, Plant list, Plant lifecycle, access grants, and admin audit view.
- Account, role, Plant lifecycle, membership, and access changes create durable AdminAuditRecord entries.
- Admin audit is retained and visible only to authorized roles.
- Minimal first-demo admin surface may be smaller than full MVP admin capability, but must support Boss plus at least one Engineer path.

## Edge Cases & Failure Modes

- Non-Boss actors cannot access admin mutations.
- Admin UI notices do not become agent facts.
- Admin changes cannot bypass backend authorization.
- Local add/invite does not imply SaaS tenancy, email delivery, password recovery, hosted account recovery, or enterprise identity.

## Verification Targets

- Unit: admin permission checks.
- Integration: every admin mutation creates durable audit.
- E2E: Boss creates Engineer, assigns role, grants Plant access, and audit entry appears.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Access & Admin bounded context.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): AdminAuditRecord authority.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): admin route grouping, errors, and authorization.

## SDD Design Gate

Feature-local `/spec-improve FT-003` and `/prd-to-tasks FT-003` are complete. Use [.memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md](../tech-specs/FT-003-boss-admin-surface-admin-audit.md) and [.memory-bank/tasks/plans/IMPL-FT-003.md](../tasks/plans/IMPL-FT-003.md) for admin routes/services, audit record shape, local invite semantics, authorization checks, TASK-011..TASK-015, and verification targets before execution.
