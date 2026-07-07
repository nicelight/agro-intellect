---
description: Durable AdminAuditRecord schema, action taxonomy, transaction semantics, and safe summaries.
status: active
type: data_contract
last_updated: 2026-07-06
source_of_truth:
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/contracts/evidence-redaction.md
  - .memory-bank/contracts/access/actor-context.md
---
# Admin Audit

## Scope

Defines PostgreSQL/read-model authority for admin audit records shared by
identity, membership, Plant, and PlantAccessGrant mutations.

## Shape

`admin_audit_records` is PostgreSQL/read-model authority:

- `admin_audit_id`: native UUID primary key, application-generated;
- `farm_id`: non-null native UUID FK to `farms.farm_id`, `ON DELETE RESTRICT`;
- `actor_kind`: `varchar(32)`, checked to `account|system_bootstrap`;
- `actor_account_id`: nullable native UUID FK to `accounts.account_id`,
  `ON DELETE RESTRICT`;
- `actor_membership_id`: nullable native UUID FK to
  `farm_memberships.membership_id`, `ON DELETE RESTRICT`;
- `actor_role_preset`: nullable `varchar(16)` checked to
  `boss|engineer|consultant` when present;
- `action_type`: non-null `varchar(64)` checked to the taxonomy below;
- `target_type`: non-null `varchar(32)` checked to the taxonomy below;
- `target_id`: non-null native UUID;
- `plant_id`: nullable native UUID FK to `plants.plant_id`,
  `ON DELETE RESTRICT`;
- `request_id`: non-null `text` with a non-blank check;
- `before_summary`, `after_summary`: non-null PostgreSQL `jsonb` objects,
  default `{}`;
- `source_refs`: non-null PostgreSQL `jsonb` array of safe references,
  default `[]`;
- `created_at`: non-null `timestamptz`, server default `now()`;
- reverse-time indexes on `(farm_id, created_at, admin_audit_id)` and
  `(plant_id, created_at, admin_audit_id)`, with the Plant index partial for
  non-null `plant_id`.

For `actor_kind=account`, both actor IDs and role are non-null and resolve to
the same Farm. For `system_bootstrap`, both actor IDs and role are null. A DB
check enforces the nullability shape; the service enforces same-Farm actor
relationships before write.

## Taxonomy

Actions: `farm_created`, `farm_display_name_changed`, `account_created`,
`account_disabled`, `membership_role_changed`, `membership_disabled`,
`plant_created`, `plant_display_name_changed`, `plant_archived`,
`plant_restored`, `plant_access_granted`, `plant_access_updated`,
`plant_access_revoked`, and `plant_approve_actions_changed`.

Targets: `farm`, `account`, `membership`, `plant`, `plant_access_grant`.

## Rules

- Every successful mutation represented by an `action_type` in this spec MUST
  write exactly one AdminAuditRecord in the same DB transaction as the state
  change. This includes Account creation/disable,
  membership role/status changes, Plant lifecycle changes, and Plant access
  grant changes.
- Failed validation, authorization, or persistence writes no misleading
  success record.
- Compact summaries may contain safe IDs, display names, role/status values,
  Plant IDs, and boolean permission deltas; they are structured data, not UI
  copy.
- Free-form notes are included only after redaction.
- `account_created` stores only safe Account/Membership/Farm identifiers, role,
  status, and authenticated-Boss or system/bootstrap provenance.
- Never store passwords, password hashes, session tokens/digests,
  headers, `.env`, API keys, provider secrets, raw model output, or reasoning.
- Plant/access services use this same contract; they do not define a second
  audit record.
- Engineer Plant creation writes `plant_created` and the atomic creator grant
  writes `plant_access_granted` in the same transaction as the Plant and grant.
  Both records use the authenticated Engineer ActorContext attribution. Boss
  Plant creation writes `plant_created` and no synthetic grant/audit pair.
- Timeline/export may reference audit IDs, but cannot replace mutable audit
  authority.
- Farm/Plant local bootstrap uses `system_bootstrap`, a safe command/migration
  request ID, and no actor credentials. It writes only for records actually
  created.
- Farm/Plant display-name changes store only the previous and resulting trimmed
  display names plus safe IDs. Immutable keys are not presented as mutable
  audit deltas.

## Retry and duplicate behavior

Duplicate normalized login and invalid/duplicate Plant key fail without a
success audit record. Plant lifecycle and grant retry semantics are defined by
the Plant lifecycle spec: no-op retries add no duplicate audit record.

## Verification

- Schema tests cover native UUIDs, restrictive FKs, actor-shape/taxonomy checks,
  JSON object summaries, source-ref arrays, indexes, attribution, and
  references.
- Transaction tests prove exactly-one-on-success and none-on-failure across
  identity, role, Plant, and access mutations.
- Redaction tests reject every secret class above.

## Related specs

- [.memory-bank/contracts/admin/boss-admin-http.md](../../contracts/admin/boss-admin-http.md)
- [.memory-bank/contracts/evidence-redaction.md](../../contracts/evidence-redaction.md)
- [.memory-bank/states/plants/plant-and-access-lifecycle.md](../../states/plants/plant-and-access-lifecycle.md)
