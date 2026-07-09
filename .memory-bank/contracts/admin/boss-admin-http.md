---
description: Boss-only direct local Account creation, personnel, role, Plant projection, and admin-audit HTTP contract.
status: active
type: api_contract
last_updated: 2026-07-09
source_of_truth:
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/contracts/auth/session-security.md
  - .memory-bank/domains/admin/admin-audit.md
  - .memory-bank/runbooks/first-boss-local-bootstrap.md
---
# Boss Admin HTTP

## Scope

Defines the minimum Boss admin API for personnel, direct local Account creation,
disable/role operations, Plant projection, and safe audit read.

## Routes

| Route | Request | Response |
|---|---|---|
| `GET /api/admin/accounts` | optional `status`, `role_preset` | safe Account/Membership summaries |
| `POST /api/admin/accounts` | `login_name`, `display_name`, `password`, `role_preset` | safe active Account/Membership summaries |
| `POST /api/admin/accounts/{account_id}/disable` | optional safe `reason` | disabled identity summary |
| `PATCH /api/admin/memberships/{membership_id}/role` | `role_preset` | membership summary |
| `GET /api/admin/plants` | optional `include_archived` | Plant summaries and grant counts |
| `GET /api/admin/audit` | optional `limit`, `cursor`, `target_type`, `target_id`, `plant_id` | reverse-chronological safe summaries and next cursor |

Plant lifecycle/access mutations use the Plant HTTP contract but are exposed
by the Boss surface and must write the shared audit record.

## Common response shapes

`AdminAccountSummary`:

- `account_id`, `login_name`, `display_name`;
- `account_status: active|disabled`;
- nullable `disabled_at`;
- `created_at`, `updated_at`;
- `membership`: `AdminMembershipSummary`.

`AdminMembershipSummary`:

- `membership_id`, `account_id`, `farm_id`;
- `role_preset: boss|engineer|consultant`;
- `membership_status: active|disabled`;
- nullable `disabled_at`;
- `created_at`, `updated_at`.

`AdminPlantProjection`:

- `plant_id`, `farm_id`, `plant_key`, `display_name`;
- `status: active|archived`;
- `created_at`, `updated_at`;
- `grant_counts`: object with `active`, `revoked`, and
  `approve_actions_enabled` integer counts.

`AdminAuditSummary`:

- `admin_audit_id`, `farm_id`, `actor_kind`, nullable actor refs,
  `actor_role_preset`, `action_type`, `target_type`, `target_id`,
  nullable `plant_id`, `request_id`, `before_summary`, `after_summary`,
  `source_refs`, and `created_at`;
- summaries and source refs are the safe structured data defined by the
  Admin Audit spec, not UI copy.

List responses use `{items: [...]}`. Audit list responses also include
`next_cursor`, nullable string. Cursor format is opaque to clients; the
implementation may encode `(created_at, admin_audit_id)` but must not expose
secrets or raw SQL state.

All admin responses exclude password input, password hashes, session tokens,
token hashes, cookies, auth headers, and raw DB/provider errors. Protected
responses set `Cache-Control: no-store`.

## Request and validation rules

- `GET /api/admin/accounts` supports `status=active|disabled` and
  `role_preset=boss|engineer|consultant`; unknown values fail validation.
- `POST /api/admin/accounts` requires `login_name`, `display_name`,
  `password`, and `role_preset`. Unknown fields fail validation.
- `login_name` is normalized through the Account storage contract before
  uniqueness checks and persistence.
- `display_name` is trimmed and must remain non-empty.
- `password` is accepted only for the create request, immediately hashed
  through the Session Security contract, and never returned.
- `POST /api/admin/accounts/{account_id}/disable` accepts only an optional safe
  `reason`; the reason is redacted before audit use and may be omitted.
- `PATCH /api/admin/memberships/{membership_id}/role` requires one
  `role_preset` value and must not change Account credentials or session rows.
- `GET /api/admin/plants` supports `include_archived=false|true`; default is
  false.
- `GET /api/admin/audit` supports `limit` (default 50, max 100), `cursor`,
  `target_type`, `target_id`, and `plant_id`.

Successful Account creation, account disable, and membership-role changes
MUST also write exactly one same-transaction AdminAuditRecord using the action
taxonomy in the admin-audit spec. Failed mutations write none. Plant grants are
a separate later FT-002 flow and are not part of the required Account creation
transaction.

`POST /api/admin/accounts` validates active Boss ActorContext, normalized login,
role, and Farm; hashes the initial password through the Argon2id security
contract; then atomically creates an active Account, active FarmMembership, and
exactly one `account_created` audit record. Any failure rolls back all three.
The local MVP trust model allows Boss to know the initial password and does not
require a first-login password change.

## Error catalog

All errors use the global `{error:{code,message,request_id}}` envelope with
safe text.

| Code | HTTP | Use |
|---|---:|---|
| existing `AUTH_*` codes | existing mapping | Session/account/membership failures and non-Boss denial through the ActorContext/session boundary. |
| `ADMIN_ACCOUNT_NOT_FOUND` | 404 | Account route target does not exist in the local Farm admin scope. |
| `ADMIN_MEMBERSHIP_NOT_FOUND` | 404 | Membership route target does not exist in the local Farm admin scope. |
| `ADMIN_ACCOUNT_CONFLICT` | 409 | Normalized login already exists. |
| `ADMIN_LAST_BOSS_CONFLICT` | 409 | Request would disable or demote the last active Boss membership. |
| `ADMIN_AUDIT_CURSOR_INVALID` | 422 | Audit cursor cannot be decoded as the supported opaque cursor. |
| `ADMIN_PERSISTENCE_FAILED` | 500 | Transaction rolled back because of an unclassified persistence failure. |
| `VALIDATION_FAILED` | 422 | Malformed UUID/body/query, blank display name, invalid role/status/filter, unknown field, or unsafe payload. |

Unexpected DB exceptions, integrity details, SQL text, DSNs, password material,
and raw exception messages are never returned. A duplicate normalized login may
map to `ADMIN_ACCOUNT_CONFLICT` only when the service positively identifies the
known account-login uniqueness conflict; unrelated persistence failures remain
`ADMIN_PERSISTENCE_FAILED`.

## Authorization and safety

- Active Boss membership is required for all admin reads/mutations.
- Engineer/Consultant cannot mutate admin state or read admin audit.
- Last-active-Boss cannot be disabled or demoted.
- Role changes cannot grant Consultant task/governance/action authority.
- `plant_approve_actions` does not bypass Safety Gate.
- The initial password is accepted only in the create request, immediately
  hashed, and never returned. Responses never return password/session hashes,
  auth headers, cookies, or raw secrets.
- Password material never enters logs, audit, timeline, Bus, UI Feed,
  screenshots, exports, or agent context.

## Presentation boundary

Minimum UI composition is personnel, direct Engineer creation, role, Plant list,
access/grant flag controls, and audit list. UI notices are presentation only:
they do not enter Agent Chat Bus, MessageEnvelope, agent context, timeline as
mutable state, or Plant facts. Backend authz and transactional audit are
authoritative.

## Verification

- Contract tests cover filters, safe response fields, Boss-only access,
  password exclusion, last-Boss protection, and audit pagination.
- Integration proves Plant/access wrappers use canonical Plant semantics and
  exactly-one audit writes.
- OpenAPI tests cover admin paths, request bodies, response models, UUIDs,
  timestamps, enums, cursor query fields, and documented error responses.
- Failure-injection tests distinguish duplicate-login conflicts from unrelated
  persistence failures and prove both paths roll back without raw exception or
  credential leakage.

## First Boss bootstrap boundary

The Boss-only API cannot create the first Boss. FT-002 defines the prerequisite
canonical Farm/`tomato_001` bootstrap. FT-003 must define one local one-shot CLI
that reads the password through `getpass`
(not argv/env), creates the first active Boss membership after the single Farm
exists, writes `account_created` with system/bootstrap provenance, and refuses
to run once an active Boss exists. The exact command, inputs, sequencing,
diagnostics, and verification are defined by the First Boss Local Bootstrap
runbook. No parallel bootstrap mechanism is introduced here.

## Related specs

- [.memory-bank/contracts/auth/session-security.md](../auth/session-security.md)
- [.memory-bank/domains/admin/admin-audit.md](../../domains/admin/admin-audit.md)
- [.memory-bank/contracts/access/actor-context.md](../access/actor-context.md)
- [.memory-bank/runbooks/first-boss-local-bootstrap.md](../../runbooks/first-boss-local-bootstrap.md)
