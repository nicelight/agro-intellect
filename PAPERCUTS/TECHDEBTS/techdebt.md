# Tech Debt Register

Consolidated register of accepted technical-debt findings for FT-014.
Source reports: `PAPERCUTS/TECHDEBTS/FT-014-W2-tech-debt.md`,
`PAPERCUTS/TECHDEBTS/FT-014-W5-tech-debt.md`.

- F1 (W2, HIGH, 10 head-pin tests) — **CLOSED** by TASK-058.
- W2-F2 (MEDIUM, seam wrapper + audit taxonomy) — **CLOSED** by TASK-059.
- W5-1 (MEDIUM, duplicated runtime skeleton) — **CLOSED** by TASK-060.
- W5-2 (LOW, triplicated audit_failed construction) — **CLOSED** by TASK-060.
- W2-F3 (low, raw-table coupling) — recorded in source report, not in scope of
  the current remediation cycle (operator selection).

Status: all remediation-cycle findings closed; W2-F3 remains recorded, out of
scope.

---

## 1. W2-F2 (MEDIUM) — Repeated `_record_dataset_evidence` seam wrapper + divergent audit-error taxonomy

**Evidence:**
- `backend/app/photo_intake/service.py:368-386` — private `_record_dataset_evidence` hard-codes
  `SourceKind.PHOTO_CATALOG_ITEM` / `photo_id`.
- `backend/app/plant_operations/service.py:287-306` — already generalized via `source_kind`/`source_ref`
  (used for check-in at :183/:189 and measurement at :244).
- `backend/app/task_follow_up/service.py:838-856` — hard-codes `SourceKind.FOLLOW_UP_OUTCOME` / `outcome_id`.
- Error taxonomy divergence: `task_follow_up/service.py:792-800` maps
  `DatasetGovernanceErrorCode.AUDIT_FAILED -> TASK_AUDIT_FAILED`, while
  `photo_intake/service.py:238-246` and `plant_operations/service.py:318-321` collapse governance
  audit failures into generic `PHOTO_PERSISTENCE_FAILED` / `OPERATION_PERSISTENCE_FAILED`.

**Impact:** repeated change cost (3 coordinated edits per seam change); the same audit failure surfaces
as an audit failure on the follow-up path but as a persistence failure on photo/check-in/measurement paths.

**Accepted remediation direction (operator decision 2026-08-11):**
1. Extract one generalized shared helper (the `plant_operations` shape) and have photo and
   task_follow_up call it, so all four source owners use the same seam invocation.
2. Add explicit dataset-audit error codes to photo/plant: `PHOTO_DATASET_AUDIT_FAILED` and
   `OPERATION_DATASET_AUDIT_FAILED` (HTTP 500), mapped from `DatasetGovernanceErrorCode.AUDIT_FAILED`;
   align the four owners' audit-failure taxonomy with the `TASK_AUDIT_FAILED` precedent.

**Required spec updates before code:** `.memory-bank/contracts/photo-intake-http.md`,
`.memory-bank/contracts/plant-operations-http.md` (register the new error codes).

---

## 3. W5-1 (MEDIUM) — Near-duplicated runtime service skeleton between the two Dataset Agents

**Evidence:** `backend/app/dataset_governance/runtime.py` re-implements the same orchestration by copy:
`_prepare`, `_require_current_scope`/`_require_candidate`, `_post_io_guard`, `_audit`,
`_end_database_transaction`, plus the near-identical `run()` sequence
(governance `runtime.py:200-291,293-358` vs curator `runtime.py:596-706,748-819`).
`_PreparedRun`/`_CuratorPreparedRun` differ only in request type. Copies already diverge
(curator `_audit` calls `_end_database_transaction()` on append failure, governance does not;
this wave fixed two curator-only runtime bugs).

**Impact:** repeated change cost (every skeleton change applied twice), regression risk on
guard/rollback semantics, and shared helpers typed for the governance protocol reused by the curator.

**Accepted remediation direction:**
Extract a module-private shared base (or plain helpers) for
prepare/scope/candidate/guard/rollback/audit-failed construction, parameterized by prepared-run type,
decision type, and gate-result mapping; keep the two public service classes as thin adapters over the
shared flow. Do NOT introduce this for hypothetical agents; justified here by two already-diverging copies.

---

## 4. W5-2 (LOW) — Triplicated `audit_failed` outcome construction with inconsistent gate recording

**Evidence:** three inline near-identical `DatasetAgentRuntimeOutcomeV1(... outcome_kind="audit_failed",
audit_status="failed", event_ref=None, ...)` blocks: `runtime.py:329-343` (governance `_audit`),
`runtime.py:517-531` (curator gate-failure branch), `runtime.py:790-804` (curator `_audit`).
Recorded `curator_gate_result` differs by site: governance and curator gate-failure hard-code
`"not_applicable"`, while curator `_audit` preserves the attempted value via `runtime.py:803`.
Matrix `runtime_contracts.py:605-614` leaves `curator_gate_result` unconstrained on `audit_failed`.
No persisted state differs (all paths roll back) — recording/consistency surface only.

**Impact:** low; an edit to one construction is not applied to the others; an observer cannot tell from
an `audit_failed` outcome whether a selected gate was attempted.

**Accepted remediation direction:**
One module-level helper `_audit_failed_outcome(command, *, model_ref, provider_call_status,
curator_gate_result)` used by all three sites, with a single documented convention (or matrix
constraint) for `curator_gate_result` on `audit_failed`.

---

## Closure criteria

- W2-F2: shared seam helper in use by all four source owners; `PHOTO_DATASET_AUDIT_FAILED` /
  `OPERATION_DATASET_AUDIT_FAILED` registered in HTTP contracts and returned on governance audit failure;
  full deterministic suite green.
- W5-1/W5-2: `runtime.py` has one shared flow core and one `_audit_failed_outcome` helper; all existing
  dataset-agent runtime tests (governance + curator) green; outcome/audit matrix unchanged.
