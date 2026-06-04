---
description: Feature FT-001 for local Accounts, sessions, FarmMembership, role presets, and ActorContext.
status: draft
lifecycle: planned
spec_design_status: needs_spec_improve
epic: EP-001
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/domains/core-domain.md
---
# FT-001 Local Accounts, Sessions, And ActorContext

## Use Cases

- Boss opens the local app as the first local Account and Farm admin.
- Engineer logs in or opens a local authorized session and receives an ActorContext.
- Consultant receives only advisory/read/comment context for granted Plants.

## Acceptance Criteria

- Local Accounts exist for login/session, authorization, attribution, and audit.
- FarmMembership binds Account to the single MVP Farm with Boss/Engineer/Consultant role preset.
- ActorContext is resolved for every Farm/Plant read, mutation, context-builder path, task, approval, and audit record.
- Session/auth provenance is available for audit without leaking auth material into forbidden surfaces.
- Frontend visibility is not treated as authorization.

## Edge Cases & Failure Modes

- Missing or invalid session fails closed.
- Disabled/removed membership cannot access Farm/Plant data.
- Role mismatch cannot be hidden by UI state.
- Session/token values are redacted from logs, timeline, manifests, Bus, UI Feed, screenshots, exports, and agent context.

## Test Strategy Pointers

- `test:auth.local-session-attribution`
- `test:auth.actor-context-all-boundaries`
- `test:privacy.secret-redaction-surfaces`

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): Local Accounts, role presets, and ActorContext requirements.
- [.memory-bank/domains/core-domain.md](../domains/core-domain.md): Account, FarmMembership, ActorContext entities and rules.
- [.memory-bank/user-scenarios.md](../user-scenarios.md): Boss setup and Engineer operations scenarios.

## SDD Design Gate

Global `/spec-design` is complete. Before `/prd-to-tasks FT-001`, run
`/spec-improve FT-001` using the completed backbone docs: [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md), [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md), [.memory-bank/states/core-lifecycles.md](../states/core-lifecycles.md), [.memory-bank/contracts/index.md](../contracts/index.md), and [.memory-bank/testing/index.md](../testing/index.md). `/spec-improve` must decide exact auth/session lifecycle,
ActorContext shape, route enforcement pattern, audit attribution, and redaction checks.
