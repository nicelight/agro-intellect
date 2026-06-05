---
description: Feature-local SDD tech spec for FT-003 Boss Admin Surface, admin mutations, and AdminAuditRecord.
status: active
feature_id: FT-003
owner: spec-improve
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/features/FT-003-boss-admin-surface-and-admin-audit.md
  - .memory-bank/requirements.md
  - .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
  - .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
  - .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/states/core-lifecycles.md
  - .memory-bank/contracts/api-guidelines.md
---
# FT-003 Boss Admin Surface And Admin Audit Tech Spec

## Purpose

Define the minimum feature-local design needed before task decomposition for the Boss
Admin Surface, local personnel/account administration, role assignment, Plant lifecycle
entry points, PlantAccessGrant management, durable `AdminAuditRecord`, and minimal audit
view.

This spec refines the global backbone and depends on FT-001 for ActorContext/session
rules, FT-002 for Farm/Plant/PlantAccessGrant rules, and FT-017 for privacy/redaction.

## Scope

In scope:

- Boss-only admin UI/API commands for personnel list and local account add/invite;
- role assignment through MVP presets: `boss`, `engineer`, `consultant`;
- Plant create/archive/restore command entry points using FT-002 lifecycle rules;
- PlantAccessGrant grant/revoke/update, including `plant_approve_actions`;
- durable `AdminAuditRecord` creation for every successful admin mutation;
- minimal admin audit read view filtered to Boss authority.

Out of scope:

- email delivery, hosted invites, hosted recovery, SaaS tenancy, enterprise identity,
  billing, or multi-Farm administration;
- broad custom permission matrix beyond role presets and `plant_approve_actions`;
- Safety Gate approval, Plant state facts, agent memory content, or physical-action
  task unlocks.

## Authority And Authorization

PostgreSQL/read model is mutable authority for Accounts, FarmMembership, Plant lifecycle,
PlantAccessGrant, and AdminAuditRecord. Admin UI rows, notices, markdown, logs, timeline
refs, and exports are not authority.

Admin mutations must:

1. resolve ActorContext;
2. require `role=boss` with active Account and FarmMembership;
3. remain scoped to the single local Farm;
4. validate the target Account, membership, Plant, or grant inside that Farm;
5. perform the state change through the owning Access & Admin or Plant lifecycle
   service;
6. create an `AdminAuditRecord` in the same logical command boundary;
7. return bounded refs and safe error envelopes.

Non-Boss users, disabled memberships, invalid sessions, or cross-Farm-like identifiers
fail closed. Frontend hide/show is presentation only.

## Admin Surface Workflows

Minimum first-MVP admin workflows:

- list personnel with role and membership status;
- add or invite a local Account without external email delivery;
- change a FarmMembership role preset;
- disable/remove or reactivate membership when supported by FT-001 tasks;
- list active and archived Plants;
- create Plant;
- archive Plant;
- restore Plant;
- grant/revoke/update PlantAccessGrant for an Account or membership;
- view recent admin audit records.

The first demo may keep screen grouping simple, but it must not omit durable audit for
implemented admin mutations.

## Local Add/Invite Semantics

Local-only add/invite means the backend creates local Account and membership records
sufficient for login/session setup and audit attribution. It must not imply email
delivery, cloud invitation, hosted recovery, or remote account service availability.

If implementation distinguishes `add` from `invite`, both remain local records and both
must be auditable. Raw temporary credentials, reset material, tokens, or session data
must not enter AdminAuditRecord, timeline, logs, screenshots, exports, Bus, UI Feed, or
agent context.

## AdminAuditRecord

Minimum semantics:

```yaml
admin_audit_id: string
farm_id: string
actor_ref: string
actor_role: boss
action_type: account_added | account_invited | account_disabled | membership_role_changed | membership_disabled | membership_removed | plant_created | plant_archived | plant_restored | plant_access_granted | plant_access_revoked | plant_access_updated
target_type: account | farm_membership | plant | plant_access_grant
target_ref: string
secondary_refs: []
before_summary: object | null
after_summary: object | null
reason: string | null
request_ref: redacted string
created_at: datetime
redaction_status: redacted | no_sensitive_fields
```

Rules:

- summaries contain only non-secret, bounded, structured fields needed to understand
  the change;
- before/after summaries may include role, membership status, Plant state, grant state,
  and `plant_approve_actions`;
- summaries must not include raw auth/session material, credentials, `.env` values,
  provider API keys, hidden reasoning, UI markdown, or raw chat;
- AdminAuditRecord may reference timeline/export events, but timeline replay cannot
  replace the durable admin audit record;
- archived Plants retain related admin audit records for authorized admin/history view.

## Agent And Context Boundary

Admin UI content is human presentation and is not agent working context. If future agent
runs need admin-derived facts, they must retrieve approved domain records through the
permission-aware context builder under ActorContext and PlantAccessGrant filtering, not
from admin UI notices or audit-view markdown.

Following `agents-best-practices`, identity/access changes are privileged admin actions:
the model must not approve or execute them directly. Any future agent-visible admin
tool must be narrow, typed, schema-validated, permissioned as `privileged_admin` or
`identity_access`, and audited with redacted argument refs.

## API Surface To Refine In Tasks

Task decomposition may define exact FastAPI/Pydantic schemas for:

- `GET` personnel list;
- local Account add/invite;
- membership role/status change;
- Plant create/archive/restore command endpoints;
- PlantAccessGrant grant/revoke/update;
- admin audit list/detail with pagination and scoped filters.

Generated OpenAPI comes from implementation schemas later.

## Verification Targets

Required tests before FT-003 can be considered implemented:

- non-Boss admin mutations are denied by backend authorization;
- disabled/expired ActorContext fails closed;
- local account add/invite does not imply email, hosted recovery, SaaS tenancy, or
  server account service;
- role assignment uses only MVP role presets;
- Plant lifecycle and PlantAccessGrant mutations obey FT-002 rules;
- every successful admin mutation creates an AdminAuditRecord;
- failed mutations do not create misleading successful audit records;
- audit records are retained after Plant archive and visible only to authorized Boss
  admin/history views;
- audit payloads redact secrets/auth material and exclude UI markdown/raw chat;
- admin authority cannot bypass Safety Gate or physical-action approval rules.

## Open Questions

No blocker for `/prd-to-tasks FT-003`. Exact screen grouping, route names, pagination
defaults, and local credential setup UX can be decided during task decomposition while
preserving Boss-only authorization, durable audit, local-only identity, and redaction.
