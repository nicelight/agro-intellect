# /tech-debt report — FT-014 wave W6 (TASK-058 / 059 / 060)

- Date: 2026-08-12
- Scope: FT-014 W6 remediation wave — TASK-058-T1-FT-014-W6 (head-pin
  reconciliation), TASK-059-T2-FT-014-W6 (shared evidence seam helper + explicit
  audit error codes, W2-F2), TASK-060-T2-FT-014-W6 (runtime flow unify + single
  `_audit_failed_outcome` helper, W5-1/W5-2).
- Resolved through: indexed task cards
  `.memory-bank/tasks/TASK-058/059/060-*-FT-014-W6.task.json` (via
  `.memory-bank/tasks/index.json`), durable evidence
  `.protocols/TASK-0XX-T?-FT-014-W6/{run,handoff,progress,verification}.md`,
  gate transcripts `.tasks/TASK-0XX-*/`, and the actual changed files listed
  below. `touched_files` on the cards is advisory; actual surface verified via
  `git diff HEAD` and direct reads.
- Mode: advisory analysis only. No task/spec/status/lifecycle change performed.

## Checked scope and evidence

Changed files (verified in working tree, `git diff --name-only HEAD`):
- `backend/app/dataset_governance/evidence_seam.py` (new shared helper)
- `backend/app/dataset_governance/__init__.py` (export; recorded deviation)
- `backend/app/dataset_governance/runtime.py` (unified flow core, W5-1/W5-2)
- `backend/app/photo_intake/service.py`, `backend/app/plant_operations/service.py`,
  `backend/app/task_follow_up/service.py` (seam invocation + audit codes)
- `backend/app/api/photos.py`, `backend/app/api/operations.py` (error tables)
- `.memory-bank/contracts/photo-intake-http.md`, `plant-operations-http.md`,
  `dataset-agents-runtime.md` (spec-first rows)
- tests: `test_photo_wiring.py`, `test_check_in_wiring.py`,
  `test_measurement_wiring.py`, `test_ft004_operations_routes.py`,
  `test_ft005_photos_routes.py`
- `runtime_contracts.py` was NOT touched (diff empty — confirmed).
- TASK-058 head-pin edits (9 migration-model test files) verified via
  `.protocols/TASK-058-T1-FT-014-W6/run.md` + working-tree reads.

Key evidence:
- `git diff HEAD` of all listed files; py_compile of all changed Python modules OK.
- `.tasks/TASK-060-T2-FT-014-W6/{probe_static.py,red_static_probe,green_static_probe,
  w52_value_probe,green_full_deterministic_regression}.txt`
- `.tasks/TASK-059-T2-FT-014-W6/{red-wiring-before,green-wiring-after,
  green-candidates-after,green-api-routes-after,gate-mb-lint}.txt`
- `.protocols/TASK-059-T2-FT-014-W6/verification.md` (13/13 verifier probes),
  `.protocols/TASK-060-T2-FT-014-W6/verification.md` (verifier reruns + outcome probe)
- Full deterministic suite green: `754 passed, 209 warnings` (TASK-060 green
  transcript); also 754 in TASK-059/058 gate transcripts.

## Area findings

### Area 1 — Seam helper single-source + coherent error surface (W2-F2)
CONFIRMED CLEAN. `RecordDatasetEvidenceCommandV1(` construction exists at exactly
one production site: `evidence_seam.py:44`. All four owners
(photo accept `photo_intake/service.py:227`; daily check-in
`plant_operations/service.py:194`; manual measurement
`plant_operations/service.py:185,252`; follow-up outcome
`task_follow_up/service.py:781`) call the shared `record_dataset_evidence`.
All three private `_record_dataset_evidence` wrappers were removed (grep: zero
residual `_record_dataset_evidence` in `backend/`). The helper's error surface
raises `DatasetGovernanceError`; each owner maps it with the same shape
(AUDIT_FAILED -> explicit owner audit code, else -> generic persistence code),
matching the pre-existing `task_follow_up/service.py:803-811` precedent. No
residual duplication found.

### Area 2 — Audit error codes taxonomy
CONFIRMED CLEAN. `PHOTO_DATASET_AUDIT_FAILED` and
`OPERATION_DATASET_AUDIT_FAILED` are defined in the owner enums
(`photo_intake/service.py:55`, `plant_operations/service.py:44`), registered
spec-first in the HTTP contracts (contract mtimes 02:44:50/02:44:55 precede RED
02:45:28), and mapped to HTTP 500 in the API tables (`api/photos.py:113`,
`api/operations.py:162`). Programmatic completeness check: all enum members map
to the tables and no dead table entries in either module. `TASK_AUDIT_FAILED`
behavior unchanged (still `task_follow_up/service.py:802-811`). The collapsed
generic-code assertions in the wiring tests were updated to the new codes with
identical rollback/cleanup assertions (RED -> GREEN evidence). No remaining
taxonomy inconsistency or dead mapping.

### Area 3 — runtime.py shared flow core (W5-1) + KISS check
CONFIRMED CLEAN. One module-private `_DatasetAgentRuntimeFlow` core
(`runtime.py:130`) with `_RuntimeFlowSpec` parameterization (`runtime.py:103`),
two public classes are thin adapters. Static probe green:
`duplicated_skeleton=False`, `has_shared_flow_core=True`.
KISS check on `_RuntimeFlowSpec`: the parameterization is warranted — it encodes
real, test-pinned divergence between the two services (curator re-locks via
`post_io_guard_locks`, rejects existing runs via `reject_existing_run`, rolls
back on audit failure via `rollback_on_audit_failure`, different
request/decision/prepared types and gate-result mapping). Per-service rollback
semantics preserved (`_GOVERNANCE_RUNTIME_SPEC.rollback_on_audit_failure=False`
vs `_CURATOR_RUNTIME_SPEC...=True`, `runtime.py:440/452`). No over-abstraction
for hypothetical agents (only the two existing services parameterize it). No
residual skeleton duplication.
Coupling note (not a finding): the two adapters call back into the flow core's
private `_audit`/`_end_database_transaction` from the same module. This is a
module-internal, private-API coupling — contained and consistent, and the exact
shape the accepted W5-1 remediation specified ("public service classes as thin
adapters over the shared flow").

### Area 4 — `_audit_failed_outcome` helper (W5-2)
CONFIRMED CLEAN. Single module-level `_audit_failed_outcome`
(`runtime.py:776`); all three previous inline `audit_failed` construction sites
(governance `_audit`, curator gate-failure branch, curator `_audit`) now route
through it — shared `_audit` covers both append-failure paths, and the curator
gate-failure branch is the second textual site. Static probe:
`inline_audit_failed_outside_helper=0`, `helper_call_sites=2`. The
`curator_gate_result` convention is documented in
`dataset-agents-runtime.md` (audit_failed matrix row note) and verified at the
outcome level by the TASK-060 verifier probe (transition-audit -> `confirmed`,
selected runtime-audit -> `confirmed`, silent -> `not_requested`, governance ->
`not_applicable`); W5-2 value probe pins `curator_gate_result=="confirmed"` on
the transition-audit failure. Consistent and coherent everywhere.

### Area 5 — Coupling from the shared helper location
NO NEW COUPLING. `evidence_seam.py` lives inside the `dataset_governance`
package; the three source owners already depended on `..dataset_governance`
(pre-wave imports of `DatasetGovernanceService`/`RecordDatasetEvidenceCommandV1`/
`SourceKind`), so the helper sits on the pre-existing seam direction
(owners -> dataset_governance) rather than reversing it. The
`dataset_governance/__init__.py` re-export is a legitimate module-pattern
necessity (recorded deviation in progress.md). No dependency-cycle or
direction-reversal introduced.

### W2-F2 / W5-1 / W5-2 closure residue
No residual debt confirmed. Head-pin (W2-F1/TASK-058) fully re-pointed: all 9
historical tests now assert head `ft014_dataset_candidates` with exact
`down_revision == "ft013_decision_effects"` chain (verified by grep at
`:107-108`, `:77-83`, `:136-140`, `:84-85`, `:88-89`, `:47-48`, `:1064-1065`,
`:115-116`, `:101-102/:304-305`); full deterministic suite green. Known owner
items mentioned but NOT re-flagged: pre-existing flaky `task_follow_up`
concurrency test
(`tests/backend/task_follow_up/test_domain_loop.py:347`) and mb-lint
`allowed_write_scope` deprecations on historical cards.

## Confirmed findings

### Finding 1 (low) — Dangling `DatasetGovernanceService` type annotation in two owner constructors after the seam refactor

- Evidence: `photo_intake/service.py:119` and `plant_operations/service.py:101`
  still annotate the injection parameter as `dataset_governance:
  DatasetGovernanceService | None`, but the TASK-059 seam refactor removed
  `DatasetGovernanceService` from both modules' imports
  (`photo_intake/service.py:24-29`, `plant_operations/service.py:23-28`).
  `typing.get_type_hints(<Owner>.__init__)` raises
  `NameError: name 'DatasetGovernanceService' is not defined` (verified
  directly). `task_follow_up/service.py:77` keeps the annotation and still
  imports the symbol (`:16`), so it is unaffected.
- Mechanism: import removal in the refactor was not paired with the annotation;
  the constructor's public signature references a name not in module scope. The
  lazy annotations (`from __future__ import annotations`) mask it at runtime, so
  it is latent today — it breaks only when the signature is introspected or
  statically type-checked.
- Practical impact: latent type-checking/introspection defect in the two most
  seam-affected services; a future tool enabling or a static analysis pass over
  these constructors fails; the signature also misleads maintainers about the
  injection contract. Not currently triggered by the test suite (all gates
  green) — that is why it was not caught by the wave's gates.
- Priority: low.
- Smallest remediation: re-import `DatasetGovernanceService` in both files (a
  `TYPE_CHECKING`-guarded or plain re-import of the name already exported by
  the package `__init__`), so the annotation resolves again.

## Checked areas with no material finding

- Owner-side governance error handling (new `except DatasetGovernanceError`
  blocks in photo/plant, pre-existing in task_follow_up) — mapping shape
  consistent across all four owners; rollback/cleanup semantics preserved.
- API route error tables and OpenAPI contract tests — complete, no dead rows.
- `runtime_contracts.py` audit_failed matrix row — intentionally left
  unconstrained on `curator_gate_result`; the convention is now documented at
  the contract level and enforced by the single helper (was flagged as
  uncertainty in W5; resolution via documentation + single construction site is
  coherent and matches the accepted W5-2 remediation direction).

## Uncertainty

- Finding 1's materiality is prospective: it is a latent annotation-only defect
  (no runtime failure in the current green suite), so its real-world impact
  depends on future tooling adoption; the dangling reference itself is
  confirmed.
- W5's non-admitted enumeration-drift candidates (`DATASET_AGENT_IDS` vs roster
  `ADVISORY_ONLY_AGENT_IDS`, `CURATOR_DECISIONS` vs `CuratorDecision`) were
  re-checked and remain unchanged, still fail-closed, and still have no
  production consumer — unchanged status, not re-admitted.
- `_RuntimeFlowSpec` and `_audit`'s wide keyword-argument call sites
  (`runtime.py`) are judged warranted/contained per the analysis above, but the
  module-private adapter->core call-back coupling is a design trade-off the
  wave deliberately accepted; recorded here for awareness, not as a finding.

## Known owner items (mentioned, not re-flagged)

- Pre-existing flaky `task_follow_up` concurrency test
  (`test_disposition_rolls_back_with_audit_failure_then_concurrent_retry_consumes_once`).
- mb-lint `allowed_write_scope` deprecations on historical cards (TASK-001..039).

## Summary

Material findings confirmed: 1 (low, latent annotation-only defect in
`photo_intake/service.py:119` and `plant_operations/service.py:101`). All five
requested inspection areas otherwise confirmed clean; W2-F2/W5-1/W5-2 and the
head-pin closure left no residual debt in their remediation surfaces.
Only this report file was created or changed.
