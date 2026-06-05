---
description: Frontend/backend API contract guidelines for MVP v2.
status: active
owner: architecture
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/invariants.md
---
# API Guidelines

## Scope

This spec defines global API rules for the Web App/PWA to FastAPI backend boundary. It
does not define every endpoint. Feature-level endpoint lists and schemas belong to
`/spec-improve FT-<NNN>`.

## API Style

- Use FastAPI with Pydantic/schema validation.
- Prefer resource-oriented JSON APIs with explicit command endpoints when a mutation
  represents a workflow decision.
- Generated OpenAPI from backend schemas is the frontend/backend HTTP contract once
  implementation exists.
- Do not hand-write a large `openapi.yaml` before feature-level design and backend
  schema work.

## ActorContext And Authorization

- Every Farm/Plant read, mutation, context-builder path, task, approval, and audit
  route must resolve `ActorContext`.
- Backend authorization is mandatory. Frontend visibility is presentation only.
- Every mutation must record actor attribution.
- Missing/invalid session, disabled membership, revoked PlantAccessGrant, archived Plant
  in normal operations, or role mismatch must fail closed.
- `plant_approve_actions` is the only MVP per-permission override.

## Request Rules

- Request payloads use strict schemas.
- Unknown properties should be rejected for command/mutation payloads unless a feature
  spec explicitly allows forward-compatible metadata.
- Mutation requests that can be retried should use idempotency keys where duplicate
  execution would create confusing state.
- File uploads must validate size, type, actor/Farm/Plant scope, and storage policy
  before catalog/timeline publication.

## Response Rules

- Responses should be structured and bounded.
- Large lists require pagination, cursors, or scoped filters.
- API responses must return refs for bulky artifacts instead of embedding large blobs.
- Internal traces, hidden reasoning, secrets, raw provider output, and auth material
  must not appear in responses.

## Error Format

Use a predictable error envelope:

```json
{
  "error": {
    "code": "permission_denied",
    "message": "Plant access is required for this operation.",
    "details": {},
    "request_ref": "req_redacted_or_trace_ref",
    "next_valid_actions": ["select_authorized_plant"]
  }
}
```

Recommended error codes:

- `invalid_request`
- `invalid_session`
- `permission_denied`
- `not_found`
- `conflict`
- `archived_resource`
- `validation_failed`
- `upload_rejected`
- `approval_required`
- `safety_gate_blocked`
- `stale_or_missing_evidence`
- `rate_limited`
- `provider_unavailable`
- `internal_error`

Do not leak whether unauthorized private records exist beyond what the ActorContext is
allowed to know.

## Upload Boundary

- Photo upload must write the file, calculate `sha256`, validate metadata, and create
  catalog/manifest/timeline refs in a failure-safe order decided by feature specs.
- File write failure must not create orphan authoritative runtime state.
- Manifest content must be redacted and must not include session/token/API key material.
- Photo files and manifests are local artifacts, not mutable runtime authority.

## CORS And LAN Mode

- Loopback is default.
- LAN mode may exist only when explicitly enabled and protected by auth/session,
  authorization, token/session protection, and CORS/origin allowlist.
- CORS/origin misconfiguration must fail closed.
- State-changing loopback/LAN browser requests must require same-origin,
  CSRF-equivalent, or stronger write protection; do not rely on CORS alone for browser
  write protection.
- LAN mode must not weaken local authorization.

## Compatibility

- MVP may use simple versioning such as `/api/v1` or schema/version fields where useful.
- Breaking changes are allowed during pre-release MVP task work when Memory Bank specs,
  generated OpenAPI, tests, and feature docs are synchronized.
- External public API compatibility is not an MVP requirement.

## Verification

Feature-level specs must create tests for:

- ActorContext resolution on protected routes;
- authorization denial for missing/revoked PlantAccessGrant;
- non-Boss admin mutation denial;
- upload validation and failure ordering;
- redaction of secrets/auth material;
- generated OpenAPI validity once backend implementation exists.
