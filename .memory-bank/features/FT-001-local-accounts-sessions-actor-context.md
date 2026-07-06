---
description: FT-001 Local Accounts Sessions And ActorContext.
status: active
type: feature
feature_id: FT-001
epic: EP-001
lifecycle: verified
last_updated: 2026-07-06
spec_design_status: complete
spec_design_links:
  - .memory-bank/domains/identity/account-membership.md
  - .memory-bank/domains/auth/session-storage.md
  - .memory-bank/contracts/auth/session-security.md
  - .memory-bank/states/auth/session-lifecycle.md
  - .memory-bank/contracts/auth/session-http.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/testing/auth/session-and-access.md
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/domains/core-domain.md
---
# FT-001 Local Accounts Sessions And ActorContext

## Use Cases

- Boss opens the local app as the first local Account and Farm admin.
- Engineer logs in or opens an authorized local session.
- Consultant, when present, receives only granted advisory/read/comment context.
- Backend resolves Account, Farm, FarmMembership, role preset, Plant permissions, and session/auth provenance before any Farm/Plant operation or agent context build.

## Acceptance Criteria

- Local Accounts exist for login/session, authorization, attribution, and audit.
- ActorContext is required for Farm/Plant reads, mutations, context builders, tasks, approvals, and audit records.
- Boss, Engineer, and Consultant role presets are represented.
- Backend authorization is authoritative; frontend visibility alone is never sufficient.

## Edge Cases & Failure Modes

- Missing or invalid session fails closed.
- Missing FarmMembership fails closed.
- Missing PlantAccessGrant prevents Plant visibility and Plant context access.
- Consultant cannot create domain task/recommendation records or approve physical actions.
- Secrets, tokens, credentials, and auth material are redacted from all audit/export/feed/agent surfaces.

## Verification Targets

- Unit: role preset and permission derivation.
- Integration: ActorContext present on every protected route/context builder.
- Deferred cross-feature E2E after FT-002/FT-003 tasking: Engineer sees only
  assigned Plants; Consultant stays advisory/read/comment only; direct Account
  creation permits login only for the intended identity/Farm scope.

## Behavior specs

- `.memory-bank/behavior-specs/FT-001-BHV-001-login-success.behavior.json`
- `.memory-bank/behavior-specs/FT-001-BHV-002-login-no-leak-failure.behavior.json`
- `.memory-bank/behavior-specs/FT-001-BHV-003-actor-context-permission-filtering.behavior.json`

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): source-of-truth hierarchy, modules, security, deployment.
- [.memory-bank/architecture/foundation-runtime-substrate.md](../architecture/foundation-runtime-substrate.md): app factory and route-mounting substrate FT-001 must preserve.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): shared native-UUID identity, non-cascading authority relations, and authority layers.
- [.memory-bank/domains/foundation-data-substrate.md](../domains/foundation-data-substrate.md): DB/session/Alembic substrate for FT-001 tables and migrations.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): ActorContext and backend authorization requirements.
- [.memory-bank/contracts/evidence-redaction.md](../contracts/evidence-redaction.md): redaction rules for auth/session evidence and reports.
- [.memory-bank/testing/strategy.md](../testing/strategy.md): risk-based verification policy for auth/session/ActorContext work.
- [.memory-bank/domains/identity/account-membership.md](../domains/identity/account-membership.md): Account/FarmMembership storage.
- [.memory-bank/domains/auth/session-storage.md](../domains/auth/session-storage.md): LocalSession storage.
- [.memory-bank/contracts/auth/session-security.md](../contracts/auth/session-security.md): credential/token/transport security.
- [.memory-bank/states/auth/session-lifecycle.md](../states/auth/session-lifecycle.md): login, expiry, disable, and revocation.
- [.memory-bank/contracts/auth/session-http.md](../contracts/auth/session-http.md): login/logout/me.
- [.memory-bank/contracts/access/actor-context.md](../contracts/access/actor-context.md): ActorContext and Plant permission resolution.
- [.memory-bank/testing/auth/session-and-access.md](../testing/auth/session-and-access.md): cross-contract evidence.

## Specification Composition

Status: complete.

- [Account and membership storage](../domains/identity/account-membership.md)
  defines identity persistence and deferred Farm relation.
- [Session storage](../domains/auth/session-storage.md), [session security](../contracts/auth/session-security.md),
  and [session lifecycle](../states/auth/session-lifecycle.md) define the local
  credential/session boundary.
- [Session HTTP](../contracts/auth/session-http.md) defines login/logout/me.
- [ActorContext](../contracts/access/actor-context.md) defines roles and Plant
  authorization context.
- [Session and access verification](../testing/auth/session-and-access.md)
  defines cross-contract evidence.

The feature composes these canonical specs and does not own or duplicate their
fields, schemas, errors, transitions, or verification rules.

## Non-Goals

- Enterprise identity, OAuth, password recovery, email delivery, SaaS
  tenancy, and multi-Farm membership.
- A general ACL/permission override engine beyond `plant_approve_actions`.
- Refresh tokens, device management, hosted account recovery, audit-export UI,
  and broad personnel management.

## Current Implementation Evidence

- `TASK-005` through `TASK-011` are recorded `done` with task-scoped evidence
  for persistence, security primitives, session lifecycle, ActorContext,
  session HTTP, and protected route/context-builder authorization seams.
- `TASK-011-T3-FT-001-W3` integration execution confirms the complete runnable
  non-environment suite: focused FT-001 tests `77 passed` with one PostgreSQL
  check deselected, and the full suite `105 passed` with three local
  PostgreSQL/`psql` checks deselected.
- The unavailable local PostgreSQL/`psql` checks remain an environment gap;
  earlier task-scoped PostgreSQL evidence is retained and this integration run
  does not represent those checks as newly executed.
- Feature document status and lifecycle are synchronized as `active` /
  `verified` after all FT-001 tasks closed and feature-level red-verification
  returned `semantic-pass`. FT-002 and FT-003 remain separate scope.

## Semantic Verification

SEMANTIC_VERDICT: semantic-pass

Repeated feature-level adversarial review confirms both prior concerns are
repaired: provider internals are excluded from `repr(ActorContext)`, and the
standard app composition returns stable protected-route auth errors. Direct
hostile probes pass and the complete non-environment suite passes `105/105`.
The owner explicitly accepts the absence of a dedicated hostile-provider
regression test. This `/mb-sync` records the owner-controlled FT-001 lifecycle
as `verified` without claiming FT-002/FT-003 completion.

Report:
[.tasks/FT-001/FT-001-S-RED-VERIFY-final-report-docs-01.md](../../.tasks/FT-001/FT-001-S-RED-VERIFY-final-report-docs-01.md).

## Implementation

- [Implementation plan](../tasks/plans/IMPL-FT-001.md): task composition,
  dependencies, verification strategy, and UAT.
