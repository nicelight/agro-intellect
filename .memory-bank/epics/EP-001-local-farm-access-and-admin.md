---
description: Epic EP-001 for local Farm access, Accounts, ActorContext, Plant access, Boss Admin, and admin audit.
status: active
owner: product
lifecycle: planned
epic_id: EP-001
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/user-scenarios.md
  - .memory-bank/domains/core-domain.md
---
# EP-001 Local Farm Access And Admin

## Value

Give the MVP a real local workspace boundary: one Farm, local Accounts, role presets,
per-Plant access, and durable admin audit. This is the foundation that prevents Plant
operations, agent context, approvals, and audit from becoming single-user assumptions.

## Features

- FT-001 Local Accounts, Sessions, And ActorContext.
- FT-002 Farm, Plant Lifecycle, And PlantAccessGrant.
- FT-003 Boss Admin Surface And Admin Audit.

## Success Metrics

- Every Farm/Plant route and context-builder path can identify Account, Farm, role,
  Plant permissions, and session provenance.
- Boss can manage at least one Engineer Account and grant access to `tomato_001`.
- Engineer sees only assigned Plants and cannot approve physical actions without
  `plant_approve_actions`.
- Plant archive/restore retains authorized history, photos, tasks, outcomes, timeline,
  and admin audit.

## Acceptance Criteria

- One local Farm workspace is supported and multi-Farm tenancy is absent.
- Local Accounts and session attribution are sufficient for authorization and audit.
- Role presets are Boss, Engineer, and Consultant.
- PlantAccessGrant gates per-Plant visibility and work authorization.
- `plant_approve_actions` is the only MVP per-permission override.
- Boss Admin Surface creates durable admin audit records for account, role, Plant
  lifecycle, membership, and access changes.

## Constraints / Invariants

- Backend authorization is authority; frontend visibility is presentation only.
- Boss/admin authority cannot bypass Safety Gate or fresh-data requirements.
- Local-only invite/add means no email delivery, hosted recovery, enterprise identity,
  SaaS tenancy, or production account service.

## Verification Targets

- `test:auth.actor-context-all-boundaries`
- `test:auth.plant-access-grants`
- `test:admin.audit-and-access-management`
