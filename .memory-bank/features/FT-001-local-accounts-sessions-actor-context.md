---
description: FT-001 Local Accounts Sessions And ActorContext.
status: draft
type: feature
feature_id: FT-001
epic: EP-001
lifecycle: planned
last_updated: 2026-06-29
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md
  - .memory-bank/domains/local-identity-session-data.md
  - .memory-bank/contracts/local-session-security.md
  - .memory-bank/contracts/local-session-api.md
  - .memory-bank/contracts/actor-context.md
  - .memory-bank/testing/ft-001-access-auth.md
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
- E2E: Engineer sees only assigned Plants; Consultant stays advisory/read/comment only.

## Behavior specs

- `.memory-bank/behavior-specs/FT-001-BHV-001-login-success.behavior.json`
- `.memory-bank/behavior-specs/FT-001-BHV-002-login-no-leak-failure.behavior.json`
- `.memory-bank/behavior-specs/FT-001-BHV-003-actor-context-permission-filtering.behavior.json`

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): source-of-truth hierarchy, modules, security, deployment.
- [.memory-bank/architecture/foundation-runtime-substrate.md](../architecture/foundation-runtime-substrate.md): app factory and route-mounting substrate FT-001 must preserve.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): shared native-UUID identity, non-cascading authority relations, Account/FarmMembership/ActorContext ownership, and authority layers.
- [.memory-bank/domains/foundation-data-substrate.md](../domains/foundation-data-substrate.md): DB/session/Alembic substrate for FT-001 tables and migrations.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): ActorContext and backend authorization requirements.
- [.memory-bank/contracts/evidence-redaction.md](../contracts/evidence-redaction.md): redaction rules for auth/session evidence and reports.
- [.memory-bank/testing/index.md](../testing/index.md): risk-based verification surfaces for auth/session/ActorContext work.
- [.memory-bank/domains/local-identity-session-data.md](../domains/local-identity-session-data.md): exact Account/FarmMembership/LocalSession storage contract.
- [.memory-bank/contracts/local-session-security.md](../contracts/local-session-security.md): credential, token, lifecycle, cookie, and bearer security contract.
- [.memory-bank/contracts/local-session-api.md](../contracts/local-session-api.md): login/logout/me, activation handoff, and auth error contract.
- [.memory-bank/contracts/actor-context.md](../contracts/actor-context.md): role, ActorContext, PlantPermissionContext interface, and context-builder contract.
- [.memory-bank/testing/ft-001-access-auth.md](../testing/ft-001-access-auth.md): feature verification matrix and quality gates.

## SDD Design Gate

Status: complete.

Use [.memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md](../tech-specs/FT-001-local-accounts-sessions-actor-context.md) as the stable feature hub. Its Specification Map routes exact data, security, HTTP API, ActorContext, and verification decisions to the atomic `spec_design_links` above.

The 2026-06-26 `/prd-to-tasks FT-001` protocol refresh found no shared/global
blocker and no duplicate authoritative owner. No new task records were created.

The 2026-06-26 standalone `/spec-improve FT-001` repair closed concrete
security primitive, session cookie transport, and PlantPermissionContext
ownership gaps while keeping the feature design status `complete`.

The 2026-06-27 KISS `/spec-improve FT-001` repair added only the
security-derived `password_hash`/`token_hash` storage contract required before
`TASK-005`, including disabled-before-activation nullability. No broader DB,
API DTO, event, or callable-interface design was added.

The 2026-06-28 `/spec-improve FT-001` repair completes TASK-005 relational
readiness: UUID identity, deferred Farm FK ownership, exact nullability,
string-domain checks, login normalization/uniqueness, non-cascading FKs, and
exact indexes. Shared identity lives in Runtime Data Model; exact FT-001 tables
live in Local Identity And Session Data; FT-002 owns final Farm FK closure.

The 2026-06-29 structural repair split the 735-line feature hub into atomic
data, security, HTTP API, ActorContext, and verification owners. It changed no
behavioral contract; the original hub path remains a compatibility facade.

## Task Decomposition

Status: `/prd-to-tasks FT-001` completed on 2026-06-25 and refreshed on
2026-06-26 against the brownfield global SDD backbone and the expanded
`/prd-to-tasks` concrete contract readiness protocol, then refreshed again after
the standalone `/spec-improve FT-001` repair. A targeted 2026-06-27 refresh
updated only `TASK-005` and its required packet for the KISS storage contract.

- Implementation plan: [.memory-bank/tasks/plans/IMPL-FT-001.md](../tasks/plans/IMPL-FT-001.md).
- Active task records: `TASK-005-T3-FT-001-W1` through `TASK-011-T3-FT-001-W3`.
- Required packets: `.memory-bank/packets/TASK-005-T3-FT-001-W1.packet.json` through `.memory-bank/packets/TASK-011-T3-FT-001-W3.packet.json`.
- Previous refresh result: no new task was created; `TASK-006` through `TASK-011`, the
  implementation plan, and required packets were refreshed against the concrete
  security primitive, cookie/session transport, and PlantPermissionContext
  ownership contracts. `TASK-005` remains unchanged because no schema-level
  storage constraints changed.
- 2026-06-27 refresh result: only `TASK-005-T3-FT-001-W1`, its canonical packet,
  and feature-level routing docs/protocol were updated for nullable unbounded
  `password_hash`, active-account credential enforcement, the single unique
  64-character `token_hash` lookup index, and PostgreSQL migration smoke.
  `TASK-006` through `TASK-011` and their packets were not changed.
- Current refresh result: the targeted 2026-06-28 `/prd-to-tasks FT-001` pass
  updated only `TASK-005`, its canonical packet, and feature-level handoff docs
  for native UUID identity, exact nullability/checks/login normalization,
  non-cascading Account FKs, the deferred Farm FK boundary, and exact indexes.
  `TASK-006` through `TASK-011` and their packets were not changed.
- Next gate: `/review-tasks-plan FT-001`, then conditional `/mb-doctor` before
  `TASK-005` execution.
