# /tech-debt report — FT-014 wave W5 (TASK-057 Training Data Curator)

- Date: 2026-08-11
- Scope: TASK-057-T3-FT-014-W5 changed surface — `backend/app/dataset_governance/runtime.py`,
  `runtime_contracts.py`, `service.py`, `repository.py`, `backend/app/agent_runtime/providers.py`,
  `roster.py`, and tests `tests/backend/dataset_governance/test_curator_agent_runtime.py`,
  `test_curator_auto_gate.py`, `test_curator_auto_production_path.py`, plus the extended
  `tests/backend/agent_runtime/test_dataset_advisory_registration.py`.
- Resolved through: task record `.memory-bank/tasks/TASK-057-T3-FT-014-W5.task.json`, durable evidence
  `.protocols/TASK-057-T3-FT-014-W5/{context,handoff,progress,verification,red-verification}.md`,
  `.tasks/TASK-057-T3-FT-014-W5/`, and the actual files.
- Advisory only. No project file outside this report was created or modified.

## Checked scope and evidence

- `DatasetGovernanceRuntimeService` vs `TrainingDataCuratorRuntimeService` in
  `backend/app/dataset_governance/runtime.py` (lines 90-362 vs 372-823) — flow skeleton,
  prepare/guard/audit/rollback duplication.
- Outcome matrix `_validate_outcome_matrix` in `backend/app/dataset_governance/runtime_contracts.py:484-616`
  (shared, single copy; branches on `agent_id`).
- The two runtime bug fixes from this wave: missing `DATASET_CONFIRMATION_POLICY_VIOLATION` import
  (`runtime.py:44`) and the direct `audit_failed` construction replacing `_audit` usage
  (`runtime.py:516-531`), per `handoff.md` and confirmed by `verification.md`.
- Three inline `audit_failed` `DatasetAgentRuntimeOutcomeV1` constructions:
  governance `_audit` (`runtime.py:329-343`), curator gate-failure branch (`runtime.py:517-531`),
  curator `_audit` (`runtime.py:790-804`).
- Agent-set enumeration: `DATASET_AGENT_IDS` (`runtime_contracts.py:51`, operative in
  `DatasetAgentCommandV1.__post_init__`/`DatasetAgentRuntimeOutcomeV1.__post_init__`) vs
  roster-derived `ADVISORY_ONLY_AGENT_IDS` (`roster.py:97`, currently unused outside roster module).
- Curator-decision enumeration: `CURATOR_DECISIONS` frozenset (`runtime_contracts.py:49`) vs
  `CuratorDecision` StrEnum (`contracts.py:59`).
- Advisory-persistence coupling: `_persist_advisory` (`runtime.py:708-725`),
  `_guard_curator_auto` (`service.py:455-491`), matrix curator branches (`runtime_contracts.py:496-532`).
- Registration tests: `tests/backend/agent_runtime/test_dataset_advisory_registration.py` (5 tests;
  both roster routes, both binding slots, both unbound fail-closed paths).

## Confirmed findings

### Finding 1 (medium) — Near-duplicated runtime service skeleton between the two Dataset Agents
Evidence: the two services in `backend/app/dataset_governance/runtime.py` re-implement the same
orchestration by copy: `_prepare`, `_require_current_scope`/`_require_candidate`, `_post_io_guard`,
`_audit`, `_end_database_transaction`, plus the near-identical `run()` sequence
(prepare → rollback → executor config → execute → from_untrusted validate → rollback → post-I/O
guard → audit). Governance covers `runtime.py:200-291` (prepare + guards) and curator covers
`runtime.py:596-706`, with `_audit` duplicated at `runtime.py:293-358` vs `runtime.py:748-819`
(~66 vs ~72 lines), and `_PreparedRun`/`_CuratorPreparedRun` (`runtime.py:83-88` vs `runtime.py:365-369`)
differing only in request type. Shared items (`_runtime_event`, `_executor_model_ref`,
`_execution_result`, `_event_ref_is_valid`, `_candidate_snapshot`) are already module-level, which
is the coherent part of the boundary.

Observable divergence already present (not hypothetical): the curator `_audit` calls
`_end_database_transaction()` on append failure (`runtime.py:789`) while the governance `_audit`
does not (`runtime.py:328-343`); the governance flow never has pending writes at audit time so this
is currently correct, but the two copies encode different rollback contracts. This wave had to fix
two runtime bugs (`runtime.py:44` import; `runtime.py:516-531` audit construction), both in
curator-only paths — the copies are already drifting. A third advisory agent would copy the skeleton
again.

Practical impact: repeated change cost (every skeleton change must be applied twice), regression risk
on guard/rollback semantics when only one copy is edited, and the shared helpers are typed for the
governance protocol while reused by the curator (`_executor_model_ref(executor:
DatasetGovernanceModelExecutor | None)` called with the curator executor at `runtime.py:418`) —
duck-typed, so latent only (no mypy/pyright/ruff configured in `pyproject.toml`).
Smallest remediation: extract a module-private shared base (or plain helpers) for
prepare/scope/candidate/guard/rollback/audit-failed construction, parameterized by prepared-run type,
decision type, and gate-result mapping; keep the two public service classes as thin adapters over the
shared flow. Per KISS, do not introduce this for hypothetical agents — it is justified here by two
already-diverging copies.

### Finding 2 (low) — Triplicated `audit_failed` outcome construction with already-inconsistent gate recording
Evidence: three inline, near-identical `DatasetAgentRuntimeOutcomeV1(... outcome_kind="audit_failed",
audit_status="failed", event_ref=None, ...)` blocks: `runtime.py:329-343`,
`runtime.py:517-531`, `runtime.py:790-804`. The recorded `curator_gate_result` differs by failure
site: governance and curator gate-failure branches hard-code `"not_applicable"`, while the curator
`_audit` failure preserves the attempted value (`"confirmed"`/`"policy_blocked"`/`"not_requested"`)
via `runtime.py:803`. The matrix accepts both because `_validate_outcome_matrix`'s `audit_failed`
branch (`runtime_contracts.py:605-614`) leaves `curator_gate_result` (and `agent_id`) unconstrained.
No persisted state differs (all paths roll back), so this is a recording/consistency defect surface,
not a state-corruption risk.

Practical impact: low; an edit to one construction (e.g. a new matrix constraint) is not applied to
the others, and an observer cannot tell from an `audit_failed` outcome whether a selected gate was
attempted. Smallest remediation: one module-level helper
`_audit_failed_outcome(command, model_ref, provider_call_status, curator_gate_result)` used by all
three sites, and a single documented convention (or a matrix constraint) for `curator_gate_result` on
`audit_failed`.

## Checked areas with no material finding

- **Advisory-persistence ↔ outcome-matrix coupling (area 4):** coherent. `_persist_advisory`
  (`runtime.py:708-725`) writes only the current-run allowlist; `_guard_curator_auto`
  (`service.py:455-491`) and the matrix curator branches (`runtime_contracts.py:496-532`) agree on
  deferred/rejected → `not_requested` and selected → `confirmed`/`policy_blocked`; silent → `model_silent`.
  Cross-validated by the verifier probe (`verification.md`) and 15/15 red probes (`red-verification.md`).
- **Registration test coverage (area 5):** `test_dataset_advisory_registration.py` covers both
  canonical agents (roster route immutability, both provider-binding slots, both unbound
  fail-closed production paths). Adequate; no gap found.
- **Provider-profiles/route relationship (area 3):** no production dispatcher routes `agent_id` to a
  runtime yet — both services are consumed only by tests; `runtime_route="dataset_advisory_v1"` is
  roster metadata only. This is a future-wiring concern, not current debt (see uncertainty).

## Uncertainty

- Finding 3 candidate (two enumerations of the dataset-advisory agent set — `DATASET_AGENT_IDS` vs
  roster `ADVISORY_ONLY_AGENT_IDS`, plus `CURATOR_DECISIONS` vs `CuratorDecision`) is recorded here
  but NOT admitted as a finding: drift fails closed (an agent id missing from `DATASET_AGENT_IDS`
  yields a `DatasetGovernanceRuntimeValidationError`, not wrong behavior), `ADVISORY_ONLY_AGENT_IDS`
  has no production consumer, and there is no evidence of actual drift. If the roster ever becomes the
  binding source for routing a third agent, add a consistency assertion or derive `DATASET_AGENT_IDS`
  from the roster.
- Finding 2's `curator_gate_result` recording on `audit_failed` has no documented canonical value, so
  the inconsistency could be intentional "attempted value on failure" vs "closed failure" semantics;
  the evidence supports only that the three sites already differ, not which is correct.

## Known owner items (mentioned, not re-flagged)

- 10 pre-existing head-pin migration tests assert `ft013_decision_effects` as repository head while
  the live head is `ft014_dataset_candidates` (documented in `handoff.md`/`verification.md`).
- Pre-existing flaky `task_follow_up` concurrency test
  (`test_disposition_rolls_back_with_audit_failure_then_concurrent_retry_consumes_once`) passes
  ~40% in isolation; unrelated to this wave's surface.

## Summary

Material findings confirmed: 2 (one medium, one low), both in `backend/app/dataset_governance/runtime.py`.
Only this report file was created or changed.
