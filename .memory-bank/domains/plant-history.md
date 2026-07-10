---
description: Plant history projection, retained-history access, and runtime authority data specification.
status: active
type: data_spec
last_updated: 2026-07-10
source_of_truth:
  - .memory-bank/features/FT-006-runtime-state-timeline-plant-history.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/contracts/timeline-event.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
---
# Plant History Data

## Scope

Defines the FT-006 backend Plant card/history projection over authoritative
PostgreSQL/read-model records, local artifact refs, admin audit refs, and
timeline audit/export refs.

Plant history is a read projection. It does not introduce event sourcing,
timeline replay, a new mutable source of truth, or a second history table for
the MVP.

## Out of scope

Plant operations writes, photo upload acceptance, Vision processing, Agent Chat
Bus publication, UI Feed presentation storage, Safety Gate decisions, task and
follow-up state machines, Companion governance state, export package
generation, and PWA layout.

## Related specs

- [.memory-bank/contracts/plant-history-http.md](../contracts/plant-history-http.md)
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md)
- [.memory-bank/contracts/access/actor-context.md](../contracts/access/actor-context.md)
- [.memory-bank/states/plants/plant-and-access-lifecycle.md](../states/plants/plant-and-access-lifecycle.md)
- [.memory-bank/domains/plant-operations.md](plant-operations.md)
- [.memory-bank/domains/photo-artifacts.md](photo-artifacts.md)
- [.memory-bank/domains/admin/admin-audit.md](admin/admin-audit.md)

## Projection authority

The Plant history service reads from PostgreSQL/read-model records and returns
safe summaries plus refs. Current FT-006 source families are:

| Source family | Authoritative source | History use |
|---|---|---|
| Plant profile/lifecycle | `plants` plus `admin_audit_records` | Plant card status and lifecycle/audit entries. |
| Daily check-ins | `daily_checkins` | Observation/check-in entries and latest check-in refs. |
| Manual measurements | `manual_measurements` | pH/EC history and latest measurement projection refs. |
| Accepted photos | `photo_catalog_items` | Photo evidence entries and safe artifact refs. |
| Timeline refs | `event_refs` on source records plus `timeline.jsonl` | Audit/export references only; never current state. |

Future source families such as tasks, approvals, outcomes, agent outputs,
Safety Gate records, Companion governance, and dataset records may extend this
spec when their owning schemas exist. FT-006 must not create placeholder rows
or fake those downstream feature outcomes.

## Plant card projection

`PlantHistoryCard` is computed from PostgreSQL/read model:

- `plant_id`, `farm_id`, `plant_key`, `display_name`, `status`;
- `permissions`: safe serializable current permission summary;
- nullable `latest_check_in_ref`;
- nullable `latest_ph_ref`, `latest_ec_ref`, `latest_ph`, `latest_ec_ms_cm`;
- `ph_fresh_for_analysis`, `ec_fresh_for_analysis`;
- `photo_count`;
- `history_entry_count`;
- `retained_history_mode`: `active_history | archived_retained_history`;
- `computed_at`: timezone-aware server timestamp.

The card never reads `timeline.jsonl`, photo manifests, UI Feed, or agent text
to compute current status, latest values, counts, or permissions.

## History entry projection

`PlantHistoryEntry` is a deterministic read projection with no standalone
mutable identity:

- `history_entry_id`: stable string derived from `source_type` and `source_id`;
- `farm_id`, `plant_id`;
- `source_type`:
  `plant_admin_audit | daily_checkin | manual_measurement | photo_catalog_item`;
- `source_id`: UUID of the authoritative PostgreSQL row;
- `occurred_at`: source event/user time when available;
- `recorded_at`: server record/audit time;
- nullable `actor_ref`;
- `summary`: redacted structured summary appropriate for display/export;
- `source_refs`: safe source refs from the authoritative record;
- `event_refs`: timeline ref shape from the authoritative record when present;
- `artifact_refs`: safe relative artifact refs for photo entries only;
- `authority_source`: `postgresql_read_model`.

`summary` may contain safe Plant IDs, check-in/measurement/photo IDs, value
presence flags, pH/EC values, status strings, timestamps, photo type,
content type, size, sha256, and safe admin action names. It must not contain
credentials, session tokens/digests, password hashes, headers, cookies, `.env`
values, raw SQL, absolute paths, user filenames, raw provider payloads, hidden
reasoning, raw Companion proposal text, or unapproved UI/chat content.

## Ordering and pagination

- Default order is newest first by `(occurred_at, recorded_at, source_type,
  source_id)`.
- Cursor pagination uses an opaque cursor derived from that tuple. The cursor
  is not a mutable authority token and must not encode credentials or raw SQL.
- Default page size is implementation-local; the API contract defines accepted
  limits.
- A source row without a timeline ref may still appear when the authoritative
  row exists; the missing ref is an integrity/evidence issue, not permission to
  rebuild runtime state from timeline.

## Authorization and retention

- Active Plant card/history reads require current ActorContext normal-read
  permission for the Plant.
- Archived Plant card/history reads require explicit
  `retained_history_read` resolution through ActorContext.
- Retained-history reads never grant operate, task creation, action approval,
  agent publication, or governance transition authority.
- Missing, unauthorized, wrong-Farm, revoked-grant, disabled-membership, and
  archived normal-operation paths fail closed with no existence leak.
- Archive retains source rows, event refs, artifact refs, and audit refs; it
  does not create, delete, complete, cancel, approve, reject, supersede, or
  replay dependent records.

## Timeline consistency

- Timeline refs in history entries are audit/export refs for the authoritative
  source row.
- Timeline replay must not add, remove, update, confirm, sort, or repair Plant
  history entries in normal runtime.
- A timeline line without a matching authorized PostgreSQL source row is
  non-authoritative audit noise for FT-006 and must not appear as a current
  history entry.
- A PostgreSQL source row whose timeline event cannot be found is still the
  runtime authority. Verification should report the missing audit/export ref.

## Verification

- Projection tests prove Plant card/latest values/history entries are derived
  from PostgreSQL/read-model rows, not timeline replay, photo manifests, UI
  Feed, or agent text.
- Authorization tests prove active normal read and archived retained-history
  read behavior for Boss, granted Engineer, granted Consultant, revoked grant,
  disabled membership, unauthorized Plant, and wrong Farm.
- Retention tests archive a Plant with existing check-in, measurement, photo,
  and admin audit rows and prove history remains readable only through
  retained-history authorization.
- Timeline consistency tests prove orphan timeline events do not create
  history entries and missing timeline lines do not overwrite PostgreSQL
  source rows.
- Redaction tests prove responses, summaries, logs, exports, and evidence omit
  auth material, absolute paths, raw SQL, provider payloads, hidden reasoning,
  and raw governance/chat content.
