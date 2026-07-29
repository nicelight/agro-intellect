---
description: Protected Plant UI Feed read API for authorized presentation events.
status: active
type: api_contract
last_updated: 2026-07-28
source_of_truth:
  - .memory-bank/contracts/api-guidelines.md
  - .memory-bank/contracts/ui-feed.md
  - .memory-bank/domains/agent-chat-ui-feed-storage.md
  - .memory-bank/contracts/access/actor-context.md
  - .memory-bank/domains/safety-action-routing.md
  - .memory-bank/states/companion-governance.md
  - .memory-bank/states/plants/plant-and-access-lifecycle.md
---
# Plant Feed HTTP

## Scope

Defines the protected boundary by which the current or future Operator PWA
loads persisted `UIFeedEventV1` rows and, only for an authorized active Plant,
idempotently materializes missing canonical roster introductions in the same
transaction. It does not define frontend layout, message submission, agent
invocation, classification, task actions, or physical-action approval.

## Endpoint

`GET /api/plants/{plant_id}/feed`

Query parameters:

- `cursor`: optional canonical opaque continuation cursor.
- `limit`: optional integer `1..100`, default `50`.

Unknown or repeated query parameters fail validation. The route resolves
ActorContext before business logic. Active Plant reads use `normal_read`;
archived Plant reads use the explicit `retained_history_read` permission path.
Neither path grants operational or agent-context authority. The archived path
is read-only; the active path may insert only missing introduction presentation
rows.

After preserving the existing query validation and no-leak authorization
precedence, the application transaction:

- locks/rechecks the current Account/FarmMembership, Plant, and applicable
  PlantAccessGrant;
- inserts only missing canonical roster-version-1 introductions when the Plant
  is still active;
- inserts none when the Plant is archived;
- reads the requested page using the unchanged order and cursor;
- commits before the success response is returned.

Plant creation, process startup, archive/restore, and Agent Chat Bus/context
paths never invoke this materialization.

## Response

`200` with `Cache-Control: no-store`:

```json
{
  "items": [
    {
      "schema_version": 1,
      "ui_event_id": "uuid",
      "created_at": "UTC timestamp",
      "farm_id": "uuid",
      "plant_id": "uuid",
      "source_type": "system|agent_message|safety|companion_governance",
      "source_id": "stable string",
      "source_refs": ["kind:identifier"],
      "display_kind": "agent_introduction|agent_message|block_notice|safety_status|companion_governance",
      "display_payload": {},
      "visible_to_roles": ["boss", "engineer", "consultant"],
      "visible_to_agents": false,
      "consumable_by_agents": false
    }
  ],
  "next_cursor": null
}
```

The exact discriminated `display_payload` variants live in the UI Feed
contract. Items are ordered by `(created_at ASC, ui_event_id ASC)`. The cursor
is unpadded base64url of canonical compact UTF-8 JSON containing exactly
`{"v":1,"created_at":"<canonical UTC>","ui_event_id":"<uuid>"}`. Decode plus
canonical re-encode identity is required; malformed, padded, non-canonical, or
unknown-field cursors fail.

Lazy materialization does not add response fields, reorder existing rows,
replace existing introduction rows, or change cursor semantics. A page may
include newly persisted rows according to the same existing order.

## Errors

- `AUTH_PLANT_FORBIDDEN` -> `404`, without existence leakage.
- `FEED_CURSOR_INVALID` -> `422`.
- `FEED_LIMIT_INVALID` -> `422`.
- `VALIDATION_FAILED` -> `422`.
- `FEED_PERSISTENCE_FAILED` -> `500`.

All errors use the global safe envelope and `Cache-Control: no-store`.
Any introduction insert, page read, flush, or commit failure rolls back the
request transaction and uses `FEED_PERSISTENCE_FAILED`. A later authorized
active-Plant Feed request is sufficient retry; the API exposes no batch,
pending, reconciliation, or repair status.

## Presentation boundary

The API returns candidate, introduction, notice, Safety status, and Companion
summary strings as JSON text data only. A frontend consumer MUST render
`introduction_text`, `quoted_text`, `summary_text`, `decision_summary`, and
notice text with
framework text interpolation/text-node semantics. It MUST NOT use an
HTML/Markdown renderer, raw-HTML insertion, URL activation, action parsing, or
copy feed payloads into agent context. Companion payloads remain presentation
data and cannot act as proposal/decision commands. The actual Svelte/PWA
component remains owned by FT-016 because this brownfield repository has no
frontend scaffold.

## Verification

- Authenticated tests cover Boss, granted Engineer/Consultant, missing/revoked
  grant, active Plant, archived retained history, and no-store responses.
- Active-Plant tests prove current authorization and active status are locked
  in the same transaction as missing-row inserts; authorization revocation or
  archive races write nothing.
- Introduction tests prove only missing rows are inserted; repeat, concurrent,
  and retried opens do not duplicate or update existing rows; archived reads
  and restore write none; and `FEED_PERSISTENCE_FAILED` rolls back before a
  later successful retry.
- Pagination tests prove stable order, canonical continuation, and rejection of
  every malformed/non-canonical cursor or invalid limit.
- Response tests preserve representative markup/prompt/URL-looking strings as
  inert JSON data with both agent flags false and no secret/auth fields.
- Response-union tests cover all three Companion payload variants, literal
  summary text, retained-history visibility, and unchanged non-consumability.
- Response-union tests cover every strict Safety status, exact non-imperative
  summary/freshness/expiry data, absence of candidate text, and unchanged
  non-consumability.
- OpenAPI reflects the path, query bounds, response union, and stable errors.
