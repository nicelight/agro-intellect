---
description: Implementation plan for FT-006 Runtime State Timeline and Plant History.
status: active
type: implementation_plan
feature_id: FT-006
last_updated: 2026-07-11
source_of_truth:
  - .memory-bank/features/FT-006-runtime-state-timeline-plant-history.md
  - .memory-bank/domains/plant-history.md
  - .memory-bank/contracts/plant-history-http.md
  - .memory-bank/testing/plant-history.md
---
# IMPL FT-006 Runtime State Timeline And Plant History

## Goal

Implement backend Plant card/history projections that preserve PostgreSQL/read
model authority, expose timeline refs as audit/export evidence only, and keep
archived Plant retained history accessible to authorized actors.

## Scope

- Add Plant history projection service over existing authoritative rows.
- Enforce active normal-read and archived retained-history authorization.
- Return safe check-in, measurement, photo, lifecycle/admin audit, and
  timeline refs.
- Expose protected Plant history card/list HTTP routes and OpenAPI coverage.
- Prove timeline replay cannot create or mutate runtime history.

## Non-goals

- Plant operations writes, photo upload, raw timeline export package, PWA UI,
  Vision processing, agent publication, Safety Gate, task/follow-up, Companion,
  dataset, or generic event-sourcing infrastructure.

## Constitution Check

- Spec Before Code: tasks derive from FT-006 and linked canonical specs.
- KISS: compute projections from source rows; no new history table or event
  sourcing, and no exhaustive URL/path parser for presentation redaction.
- Safety/authority: history reads never grant state-advancing authority and
  timeline refs never become runtime authority.
- Security: T3 because retained-history reads and source refs are
  authorization-sensitive and cross multiple runtime records.
- Blockers: none.

## Direct Canonical Design Links

- `.memory-bank/domains/plant-history.md`
- `.memory-bank/contracts/plant-history-http.md`
- `.memory-bank/contracts/timeline-event.md`
- `.memory-bank/contracts/access/actor-context.md`
- `.memory-bank/states/plants/plant-and-access-lifecycle.md`
- `.memory-bank/domains/plant-operations.md`
- `.memory-bank/domains/photo-artifacts.md`
- `.memory-bank/domains/admin/admin-audit.md`
- `.memory-bank/testing/plant-history.md`

## Dependencies

- `TASK-021-T3-FT-005-W1` provides photo catalog/artifact source rows.
- `TASK-022-T3-FT-005-W2` provides integrated operations/photo HTTP evidence
  used by the final FT-006 API flow.

## Ordered Implementation Strategy

### W1 - Projection Service And Authority Checks

`TASK-023-T3-FT-006-W1` implements Plant history service/query helpers,
projection shapes, retained-history authorization, pagination core, timeline
consistency checks, and focused service tests.

### W2 - HTTP And Integrated Evidence

`TASK-024-T3-FT-006-W2` implements protected history/card HTTP routes, OpenAPI
tests, integrated active/archive retained-history flow, behavior-spec
traceability, and durable FT-006 docs sync.

### W3 - Privacy And Cursor Strictness Repair

`TASK-027-T3-FT-006-W3` applies one recursive URL-first best-effort local-path
policy to card/list strings and mapping keys and keeps cursor decoding
canonical and non-malleable. The current retry must remove the complex
URL-candidate grammar/state-machine machinery and generated delimiter arms-race
tests introduced by retries 01-07, leaving a minimal recognizer for obvious
local paths plus strict cursor behavior. It depends on the completed W2 HTTP
boundary and does not alter PostgreSQL authority, retained-history
authorization, or source families.

## Expected Touched Areas

- `backend/app/plant_history/`
- `backend/app/api/history.py`
- `backend/app/api/__init__.py`
- `backend/app/main.py`
- `tests/backend/plant_history/`
- `tests/backend/api/`
- FT-006 protocol/evidence and Memory Bank docs during execution.

## Verification Strategy

- Focused projection/authorization/timeline-consistency tests for FT-006.
- API/OpenAPI tests for history card/list routes.
- Regression tests for auth, Plant access, operations, photo, and admin routes.
- Full test suite when practical.
- `node scripts/mb-lint.mjs` and `git diff --check`.
- PostgreSQL-backed recursive redaction probes for direct card fields, nested
  values/keys, and obvious standalone/clearly bounded POSIX, Windows-drive,
  UNC, and `file://` forms.
- Preservation probes for complete valid non-file URLs (including their
  path/query/fragment and path-like substrings), delimiter-free ambiguous
  URL-first values, and safe relative artifact refs.
- Static review proving retry-era URL candidate grammar/state-machine helpers
  and generated delimiter/candidate matrices used only for exhaustive
  discrimination were removed rather than replaced.
- Service/HTTP cursor probes covering canonical input and malformed
  non-alphabet, whitespace, padding, version, shape, timestamp, source type,
  and UUID cases.

## UAT

1. Boss or granted Engineer creates check-in, pH/EC measurement, and accepted
   photo for `tomato_001`.
2. Authorized user opens Plant history and sees safe source refs, artifact
   refs, and timeline refs derived from PostgreSQL/read model.
3. Boss archives the Plant and can still read retained history.
4. Archived history read does not enable check-in, upload, task, approval,
   agent publication, or governance transitions.
5. Obvious local paths are redacted recursively on a best-effort basis, complete
   valid non-file URLs and safe relative refs remain visible, no exhaustive
   parser/delimiter machinery remains, and every non-canonical cursor returns
   `422 HISTORY_CURSOR_INVALID`.

## Owner Clarification For W3

- URL-first and KISS govern ambiguous URL/path strings.
- Preserving/displaying an ambiguous path or link is preferable to cumbersome
  exhaustive discrimination; local-path completeness is not a hard privacy or
  security guarantee.
- Strict credential/auth redaction, ActorContext, PostgreSQL authority,
  retained-history authorization, and cursor canonicality remain unchanged.
- Queue action: reconcile existing `TASK-027`; no identity, tier, wave,
  dependency, status, or task slicing change is required.

## Repair Evidence Basis

- `.tasks/FT-006/FT-006-S-RED-VERIFY-final-report-docs-01.md`
- Existing `TASK-023` and `TASK-024` records remain `done` historical evidence.
