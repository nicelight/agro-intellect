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

- `admin_audit_id`, `farm_id`, `actor_kind: account|system_bootstrap`;
- nullable `actor_account_id`, `actor_membership_id` (null only for
  `system_bootstrap`);
- `actor_role_preset`, `action_type`, `target_type`, `target_id`;
- optional `plant_id`; `request_id`;
- compact structured `before_summary`, `after_summary`, `source_refs`;
- `created_at`.

## Taxonomy

Actions: `account_created`, `account_disabled`, `membership_role_changed`,
`membership_disabled`, `plant_created`, `plant_archived`, `plant_restored`,
`plant_access_granted`, `plant_access_updated`, `plant_access_revoked`, and
`plant_approve_actions_changed`.

Targets: `account`, `membership`, `plant`,
`plant_access_grant`.

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

## Retry and duplicate behavior

Task-level idempotency may be added where specified. Duplicate normalized login
and duplicate active grants fail without a success audit record.

## Verification

- Schema tests cover required fields, taxonomy checks, safe JSON summaries,
  attribution, and references.
- Transaction tests prove exactly-one-on-success and none-on-failure across
  identity, role, Plant, and access mutations.
- Redaction tests reject every secret class above.

## Related specs

- [.memory-bank/contracts/admin/boss-admin-http.md](../../contracts/admin/boss-admin-http.md)
- [.memory-bank/contracts/evidence-redaction.md](../../contracts/evidence-redaction.md)
- [.memory-bank/states/plants/plant-and-access-lifecycle.md](../../states/plants/plant-and-access-lifecycle.md)
