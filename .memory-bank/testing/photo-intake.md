---
description: Verification specification for local photo intake, catalog rows, capture manifests, and upload HTTP.
status: active
type: testing_spec
last_updated: 2026-07-11
source_of_truth:
  - .memory-bank/domains/photo-artifacts.md
  - .memory-bank/contracts/photo-intake-http.md
  - .memory-bank/testing/strategy.md
---
# Photo Intake Verification

## Scope

Defines deterministic evidence for FT-005 accepted photo artifacts.

## Required evidence

- Migration/model tests for `photo_catalog_items`, native UUID FKs,
  restrictive deletes, accepted status, allowed content types, allowed
  `photo_type`, local-only fields, and event refs.
- Filesystem tests for safe relative layout, temp-write plus atomic rename,
  no user-controlled destination path, and no absolute path leakage.
- Manifest tests for `photo_manifest.v1`, `manifest_kind=initial_capture`,
  required identity/file/source/authority fields, immutable file refs, and
  secret/auth exclusion.
- Checksum tests proving catalog and manifest `sha256` match the stored
  original.
- Upload API/OpenAPI tests for accepted JPEG/PNG/WebP, 20 MiB max, validation
  errors, no-store responses, and safe error envelope.
- Authorization tests for Boss/Engineer upload, Consultant denial, missing or
  revoked grant, disabled membership, unauthorized Plant, and archived
  normal-operation denial.
- Timeline-ref tests proving `photo_accepted` is appended only for accepted
  photos and cannot become Plant state authority.
- Service/repository/HTTP pagination tests seed more rows than `limit` and
  prove stable `uploaded_at DESC, photo_id ASC` keyset continuation, a real
  `next_cursor`, no duplicates or omissions, complete enumeration, and a null
  terminal cursor.
- Cursor-negative tests cover empty, non-base64url, non-canonical, wrong
  version, invalid timestamp/UUID, and wrong-Plant cursor payloads; each returns
  `422 VALIDATION_FAILED` without bypassing ActorContext read authorization.

## Anti-cheat checks

- Catalog reads use PostgreSQL/read model and never scan manifests as current
  authority.
- A supplied cursor changes the keyset query or fails validation; it is never
  a silent no-op, and `limit` truncation never claims terminal pagination while
  more rows exist.
- A failed file, manifest, catalog, checksum, or timeline step does not return
  accepted photo success.
- Photo artifacts default to `can_train_on=false` and local-only; no server sync
  is implied.
- Responses, manifests, timeline events, logs, screenshots, exports, and
  evidence omit secrets/auth material.

## Suggested gates

- `.venv/bin/python -m pytest tests/backend/photo_intake`
- `.venv/bin/python -m pytest tests/backend/api -k ft005`
- `.venv/bin/python -m pytest tests`
- `node scripts/mb-lint.mjs`
- `git diff --check`
