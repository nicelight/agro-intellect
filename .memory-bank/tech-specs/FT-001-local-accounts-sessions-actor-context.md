---
description: Feature design hub for FT-001 Local Accounts Sessions And ActorContext.
status: active
owner: architecture
type: feature_design
feature_id: FT-001
last_updated: 2026-06-29
source_of_truth:
  - .memory-bank/features/FT-001-local-accounts-sessions-actor-context.md
  - .memory-bank/domains/local-identity-session-data.md
  - .memory-bank/contracts/local-session-security.md
  - .memory-bank/contracts/local-session-api.md
  - .memory-bank/contracts/actor-context.md
  - .memory-bank/testing/ft-001-access-auth.md
---
# FT-001 Local Accounts Sessions And ActorContext

## Purpose

Route implementers and reviewers to the atomic specifications that define the
local identity, session, role, and ActorContext boundary used by every
Farm/Plant route, domain service, audit writer, and agent/context builder.

This path remains the stable feature-design hub for compatibility with existing
task records, packets, plans, and adjacent feature specs. It is not a second
owner for the detailed contracts linked below.

## Ownership

- Owns: FT-001 design navigation, cross-spec boundary summary, non-goals, and
  implementation handoff.
- Does not own: relational shapes, security primitives, HTTP payloads/errors,
  ActorContext fields/permission rules, or verification details.
- Related specs: see `Specification Map`.

## Specification Map

| Specification | Authoritative scope |
|---|---|
| [.memory-bank/domains/local-identity-session-data.md](../domains/local-identity-session-data.md) | `Account`, `FarmMembership`, and `LocalSession` schema, constraints, indexes, migration, and deferred Farm FK. |
| [.memory-bank/contracts/local-session-security.md](../contracts/local-session-security.md) | Argon2id credentials, opaque session tokens, session lifecycle, cookie transport, and optional bearer transport. |
| [.memory-bank/contracts/local-session-api.md](../contracts/local-session-api.md) | Login/logout/me routes, internal activation handoff, error catalog, and no-leak API failures. |
| [.memory-bank/contracts/actor-context.md](../contracts/actor-context.md) | Role presets, ActorContext, PlantPermissionContext interface, protected entrypoints, and context-builder authorization. |
| [.memory-bank/testing/ft-001-access-auth.md](../testing/ft-001-access-auth.md) | Cross-contract test coverage, task/evidence mapping, and quality gates. |

Shared/global inputs remain authoritative for their own boundaries:

- [.memory-bank/architecture/system-architecture.md](../architecture/system-architecture.md)
- [.memory-bank/architecture/foundation-runtime-substrate.md](../architecture/foundation-runtime-substrate.md)
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md)
- [.memory-bank/domains/foundation-data-substrate.md](../domains/foundation-data-substrate.md)
- [.memory-bank/contracts/api-guidelines.md](../contracts/api-guidelines.md)
- [.memory-bank/contracts/evidence-redaction.md](../contracts/evidence-redaction.md)
- [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md)
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md)
- [.memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md](FT-002-farm-plant-lifecycle-access-grants.md)
- [.memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md](FT-003-boss-admin-surface-admin-audit.md)

## Component Boundaries

FT-001 owns local Accounts, FarmMemberships, LocalSessions, credential/session
services, login/logout/session inspection, ActorContext, fixed role policy, and
the PlantPermissionContext interface envelope.

FT-001 does not own:

- Foundation app/database substrate;
- Farm, Plant, PlantAccessGrant lifecycle, `tomato_001` seed, concrete
  PlantPermissionContext resolver values, or Plant HTTP denial mapping (FT-002);
- public invite activation, Account/admin mutation routes, admin UI, or durable
  AdminAuditRecord behavior (FT-003);
- Agent Chat Bus publication, MessageEnvelope validation, UI Feed projection,
  Safety Gate clearance, or physical-action approval.

Small fail-closed interfaces/test fixtures for FT-002/FT-003 dependencies are
allowed only when required by task sequencing; they must not duplicate the
owning feature's domain rules.

## Non-Goals

- Enterprise identity, OAuth, password recovery, email invite delivery, SaaS
  tenancy, and multi-Farm membership.
- Full ACL/permission override engine beyond `plant_approve_actions`.
- Refresh tokens, device management, hosted account recovery, audit export UI,
  and broad personnel management.

## Handoff To Tasks

Tasks may implement FT-001 storage, credential/session services,
login/logout/me routes, the internal activation/session primitive used by
FT-003, ActorContext, fixed role policy, PlantPermissionContext interface,
auth error mapping, migrations, and linked verification.

Tasks must not implement FT-002 Plant lifecycle or PlantAccessGrant mutation,
or FT-003's public invite/admin surfaces beyond the explicit handoff interfaces.

The structural split changes no behavioral contract. Existing task and packet
references to this hub remain valid through the Specification Map. The next
workflow gate remains `/review-tasks-plan FT-001`, followed by conditional
`/mb-doctor` before execution.

## Open Questions

None for FT-001 task decomposition. Hosted identity, recovery, multi-Farm
membership, refresh tokens, or a general permission matrix require a later
global spec.
