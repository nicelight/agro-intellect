---
description: Global HTTP/API guardrails for MVP v2.
status: active
owner: architecture
type: contract
last_updated: 2026-06-14
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/architecture/system-architecture.md
---
# API Guidelines

## Scope

This document defines global HTTP/API guardrails. It does not define endpoint-by-endpoint schemas. Concrete route contracts belong to feature-level `/spec-improve` and later FastAPI/Pydantic schemas.

## API Style

- Use FastAPI-style HTTP JSON APIs with Pydantic-style request/response validation.
- Use multipart upload only for photo/file intake routes.
- Use generated OpenAPI from backend schemas when implementation exists.
- Do not maintain a large hand-written OpenAPI file as the primary source of truth before code exists.

## Route Grouping

Use module-oriented route groups:

- session/account routes for local login/session.
- admin routes for Boss personnel, role, Plant, access, and admin audit workflows.
- Farm/Plant routes for Plant lifecycle, Plant selector, and Plant history.
- operations routes for check-in, observations, measurements, tasks, approvals, and outcomes.
- photo routes for upload, catalog, manifest refs, and authorized retrieval.
- agent routes only for project-owned adapter/runtime outputs, not raw provider output.
- safety routes for Safety Gate decisions and physical-action approval flow.
- companion routes for IssueStack, proposals, decisions, and approved governance summaries.
- dataset routes for dataset fields and evidence refs when implemented.

Exact path names are feature-local design work.

## ActorContext And Authorization

- Every non-health route must resolve ActorContext before business logic.
- Every Farm/Plant route must enforce backend authorization using FarmMembership, role preset, PlantAccessGrant, and optional `plant_approve_actions`.
- Frontend hide/show is never an authorization substitute.
- Context builders follow the same authorization rules as user-facing reads.

## Error And Response Rules

- Errors must use stable machine-readable codes plus safe user-facing messages.
- Error details must not include secrets, tokens, credentials, `.env` values, API keys, raw provider payloads, or hidden reasoning.
- Authorization failures must fail closed and avoid leaking whether unauthorized Plant data exists.
- Validation errors should identify invalid fields without exposing protected context.

## Upload Rules

- Photo upload must validate content type, size, path safety, and actor/Plant authorization.
- Backend creates the accepted catalog record, checksum, manifest, and audit/export refs only after validation and successful artifact handling.
- Upload routes must not imply server sync or upload beyond local storage.

## CORS And Exposure

- Default backend exposure is loopback.
- LAN mode, if implemented, requires explicit enablement, authentication, authorization, token/session protection, and CORS/origin controls.

## Compatibility

- MVP can evolve quickly, but breaking changes must be synchronized across API consumers, tests, and Memory Bank docs.
- Feature-local `/spec-improve` decides versioning only when a boundary needs it.
