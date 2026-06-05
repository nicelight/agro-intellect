---
description: Feature FT-001 for local Accounts, sessions, FarmMembership, role presets, and ActorContext.
status: active
owner: product
lifecycle: planned
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
epic: EP-001
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/domains/core-domain.md
  - .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
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

Global `/spec-design` and feature-level `/spec-improve FT-001` are complete. Use
[.memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md](../tech-specs/FT-001-local-accounts-sessions-and-actor-context.md)
as the feature-local design hub before `/prd-to-tasks FT-001`.
