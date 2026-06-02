---
description: HTTP API guidelines for the FastAPI backend and Next/PWA frontend boundary.
status: active
owner: architecture
last_updated: 2026-05-31
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/spec-index.md
---
# API Guidelines

## Scope

The HTTP API is the frontend/backend boundary only. It is not the source of truth for agent contracts, domain events, state lifecycles, safety policy, or dataset governance.

## OpenAPI Policy

- FastAPI/Pydantic or equivalent backend schemas should generate OpenAPI once backend code exists.
- Do not hand-write a large `openapi.yaml` before feature-local design and implementation.
- Generated OpenAPI must validate in CI once the backend exists.
- Critical endpoints must have integration or contract tests.

## API Shape Rules

- Keep endpoints feature-local and PRD-grounded.
- Use JSON request/response bodies for structured data.
- Use multipart upload only where photo/file upload requires it.
- Preserve stable identifiers in responses: `plant_id`, `photo_id`, `task_id`, `approval_id`, `event_id`, and refs where applicable.
- Do not expose raw model reasoning or UI Feed internals as agent-consumable data.

## Error Format

Use a small structured error envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Human-readable summary",
    "details": {},
    "trace_id": "optional"
  }
}
```

Feature specs may define exact error codes, but must preserve machine-readable `code` and safe user-facing `message`.

## Security Baseline

- Backend binds to loopback by default.
- LAN mode requires explicit enablement and authentication/token protection.
- CORS uses an allowlist, not wildcard production behavior.
- Uploads validate size, MIME/content type, safe paths, and path traversal rejection.
- Secrets, tokens, `.env` values, and credentials must be redacted from logs, timeline, manifests, UI Feed, Agent Chat Bus, screenshots, and export candidates.

## Compatibility

- Breaking API changes are allowed during early MVP only when specs and dependent feature tasks are updated together.
- Once a feature is implemented and verified, later changes must update the relevant feature-local spec, tests, and generated OpenAPI evidence.
