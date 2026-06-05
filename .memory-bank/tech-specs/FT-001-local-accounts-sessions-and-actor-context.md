---
description: Feature-local SDD tech spec for FT-001 local Accounts, sessions, FarmMembership, role presets, and ActorContext.
status: active
feature_id: FT-001
owner: spec-improve
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/features/FT-001-local-accounts-sessions-and-actor-context.md
  - .memory-bank/requirements.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/states/core-lifecycles.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/agent-harness.md
---
# FT-001 Local Accounts, Sessions, And ActorContext Tech Spec

## Purpose

Define the minimum feature-local design needed before task decomposition for local
Accounts, local sessions, role presets, FarmMembership, ActorContext resolution, audit
attribution, and secret redaction.

This spec refines the global backbone. It does not replace the global authority rules in
[.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md),
[.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md),
[.memory-bank/states/core-lifecycles.md](../states/core-lifecycles.md), or
[.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md).

## Scope

In scope:

- local Account records for login/session, authorization, attribution, and audit;
- one local Farm membership per Account in the single MVP Farm;
- Boss, Engineer, and Consultant role presets;
- local session baseline with opaque auth material;
- ActorContext resolution for protected API routes, context-builder paths, tasks,
  approvals, and audit records;
- redaction of session/token/auth material from forbidden surfaces.

Out of scope:

- hosted identity, email delivery, hosted recovery, SaaS tenancy, OAuth/SAML, billing,
  or multi-Farm membership;
- separate authorization logic in the frontend;
- physical-action approval semantics beyond carrying ActorContext into Safety Gate
  features.

## Data Ownership

PostgreSQL/read model is the mutable authority for:

- `Account`;
- `Farm`;
- `FarmMembership`;
- local session records or session state;
- ActorContext-derived audit attribution;
- security traces that store only redacted refs.

Admin/audit records may reference access/session events but must not contain raw
session IDs, tokens, passwords, API keys, `.env` values, credentials, or auth material.

## Local Account And Membership Shape

Minimum `Account` semantics:

- stable `account_id`;
- human label/display name;
- local login identifier;
- lifecycle status: `active`, `invited`, or `disabled`;
- created/updated audit attribution;
- no raw password, token, reset secret, API key, or credential value in logs, timeline,
  Bus, UI Feed, screenshots, exports, manifests, or agent context.

Minimum `FarmMembership` semantics:

- stable `membership_id`;
- `account_id`;
- single MVP `farm_id`;
- role preset: `boss`, `engineer`, or `consultant`;
- lifecycle status: `active`, `invited`, `disabled`, or `removed`;
- audit refs for create, role change, disable/remove, and restore-like reactivation if
  allowed by implementation.

MVP has exactly one active local Farm. Multi-Farm membership is forbidden.

## Role Presets

Role presets are coarse and intentionally small:

| Role | Baseline Authority |
|---|---|
| `boss` | Manage local Accounts, FarmMembership, role presets, Plant lifecycle, PlantAccessGrant, and admin audit. May approve physical-action proposals only through Safety Gate rules. |
| `engineer` | Operate granted Plants: select Plant, check in, upload photos, record observations/measurements, and work allowed tasks/follow-up. May approve physical actions only when PlantAccessGrant has `plant_approve_actions=true`. |
| `consultant` | Read/comment/advisory access for granted Plants. No admin authority and no physical-action approval authority in MVP. |

`plant_approve_actions` is the only MVP per-permission override. Do not add a broad
custom permission system in this feature.

## Session Semantics

Sessions use opaque auth material controlled by the backend. Feature tasks may choose
the exact secure cookie/header mechanism, but the design requirements are fixed:

- missing, expired, malformed, revoked, or invalid session resolves to
  `ActorContext.state=denied` or `expired` and fails closed;
- disabled Account or disabled/removed FarmMembership fails closed;
- session provenance may be stored as redacted refs or hashes for audit;
- raw auth material is never persisted into product logs, timeline, manifests, Bus, UI
  Feed, screenshots, exports, traces visible to agents, or agent context;
- session expiry/revocation must not leave a reusable approval or context-builder
  capability.

## ActorContext Shape

Every protected route and every agent context-builder path resolves ActorContext before
reading or mutating Farm/Plant data.

Minimum ActorContext fields:

```yaml
state: resolved | denied | expired
account_id: string
farm_id: string
membership_id: string
role: boss | engineer | consultant
membership_status: active | invited | disabled | removed
plant_permissions:
  - plant_id: string
    grant_state: granted | revoked
    can_view: boolean
    can_work: boolean
    plant_approve_actions: boolean
session_ref: redacted string
auth_provenance_ref: redacted string
request_ref: redacted string
resolved_at: datetime
```

Denied/expired contexts must carry only safe diagnostic refs and must not disclose
private record existence beyond the caller's allowed scope.

## Enforcement Pattern

- Backend authorization is authority; frontend visibility is presentation only.
- Resolve ActorContext once at the API/service boundary, then pass the resolved context
  into domain services and context builder calls.
- Re-check PlantAccessGrant for Plant-scoped reads/mutations and context retrieval.
- Admin mutations require `role=boss`.
- Mutations record actor attribution and audit refs.
- Unauthorized access returns the global error envelope from
  [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md) with a
  safe `permission_denied`, `invalid_session`, or `not_found` style response.
- Do not leak whether unauthorized Plant/Farm records exist.

## API Surface To Refine In Tasks

Task decomposition may define exact FastAPI/Pydantic schemas for:

- local login/session create and revoke;
- current ActorContext lookup;
- local Account create/disable;
- FarmMembership role assignment and state changes;
- authorized Plant list derived from ActorContext and PlantAccessGrant;
- admin audit list filtered by Boss authority.

The generated OpenAPI artifact is produced from implementation schemas later. Do not
hand-write a broad OpenAPI file in this spec.

## Agent Harness And Context Boundary

ActorContext is mandatory input to every permission-aware context build. The context
builder must filter by Account, Farm, role, PlantAccessGrant, AgentProfile, evidence
refs, trust/freshness labels, and redaction policy.

Following `agents-best-practices`, the model never decides access. The harness and
backend permission engine own context visibility, tool visibility, permission decisions,
structured observations, trace refs, and approval pauses. Tool/permission traces may
store redacted argument hashes and ActorContext refs, but not auth material.

## Verification Targets

Required tests before FT-001 can be considered implemented:

- missing/invalid/expired session fails closed;
- disabled Account cannot access Farm/Plant routes or context-builder paths;
- disabled/removed FarmMembership cannot access Farm/Plant data;
- role preset matrix blocks non-Boss admin mutation;
- ActorContext is present for every protected route class and context-builder path;
- frontend-hidden controls are not relied on as authorization;
- session/token/auth material is redacted from logs, timeline, manifests, Bus, UI Feed,
  screenshots, exports, traces visible to agents, and agent context;
- generated OpenAPI validation after implementation schemas exist.

## Open Questions

No blocker for `/prd-to-tasks FT-001`. Exact password/session storage mechanism,
password policy, cookie/header choice, and endpoint names can be decided during task
decomposition as long as this spec's authz, audit, and redaction constraints hold.
