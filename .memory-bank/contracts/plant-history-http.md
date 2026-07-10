---
description: Concrete HTTP contract for Plant history card, retained-history reads, and timeline refs.
status: active
type: api_contract
last_updated: 2026-07-10
source_of_truth:
  - .memory-bank/domains/plant-history.md
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
---
# Plant History HTTP

## Scope

Defines the protected JSON API for Plant card/history reads and retained
archived-Plant history access in FT-006.

## Out of scope

Plant operations writes, photo upload, raw timeline export packages, history UI
layout, Agent Chat Bus publication, UI Feed persistence, Safety Gate/task/
follow-up state transitions, Companion governance transitions, and PWA
components.

## Common rules

- Every route resolves ActorContext before repository/service reads.
- Active Plant card/history reads require normal Plant read permission.
- Archived Plant card/history reads require explicit retained-history
  authorization; they do not allow operate/task/action/governance transitions.
- Protected responses set `Cache-Control: no-store`.
- Request query parameters reject unknown fields.
- Responses exclude credentials, password hashes, session tokens/digests,
  cookies, headers, raw SQL errors, absolute local paths, provider payloads,
  hidden reasoning, raw Companion proposal text, raw chat, and UI Feed content.
- `timeline_ref` and `event_refs` are audit/export refs only and never make a
  history response a mutable state authority.

## Response shapes

`PlantHistoryCard`:

- `plant_id`, `farm_id`, `plant_key`, `display_name`, `status`;
- `permissions`;
- nullable `latest_check_in_ref`;
- nullable `latest_ph_ref`, `latest_ec_ref`, `latest_ph`, `latest_ec_ms_cm`;
- `ph_fresh_for_analysis`, `ec_fresh_for_analysis`;
- `photo_count`;
- `history_entry_count`;
- `retained_history_mode: active_history|archived_retained_history`;
- `computed_at`.

`PlantHistoryEntry`:

- `history_entry_id`;
- `farm_id`, `plant_id`;
- `source_type`: `plant_admin_audit | daily_checkin | manual_measurement |
  photo_catalog_item`;
- `source_id`;
- `occurred_at`, `recorded_at`;
- nullable `actor_ref`;
- `summary`;
- `source_refs`;
- `event_refs`;
- `artifact_refs`;
- `authority_source: postgresql_read_model`.

`PlantHistoryList`:

- `items: PlantHistoryEntry[]`;
- nullable `next_cursor`.

## Routes

| Method and path | Request | Success | Authorization and behavior |
|---|---|---|---|
| `GET /api/plants/{plant_id}/history/card` | none | `200 PlantHistoryCard` | active normal read or archived retained-history read; computes from PostgreSQL/read model only |
| `GET /api/plants/{plant_id}/history` | optional `cursor`, `limit`, optional `source_type` | `200 PlantHistoryList` | active normal read or archived retained-history read; returns reverse-chronological entries with safe refs |

The default `limit` is 50. Accepted `limit` range is `1..100`. `cursor` is an
opaque value returned by the previous page. `source_type`, when present, must
be one of the currently implemented entry source types.

## Error catalog

All errors use the global `{error: {code, message, request_id}}` envelope.

| Code | HTTP | Meaning |
|---|---:|---|
| existing `AUTH_*` codes | existing mapping | session/account/membership/role failures |
| `AUTH_PLANT_FORBIDDEN` | 404 | missing, unauthorized, revoked, wrong-Farm, or archived without retained-history access |
| `HISTORY_CURSOR_INVALID` | 422 | cursor is malformed, expired for the current shape, or not decodable |
| `HISTORY_LIMIT_INVALID` | 422 | limit is outside `1..100` or has the wrong type |
| `HISTORY_SOURCE_TYPE_INVALID` | 422 | source_type is unknown or not implemented |
| `HISTORY_PERSISTENCE_FAILED` | 500 | unclassified rollback-safe read/projection failure |
| `VALIDATION_FAILED` | 422 | malformed UUID/query or unknown field |

## Verification

- API/OpenAPI tests cover both routes, query parameters, response shapes,
  source type enum, pagination, no-store behavior, and documented errors.
- Authorization tests cover active normal reads, archived retained-history
  reads, no-leak denial for unauthorized/missing/wrong-Farm/revoked/disabled
  cases, and denial of archived normal-operation semantics.
- Authority tests prove card/history data comes from PostgreSQL/read-model
  source rows and not from timeline replay, photo manifests, UI Feed, or agent
  text.
- Retention tests prove archived Plant check-in, measurement, photo, and admin
  audit refs remain readable to authorized retained-history users without
  enabling writes.
- Redaction tests prove responses and evidence omit auth material, raw SQL,
  absolute paths, provider payloads, hidden reasoning, raw chat, and unapproved
  governance content.
