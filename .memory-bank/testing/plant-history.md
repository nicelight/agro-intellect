---
description: Verification specification for Plant card/history projections, retained-history access, and timeline authority boundaries.
status: active
type: testing_spec
last_updated: 2026-07-11
source_of_truth:
  - .memory-bank/domains/plant-history.md
  - .memory-bank/contracts/plant-history-http.md
  - .memory-bank/testing/strategy.md
---
# Plant History Verification

## Scope

Defines deterministic evidence for FT-006 Plant card/history projections,
timeline-ref authority separation, and retained-history reads.

## Required evidence

- Service/projection tests for `PlantHistoryCard` and `PlantHistoryEntry`
  computed from PostgreSQL/read-model source rows.
- Authorization tests for active normal read and archived retained-history
  read across Boss, granted Engineer, granted Consultant, revoked grant,
  disabled membership, unauthorized Plant, and wrong Farm.
- Retention tests that archive a Plant after check-in, manual measurement,
  accepted photo, and Plant/admin audit rows exist, then prove authorized
  retained history remains readable and no state-advancing command is implied.
- Timeline consistency tests proving orphan timeline lines cannot create
  history entries and missing timeline lines cannot override PostgreSQL source
  rows.
- Pagination tests for newest-first ordering, stable cursor behavior, limits,
  and source-type filtering.
- API/OpenAPI tests for `/api/plants/{plant_id}/history/card` and
  `/api/plants/{plant_id}/history`.
- Redaction tests for response summaries, timeline refs, artifact refs, logs,
  exports, screenshots, and evidence.
- PostgreSQL-backed service and HTTP tests traverse direct card/list fields,
  nested values, and mapping keys. Grounded cases cover obvious standalone or
  clearly bounded POSIX, Windows-drive, UNC, and `file://` paths with
  best-effort redaction, plus complete valid non-file URL and safe-relative-ref
  preservation.
- Cursor tests prove canonical unpadded base64url continuation succeeds while
  inserted non-alphabet bytes, whitespace, padding, wrong version,
  extra/missing fields, invalid timestamps/source type/UUID, and non-canonical
  encodings return `HISTORY_CURSOR_INVALID`; HTTP maps each to `422`.

## Anti-cheat checks

- Plant card latest values, counts, and status read PostgreSQL source rows, not
  `timeline.jsonl`, photo manifests, UI Feed, raw chat, or agent text.
- Timeline replay is audit/export only and cannot mutate or populate runtime
  Plant history.
- Archived retained-history read does not grant operate, task creation, action
  approval, agent publication, or governance transition authority.
- Future source families such as tasks, approvals, agent outputs, Companion,
  and dataset records are not faked before their owning feature schemas exist.
- Responses and evidence omit secrets/auth material, raw SQL, provider
  payloads, hidden reasoning, raw Companion proposal text, raw chat, and UI
  Feed content.
- The best-effort local-path policy is applied recursively, including card
  fields and mapping keys; testing only selected `summary` values is
  insufficient.
- Complete valid non-file URLs are preserved as whole values/spans, including
  path/query/fragment and path-like substrings. Delimiter-free ambiguous text
  that parses as one such URL is URL-first.
- Remove retry-era generated delimiter/candidate matrices and assertions whose
  only purpose is exhaustive URL/path discrimination. Do not replace them with
  another parser grammar or state-machine arms race.
- Local-path completeness is not a hard privacy/security gate when ambiguity
  or implementation complexity arises; preserve/display the path or link in
  that case. Secret/auth redaction remains strict.
- Cursor decoding never relies on permissive base64 behavior and accepts only
  the canonical representation emitted by the service.

## Suggested gates

- `.venv/bin/python -m pytest tests/backend/plant_history`
- `.venv/bin/python -m pytest tests/backend/api -k ft006`
- `.venv/bin/python -m pytest tests`
- `node scripts/mb-lint.mjs`
- `git diff --check`
