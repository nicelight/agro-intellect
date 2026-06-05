---
description: Implementation plan for FT-017 Local Privacy, Deployment Controls, And Secret Redaction.
status: active
---
# IMPL-FT-017 Local Privacy, Deployment Controls, And Secret Redaction

## Goals

- Keep MVP local/private by default with loopback exposure.
- Support optional LAN mode only when explicitly enabled and protected by auth/session,
  ActorContext authorization, token/session protection, and CORS/origin allowlist.
- Reject state-changing loopback/LAN browser writes unless same-origin, CSRF-equivalent,
  or stronger write protection passes.
- Preserve `sync.status=local_only`; forbid `server_verified`, upload, backup, and
  remote sync semantics.
- Redact secrets/auth material before logs, timeline, manifests, Bus, UI Feed,
  screenshots, exports, harness observations, and agent context.

## Constitution Check

- Aligns with local-first scope, secret redaction, bounded autonomy, and tiered DoD.
- No conflict found with the Constitution.
- Tier policy: redaction and LAN/deployment controls are T3; sync/storage semantics
  are T2.
- KISS boundary: no production SaaS, server sync, object storage, external account
  recovery, or connector marketplace.

## Source Artifacts

- .memory-bank/features/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
- .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
- .memory-bank/epics/EP-006-dataset-privacy-and-local-deployment.md
- .memory-bank/requirements.md

## Normative Inputs

- .memory-bank/invariants.md
- .memory-bank/architecture/system-architecture.md
- .memory-bank/contracts/api-guidelines.md
- .memory-bank/contracts/agent-harness.md
- .memory-bank/contracts/agent-chat-bus.md
- .memory-bank/contracts/message-envelope.md
- .memory-bank/domains/runtime-data-model.md
- .memory-bank/states/core-lifecycles.md
- .memory-bank/testing/index.md
- agents-best-practices: tool result redaction, context isolation, permission
  decisions, trace/eval observability, prompt-injection handling.

## Constraints

- Loopback is default.
- LAN mode fails closed when CORS/origin config is missing, malformed, or too broad.
- State-changing loopback/LAN browser requests cannot rely on CORS alone; they require
  same-origin, CSRF-equivalent, or stronger write protection.
- LAN mode cannot weaken ActorContext or PlantAccessGrant authorization.
- `sync.status` has only `local_only` in MVP.
- Redaction runs before forbidden-surface persistence or publication.
- Prompt-injection-like content remains data and cannot choose tools or override
  redaction/permission policy.

## Invariants

- NEVER log or export secrets, API keys, tokens, `.env` values, credentials, or auth
  material.
- NEVER use `server_verified` before a later server-sync spec exists.
- Tool/connector credentials never enter model context; tool results return bounded
  redacted summaries and refs.
- If redaction confidence is uncertain for a high-risk surface, reject or truncate
  rather than publish raw content.

## Steps

1. Implement shared secret redaction policy/utility and detector registry.
2. Apply redaction at logs, traces, export/context/publication boundaries.
3. Implement `SyncStatus.local_only` schema/config and block server-like fields/copy.
4. Implement loopback default and optional fail-closed LAN mode controls.
5. Add local storage prompt copy/sync guard for no-upload implication.
6. Add privacy/security regression suite across forbidden surfaces and prompt-injection
   attempts.

## Expected Touched Files

- backend/app/privacy/*
- backend/app/config/*
- backend/app/api/*
- backend/app/logging/*
- backend/app/harness/*
- backend/app/publication/*
- frontend/src/*
- backend/tests/privacy/*
- backend/tests/security/*
- frontend/tests/*
- .memory-bank/changelog.md

## Tests

- Unit: redaction detectors, sync status enum, CORS config validation.
- Integration: loopback default, LAN explicit enablement, auth/session required in LAN,
  ActorContext unchanged in LAN, cross-site simple request denial for state-changing
  loopback/LAN writes, forbidden surface redaction.
- Security/adversarial: secret-like user/provider/connector text cannot force
  disclosure or tool misuse; security traces visible to agents and capture metadata
  are covered as explicit forbidden surfaces.
- UI/e2e smoke when UI exists: local storage prompt and no-upload copy.

## Quality Gates

- pytest backend/tests/privacy backend/tests/security backend/tests/integration
- Frontend/UI smoke or e2e evidence under the task report when a frontend test runner exists; otherwise record the missing-runner reason in /verify
- node scripts/mb-lint.mjs
- node scripts/mb-doctor.mjs
- /verify and /red-verify for T2/T3 closure
- T3 human checkpoint and rollback/recovery note for redaction/LAN/security tasks

## UAT Steps

- App starts bound to loopback by default.
- LAN mode cannot start with missing/broad CORS config.
- LAN mode requires session and preserves authorization denials.
- Cross-site simple browser requests cannot mutate state through loopback/LAN endpoints.
- `sync.status` remains `local_only` and UI copy does not imply upload/server backup.
- Secret-like strings are redacted from all forbidden surfaces.

## Task Slice

- TASK-011: Secret redaction policy/utility foundation.
- TASK-012: Forbidden-surface redaction integrations.
- TASK-013: `local_only` sync status contract.
- TASK-014: Loopback default and fail-closed LAN controls.
- TASK-015: Local storage prompt no-upload/sync guard.
- TASK-016: Privacy/security regression suite.
