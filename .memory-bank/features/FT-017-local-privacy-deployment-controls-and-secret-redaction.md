---
description: Feature FT-017 for local-first privacy, loopback/LAN controls, local_only sync, and secret redaction.
status: active
owner: product
lifecycle: planned
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
epic: EP-006
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
---
# FT-017 Local Privacy, Deployment Controls, And Secret Redaction

## Use Cases

- MVP runs private/local by default on loopback.
- User explicitly enables LAN mode only with authentication, authorization, session/token protection, and CORS/origin controls.
- Logs, exports, screenshots, agent context, Bus, UI Feed, timeline, and manifests redact secrets and auth material.

## Acceptance Criteria

- MVP remains local-first and private by default.
- Default exposure boundary is loopback.
- LAN mode may exist only when explicitly enabled and protected by auth/session, authorization, token/session protection, and CORS/origin controls.
- `sync.status` remains `local_only`; `server_verified` and server upload semantics are forbidden until a later server-sync stage exists.
- Sessions, tokens, credentials, `.env` values, API keys, and auth material never enter logs, timeline, manifests, Bus, UI Feed, screenshots, exports, or agent context.

## Edge Cases & Failure Modes

- LAN mode cannot weaken local authorization.
- CORS/origin misconfiguration fails closed.
- Secret-like values in user input, logs, or connector output are redacted before export/context.
- Local privacy prompt cannot imply cloud sync or server availability.

## Test Strategy Pointers

- `test:privacy.local-only-loopback-lan-controls`
- `test:privacy.secret-redaction-surfaces`
- `test:storage.200mb-local-prompt-no-upload`

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): local-first, loopback/LAN, local_only, and secret redaction requirements.
- [.memory-bank/invariants.md](../invariants.md): local/private and secret NEVER rules.
- [.memory-bank/testing/index.md](../testing/index.md): testing risk surfaces for local auth/security.

## SDD Design Gate

Global `/spec-design` and feature-level `/spec-improve FT-017` are complete. Use
[.memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md](../tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md)
as the feature-local design hub before `/prd-to-tasks FT-017`. This Wave 1 pass is the
authoritative FT-017 `/spec-improve` result if a later wave list repeats FT-017.
