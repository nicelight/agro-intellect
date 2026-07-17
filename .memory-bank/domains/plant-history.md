---
description: Plant history projection, retained-history access, and runtime authority data specification.
status: active
type: data_spec
last_updated: 2026-07-18
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
spec only when their owning schemas and an explicit product requirement exist.
FT-013 does not add a Companion-governance `PlantHistoryEntry` source family in
the current MVP slice: authoritative governance records remain in their owning
storage and human presentation uses the shared UI Feed projection. FT-006 must
not create placeholder rows or fake those downstream feature outcomes.

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
values, raw SQL, user filenames, raw provider payloads, hidden reasoning, raw
Companion proposal text, or unapproved UI/chat content. Local-path handling is
the separate best-effort presentation policy below, not a secret-redaction
guarantee.

### Response-safe string projection

- Apply one recursive policy to direct card/list string fields, nested string
  values, and mapping keys, not only `summary` and `source_refs`.
- URL-first and KISS: a complete valid non-`file` URL is one exempt value/span,
  including its path, query, fragment, and any path-like substrings within it.
  If a delimiter-free ambiguous concatenation parses as that complete URL, the
  URL interpretation wins and the value/span is preserved.
- Use only a small best-effort recognizer for obvious standalone local paths or
  paths embedded after a clear boundary: POSIX `/...`, Windows drive
  `C:\\...` or `C:/...`, UNC `\\\\server\\share`, and `file://...` forms. A
  recognized string value is replaced as a whole by the project redaction
  marker; a recognized mapping key is omitted to avoid key collisions.
- Do not build exhaustive URL/path grammar, candidate state machines, or a
  finite delimiter catalogue to discriminate every composition. When more
  exhaustive redaction would require cumbersome construction, preserving and
  displaying the ambiguous path or link is preferred.
- Safe relative artifact refs such as `plants/<uuid>/photos/...` remain
  allowed.
- Local-path redaction completeness is not a hard privacy/security guarantee
  when syntax is ambiguous or the required discrimination would violate KISS.
  Secret/auth-material exclusions remain strict and separate.

## Ordering and pagination

- Default order is newest first by `(occurred_at, recorded_at, source_type,
  source_id)`.
- Cursor pagination uses an opaque cursor derived from that tuple. The cursor
  is not a mutable authority token and must not encode credentials or raw SQL.
- Cursor decoding is canonical and non-malleable: only the unpadded base64url
  alphabet is accepted, decode/re-encode must reproduce the exact input, and
  the decoded versioned payload must have the exact expected fields and valid
  timestamps/source type/source UUID.
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
  auth material, raw SQL, provider payloads, hidden reasoning, and raw
  governance/chat content.
- Response-recursion tests cover card fields (including `display_name`), nested
  values, and mapping keys with simple obvious POSIX, Windows-drive, UNC, and
  `file://` cases. They also prove complete valid non-file URLs and safe
  relative artifact refs remain unchanged.
- Local-path tests do not claim exhaustive discrimination and do not generate
  delimiter/candidate matrices solely to search for ambiguous URL/path forms.
