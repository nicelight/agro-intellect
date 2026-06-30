---
description: FT-010 - Local security, privacy, and lazy sync.
status: draft
lifecycle: planned
parent_epic: EP-004
spec_design_status: complete
spec_design_links:
  - .memory-bank/tech-specs/FT-010-local-security-privacy-lazy-sync.md
---
# FT-010 Local Security, Privacy, and Lazy Sync

## Parent Epic

- [EP-004 Local Operations and Operator UI](../epics/EP-004-local-operations-operator-ui.md): local operations and first operator UI.

## Purpose

Define the MVP local operations baseline that keeps the app private by default, validates uploads safely, redacts secrets, supports protected LAN mode only by explicit choice, and uses only `local_only` sync until a later server sync stage exists.

## Source Artifacts

- [.memory-bank/prd.md](../prd.md): FR-017, local security/privacy non-functional requirements, secrets baseline, privacy baseline, edge cases, and verification strategy.
- [.memory-bank/requirements.md](../requirements.md): REQ-012.
- [.memory-bank/constitution.md](../constitution.md): low-maintenance, local-first, KISS, and no-speculation constraints.
- [.memory-bank/spec-index.md](../spec-index.md): route map for local security runbook and lazy sync workflow.
- [.memory-bank/testing/index.md](../testing/index.md): local security and lazy sync risk-surface gates.

## Use Cases

- The user runs the app locally with backend binding to loopback.
- The user explicitly enables protected LAN access when needed.
- The user uploads plant photos and unsafe upload inputs are rejected.
- The system redacts secrets from logs, exports, manifests, UI, Bus, and screenshots.
- The system keeps plant photos and manifests private unless the user explicitly approves upload or sync.
- The UI warns when local dataset storage exceeds 200 MB without changing sync status.

## Acceptance Criteria

- Backend binds to loopback by default.
- LAN mode requires explicit enablement and authentication/token protection.
- API CORS uses an allowlist.
- Uploads validate size, MIME/content type, safe path handling, and path traversal rejection.
- Secrets are redacted from logs, `timeline.jsonl`, photo manifests, UI Feed, Agent Chat Bus, screenshots, and export candidates.
- Local plant photos and manifests are private project data by default.
- Upload or sync requires explicit user approval.
- MVP sync status supports `local_only`.
- The 200 MB prompt can only show local storage pressure and acknowledge/dismiss behavior.
- Server/upload sync is TODO for a later version and is unavailable in the MVP.
- The 200 MB prompt does not imply that a server/upload target exists and does not mutate `sync.status`.
- `server_verified` is unavailable until a real server sync stage exists.

## Edge Cases / Failure Modes

- Backend attempts to bind broadly by default: block or fail configuration validation.
- LAN mode is enabled without auth/token protection: block startup or fail configuration validation.
- CORS wildcard is used for API access: fail security validation unless future design explicitly permits a constrained case.
- Upload has unsupported MIME/content type, unsafe size, missing file, unsafe path, or path traversal sequence: reject.
- Secret-like value appears in logs, manifests, timeline, UI Feed, Bus, screenshots, or export candidates: redact and fail the unsafe operation where applicable.
- User has not approved upload/sync: keep artifacts local.
- Local storage exceeds 200 MB: show local storage prompt only and keep `sync.status=local_only`.
- A `server_verified` status appears before server sync exists: reject.

## Test Strategy Pointers

- `security:local-backend-baseline` for loopback default and explicit protected LAN mode.
- `security:cors-allowlist` for CORS allowlist behavior.
- `security:upload-validation` for size, MIME/content type, safe path, and path traversal rejection.
- `security:secret-redaction` for logs, timeline, manifests, UI Feed, Bus, screenshots, and export candidates.
- `policy:private-artifacts-default` for photos/manifests staying local without explicit user approval.
- `policy:lazy-sync-local-only` for `local_only` as the only MVP sync status.
- `policy:lazy-sync-200mb-prompt` for prompt-only behavior with no server implication and no sync status mutation.

## Constraints / Invariants

- The MVP is local-first and private by default.
- Server sync lifecycle is deferred.
- `server_verified` is forbidden before server sync exists.
- The 200 MB prompt is presentation behavior, not sync authority.
- Keep security baseline simple and testable.

## SDD Design Gate

Global `/spec-design` completed the shared backbone. `/spec-improve FT-010` completed the feature-local SDD gate.

- [.memory-bank/runbooks/local-security.md](../runbooks/local-security.md): loopback default, protected LAN mode, upload validation, secret redaction, privacy, and lazy-sync rules.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): HTTP API security and upload boundary.
- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): sync and artifact authority.
- [.memory-bank/invariants.md](../invariants.md): cross-cutting privacy, secret, and sync prohibitions.
- [.memory-bank/testing/first-demo.md](../testing/first-demo.md): local security and lazy-sync gates.
- [.memory-bank/tech-specs/FT-010-local-security-privacy-lazy-sync.md](../tech-specs/FT-010-local-security-privacy-lazy-sync.md): feature-local decisions for LAN bearer-token auth, CORS allowlist, upload limits/MIME allowlist, redaction boundary, privacy, API support, lazy-sync state, and verification targets.

No FT-010 design blocker remains for `/prd-to-tasks FT-010`.
