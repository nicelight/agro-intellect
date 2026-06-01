---
description: Local security, privacy, upload validation, and lazy-sync runbook.
status: active
owner: architecture
last_updated: 2026-05-31
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/spec-index.md
---
# Local Security

## Runtime Defaults

- Backend binds to loopback by default.
- LAN mode requires explicit enablement and authentication/token protection.
- CORS uses an allowlist.
- Local plant photos and manifests are private project data by default.

## Upload Validation

Upload handling must validate:

- maximum size;
- MIME/content type;
- safe local destination;
- file extension/content consistency where practical;
- path traversal rejection;
- required `plant_id`, `photo_type`, and file identity before catalog publication.

Exact limits and MIME allowlist are feature-local decisions for `/spec-improve FT-002` or `/spec-improve FT-010`.

## Secret Redaction

Secrets must not be written to logs, `timeline.jsonl`, photo manifests, UI Feed, Agent Chat Bus, screenshots, or export candidates.

Secret categories include `.env` values, API keys, tokens, credentials, local auth secrets, provider keys, and database credentials.

## Lazy Sync

- MVP sync status is `local_only`.
- If local dataset/photo storage exceeds 200 MiB, the UI may show a local storage prompt.
- The user may acknowledge or dismiss the local prompt only.
- The prompt must not imply upload availability, server availability, or remote sync.
- The prompt must not mutate sync status.
- `server_verified` is forbidden before a real server sync stage exists.

## Verification Checklist

- Loopback default is tested.
- LAN mode requires explicit config and token/auth.
- CORS wildcard behavior is rejected outside explicitly safe local development.
- Upload path traversal attempts are rejected.
- Secret-like values are redacted from logs/export surfaces.
- Privacy and lazy-sync tests prove no upload occurs in the MVP and prompt acknowledgement does not trigger transfer.
