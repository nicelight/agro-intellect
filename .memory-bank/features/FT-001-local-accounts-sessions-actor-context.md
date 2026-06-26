---
description: FT-001 Local Accounts Sessions And ActorContext.
status: draft
type: feature
feature_id: FT-001
epic: EP-001
lifecycle: planned
last_updated: 2026-06-26
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md
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
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): Account, FarmMembership, ActorContext, and authority layers.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): ActorContext and backend authorization requirements.

## SDD Design Gate

Status: feature-local `/spec-improve FT-001` is complete.

Use [.memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md](../tech-specs/FT-001-local-accounts-sessions-actor-context.md) as the current normative feature design for exact auth/session lifecycle, ActorContext shape, permission checks, route contracts, error handling, migration/indexing targets, and verification targets.

## Task Decomposition

Status: `/prd-to-tasks FT-001` completed on 2026-06-25 and refreshed on
2026-06-26 against the brownfield global SDD backbone.

- Implementation plan: [.memory-bank/tasks/plans/IMPL-FT-001.md](../tasks/plans/IMPL-FT-001.md).
- Active task records: `TASK-005-T3-FT-001-W1` through `TASK-011-T3-FT-001-W3`.
- Required packets: `.memory-bank/packets/TASK-005-T3-FT-001-W1.packet.json` through `.memory-bank/packets/TASK-011-T3-FT-001-W3.packet.json`.
- Refresh result: no new feature-local or global spec was required; task records
  and packets are the current planning surface for review.
- Next gate: `/review-tasks-plan FT-001` before any FT-001 implementation.
