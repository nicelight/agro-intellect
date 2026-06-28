---
description: Feature SDD design for FT-001 Local Accounts Sessions And ActorContext.
status: active
owner: architecture
type: feature_design
feature_id: FT-001
last_updated: 2026-06-28
source_of_truth:
  - .memory-bank/features/FT-001-local-accounts-sessions-actor-context.md
  - .memory-bank/foundation.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/architecture/foundation-runtime-substrate.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/domains/foundation-data-substrate.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/evidence-redaction.md
  - .memory-bank/contracts/agent-chat-bus.md
  - .memory-bank/contracts/message-envelope.md
  - .memory-bank/testing/index.md
  - .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md
  - .memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md
---
# FT-001 Local Accounts Sessions And ActorContext

## Purpose

Define the local identity, session, role, and ActorContext boundary that every Farm/Plant route, domain service, audit writer, and agent/context builder must use.

## Ownership

- Owns: FT-001 feature-local Account, FarmMembership, LocalSession relational
  schema/constraints,
  credential/session primitive, session route, ActorContext,
  PlantPermissionContext interface envelope, auth/session error catalog, and
  task-ready verification contract.
- Does not own: Foundation app/database substrate, Farm/Plant/PlantAccessGrant
  lifecycle, concrete PlantPermissionContext resolver semantics and route-level
  Plant denial codes, Boss admin/invite UI and mutation flows,
  AdminAuditRecord durable write policy, Agent Chat Bus runtime implementation,
  MessageEnvelope validation, UI Feed projection, Safety Gate clearance, or
  physical-action approval.
- Related specs:
  - [.memory-bank/architecture/foundation-runtime-substrate.md](../architecture/foundation-runtime-substrate.md):
    owns app factory, entrypoint, dependency direction, and smoke route mounting
    that FT-001 must preserve.
  - [.memory-bank/domains/foundation-data-substrate.md](../domains/foundation-data-substrate.md):
    owns DB/session/Alembic/runtime-root substrate that FT-001 product tables
    and migrations must use.
  - [.memory-bank/contracts/evidence-redaction.md](../contracts/evidence-redaction.md):
    owns redaction rules for command/test/evidence artifacts that mention auth
    material.
  - [.memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md](FT-002-farm-plant-lifecycle-access-grants.md):
    owns Farm, Plant, PlantAccessGrant lifecycle/mutation semantics, concrete
    PlantPermissionContext resolver output semantics, and Plant route denial
    code mapping.
  - [.memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md](FT-003-boss-admin-surface-admin-audit.md):
    owns public invite activation route, admin mutations, and durable admin
    audit behavior.

## Normative Inputs

- [.memory-bank/spec-backbone.md](../spec-backbone.md): global backbone is complete.
- [.memory-bank/foundation.md](../foundation.md): verified Foundation baseline for migrations, DB/session helpers, local runtime roots, and redaction.
- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Access & Admin module and source-of-truth hierarchy.
- [.memory-bank/architecture/foundation-runtime-substrate.md](../architecture/foundation-runtime-substrate.md): app factory, route mounting, and substrate dependency direction.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): Account, FarmMembership, ActorContext authority.
- [.memory-bank/domains/foundation-data-substrate.md](../domains/foundation-data-substrate.md): shared DB/session/Alembic/runtime-root substrate.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): API authz and error guardrails.
- [.memory-bank/contracts/evidence-redaction.md](../contracts/evidence-redaction.md): redaction rules for auth/session evidence.
- [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md): context builders must resolve ActorContext and PlantAccessGrant before returning Bus context.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): MessageEnvelope authorization scope must not include unauthorized Farm/Plant context or auth material.
- [.memory-bank/testing/index.md](../testing/index.md): risk-based verification and T3 auth/session test surfaces.
- [.memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md](FT-002-farm-plant-lifecycle-access-grants.md): Farm, Plant, and PlantAccessGrant ownership used by the ActorContext permission resolver.
- [.memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md](FT-003-boss-admin-surface-admin-audit.md): local invite/admin mutation and AdminAuditRecord ownership.
- [.memory-bank/requirements.md](../requirements.md): REQ-002, REQ-003, REQ-004, REQ-022.

## Design Depth

Feature hub only. No new global spec is needed; shared access/admin backbone is already covered by system architecture, runtime data model, API guidelines, Agent Chat Bus, MessageEnvelope, and adjacent FT-002/FT-003 feature specs.

## Concrete Contract Readiness

This feature-local hub is the authoritative owner for FT-001 concrete blocks.
Shared specs above remain authoritative for their global boundaries.

| Boundary | Shape owner | Rules owner | Edge cases/errors owner | Verification target |
|---|---|---|---|---|
| Account, FarmMembership, LocalSession data contract | `## Data Model`, `## TASK-005 Relational Storage Contract`, `## Migration And Indexing Targets` | `## TASK-005 Relational Storage Contract`, `## Session Lifecycle` | `## TASK-005 Relational Storage Contract`, `## Failure Rules`, `## Error Contract` | `## TASK-005 Relational Storage Contract`, `## Verification`; `TASK-005`, `TASK-007` records |
| Credential/session lifecycle component contract | `## Credential And Session Primitive Contract`, `## Session Lifecycle`, internal primitive under `## API Surface` | `## Credential And Session Primitive Contract`, `## Session Lifecycle`, `## Failure Rules` | `## Error Contract`, `## Failure Rules` | `## Verification`; `TASK-006`, `TASK-007` records |
| Session HTTP API contract | route blocks under `## API Surface` | `## API Surface`, [API Guidelines](../contracts/api-guidelines.md) | `## Error Contract`, `## Failure Rules` | `## Verification`; `TASK-009` record |
| Session cookie and bearer transport contract | `## Session Cookie And Bearer Transport Contract`, route blocks under `## API Surface` | `## Session Cookie And Bearer Transport Contract`, [API Guidelines](../contracts/api-guidelines.md) | `## Session Cookie And Bearer Transport Contract`, `## Error Contract` | `## Verification`; `TASK-009` record |
| ActorContext and PlantPermissionContext contract | `## ActorContext`, `## Context Builder Rules`; FT-002 `## PlantPermissionContext Resolver` for concrete resolver output | `## Role Presets`, `## Context Builder Rules`; FT-002 grant semantics | `## Failure Rules`, `## Error Contract`; FT-002 route denial mapping | `## Verification`; `TASK-008`, `TASK-010` records |
| Auth/session evidence redaction contract | `## Failure Rules`, [Evidence Redaction](../contracts/evidence-redaction.md) | `## Failure Rules`, [API Guidelines](../contracts/api-guidelines.md) | `## Error Contract`, [Evidence Redaction](../contracts/evidence-redaction.md) | `## Verification`; `TASK-006`, `TASK-009`, `TASK-011` records |

No duplicate owner was found during the 2026-06-26 `/prd-to-tasks FT-001`
refresh. FT-001 owns only feature-local auth/session/ActorContext detail; the
Foundation, FT-002, FT-003, Bus, MessageEnvelope, and evidence-redaction specs
own their respective shared boundaries.

The 2026-06-28 `/spec-improve FT-001` repair completes the relational contract
required by `TASK-005`: shared UUID identity, exact nullability, status/role
checks, normalized login uniqueness, non-cascading relations/indexes, and the
deferred `FarmMembership.farm_id` FK handoff owned by FT-002. It does not add a
second Farm authority, runtime code, API DTO, event, or Python callable design.

## Component Boundary Rules

FT-001 owns:

- `Account`, `FarmMembership`, and `LocalSession` table contracts.
- local credential setup primitives, login, logout, session inspection, session invalidation, and auth error codes.
- `ActorContext` shape and the PlantPermissionContext interface envelope that
  downstream resolvers must satisfy.
- role-preset policy as consumed by backend authorization.
- the interface used by routes, audit writers, and context builders to require ActorContext.

FT-001 does not own:

- `Farm`, `Plant`, `PlantAccessGrant`, Plant lifecycle, `tomato_001`
  seeding, concrete PlantPermissionContext resolver output values, or Plant
  HTTP route denial codes; these belong to FT-002.
- Boss admin invite creation, public local invite activation route, account/personnel management UI, role mutation routes, Plant access mutation routes, or durable admin audit write policy; these belong to FT-003.
- Safety Gate clearance; `can_approve_actions` means actor authority only and never means Safety Gate pass.
- agent output publication, Bus event payloads, MessageEnvelope validation, or UI Feed projection.

The implementation may build a small interface stub for FT-002/FT-003 dependencies only when needed for task sequencing, but must not duplicate their domain rules.

## Data Model

Feature-owned mutable records:

- `Account`
  - `account_id`: UUID stable local identifier.
  - `login_name`: required normalized lowercase login, unique locally.
  - `display_name`: required safe display text.
  - `account_status`: `pending_activation | active | disabled`
  - `password_hash`: required for `active`; nullable for `pending_activation`
    and for an Account disabled before activation.
  - `created_at`, `updated_at`: required timezone-aware timestamps.
  - `disabled_at`: nullable timezone-aware timestamp.
- `FarmMembership`
  - `membership_id`: UUID stable local identifier.
  - `account_id`: required UUID Account reference.
  - `farm_id`: required UUID, with its Farm FK deferred to FT-002.
  - `role_preset`: `boss | engineer | consultant`
  - `membership_status`: `invited | active | disabled`
  - `created_at`, `updated_at`: required timezone-aware timestamps.
  - `disabled_at`: nullable timezone-aware timestamp.
- `LocalSession`
  - `session_id`: UUID stable local identifier.
  - `account_id`: required UUID Account reference.
  - `token_hash`: unique server-side hash of the opaque token.
  - `created_at`, `expires_at`: required timezone-aware timestamps.
  - `revoked_at`, `last_seen_at`: nullable timezone-aware timestamps.
  - `auth_method`: `local_password | local_invite_activation`
  - `client_label`: optional safe label such as `local_pwa`; never user-agent secrets.

Minimum constraints:

- `Account.login_name` is unique after normalization.
- `FarmMembership` has one row per `account_id + farm_id` in MVP; multi-Farm membership is out of scope.
- `LocalSession.token_hash` is unique and indexed for lookup.
- `LocalSession` validity is computed from `expires_at`, `revoked_at`, `Account.account_status`, and `FarmMembership.membership_status`.
- Foreign keys must preserve account/session/membership referential integrity; disabling is preferred over hard delete in MVP.

The client receives only an opaque session token. Store only a token hash server-side.

## TASK-005 Relational Storage Contract

This block is the single authoritative owner for the exact FT-001 table shape,
constraints, and initial migration. Shared UUID compatibility comes from
[Runtime Data Model](../domains/runtime-data-model.md);
FT-002 owns only the later Farm authority/FK closure described below.

Shape:

- Table `accounts`:
  - `account_id`: PostgreSQL `uuid`, primary key, non-null, application default
    `uuid.uuid4`.
  - `login_name`: `text`, non-null; stores only the canonical normalized value.
  - `display_name`: `text`, non-null.
  - `account_status`: `varchar(32)`, non-null.
  - `password_hash`: unbounded `text`, nullable.
  - `created_at`, `updated_at`: `timestamptz`, non-null, server default `now()`.
  - `disabled_at`: nullable `timestamptz`.
- Table `farm_memberships`:
  - `membership_id`: PostgreSQL `uuid`, primary key, non-null, application
    default `uuid.uuid4`.
  - `account_id`: PostgreSQL `uuid`, non-null.
  - `farm_id`: PostgreSQL `uuid`, non-null.
  - `role_preset`: `varchar(16)`, non-null.
  - `membership_status`: `varchar(16)`, non-null.
  - `created_at`, `updated_at`: `timestamptz`, non-null, server default `now()`.
  - `disabled_at`: nullable `timestamptz`.
- Table `local_sessions`:
  - `session_id`: PostgreSQL `uuid`, primary key, non-null, application default
    `uuid.uuid4`.
  - `account_id`: PostgreSQL `uuid`, non-null.
  - `token_hash`: `varchar(64)`, non-null; stores lowercase ASCII hexadecimal
    SHA-256 only.
  - `created_at`: `timestamptz`, non-null, server default `now()`.
  - `expires_at`: `timestamptz`, non-null.
  - `revoked_at`, `last_seen_at`: nullable `timestamptz`.
  - `auth_method`: `varchar(32)`, non-null.
  - `client_label`: nullable `text` containing only a safe local label.
- `LocalSession` has no raw-token, cookie, bearer, or auth-header column.

Rules:

- SQLAlchemy maps every UUID column above as Python `uuid.UUID` with
  `Uuid(as_uuid=True)`. UUIDs are application-generated with `uuid.uuid4`; no
  PostgreSQL extension or integer sequence is required.
- Statuses/roles use ordinary string columns plus named DB `CHECK` constraints,
  not PostgreSQL native ENUM types:
  - `accounts.account_status IN ('pending_activation', 'active', 'disabled')`;
  - `farm_memberships.membership_status IN ('invited', 'active', 'disabled')`;
  - `farm_memberships.role_preset IN ('boss', 'engineer', 'consultant')`;
  - `local_sessions.auth_method IN ('local_password', 'local_invite_activation')`.
- The Account credential check is:
  `active -> password_hash IS NOT NULL`,
  `pending_activation -> password_hash IS NULL`, and
  `disabled -> password_hash may be null or non-null`.
  Argon2id PHC validation remains in the FT-001 security component; the DB must
  not add a brittle PHC-prefix check or arbitrary maximum length.
- The application canonicalizes login input with `strip().lower()` before
  persistence. PostgreSQL is the final guard: a named check requires
  `login_name = lower(btrim(login_name))` and `login_name <> ''`; one unique
  B-tree constraint/index on stored `login_name` provides normalized
  uniqueness. Do not add `citext` or a second functional unique index.
- `updated_at` is set to the mutation time by the owning service; no DB trigger
  is introduced. Nullable lifecycle timestamps remain null until their matching
  disable/revoke/seen transition occurs.
- `farm_memberships.account_id -> accounts.account_id` and
  `local_sessions.account_id -> accounts.account_id` are required FKs with
  `ON DELETE RESTRICT`. No authority relation uses cascading delete.
- `farm_memberships.farm_id` is intentionally non-null but has no FK in the
  FT-001 migration because FT-001 must not create the FT-002-owned `farms`
  table. Before FT-002, no released bootstrap/admin path may create durable
  FarmMembership rows; rollback-scoped migration/repository fixtures and
  internal service tests may use temporary rows.
- FT-002 must close the deferred relation before enabling Farm/membership
  product writes: create/reuse the single Farm authority, reconcile at most one
  existing distinct membership `farm_id`, then add and validate
  `farm_memberships.farm_id -> farms.farm_id ON DELETE RESTRICT`.
- Required uniqueness/indexes are exactly:
  - one unique normalized lookup for `accounts.login_name`;
  - one unique constraint/index on
    `farm_memberships(account_id, farm_id)`;
  - one unique lookup index on `local_sessions.token_hash`;
  - one non-unique index on `local_sessions.account_id`;
  - one non-unique index on `local_sessions.expires_at`.
  Do not add duplicate indexes for the same leading columns.
- Token generation/hashing must produce exactly 64 lowercase hex characters
  before persistence. Format validation belongs to the FT-001 security
  component; the migration owns the non-null `varchar(64)` storage shape.

Edge cases/errors:

- Invalid status, role, or auth-method values are rejected by DB checks.
- An `active` Account without `password_hash`, or a `pending_activation`
  Account with one, is rejected. Disabling an unactivated Account may preserve
  `password_hash=null`.
- Non-normalized or empty `login_name` is rejected; two inputs that normalize
  to the same stored value conflict on the single unique lookup.
- Account deletion is rejected while membership/session rows reference it;
  disabling/revoking is the supported lifecycle path.
- More than one distinct pre-FT-002 `farm_id` in durable membership rows blocks
  the FT-002 migration; it must not create multiple Farm authorities or rewrite
  memberships silently.
- A migration/model containing raw session material, a cascading authority FK,
  duplicate token/login indexes, or an FT-001-created `farms` table violates
  this contract.

Verification target:

- `TASK-005` model/migration tests inspect table/column names, native UUID and
  `timestamptz` types, nullability/defaults, named checks, FKs, uniqueness, and
  the exact index set.
- PostgreSQL integration tests prove UUID round-trip, normalized login conflict,
  invalid enum-like values rejected, active/pending password checks, required
  fields/timestamps, non-cascading Account relations, and no raw-token column.
- `TASK-005` tests explicitly prove `farm_memberships.farm_id` is UUID/non-null
  but has no FK and that no `farms` table is created by the FT-001 migration.
- FT-002 migration tests prove zero/one/multiple pre-existing distinct
  membership `farm_id` handling and successful final `RESTRICT` FK validation.
- `TASK-006` security tests prove Argon2id PHC and lowercase 64-character
  SHA-256 formats before values reach persistence.

## Credential And Session Primitive Contract

FT-001 owns the concrete credential/session primitive used by login and by the
FT-003 invite activation handoff.

Shape:

- `password_hash`: Argon2id PHC string generated through `argon2-cffi`.
- `raw_session_token`: client-only opaque URL-safe token generated from at
  least 32 random bytes with Python `secrets` APIs.
- `token_hash`: lowercase hex SHA-256 digest of the exact raw session token
  bytes after UTF-8 encoding.

Rules:

- `TASK-006` must add `argon2-cffi` as a runtime dependency and use Argon2id
  for password hashing and verification.
- Runtime password hashing parameters are
  `time_cost=3`, `memory_cost=65536`, `parallelism=4`, `hash_len=32`, and
  `salt_len=16` unless a later explicit security spec replaces them.
- Plain SHA, unsalted hashes, reversible encryption, homemade password KDFs,
  and plaintext password storage are forbidden for `password_hash`.
- Session tokens must be generated with at least 256 bits of entropy; for
  example, `secrets.token_urlsafe(32)`.
- The raw session token may be returned only once through the selected session
  transport and must never be persisted, logged, audited, exported, inserted
  into Bus/UI Feed/agent context, or written into test evidence.
- Session lookup computes `token_hash` from the presented token and then
  verifies the stored digest with constant-time comparison such as
  `hmac.compare_digest`.
- Password verification delegates secret comparison to Argon2id verification;
  failure must surface only generic auth errors.

Edge cases/errors:

- Empty, malformed, unknown, revoked, expired, or unverifiable tokens fail as
  `AUTH_SESSION_INVALID` or the more specific expiry/status code defined below.
- Password mismatch and missing login both surface as `AUTH_CREDENTIAL_INVALID`
  without account enumeration.
- Any primitive failure path must redact passwords, raw tokens, token hashes,
  cookies, bearer tokens, auth headers, and `.env` values before logs or
  evidence are written.

Verification target:

- Unit tests prove Argon2id hash/verify success and failure without storing or
  returning plaintext passwords.
- Unit tests prove session token generation produces opaque high-entropy
  values, persists only the SHA-256 `token_hash`, rejects bad tokens, and uses
  constant-time digest comparison.
- Redaction evidence proves passwords, raw tokens, token hashes, cookies,
  bearer tokens, and auth headers are removed from error/log-like strings.

## Session Lifecycle

```text
FT-003 local invite/bootstrap -> Account pending_activation + FarmMembership invited
FT-003 public invite activation calls FT-001 credential/session primitive -> Account active + FarmMembership active
active account + valid password -> LocalSession active until expires_at or revoked_at
logout -> current LocalSession revoked
disabled account or disabled membership -> all related sessions invalid for privileged use
```

Session token transport:

- Browser/PWA default: HTTP-only same-site cookie named
  `agro_intellect_session`.
- Bearer token may be used only for explicit non-browser/LAN mode and must
  follow the same server-side session model.
- No hosted recovery, email delivery, third-party identity, or SaaS tenancy in MVP.

## Session Cookie And Bearer Transport Contract

Cookie shape for browser/PWA transport:

- Name: `agro_intellect_session`.
- Value: raw opaque session token from `## Credential And Session Primitive Contract`.
- `HttpOnly`: required.
- `SameSite`: `Lax`.
- `Path`: `/`.
- `Max-Age`: `604800` seconds by default.
- `Expires`: same instant as `LocalSession.expires_at`.
- `Secure`: `false` only for explicit loopback HTTP development origins such
  as `http://localhost` or `http://127.0.0.1`; `true` for HTTPS and any
  browser cookie use outside loopback.

Rules:

- Login and FT-003 invite activation success set exactly this cookie for
  browser/PWA transport and do not include the raw token in the JSON body.
- Logout clears the cookie with the same name/path/samesite/secure mode and
  `Max-Age=0`; the clearing response should also set an already-expired
  `Expires` value.
- Cookie TTL must not outlive the persisted `LocalSession.expires_at`.
- Plain HTTP LAN browser cookie mode is forbidden. If optional LAN browser mode
  is implemented, it must use HTTPS, explicit enablement, origin controls from
  API Guidelines, and `Secure=true`.
- Bearer mode is disabled by default for browser/PWA flows. When explicitly
  enabled for non-browser/LAN clients, the raw token is returned once in a safe
  response field or header, clients send it as `Authorization: Bearer ...`, and
  the server still stores only `token_hash`.
- Bearer responses must use no-store cache behavior and must not also set the
  session cookie.

Edge cases/errors:

- Missing cookie and missing bearer credential on a protected route surface
  `AUTH_SESSION_REQUIRED`.
- Multiple session credentials on one request are invalid unless a later route
  spec explicitly chooses precedence; FT-001 default is fail closed with
  `AUTH_SESSION_INVALID`.
- Cookie clearing is idempotent: logout returns `204` and clears the browser
  cookie even when the presented session is missing or invalid.

Verification target:

- Session API tests assert login `Set-Cookie` includes the exact name,
  `HttpOnly`, `SameSite=Lax`, `Path=/`, TTL aligned with `expires_at`, and the
  correct `Secure` behavior for loopback versus HTTPS.
- Logout tests assert the same cookie is cleared with `Max-Age=0` and expired
  `Expires` while remaining idempotent.
- Bearer-mode tests, when implemented, prove no cookie is emitted and only
  `token_hash` is persisted.

Concrete lifecycle decisions:

- Default session TTL is 7 days from `created_at`.
- MVP has no refresh-token flow; users re-login after expiry.
- `last_seen_at` may be updated at most once per request and should be cheap; it is not an authorization source.
- Login creates a new `LocalSession`; it does not silently revive expired or revoked sessions.
- Logout revokes only the current session. Admin disable paths from FT-003 invalidate all privileged use by status check even before batch revocation exists.
- Activation/setup secrets are one-time local secrets created, validated, and status-tracked by FT-003. FT-001 does not expose a public activation route.
- FT-003's `POST /api/local-invites/activate` is the only public invite activation endpoint. After FT-003 validates `local_invite_id` plus `activation_secret`, it calls the FT-001 internal credential/session primitive to set `password_hash`, activate Account/Membership, and issue a `LocalSession`.
- Pending activation and invited membership may access only the FT-003 public invite activation route. They cannot access Farm/Plant data, context builders, admin routes, agent routes, Bus context, or UI Feed data.

## Role Presets

KISS role presets are fixed in MVP:

| Role | Base authority |
|---|---|
| `boss` | Farm admin, account/member management, Plant lifecycle management, Plant access management, admin audit read, all Farm Plant visibility and operations, physical-action approval authority only through Safety Gate. |
| `engineer` | Granted Plant read/operate, check-ins, photos, measurements, allowed tasks/follow-up; physical-action approval authority only when the active PlantAccessGrant has `plant_approve_actions=true`. |
| `consultant` | Granted Plant read/comment/advice context only; no domain task/recommendation record creation, no governance approval by default, no physical-action approval authority. |

Do not add a general permission override matrix in MVP. The only per-Plant override is `plant_approve_actions`.

## ActorContext

Every protected product API route, protected domain service entrypoint, audit
writer, and agent/context builder must resolve:

- `request_id`
- `session_id`
- `account_id`
- `farm_id`
- `membership_id`
- `role_preset`
- `membership_status`
- `auth_provenance`
  - `auth_method`
  - `session_created_at`
  - `session_expires_at`
  - `transport`: `cookie | bearer`
- `plant_permission_resolver`

For Plant-scoped operations, the resolver must return a `PlantPermissionContext`:

- `plant_id`
- `plant_status`: `active | archived | null`; `null` is allowed only for
  denied/not-found/internal fail-closed paths and must not be exposed as a Plant
  existence leak.
- `can_read`
- `can_comment`
- `can_operate`
- `can_create_domain_tasks`
- `can_manage_access`
- `can_approve_actions`
- `source`: `boss_role | plant_access_grant | denied`
- `grant_id`: present only when `source=plant_access_grant`

Permission derivation:

| Role/grant state | can_read | can_comment | can_operate | can_create_domain_tasks | can_manage_access | can_approve_actions |
|---|---:|---:|---:|---:|---:|---:|
| Boss active membership | yes | yes | yes | yes | yes | yes, subject to Safety Gate |
| Engineer active PlantAccessGrant | yes | yes | yes | yes | no | grant `plant_approve_actions`, subject to Safety Gate |
| Consultant active PlantAccessGrant | yes | yes | no | no | no | no |
| Engineer/Consultant missing or revoked grant | no | no | no | no | no | no |
| Disabled account or membership | no | no | no | no | no | no |

ActorContext must be created before business logic and must be present in audit records as account/membership/role references, not as session tokens or auth material. Service endpoints `/health` and `/ready`, plus explicitly public auth endpoints such as login/bootstrap endpoints, are exceptions; exceptions must not expose Farm/Plant data or auth material.

Ownership split:

- FT-001 owns the field names above as the interface contract consumed by
  protected routes and context builders.
- FT-002 owns the concrete PlantPermissionContext resolver semantics for
  `plant_status`, `grant_id`, archived/retained-history behavior,
  PlantAccessGrant lookup, and route-level Plant denial codes.
- Before FT-002 persistence exists, FT-001 tasks may implement interface types
  and fail-closed resolver adapters or test fixtures, but must not implement
  PlantAccessGrant mutation, retained-history authorization, or archived-Plant
  lifecycle rules.
- FT-001 auth/session seams may surface `AUTH_PLANT_FORBIDDEN` for generic
  protected-route/context-builder denial. FT-002 Plant HTTP routes must surface
  `plant_not_found_or_forbidden` for the same no-existence-leak class.

## Context Builder Rules

- Context builders must use the same ActorContext and PlantPermissionContext as user-facing reads.
- Agent Chat Bus context must include `authorization_scope` derived from ActorContext, but must not include session IDs, tokens, token hashes, password hashes, invite/setup secrets, auth headers, or cookies.
- For Plant-scoped agent context, `can_read=true` is required. Consultant context may include read/comment/advisory facts but must not expose operational task creation or approval authority.
- A valid MessageEnvelope or Bus event may reference `actor_ref` and `authorization_scope`; it must never carry auth provenance fields beyond safe account/membership/role refs.

## API Surface

Feature-local route groups:

- `POST /api/session/login`
- `POST /api/session/logout`
- `GET /api/session/me`

Account creation and invite activation routes belong to FT-003. PlantAccessGrant resolution belongs to FT-002 but must be callable by ActorContext.

Route contracts:

Canonical public activation request belongs to FT-003's `POST /api/local-invites/activate`: `local_invite_id`, `activation_secret`, `password`, and optional `display_name`. FT-001 receives only the validated activation handoff plus credential/session inputs through the internal primitive below.

### Internal `activate local credential and issue session`

Purpose: provide the credential/session primitive used by FT-003's public `POST /api/local-invites/activate` route after FT-003 validates the invite credential.

Inputs from FT-003:

- `local_invite_id`
- `account_id`
- `farm_id`
- `membership_id`
- `password`
- `display_name` optional
- `transport`: `cookie | bearer`

Behavior:

- atomically sets the first local `password_hash` for the pending Account;
- activates the Account and FarmMembership;
- creates a `LocalSession` using the same server-side session model as login;
- returns session identity and `session_expires_at`;
- emits the HTTP-only same-site `Set-Cookie` session instruction for browser/PWA transport when called from the FT-003 route boundary.

Failure codes surfaced by the FT-003 route: `AUTH_ACTIVATION_INVALID`, `AUTH_ACCOUNT_DISABLED`, `AUTH_MEMBERSHIP_DISABLED`, `VALIDATION_FAILED`.

### `POST /api/session/login`

Request fields:

- `login_name`
- `password`

Success response:

- status `200`
- sets the session cookie for browser/PWA transport
- body:
  - `account_id`
  - `farm_id`
  - `membership_id`
  - `role_preset`
  - `session_expires_at`

Failure codes: `AUTH_CREDENTIAL_INVALID`, `AUTH_ACCOUNT_PENDING`, `AUTH_ACCOUNT_DISABLED`, `AUTH_MEMBERSHIP_REQUIRED`, `AUTH_MEMBERSHIP_DISABLED`, `VALIDATION_FAILED`.

`AUTH_CREDENTIAL_INVALID` must be generic and must not reveal whether the login exists.

### `POST /api/session/logout`

Request fields: none.

Success response:

- status `204`
- revokes the current session when present
- clears the session cookie for browser/PWA transport

Failure behavior:

- Missing or invalid session may still return `204` after clearing local client auth state. This route must not leak session validity.

### `GET /api/session/me`

Success response:

- status `200`
- body:
  - `account_id`
  - `display_name`
  - `farm_id`
  - `membership_id`
  - `role_preset`
  - `membership_status`
  - `session_expires_at`
  - `plant_scope_summary`: safe summary only, such as role-level all-Plant access for Boss or granted Plant IDs for Engineer/Consultant when FT-002 resolver is available

Failure codes: `AUTH_SESSION_REQUIRED`, `AUTH_SESSION_INVALID`, `AUTH_SESSION_EXPIRED`, `AUTH_ACCOUNT_DISABLED`, `AUTH_MEMBERSHIP_REQUIRED`, `AUTH_MEMBERSHIP_DISABLED`.

## Error Contract

All auth/session errors follow API Guidelines:

```json
{
  "error": {
    "code": "AUTH_SESSION_REQUIRED",
    "message": "Authentication is required.",
    "request_id": "req_..."
  }
}
```

Stable FT-001 error codes:

| Code | HTTP status | Use |
|---|---:|---|
| `AUTH_SESSION_REQUIRED` | 401 | No session credential on a protected route. |
| `AUTH_SESSION_INVALID` | 401 | Malformed, unknown, revoked, or unverifiable session. |
| `AUTH_SESSION_EXPIRED` | 401 | Session exists but `expires_at` is in the past. |
| `AUTH_CREDENTIAL_INVALID` | 401 | Login failed with generic no-leak message. |
| `AUTH_ACTIVATION_INVALID` | 401 | Invite activation credential missing, expired, used, revoked, or invalid; surfaced by FT-003's public activation route. |
| `AUTH_ACCOUNT_PENDING` | 403 | Account is not activated for normal routes. |
| `AUTH_ACCOUNT_DISABLED` | 403 | Account disabled. |
| `AUTH_MEMBERSHIP_REQUIRED` | 403 | No FarmMembership for the single local Farm. |
| `AUTH_MEMBERSHIP_DISABLED` | 403 | FarmMembership disabled or not active. |
| `AUTH_FORBIDDEN` | 403 | Role lacks authority for a non-Plant-specific operation. |
| `AUTH_PLANT_FORBIDDEN` | 404 | Generic FT-001 protected-route/context-builder Plant-scoped denial; response must not reveal whether the Plant exists. Concrete FT-002 Plant HTTP routes use `plant_not_found_or_forbidden`. |
| `VALIDATION_FAILED` | 422 | Invalid request fields without protected details. |

## Failure Rules

- Missing, expired, revoked, malformed, or unknown session fails closed.
- `pending_activation` Account cannot access normal routes except FT-003's public invite activation route.
- `disabled` Account or disabled membership fails closed.
- Missing FarmMembership fails closed.
- Missing PlantAccessGrant prevents Plant-scoped visibility for Engineer/Consultant.
- Authorization errors must not reveal unauthorized Plant existence.
- Consultant cannot create domain task/recommendation records, approve governance by default, or approve physical actions.
- Passwords, activation secrets, session tokens, token hashes, cookies, bearer tokens, and auth headers must not enter logs, audit/export, Bus, UI Feed, screenshots, or agent context.

## Migration And Indexing Targets

`TASK-005` creates only `accounts`, `farm_memberships`, and `local_sessions`
through the Foundation Alembic path. It enforces the exact relational storage
contract above and does not create `farms`, `plants`, `plant_access_grants`,
invite, or admin-audit tables.

Required indexes:

- one unique normalized `accounts.login_name` lookup;
- one unique `farm_memberships(account_id, farm_id)` lookup;
- one unique `local_sessions.token_hash` lookup;
- one non-unique `local_sessions.account_id` lookup for revocation/status checks;
- one non-unique `local_sessions.expires_at` lookup for cleanup.

The initial migration deliberately omits only the `farm_memberships.farm_id`
FK. FT-002 owns its closure after creating/reusing the single Farm authority.
No migration may create a second Farm authority, silently rewrite multiple
Farm IDs, cascade-delete authority/history, or duplicate FT-002
PlantAccessGrant rules.

## Verification

- Unit: role preset derivation and `PlantPermissionContext` rules.
- Unit: PlantPermissionContext interface field compatibility with FT-002
  resolver output, including `plant_status`, `grant_id`, `source=denied`,
  `can_comment`, and `can_create_domain_tasks`.
- Unit: account/session lifecycle and disabled-account behavior.
- Integration: FT-001 relational schema contract covers UUID identity,
  nullability/timestamps, normalized login uniqueness, status/role/auth checks,
  non-cascading Account FKs, exact indexes, and deferred Farm FK absence.
- Unit: Argon2id password hash/verify parameters, one-way behavior, and
  no-plaintext persistence.
- Unit: opaque session token generation, SHA-256 `token_hash` persistence,
  constant-time token hash comparison, and malformed-token failure.
- Unit: secret redaction in auth/session errors.
- Unit: exact FT-001 error code mapping and no-leak login/Plant authorization behavior.
- Unit: session TTL, expiry, revocation, and logout idempotence.
- Integration: login and invite activation set the exact
  `agro_intellect_session` cookie attributes for browser/PWA transport.
- Integration: logout clears the exact cookie and remains idempotent.
- Integration: every protected route has ActorContext before business logic.
- Integration: context builders enforce the same Plant authorization as user-facing reads.
- Integration: Agent Chat Bus context excludes session/auth material and unauthorized Plants.
- Integration: `GET /api/session/me` returns safe actor/session summary without secrets.
- E2E: Engineer sees only granted Plants; Consultant remains read/comment/advice only.
- E2E: pending activation cannot access Farm/Plant data until FT-003 invite activation succeeds and FT-001 issues a session.

## Non-Goals

- Enterprise identity, OAuth, password recovery, email invite delivery, SaaS tenancy, and multi-Farm membership.
- Full ACL/permission override engine beyond `plant_approve_actions`.
- Remember-me refresh tokens, device management, hosted account recovery, audit export UI, and broad personnel management.

## Handoff To /prd-to-tasks

Tasks may implement local session storage, login/logout/me routes, the internal credential activation/session issuing primitive used by FT-003, ActorContext builder, role preset policy, PlantPermissionContext interface envelope, auth error mapping, migrations for FT-001-owned records, and tests.

Tasks must not implement FT-002 Plant lifecycle, FT-002 PlantAccessGrant mutation rules, FT-003's public local invite activation route, or FT-003 admin mutation surfaces except minimal interfaces needed by ActorContext and local activation sequencing.

After this 2026-06-28 repair, `/prd-to-tasks FT-001` must refresh the existing
`TASK-005` record and canonical packet before review/execution. It must not
create a Farm table or alter `TASK-006` through `TASK-011` unless another
contract change independently requires it.

## Resolved Design Decisions

- Session transport defaults to HTTP-only same-site cookie; bearer token is optional only for explicit non-browser/LAN mode.
- Browser/PWA session cookie name is `agro_intellect_session` with
  `HttpOnly`, `SameSite=Lax`, `Path=/`, default `Max-Age=604800`, `Expires`
  aligned to `LocalSession.expires_at`, and `Secure` required outside explicit
  loopback HTTP.
- Password hashing uses Argon2id through `argon2-cffi`; session token storage
  uses only SHA-256 `token_hash` over a 256-bit opaque raw token and
  constant-time digest comparison.
- Relational IDs use PostgreSQL native UUID/Python `uuid.UUID`, generated by
  application `uuid.uuid4`; authority FKs never cascade delete.
- Login names are stored as non-empty `strip().lower()` values, guarded by a DB
  normalization check and one unique lookup on the stored normalized value.
- Status, role, and auth-method domains use string columns plus DB checks, not
  PostgreSQL native ENUM types.
- FT-001 stores required UUID `farm_memberships.farm_id` without a FK; FT-002
  creates/reuses the single Farm authority and adds the final `RESTRICT` FK.
- Public invite activation is owned only by FT-003 as `POST /api/local-invites/activate`; FT-001 exposes only the internal credential/session primitive it calls.
- Default session TTL is 7 days; no refresh-token mechanism in MVP.
- `Account` status is `pending_activation | active | disabled`.
- `FarmMembership` status is `invited | active | disabled`.
- `LocalSession` validity is computed fail-closed from session, account, and membership state.
- `PlantPermissionContext` has explicit read/comment/operate/task/manage/approve
  booleans plus `plant_status`, `source`, and optional `grant_id`; FT-002 owns
  concrete resolver values.
- Boss can approve actions only as actor authority and still needs Safety Gate; Engineer needs `plant_approve_actions`; Consultant never approves physical actions.
- Unauthorized Plant access through FT-001 generic protected seams returns
  `AUTH_PLANT_FORBIDDEN` as 404; concrete FT-002 Plant routes return
  `plant_not_found_or_forbidden` for the same no-existence-leak class.
- Auth/session material is forbidden from audit/export, Bus, UI Feed, screenshots, and agent context.

## Open Questions

None for FT-001 task decomposition. Any future need for hosted identity, recovery, multi-Farm membership, refresh tokens, or a general permission matrix must route to a later global spec, not FT-001 tasks.
