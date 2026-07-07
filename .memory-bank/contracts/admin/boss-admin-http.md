---
description: Boss-only direct local Account creation, personnel, role, Plant projection, and admin-audit HTTP contract.
status: active
type: api_contract
last_updated: 2026-06-30
source_of_truth:
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/contracts/auth/session-security.md
  - .memory-bank/domains/admin/admin-audit.md
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

## First Boss bootstrap boundary

The Boss-only API cannot create the first Boss. FT-002 defines the prerequisite
canonical Farm/`tomato_001` bootstrap. FT-003 must define one local one-shot CLI
that reads the password through `getpass`
(not argv/env), creates the first active Boss membership after the single Farm
exists, writes `account_created` with system/bootstrap provenance, and refuses
to run once an active Boss exists. Exact CLI commands and storage sequencing are
deferred; no parallel bootstrap mechanism is introduced here.

## Related specs

- [.memory-bank/contracts/auth/session-security.md](../auth/session-security.md)
- [.memory-bank/domains/admin/admin-audit.md](../../domains/admin/admin-audit.md)
- [.memory-bank/contracts/access/actor-context.md](../access/actor-context.md)
