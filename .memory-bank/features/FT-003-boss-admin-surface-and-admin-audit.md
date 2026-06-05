---
description: Feature FT-003 for Boss Admin Surface, personnel, role, Plant access management, and durable admin audit.
status: active
owner: product
lifecycle: planned
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-003-boss-admin-surface-and-admin-audit.md
epic: EP-001
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/analysis/accounts-farm-access-admin-analysis.md
  - .memory-bank/tech-specs/FT-003-boss-admin-surface-and-admin-audit.md
---
# FT-003 Boss Admin Surface And Admin Audit

## Use Cases

- Boss views personnel and adds a local Engineer Account.
- Boss assigns role preset and grants Plant access.
- Boss creates, archives, or restores a Plant.
- Boss reviews minimal admin audit for personnel, role, Plant lifecycle, and access changes.

## Acceptance Criteria

- Boss Admin Surface supports personnel list, local-only account add/invite, role assignment, Plant list, Plant archive/restore, Plant access management, durable admin audit records, and minimal admin audit view.
- Admin changes create durable AdminAuditRecord entries, not only UI rows.
- Local user add/invite does not require email delivery, hosted account recovery, enterprise identity, or SaaS tenancy.
- Admin authority does not bypass Safety Gate or physical-action approval rules.

## Edge Cases & Failure Modes

- Non-Boss users cannot perform admin mutations.
- Admin audit remains retained when a Plant is archived.
- Admin UI notices and markdown cannot become agent facts.
- Role/access changes are actor-attributed and redact secrets/session material.

## Test Strategy Pointers

- `test:admin.audit-and-access-management`
- `test:auth.actor-context-all-boundaries`
- `test:privacy.secret-redaction-surfaces`

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): Boss Admin Surface requirements.
- [.memory-bank/analysis/accounts-farm-access-admin-analysis.md](../analysis/accounts-farm-access-admin-analysis.md): source analysis for roles, permissions, and admin surface.
- [.memory-bank/user-scenarios.md](../user-scenarios.md): Boss setup scenario.

## SDD Design Gate

Global `/spec-design` and feature-level `/spec-improve FT-003` are complete. Use
[.memory-bank/tech-specs/FT-003-boss-admin-surface-and-admin-audit.md](../tech-specs/FT-003-boss-admin-surface-and-admin-audit.md)
as the feature-local design hub before `/prd-to-tasks FT-003`.
