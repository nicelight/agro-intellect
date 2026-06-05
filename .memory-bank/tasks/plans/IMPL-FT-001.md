---
description: Implementation plan for FT-001 Local Accounts, Sessions, And ActorContext.
status: active
---
# IMPL-FT-001 Local Accounts, Sessions, And ActorContext

## Goals

- Implement local Account, FarmMembership, session baseline, role presets, and
  ActorContext resolution.
- Ensure every protected Farm/Plant route and context-builder path resolves
  ActorContext before read or mutation.
- Preserve audit attribution with redacted session/auth provenance only.

## Constitution Check

- Aligns with AI-first Spec-Driven Development, Schema-Backed Task Execution, and
  Risk-Based Definition of Done.
- No conflict found with the Constitution.
- Tier policy: all slices are T3 because they affect auth, sessions, authorization,
  audit attribution, and secret/auth material redaction.
- KISS boundary: local-only identity/session baseline; no hosted identity, SaaS
  tenancy, OAuth/SAML, billing, email delivery, or hosted recovery.

## Source Artifacts

- .memory-bank/features/FT-001-local-accounts-sessions-and-actor-context.md
- .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
- .memory-bank/epics/EP-001-local-farm-access-and-admin.md
- .memory-bank/requirements.md

## Normative Inputs

- .memory-bank/architecture/system-architecture.md
- .memory-bank/domains/runtime-data-model.md
- .memory-bank/states/core-lifecycles.md
- .memory-bank/contracts/api-guidelines.md
- .memory-bank/contracts/agent-harness.md
- .memory-bank/testing/index.md
- agents-best-practices: tools/permissions, context isolation, traces/evals, secret
  handling.

## Constraints

- Backend authorization is authority; frontend visibility is presentation only.
- Missing/invalid/expired/revoked sessions fail closed.
- Disabled Accounts and disabled/removed FarmMembership cannot access Farm/Plant data
  or context-builder paths.
- Raw session IDs, tokens, passwords, credentials, API keys, `.env` values, and auth
  material cannot enter forbidden surfaces.

## Invariants

- ActorContext is required for every Farm/Plant read, mutation, context-builder path,
  task, approval, and audit route.
- FarmMembership role presets are Boss, Engineer, and Consultant.
- `plant_approve_actions` remains the only MVP per-permission override and is not
  implemented as a broad permission system.
- The model never decides access; backend/harness permission logic does.

## Steps

1. Build Account/FarmMembership/session persistence and one-Farm bootstrap support.
2. Implement ActorContext resolver and protected API dependency/middleware.
3. Implement role preset authorization policy and redacted audit attribution.
4. Add context-builder permission boundary hooks/tests.
5. Add auth/session API smoke, generated OpenAPI validation once schemas exist, and
   redaction regression coverage.

## Expected Touched Files

- backend/app/access/*
- backend/app/db/migrations/*
- backend/app/api/*
- backend/app/context/*
- backend/app/audit/*
- backend/tests/access/*
- backend/tests/integration/*
- .memory-bank/changelog.md

## Tests

- Unit: session state, membership state, role preset matrix, redaction helpers.
- Integration: protected route denial, ActorContext propagation, context-builder
  rejection, audit attribution.
- Contract: generated OpenAPI after schemas exist.
- Security regression: no raw auth material in logs, timeline, Bus, UI Feed, traces,
  screenshots, exports, manifests, or agent context.

## Quality Gates

- pytest backend/tests/access backend/tests/integration
- generated OpenAPI validation after implementation schemas exist
- node scripts/mb-lint.mjs
- node scripts/mb-doctor.mjs
- /verify and /red-verify before T3 closure
- T3 human checkpoint and rollback/recovery note before closure

## UAT Steps

- Boss creates or opens local Farm session and sees resolved ActorContext.
- Engineer logs in and receives only role/grant-scoped context.
- Missing/invalid/expired session fails closed.
- Disabled membership immediately loses access.
- Auth/session values do not appear in user-visible or agent-visible surfaces.

## Task Slice

- TASK-001: Account, FarmMembership, and session data foundation.
- TASK-002: ActorContext resolver and API boundary.
- TASK-003: Role preset authorization and redacted audit attribution.
- TASK-004: Context-builder ActorContext enforcement.
- TASK-005: Auth/session API and redaction regression coverage.
