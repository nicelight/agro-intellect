# TODO: FT-001 Spec Gaps Handoff

Status: closed by `/spec-improve FT-001` and refreshed by
`/prd-to-tasks FT-001` on 2026-06-26.

Assessment: all three findings below were objective against the current
FT-001/FT-002 specs and T3 task records. The repair updated the existing
feature-local SDD owners instead of creating a new shared/global spec.

Repair summary:

- FT-001 now defines concrete Argon2id/password, opaque session token,
  `token_hash`, constant-time verification, cookie transport, bearer-mode, and
  verification targets.
- FT-001 now owns the ActorContext and PlantPermissionContext interface
  envelope; FT-002 now owns concrete PlantPermissionContext resolver semantics
  and Plant route denial codes.
- `/prd-to-tasks FT-001` refreshed existing FT-001 task cards/packets; next
  route is `/review-tasks-plan FT-001`.

## Context

User requested `/spec-improve FT-001` in audit-only mode: do not generate new
artifacts yet, only check what is missing. No files were changed during that
audit.

Audit-time gates before this repair:

- `node scripts/mb-lint.mjs` passes.
- `node scripts/mb-doctor.mjs` passes.
- `/review-tasks-plan FT-001` was approved before these spec changes.
- `FT-001` task queue is `TASK-005-T3-FT-001-W1` through
  `TASK-011-T3-FT-001-W3`.

Main source files:

- `.memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md`
- `.memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md`
- `.memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md`
- `.memory-bank/tasks/TASK-006-T3-FT-001-W1.task.json`
- `.memory-bank/tasks/TASK-008-T3-FT-001-W2.task.json`
- `.memory-bank/tasks/TASK-009-T3-FT-001-W2.task.json`
- `.memory-bank/tasks/TASK-010-T3-FT-001-W3.task.json`

## Spec Gaps Repaired

### 1. FT-001 security primitives are underspecified

Resolution: objective and repaired in
`.memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md`
under `## Credential And Session Primitive Contract` and `## Verification`.

Problem:

- FT-001 requires one-way password hashing, opaque session tokens, and
  persisted `token_hash`, but does not specify the concrete security primitive
  contract.
- `pyproject.toml` currently has no password hashing dependency such as
  `argon2-cffi`, `bcrypt`, or `passlib`.

Current references:

- `.memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md`
  - `password_hash` field
  - `token_hash` field
  - "Store only a token hash server-side"
  - "Default session TTL is 7 days"
- `.memory-bank/tasks/TASK-006-T3-FT-001-W1.task.json`
  - "Password hashing and verification are one-way"
  - "Opaque session tokens are generated"
  - "only token_hash is persisted"

Missing concrete block:

- password KDF/hash algorithm and parameters;
- session token entropy/length/source;
- token hash algorithm;
- constant-time verification rule;
- dependency decision if a third-party password hashing library is required;
- verification targets for the exact primitive behavior.

Suggested repair owner:

- Update existing FT-001 tech spec. Do not create a new spec unless the repair
  needs a shared/global security contract.

### 2. Cookie/session transport is too vague

Resolution: objective and repaired in
`.memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md`
under `## Session Cookie And Bearer Transport Contract`.

Problem:

- FT-001 says browser/PWA session transport is "HTTP-only same-site cookie", but
  TASK-009 needs testable cookie evidence.
- The cookie contract is not concrete enough for T3 implementation.

Current references:

- `.memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md`
  - Browser/PWA default: HTTP-only same-site cookie on loopback.
  - login sets the session cookie.
  - logout clears the session cookie.
- `.memory-bank/tasks/TASK-009-T3-FT-001-W2.task.json`
  - requires HTTP-only same-site session cookie evidence.

Missing concrete block:

- cookie name;
- `Path`;
- exact `SameSite` value;
- `Secure` behavior for loopback vs optional LAN mode;
- `Max-Age`/`Expires` relation to 7-day session TTL;
- clear-cookie behavior on logout;
- bearer-token mode boundaries, if it remains allowed.

Suggested repair owner:

- Update existing FT-001 tech spec.

### 3. PlantPermissionContext shape conflicts across FT-001 and FT-002

Resolution: objective and repaired by aligning
`.memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md`
with `.memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md`.
FT-001 owns the interface envelope; FT-002 owns concrete resolver output,
PlantAccessGrant semantics, and Plant route denial codes.

Problem:

- FT-001 and FT-002 both define `PlantPermissionContext`, but the shapes are not
  identical.
- This can make `TASK-008` and `TASK-010` implementation guess whether FT-001 or
  FT-002 is authoritative for fields.

Current references:

- FT-001 defines:
  - `plant_id`
  - `can_read`
  - `can_comment`
  - `can_operate`
  - `can_create_domain_tasks`
  - `can_manage_access`
  - `can_approve_actions`
  - `source`
- FT-002 resolver defines:
  - `plant_id`
  - `plant_status`
  - `can_read`
  - `can_operate`
  - `can_manage_access`
  - `can_approve_actions`
  - `source`
  - `grant_id`

Also conflicting / misaligned:

- FT-001 uses `AUTH_PLANT_FORBIDDEN`.
- FT-002 uses `plant_not_found_or_forbidden`.

Missing concrete block:

- single canonical `PlantPermissionContext` shape;
- which feature owns the final resolver output;
- which fields FT-001 may define as interface-only before FT-002 implementation;
- canonical Plant denial error code mapping between auth/session code style and
  Plant route code style;
- tests proving FT-001 interface and FT-002 resolver stay compatible.

Suggested repair owner:

- Update FT-001 and FT-002 tech specs together, keeping one authoritative owner
  statement.
- Likely ownership split:
  - FT-001 owns ActorContext and an interface boundary.
  - FT-002 owns concrete PlantAccessGrant resolver semantics and Plant route
    denial code.
  - FT-001 should reference FT-002 for resolver-owned fields instead of
    duplicating incompatible shape.

## After Repair And Task Refresh

Expected route after fixing specs and refreshing task artifacts:

```text
/review-tasks-plan FT-001
```

Reason:

- Changing specs that are linked by `TASK-006`, `TASK-008`, `TASK-009`, or
  `TASK-010` likely changes task records or packet `source_task_hash` inputs.
- Do not execute `TASK-005` or later FT-001 tasks until task/packet refresh and
  task-plan review are clean.
