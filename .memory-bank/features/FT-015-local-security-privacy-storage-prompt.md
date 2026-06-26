---
description: FT-015 Local Security Privacy And Storage Prompt.
status: draft
type: feature
feature_id: FT-015
epic: EP-006
lifecycle: planned
last_updated: 2026-06-26
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
---
# FT-015 Local Security Privacy And Storage Prompt

## Use Cases

- App runs local-first and private by default.
- Default backend exposure is loopback.
- Optional LAN mode, if present, is explicitly enabled and protected.
- Local dataset/photo storage exceeds 200 MB and UI shows prompt without upload/server implication.
- Logs, exports, screenshots, Bus, UI Feed, manifests, and agent context redact auth material.

## Acceptance Criteria

- MVP sync status remains `local_only`.
- `server_verified` and server upload semantics are forbidden until later server-sync stage exists.
- LAN mode requires authentication, authorization, session/token protection, and CORS/origin controls.
- Local storage prompt appears at 200 MB and supports acknowledge/dismiss.
- Secrets, sessions, tokens, credentials, `.env` values, API keys, and auth material do not enter forbidden surfaces.

## Edge Cases & Failure Modes

- Storage prompt cannot imply upload, server availability, or sync status change.
- LAN mode cannot weaken local auth/authz.
- Secret redaction applies to errors, logs, audit/export, UI, and agent context.
- Local artifact privacy is default; upload/sync is not an MVP requirement.

## Verification Targets

- Unit: redaction helpers and storage threshold calculation after spec defines implementation.
- Integration: loopback default, LAN controls if implemented, `local_only` status.
- E2E: 200 MB prompt appears without upload/server wording.

## Normative Backbone Links

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): local privacy, deployment, and security constraints.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): loopback/LAN, CORS, authz, upload, and redacted errors.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): local artifact and sync-status authority.

## SDD Design Gate

Run global `/spec-design` before this feature is task-decomposed. Then run `/prd-to-tasks FT-015`; it must define exact local security controls, redaction rules, storage accounting, LAN mode, and tests during its feature-level SDD design phase before writing tasks. Use standalone `/spec-improve FT-015` only for repair or advanced refresh without task generation.
