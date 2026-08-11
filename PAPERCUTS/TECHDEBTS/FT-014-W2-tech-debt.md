# /tech-debt — FT-014 W2 wave (advisory)

Date: 2026-08-11
Scope: FT-014 tasks closed in W2 — TASK-048, TASK-050, TASK-051, TASK-052, TASK-053,
TASK-055, plus TASK-047 W1 (shared foundation of the seam wiring).
Mode: advisory analysis only. No task/spec/status/lifecycle change performed.

## Checked scope

- Task records: `.memory-bank/tasks/TASK-047-T3-FT-014-W1.task.json`, TASK-048/050/051/052/053/055 W2 cards.
- Protocols/evidence: `.protocols/TASK-047/048/050/051/052/053/055-T3-FT-014-*/` (progress, handoff, verification, red-verification) and `.tasks/TASK-0XX-*/` gate transcripts.
- Source: `backend/app/dataset_governance/`, `backend/app/photo_intake/service.py`, `backend/app/plant_operations/service.py`, `backend/app/task_follow_up/service.py`, `backend/app/agent_runtime/{providers,roster}.py`, `backend/app/timeline/writer.py`.
- Tests: `tests/backend/dataset_governance/*_wiring.py`, `test_transition_authority.py`, `tests/backend/{photo_intake,plant_operations,task_follow_up}/*dataset_candidate*.py`, migration-model head-pin tests.
- Full-suite regression transcripts: `gate-full-backend.txt`, `supporting-full-regression.txt`, `gate-*-regression.txt`.

## Findings

### F1 (HIGH) — 10 historical feature migration head-pin tests assert the pre-FT-014 head and fail in every full suite run

Evidence: the live Alembic head is now `ft014_dataset_candidates`
(`tests/backend/test_foundation_database_contract.py:104` asserts
`script.get_heads() == ["ft014_dataset_candidates"]`; `backend/migrations/versions/ft014_dataset_candidates.py` has
down_revision `ft013_decision_effects`). Yet 10 historical feature tests still hard-pin
`ft013_decision_effects` as the current head, so they fail deterministically in the full
deterministic suite on every run (transcripts: TASK-047 `supporting-full-regression.txt`
576 passed / 10 failed; TASK-051 `gate-full-backend.txt` 641/10; TASK-052 653/10; TASK-055
`supporting-full-regression.txt` 682/10).

Failing assertions (all assert `revision == "ft013_decision_effects"` or
`get_heads() == ["ft013_decision_effects"]`):
- `tests/backend/access_admin/test_ft002_schema_migration.py:107`
- `tests/backend/agent_chat/test_ft008_migration_models.py:77,80`
- `tests/backend/companion_governance/test_migration_models.py:136`
- `tests/backend/photo_intake/test_ft005_migration_models.py:84`
- `tests/backend/plant_operations/test_ft004_migration_models.py:88`
- `tests/backend/plant_state/test_migration_models.py:47`
- `tests/backend/safety_gate/test_classification_persistence.py:1064`
- `tests/backend/safety_gate/test_migration_models.py:115`
- `tests/backend/task_follow_up/test_migration_models.py:101,305`

Impact: material regression risk — the full deterministic suite can never be green; each
run ships 10 known failures that mask genuine regressions and force manual triage of every
result. Repeated change cost and maintenance burden for any future migration that changes the head.

Remediation (smallest): a single dedicated head-pin reconciliation task that updates the 10
assertions to `ft014_dataset_candidates` (or better: reads the head from one shared constant).
Deferred intentionally per operator instruction during the wave ("historical feature tests left
untouched"), so the debt is accepted-forward-drift, not hidden.

### F2 (MEDIUM) — Repeated near-identical `_record_dataset_evidence` seam wrapper in 3 source-owner services with divergent error taxonomy

Evidence: three private seam wrappers with the same shape
(injectable `dataset_governance=` binding, default `DatasetGovernanceService(self._session,
timeline_appender=...)`, then `record_dataset_evidence(RecordDatasetEvidenceCommandV1(...))`):
- `backend/app/photo_intake/service.py:368-386` (hard-codes `SourceKind.PHOTO_CATALOG_ITEM`)
- `backend/app/plant_operations/service.py:287-306` (already generalized via `source_kind`/`source_ref`, reused for check-in at :183/:189 and measurement at :244)
- `backend/app/task_follow_up/service.py:838-856` (hard-codes `SourceKind.FOLLOW_UP_OUTCOME`)

The two hard-coded wrappers (photo, follow-up) are specializations of the generalized form already
present in plant_operations; a single shared generalized helper (parameterized by
`source_kind`/`source_ref`, as plant_operations already is) could serve all four source owners.
Also, the four source owners map governance seam failures differently: task_follow_up explicitly
maps `DatasetGovernanceError.AUDIT_FAILED -> TASK_AUDIT_FAILED` (`task_follow_up/service.py:792-800`),
whereas photo_intake (`service.py:238-246`, `except (IntegrityError, Exception)`) and plant_operations
(`service.py:318-321`, `except Exception`) collapse governance audit failures into a generic
persistence failure (`PHOTO_PERSISTENCE_FAILED` / `OPERATION_PERSISTENCE_FAILED`).

Impact: repeated change cost when the seam signature/error contract changes (3 coordinated edits per
change), plus an observable inconsistency: the same underlying audit failure surfaces as an audit
failure on the follow-up path but as a persistence failure on the photo/check-in/measurement paths.

Remediation (smallest): extract the generalized helper (exact plant_operations shape) once and have
photo/task_follow_up call it; align the audit-failure mapping across the four owners.

### F3 (LOW) — Dataset Governance couples to source-owner physical schemas via hard-coded raw-table lookups

Evidence: `backend/app/dataset_governance/repository.py:29-35` `_EVIDENCE_KIND_TABLE` hard-codes
physical table/id column names (`photo_catalog_items`/`photo_id`, `daily_checkins`/`check_in_id`,
`manual_measurements`/`measurement_id`, `outcomes`/`outcome_id`) and `evidence_refs_resolve`
(`repository.py:173-221`) performs raw `table()`/`text()` existence checks across module boundaries.
The kind strings are duplicated from `service.py:40-45` `_INITIAL_EVIDENCE_KIND` (which maps
`SourceKind` -> kind string, e.g. `DAILY_CHECK_IN -> "observation"`) and `ALLOWED_EVIDENCE_KINDS`
(repository.py:24-26) which additionally contains `"check_in"` and `"review"` that have no table
target (a `"review"`-kind ref can never resolve). This is a deliberate, documented boundary choice
("Raw-table existence checks keep Dataset Governance off other modules' ORM models"), and the
contract test `tests/backend/dataset_governance/test_transition_authority.py:671-...`
(`test_valid_canonical_same_farm_plant_evidence_permits_exact_confirm`) covers the current wiring.

Impact: coupling risk — a rename or migration of any source-owner table/column silently breaks
evidence resolution (returns False, `EVIDENCE_INVALID`), and the kind-string list is triplicated
across `service.py`, `repository.py` constants and the raw table map. Not yet triggered; moderate
future maintenance burden.

Remediation (smallest): keep the raw-table direction, but derive `_EVIDENCE_KIND_TABLE` targets and
the canonical kind set from one place (e.g. a single constant in repository.py re-used by
`ALLOWED_EVIDENCE_KINDS`, and remove the unreachable `"review"`/`"check_in"` entries or give them
explicit targets) so table names and kinds live in exactly one location.

## Non-findings (checked, no material debt confirmed)

- Candidate area (1) partial: the seam duplication above is the only extractable duplication; the
  per-owner wiring is otherwise correctly minimal (one call per creation path, same-UoW, idempotent).
- Candidate area (3): `node scripts/mb-lint.mjs` currently exits 0; the `allowed_write_scope`
  deprecations are warnings on historical cards (TASK-001..TASK-039), not introduced by this wave and
  non-blocking. The TASK-047 `red_verify` extra-key error seen in earlier gate transcripts is no
  longer present in the current working tree. Not a wave finding.
- Candidate area (5): `_as_utc` is a well-known pre-existing module-local convention
  (`access_admin/session_service.py:224`, `agent_runtime/service.py:761`, `api/session.py:389`,
  `plant_state/{service,runtime}`, `task_follow_up/runtime.py:999`, `companion_governance/runtime.py:1151`,
  `hydroponics_advisor/runtime.py:761`, `vision_observation/service.py:721`); the wave added one more
  copy in `dataset_governance/repository.py:38` with matching semantics (naive->UTC attach,
  aware->astimezone). Consistent, tested; style/preference only, not a finding.
- Candidate area (6): the generalized `_record_dataset_evidence` in plant_operations is the correct
  minimal form and is reused across check-in and measurement paths; the only issue is that photo and
  task_follow_up duplicated rather than reused it (covered by F2).
- Coverage/style/function-size: no findings; existing tests are focused and evidence-backed.

## Uncertainty

- Whether F2's audit-failure taxonomy divergence is a genuine defect or an accepted per-module
  contract decision is not fully specified in the specs; the follow-up path's explicit mapping versus
  the generic collapse in the other two looks accidental rather than deliberate.
- F3 materiality is prospective (no current failure); its triplicated kind/table metadata is confirmed
  by reading the code, but its impact is only realized on schema drift.
- The 10 head-pin failures' exact set may vary by suite subset (some gates show slightly different
  counts), but all observed transcripts report exactly 10 deterministic failures of the same class.

## Confirmation

Only this report file was created/changed: `PAPERCUTS/TECHDEBTS/FT-014-W2-tech-debt.md`.
No other project file was modified; no task/spec/status/lifecycle state was touched.
