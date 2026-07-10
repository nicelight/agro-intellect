---
description: FT-003 Boss Admin Surface And Admin Audit.
status: active
type: feature
feature_id: FT-003
epic: EP-001
lifecycle: implemented
last_updated: 2026-07-10
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/user-scenarios.md
spec_design_status: complete
spec_design_links:
  - .memory-bank/domains/identity/account-membership.md
  - .memory-bank/contracts/auth/session-security.md
  - .memory-bank/states/auth/session-lifecycle.md
  - .memory-bank/contracts/auth/session-http.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/domains/admin/admin-audit.md
  - .memory-bank/contracts/admin/boss-admin-http.md
  - .memory-bank/contracts/farm/plant-management-http.md
  - .memory-bank/runbooks/first-boss-local-bootstrap.md
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

## Current Implementation State

- TASK-016 and TASK-017 are recorded `done` by the scheduler with functional
  and semantic verification evidence for first-Boss bootstrap, admin service,
  Boss-only admin HTTP routes, safe responses, OpenAPI, and audit behavior.
- TASK-018 implementation evidence adds integrated FT-003 flow coverage:
  canonical Farm/`tomato_001` bootstrap, first Boss bootstrap, Boss login,
  Boss-created Engineer, Engineer login, Boss Plant access grant through the
  canonical Plant API, non-Boss denial, last-Boss protection, safe admin audit,
  password exclusion, and no-store response checks.
- Local gates for TASK-018 passed: focused FT-003 `18/18`, EP-001
  auth/admin/Farm regression `139/139`, and full regression `169/169`.
- FT-003 is synchronized as `implemented`, not `verified`; feature-level
  semantic review is recorded below, while lifecycle promotion remains a
  scheduler/owner decision.
- FT-003 does not claim FT-016 PWA/admin UI, Plant operations beyond the
  existing canonical Plant API, Safety Gate, agent runtime, dataset, or
  downstream feature completion.

## Semantic Verification

SEMANTIC_VERDICT: semantic-pass

- Feature-level semantic review report:
  [.tasks/FT-003/FT-003-S-RED-VERIFY-final-report-docs-01.md](../../.tasks/FT-003/FT-003-S-RED-VERIFY-final-report-docs-01.md).
- Final FT-003 task-plan review after execution:
  [.tasks/TASK-MB-REVIEW-TASKS-PLAN/TASK-MB-REVIEW-TASKS-PLAN-S-TASKS-FT-003-final-report-docs-02.md](../../.tasks/TASK-MB-REVIEW-TASKS-PLAN/TASK-MB-REVIEW-TASKS-PLAN-S-TASKS-FT-003-final-report-docs-02.md).
- Owner explicitly waived `mb-doctor` for this autopilot run; scheduler owns
  terminal state and lifecycle promotion decisions.

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
design are owned by the First Boss Local Bootstrap runbook.

Feature-level not-applicable rationale:

- No new event/message or agent-tool payload is introduced by FT-003.
- No new local artifact/filesystem storage is introduced by FT-003.
- No PWA component is implemented in this feature; role-aware UI composition
  remains with FT-016 and consumes the admin HTTP boundary.

## Behavior specs

- `.memory-bank/behavior-specs/FT-003-BHV-001-first-boss-bootstrap-one-shot.behavior.json`
- `.memory-bank/behavior-specs/FT-003-BHV-002-boss-creates-engineer-atomic-audit.behavior.json`
- `.memory-bank/behavior-specs/FT-003-BHV-003-admin-denial-last-boss-guard.behavior.json`

## Non-Goals

- Hosted identity, email delivery, password recovery, enterprise identity, or
  SaaS tenancy.
- Broad HR/personnel management.
- Complex audit search/export beyond the minimal admin audit view.
- A complete Consultant UI path in the first demo.
