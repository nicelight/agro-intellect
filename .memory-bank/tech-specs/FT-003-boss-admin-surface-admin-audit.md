---
description: Feature SDD design for FT-003 Boss Admin Surface And Admin Audit.
status: active
owner: architecture
type: feature_design
feature_id: FT-003
last_updated: 2026-06-29
source_of_truth:
  - .memory-bank/features/FT-003-boss-admin-surface-admin-audit.md
  - .memory-bank/foundation.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/domains/local-identity-session-data.md
  - .memory-bank/contracts/local-session-security.md
  - .memory-bank/contracts/local-session-api.md
  - .memory-bank/contracts/actor-context.md
  - .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md
---
# FT-003 Boss Admin Surface And Admin Audit

## Purpose

Define the minimum Boss admin workflow and durable admin audit boundary for local personnel, role, Plant, and Plant access administration.

## Normative Inputs

- [.memory-bank/spec-backbone.md](../spec-backbone.md): global backbone is complete.
- [.memory-bank/foundation.md](../foundation.md): verified Foundation baseline for admin package anchors, route include pattern, DB migrations/session helpers, and redaction.
- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md): Access & Admin module.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): AdminAuditRecord authority.
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md): admin API guardrails.
- [.memory-bank/domains/local-identity-session-data.md](../domains/local-identity-session-data.md): Account, FarmMembership, and LocalSession storage contract.
- [.memory-bank/contracts/local-session-security.md](../contracts/local-session-security.md): credential/session primitives and transport used after invite validation.
- [.memory-bank/contracts/local-session-api.md](../contracts/local-session-api.md): internal credential activation handoff and auth/session errors.
- [.memory-bank/contracts/actor-context.md](../contracts/actor-context.md): role and ActorContext authorization contract.
- [.memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md](FT-002-farm-plant-lifecycle-access-grants.md): Plant and PlantAccessGrant design.
- [.memory-bank/requirements.md](../requirements.md): REQ-003, REQ-005, REQ-021, REQ-022.

## Design Depth

Feature hub only. Admin UI/API/audit is feature-local but depends on FT-001 and FT-002 contracts.

Feature-relevant global contracts are already decided:

| Area | Decision for FT-003 |
|---|---|
| Runtime authority | PostgreSQL/read model owns Account, FarmMembership, Plant, PlantAccessGrant, and AdminAuditRecord state. |
| HTTP API | FastAPI/Pydantic-style JSON routes under admin/local-invite/Plant groups; generated OpenAPI comes from implementation schemas later. |
| ActorContext/authz | Every admin read/mutation resolves ActorContext before business logic; Boss role is required for admin mutations and admin audit read. |
| Agent Chat Bus | Not applicable for admin notices/audit text; FT-003 does not publish admin UI text or audit display strings as agent-consumable Bus facts. |
| MessageEnvelope | Not applicable; FT-003 has no agent-originated output. |

## Admin Scope

Boss Admin Surface owns:

- personnel list;
- local-only account add/invite;
- role preset assignment;
- Plant list and Plant lifecycle controls from FT-002;
- PlantAccessGrant management from FT-002;
- durable admin audit records;
- minimal admin audit view.

Advanced admin dashboard, full role matrix editor, hosted invite delivery, password recovery, and enterprise identity are out of MVP.

## Data Model Additions

FT-003 uses FT-001 `Account` and `FarmMembership` plus FT-002 `Plant` and `PlantAccessGrant` records. It adds only the invite/audit records needed for local admin workflows.

`LocalInviteCredential`:

- `local_invite_id`
- `farm_id`
- `account_id`
- `membership_id`
- `invite_status`: `pending | accepted | revoked | expired`
- `activation_secret_hash`
- `created_by_account_id`
- `created_at`
- `expires_at`
- `accepted_at`
- `revoked_by_account_id`, `revoked_at`

Rules:

- The plaintext activation secret is shown only once to the Boss at creation.
- Only `activation_secret_hash` is stored.
- `expires_at` is required; MVP default is 7 days unless implementation config chooses a shorter local default.
- Expired invites cannot activate an account and may be marked `expired` lazily during validation.
- `LocalInviteCredential` is local-only and never implies email delivery, hosted recovery, or SaaS tenancy.

## Local Add / Invite Lifecycle

Use a local-only invite flow:

```text
Boss creates local invite -> Account pending_activation + FarmMembership invited + LocalInviteCredential pending
Invite setup accepted locally -> Account active + FarmMembership active + LocalInviteCredential accepted
Boss revokes invite before acceptance -> LocalInviteCredential revoked + Account disabled + FarmMembership disabled
Boss disables active user -> Account disabled and/or FarmMembership disabled
```

Rules:

- No email delivery.
- No hosted recovery.
- No SaaS tenancy.
- Invite code/temporary credential is shown only to Boss at creation time and must not be logged or audited in plaintext.
- Pending accounts cannot use normal Farm/Plant routes.
- Invite acceptance resolves a constrained activation ActorContext from the valid invite credential: target Account, invited FarmMembership, target Farm, `session_auth_method=local_invite_activation`, and no Plant permissions.
- Activation creates the user's first local password credential through FT-001 and then follows FT-001 session issuing semantics.
- Boss cannot disable or demote the last active Boss membership in the single local Farm.

## Invite Activation Boundary With FT-001

FT-003 owns the local invite/add workflow and the only public invite activation endpoint: `POST /api/local-invites/activate`.

FT-001 owns the Account/FarmMembership credential primitive and session issuing semantics called by that endpoint. FT-003 must not define a second session activation route, and FT-001 must not expose a public invite activation route.

Canonical activation request:

- `local_invite_id`
- `activation_secret`
- `password`
- `display_name` optional

Activation success:

- validates the `LocalInviteCredential` by `local_invite_id` plus plaintext `activation_secret`;
- marks `LocalInviteCredential` as `accepted`;
- activates the target FT-001 Account and FarmMembership;
- stores the first local password credential through FT-001;
- issues a FT-001 `LocalSession`;
- uses FT-001 browser/PWA default session transport by setting the HTTP-only same-site `Set-Cookie` session header;
- returns `session_expires_at` in the response body.

Bearer token response is allowed only for explicit non-browser/LAN mode under FT-001 session transport rules. It is not the default browser/PWA activation path.

Activation failure uses the shared FT-001 auth/session error code `AUTH_ACTIVATION_INVALID` for missing, expired, used, revoked, or invalid invite credentials, plus `AUTH_ACCOUNT_DISABLED`, `AUTH_MEMBERSHIP_DISABLED`, and `VALIDATION_FAILED` where applicable. Do not introduce duplicate invite-invalid error names for the same failure class.

## AdminAuditRecord

Admin audit is durable runtime state in PostgreSQL/read model. It may be referenced by timeline/export later, but the audit record is the admin audit authority.

Minimum fields:

- `admin_audit_id`
- `farm_id`
- `actor_account_id`
- `actor_membership_id`
- `actor_role_preset`
- `action_type`
- `target_type`
- `target_id`
- `plant_id` when relevant
- `request_id`
- `before_summary`
- `after_summary`
- `source_refs`
- `created_at`

Sensitive values must be redacted. Never store passwords, invite codes, session tokens, token hashes, auth headers, `.env` values, API keys, or provider secrets in admin audit.

Audit summaries must be compact structured JSON, not UI copy. They may include safe ids, display names, role/status values, Plant ids, and boolean permission values. They must not include free-form admin notes unless those notes have passed the same redaction policy.

## Audited Action Types

Admin audit must record:

- `local_invite_created`
- `local_invite_revoked`
- `local_invite_accepted`
- `account_disabled`
- `membership_role_changed`
- `membership_disabled`
- `plant_created`
- `plant_archived`
- `plant_restored`
- `plant_access_granted`
- `plant_access_updated`
- `plant_access_revoked`
- `plant_approve_actions_changed`

Allowed `target_type` values are `account`, `membership`, `local_invite`, `plant`, and `plant_access_grant`.

Audit write semantics:

- Successful admin mutations write exactly one AdminAuditRecord in the same database transaction as the state change.
- Failed validation, failed authorization, and failed persistence do not create a misleading success audit record.
- Idempotent retry behavior is task-level, but duplicate active PlantAccessGrant and duplicate pending invite creation for the same login must fail validation unless the implementation explicitly revokes/replaces the old pending invite in the same transaction and audits that transition.
- Plant lifecycle and PlantAccessGrant mutations may live in FT-002 services, but they must call the FT-003 audit writer when admin audit is available.

## API Surface

Feature-local route groups:

| Route | Authz | Request | Response |
|---|---|---|---|
| `GET /api/admin/accounts` | Boss | Optional `status`, `role_preset` filters. | Account and FarmMembership summaries with redacted auth fields. |
| `POST /api/admin/accounts/local-invite` | Boss | `login_name`, `display_name`, `role_preset`, optional initial `plant_grants[]`. | Account summary, membership summary, `local_invite_id`, one-time plaintext activation secret. |
| `POST /api/admin/accounts/{account_id}/disable` | Boss | Optional safe `reason`. | Disabled account/membership summary. |
| `PATCH /api/admin/memberships/{membership_id}/role` | Boss | `role_preset`. | Updated membership summary. |
| `POST /api/local-invites/activate` | Valid local invite credential | `local_invite_id`, `activation_secret`, `password`, optional `display_name`. | Activated account/membership summary, `session_expires_at`, and FT-001 `Set-Cookie` session header by default; no admin privileges beyond resulting role/session rules. |
| `GET /api/admin/plants` | Boss | Optional `include_archived`. | Plant summaries including active/archived status and grant counts. |
| `GET /api/admin/audit` | Boss | Optional `limit`, `cursor`, `target_type`, `target_id`, `plant_id`. | Reverse-chronological safe audit summaries plus next cursor. |

Plant lifecycle and PlantAccessGrant mutations may reuse FT-002 route groups but must be exposed through Boss Admin UI and must write AdminAuditRecord.

Admin route responses must never return password hashes, session token hashes, activation secret hashes, auth headers, or raw secret material. The only exception is the one-time plaintext activation secret returned by `POST /api/admin/accounts/local-invite`; it must not be retrievable later.

## Authorization Policy

- Boss role in an active FarmMembership is required for admin read and mutation routes.
- Engineer and Consultant cannot access admin mutation routes or admin audit read.
- Invite activation is the only non-health FT-003 route that may run without an active session; it must resolve the constrained activation ActorContext described above and then call FT-001's internal credential/session primitive.
- Role changes cannot grant Consultant task/recommendation/physical-action approval authority.
- `plant_approve_actions` remains a PlantAccessGrant boolean and does not bypass Safety Gate.
- Admin audit read exposes only safe summaries and must not leak secrets or unauthorized Plant data.

## UI Surface

Minimum first-demo admin UI:

- personnel list;
- create local Engineer invite/account;
- assign role preset;
- Plant list including `tomato_001`;
- grant/revoke Plant access and toggle `plant_approve_actions`;
- admin audit list with timestamp, actor, action, target, and safe summary.

Frontend UI is presentation only. Backend authz and audit writes are authoritative.
Admin UI success/error notices are UI Feed-style presentation only and must not enter Agent Chat Bus, MessageEnvelope, agent context builders, timeline replay as mutable state, or Plant facts.

## Failure Rules

- Non-Boss actor cannot access admin mutation routes.
- Consultant cannot gain task/recommendation/approval authority through admin UI.
- Admin UI notices and audit display text do not become agent facts.
- Failed mutations must not create misleading success audit.
- Secret values are redacted from all admin audit and error surfaces.
- Admin mutations cannot leave the local Farm without at least one active Boss membership.
- Missing, used, revoked, expired, or invalid invites cannot activate an account and surface as `AUTH_ACTIVATION_INVALID`.
- Invite activation cannot create access beyond the invited FarmMembership and explicit PlantAccessGrant records.

## Verification

- Unit: Boss-only admin mutation policy.
- Unit: local invite status transitions and secret redaction.
- Unit: last-active-Boss guard.
- Integration: every audited mutation writes exactly one durable AdminAuditRecord after success.
- Integration: `POST /api/local-invites/activate` uses constrained activation ActorContext, activates Account/FarmMembership through FT-001, issues the FT-001 browser/PWA `Set-Cookie` session header plus `session_expires_at`, and does not allow normal Farm/Plant access until activation succeeds.
- Integration: PlantAccessGrant changes affect Plant visibility and ActorContext permission resolver.
- Integration: admin notices/audit display text are excluded from agent context fixtures.
- E2E: Boss creates Engineer, assigns role, grants `tomato_001`, toggles `plant_approve_actions`, and sees admin audit entry.

## Non-Goals

- Hosted invites, email delivery, password recovery, enterprise identity, SaaS tenancy.
- Broad HR/personnel management.
- Complex audit search/export beyond minimal admin audit view.
- Full Consultant UI path for first demo.

## Handoff To /prd-to-tasks

Tasks may implement Boss admin UI/API slices, local invite/account creation and activation, role assignment, Plant/access admin wrappers, AdminAuditRecord persistence, audit list view, and tests. They must use FT-001 and FT-002 contracts instead of redefining Account, session, Plant, or PlantAccessGrant semantics.

No shared/global spec update is required by this feature-local design itself. The integrator should add this feature design to the shared spec registry when registry edits are allowed.
