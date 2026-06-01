---
description: Feature-local SDD tech spec for FT-010 local security, privacy, and lazy sync.
status: active
owner: architecture
last_updated: 2026-05-31
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/features/FT-010-local-security-privacy-lazy-sync.md
  - .memory-bank/spec-index.md
---
# FT-010 Local Security, Privacy, and Lazy Sync Tech Spec

## Scope

This spec closes the feature-local SDD design gate for FT-010 before `/prd-to-tasks FT-010`.

FT-010 owns the MVP local operations baseline:

- loopback-by-default backend binding;
- explicit protected LAN mode;
- CORS allowlist behavior;
- upload security limits and MIME allowlist;
- safe path handling and path traversal rejection;
- secret redaction across export/display/audit surfaces;
- private-by-default local artifacts;
- `local_only` sync status and 200 MB prompt-only behavior.

FT-010 does not own photo catalog schema, photo manifest schema, daily photo workflow endpoints, UI layout, server sync, remote upload, multi-user auth, production deployment, or automated plant/device control.

## Normative Inputs

- [.memory-bank/runbooks/local-security.md](../runbooks/local-security.md): local security, upload validation, privacy, and lazy-sync runbook.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): API security baseline, error envelope, and upload boundary.
- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): local modular monolith, authority boundaries, artifact adapters, and sync boundary.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): `sync_state` as PostgreSQL/read-model mutable state.
- [.memory-bank/domains/photo-artifacts.md](../domains/photo-artifacts.md): photo file/artifact boundary and upload validation requirement.
- [.memory-bank/testing/index.md](../testing/index.md): local security and lazy-sync risk-surface gates.
- [.memory-bank/invariants.md](../invariants.md): privacy, secret, and `server_verified` prohibitions.

## Design Decisions

### Runtime Binding And LAN Mode

- Backend host binding defaults to loopback: `127.0.0.1` or `localhost`.
- Binding to `0.0.0.0`, a LAN interface, or any non-loopback host is forbidden unless explicit LAN mode is enabled.
- LAN mode uses a simple shared bearer token for MVP. Do not introduce user accounts, sessions, OAuth, RBAC, or multi-user tenancy in FT-010.
- LAN mode requires a configured token with at least 32 characters of entropy-like material. Startup must fail closed if LAN mode is enabled and the token is missing, empty, default, logged, or visibly weak.
- In LAN mode, every API route that can expose project data or mutate state requires `Authorization: Bearer <token>`.
- `GET /api/runtime/health` may remain unauthenticated only if it returns a minimal readiness result and does not expose secrets, local absolute paths, CORS origins, tokens, database URLs, file names, or plant photo metadata.

Configuration names are implementation details, but implementation tasks should preserve these settings conceptually:

| Setting concept | Default | Rule |
|---|---|---|
| backend host | loopback | Non-loopback requires explicit LAN mode. |
| LAN mode enabled | `false` | Must be explicit; no auto-enable from network detection. |
| LAN auth token | unset | Required only when LAN mode is enabled; must be redacted everywhere. |
| CORS allowed origins | exact local UI origins | Wildcard is forbidden for API access. |

### CORS Allowlist

- CORS must use exact allowed origins with scheme, host, and port.
- Default local development origins may include `http://localhost:3000` and `http://127.0.0.1:3000`.
- LAN origins may be added only by explicit configuration when LAN mode is enabled.
- `*`, reflected origins, broad host globs, and permissive credentialed CORS are forbidden for API access.
- Requests with missing or disallowed `Origin` must not receive permissive CORS headers.

### Upload Validation

FT-010 defines the security envelope for uploads. FT-002 owns photo identity/catalog/manifest workflow details.

MVP upload limits:

| Field | Required value |
|---|---|
| maximum file size | 20 MiB per uploaded file |
| maximum multipart request payload | 80 MiB |
| allowed MIME/content types | `image/jpeg`, `image/png`, `image/webp` |
| allowed extensions | `.jpg`, `.jpeg`, `.png`, `.webp` |
| unsupported in MVP | HEIC/HEIF, TIFF, RAW camera formats, SVG, PDF, archives, executable content |

Validation sequence:

1. Reject missing file input before reading or persisting content.
2. Enforce request and per-file size limits before catalog publication.
3. Validate declared content type and extension against the allowlist.
4. Sniff file magic bytes where practical and reject obvious MIME/content mismatch.
5. Generate server-side storage paths from trusted identifiers only.
6. Treat the user-provided filename as display metadata only after sanitization; never use it as a destination path.
7. Resolve the final destination path and prove it remains under the configured local artifact root.
8. Reject absolute paths, `..`, encoded traversal, path separators in untrusted name segments, symlinks that escape the artifact root, and overwrite attempts.
9. Require the owning photo workflow to validate `plant_id`, `photo_type`, file identity, and `sha256` before accepted-photo publication.

Rejected uploads must use the shared API error envelope with a safe message and machine-readable code such as `upload_too_large`, `unsupported_media_type`, `unsafe_path`, or `validation_error`.

### Secret Redaction

The application must maintain a centralized redaction boundary for all surfaces that can persist, export, display, or capture text.

Secret categories include:

- `.env` values;
- LLM/provider API keys;
- LAN bearer token and future auth material;
- database URLs, passwords, and credentials;
- access tokens, refresh tokens, and private local service credentials.

Protected surfaces:

- application logs;
- `timeline.jsonl`;
- photo manifests and export snapshot candidates;
- UI Feed events;
- Agent Chat Bus events;
- screenshots and UI/e2e captured artifacts;
- error responses and health/readiness output.

Rules:

- Exact configured secret values must be replaced with `[REDACTED:<kind>]` before writing to protected surfaces.
- Common token/key patterns should be redacted as a defense-in-depth measure, but exact configured values are the authoritative test fixture.
- Redaction must run before append/write/publish, not as a later cleanup pass.
- If a surface cannot be redacted reliably, the operation must fail closed instead of writing a secret.
- Redaction must not mutate the runtime source value used for real authentication or provider calls.

### Privacy And Local Artifacts

- Local plant photos, manifests, timeline files, and runtime database data are private project data by default.
- FT-010 must not add outbound sync, remote upload, server target configuration, or background network transfer.
- Any future upload/sync feature requires a new spec stage and explicit user approval flow.
- For the MVP, user approval for upload/sync can only acknowledge or dismiss the local prompt; it must not trigger remote transfer because no server sync exists.
- Privacy checks must treat photo files and manifests as local artifacts even when the UI displays a local storage prompt.

### Lazy Sync State

- PostgreSQL/read model owns current `sync_state`.
- The only allowed MVP sync status is `local_only`.
- `server_verified`, `pending_upload`, `uploading`, `uploaded`, and `sync_failed` are forbidden until a real server sync stage exists.
- The dataset/photo local storage threshold is 209715200 bytes (200 MiB).
- When local dataset/photo storage exceeds the threshold, the system may set or compute `upload_prompt_visible=true` for presentation.
- Showing, acknowledging, or dismissing the 200 MiB prompt must not change `sync.status`.
- The prompt must not imply that a server exists, an upload is available, or data has been synced.

Minimal `sync_state` fields for FT-010 task decomposition:

| Field | Rule |
|---|---|
| `scope_ref` | Identifies the storage scope, initially `plant:tomato_001` or equivalent local scope. |
| `status` | Must equal `local_only` in MVP. |
| `local_storage_bytes` | Non-negative integer from local artifact accounting. |
| `upload_prompt_threshold_bytes` | Defaults to 209715200. |
| `upload_prompt_visible` | Derived or stored presentation flag; does not imply sync. |
| `prompt_acknowledged_at` | Optional user acknowledgment timestamp; does not imply approval to upload. |
| `event_refs` | Timeline refs when prompt visibility/acknowledgment is audited. |

## API Surface

FT-010 defines security and sync-support behavior, not the full photo intake API.

Minimum API expectations:

- Upload endpoints owned by FT-002 must apply the FT-010 upload validation envelope before accepting files.
- All API errors use the shared structured error envelope from [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md).
- `GET /api/runtime/health` may expose minimal local readiness without secrets or absolute paths.
- `GET /api/sync/status` may return the MVP `sync_state` projection for the UI prompt.
- `POST /api/sync/prompt-ack` may record prompt acknowledgment, but it must not upload data or change `status` away from `local_only`.

If implementation tasks choose different route names, they must preserve the behavior above and update this spec plus generated OpenAPI evidence when code exists.

## Verification Targets

Required before FT-010 can be marked implemented:

- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- Configuration tests proving loopback default and startup failure for non-loopback binding without explicit LAN mode.
- LAN auth tests proving protected routes reject missing/wrong bearer token and accept the configured token without logging it.
- CORS tests proving exact allowlist behavior and rejecting wildcard/reflected origins.
- Upload tests for size limit, multipart request limit, allowed MIME/extension, unsupported type rejection, MIME/content mismatch, missing file, path traversal, encoded traversal, absolute paths, symlink escape, and overwrite attempts.
- Redaction tests using configured secret fixtures across logs, timeline events, manifests/export candidates, UI Feed, Agent Chat Bus, API errors, health output, and screenshot/e2e artifact text where applicable.
- Privacy tests proving no outbound upload/sync path exists in FT-010 and local artifacts remain local without explicit future sync spec.
- Lazy-sync tests proving only `local_only` is accepted, forbidden future statuses are rejected, 200 MiB threshold controls prompt visibility, and prompt acknowledgment does not mutate sync status or imply server sync.
- Anti-cheat check proving `server_verified` cannot be created through API input, seed data, defaults, fixtures, or UI prompt code before a real server sync stage exists.

## Gaps And Non-Goals

- No FT-010 blocker remains for `/prd-to-tasks FT-010`.
- Exact setting names, dependency choices, middleware class names, and filesystem helper names belong to implementation tasks.
- HEIC/HEIF support, antivirus scanning, perceptual image validation, user accounts, remote backup, server sync lifecycle, production TLS/certificate management, and deployment hardening are outside FT-010 MVP scope.
