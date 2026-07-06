---
description: FT-003 Boss Admin Surface And Admin Audit.
status: draft
type: feature
feature_id: FT-003
epic: EP-001
lifecycle: planned
last_updated: 2026-07-06
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/user-scenarios.md
spec_design_links:
  - .memory-bank/domains/identity/account-membership.md
  - .memory-bank/contracts/auth/session-security.md
  - .memory-bank/states/auth/session-lifecycle.md
  - .memory-bank/contracts/auth/session-http.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/domains/admin/admin-audit.md
  - .memory-bank/contracts/admin/boss-admin-http.md
  - .memory-bank/testing/admin/boss-admin-and-audit.md
---
# FT-003 Boss Admin Surface And Admin Audit

## Use Cases

- Boss manages a personnel list.
- Boss directly creates a local active Account with login, initial password,
  and role.
- Boss assigns role presets.
- Boss manages Plant list, archive/restore, and Plant access; Plant creation is
  also available to active Engineers through FT-002 and is not an admin grant.
- Boss views minimal durable admin audit records.

## Acceptance Criteria

- Boss Admin Surface supports personnel, direct Account creation, role
  assignment, Plant list, Plant archive/restore, access grants, and admin audit
  view.
- Account, active FarmMembership, and exactly one safe `account_created` audit
  record are committed atomically; password material is never returned or
  audited.
- Account, role, Plant lifecycle, membership, and access changes create durable AdminAuditRecord entries.
- Admin audit is retained and visible only to authorized roles.
- Minimal first-demo admin surface may be smaller than full MVP admin capability, but must support Boss plus at least one Engineer path.

## Edge Cases & Failure Modes

- Non-Boss actors cannot access admin mutations. The FT-002 Engineer Plant-
  creation command is a Farm-scoped Plant mutation, not an admin mutation, and
  grants no access to this surface.
- Admin UI notices do not become agent facts.
- Admin changes cannot bypass backend authorization.
- Direct local creation does not imply SaaS tenancy, email delivery, password
  recovery, hosted account recovery, or enterprise identity.

## Verification Targets

- Unit: admin permission checks.
- Integration: every admin mutation creates durable audit.
- E2E: Boss creates Engineer, assigns role, grants Plant access, and audit entry appears.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Access & Admin bounded context.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): AdminAuditRecord authority.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): admin route grouping, errors, and authorization.

## Specification Composition

- Existing identity/session/ActorContext specs define login and authorization.
- [Admin audit](../domains/admin/admin-audit.md) defines durable transaction
  evidence; [Boss admin HTTP](../contracts/admin/boss-admin-http.md) defines
  personnel/admin routes.
- [Boss admin verification](../testing/admin/boss-admin-and-audit.md) defines
  policy, security, audit, isolation, and E2E evidence.

UI composition and product use cases remain here; concrete contracts remain in
the linked subject specs. Exact first-Boss one-shot CLI and implementation
design are outside this composition.

## Non-Goals

- Hosted identity, email delivery, password recovery, enterprise identity, or
  SaaS tenancy.
- Broad HR/personnel management.
- Complex audit search/export beyond the minimal admin audit view.
- A complete Consultant UI path in the first demo.
