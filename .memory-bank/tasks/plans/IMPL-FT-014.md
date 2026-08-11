---
description: Implementation plan for the reconciled FT-014 Dataset Governance And Trainability queue.
status: active
last_updated: 2026-08-12
---
# IMPL-FT-014 — Dataset Governance And Trainability

## Planning status

Feature design is complete at Global Planning Revision 3. The operator
explicitly authorized full rebuild/reslicing of the rejected planned queue.
TASK-047..055 plus TASK-057 are the reconciled sequential JSON queue that
received fresh `/review-tasks-plan FT-014` APPROVE and has since been fully
executed to terminal `done`. The W6 remediation cycle (TASK-058/059/060) below
is likewise terminal `done`; the feature `lifecycle` stays `implemented` and
the feature-level T2 completion gate recorded `SEMANTIC_VERDICT: semantic-pass`.

## Remediation cycle (W6)

An approved tech-debt remediation cycle (2026-08-12, register
`PAPERCUTS/TECHDEBTS/techdebt.md`) added follow-up cards to the already
`implemented` feature without changing feature lifecycle, the executed queue,
or accepted evidence. All three are terminal `done` with fresh `/verify` `PASS`
evidence under `.protocols/TASK-0XX-*/` and `.tasks/TASK-0XX-*/`:

- `TASK-058-T1-FT-014-W6` (F1): the ten historical feature migration tests are
  re-pinned to the live head `ft014_dataset_candidates`.
- `TASK-059-T2-FT-014-W6` (W2-F2): one generalized dataset-evidence seam helper
  shared by all four source owners plus explicit audit error codes
  `PHOTO_DATASET_AUDIT_FAILED` / `OPERATION_DATASET_AUDIT_FAILED` (HTTP 500)
  registered spec-first in `photo-intake-http.md` and `plant-operations-http.md`.
- `TASK-060-T2-FT-014-W6` (W5-1 + W5-2): one module-private Dataset Agent
  runtime flow core with the two public services as thin adapters, plus one
  `_audit_failed_outcome` helper with a documented `curator_gate_result`
  convention recorded spec-first in `dataset-agents-runtime.md`. Behavior
  preserved; outcome/audit matrix unchanged.

## Goal

Establish Dataset Governance as the sole Dataset Candidate/evidence/lifecycle/
trainability authority; create raw non-trainable candidates from the four
accepted production evidence flows; make strong multi-evidence state reachable
through the Outcome-owned UoW; and run both canonical Dataset Agents through
the registered provider-neutral advisory-only route without MessageEnvelope,
Safety, Bus, UI, or direct model authority.

## Scope

- one additive `dataset_candidates` aggregate/migration with exact enums,
  native UUID/FKs, record version, current curator-run identity, ordered audit
  refs, check constraints, and named normal source identity uniqueness;
- one sole candidate-creation seam and one locked transition/trainability
  authority;
- one separate `associate_follow_up_evidence` command that derives candidate
  targets from authorized Outcome source refs and never accepts arbitrary
  association or lifecycle fields;
- separate same-UoW integrations for Photo Intake, daily check-in, manual
  measurement, Outcome candidate creation, and Outcome evidence association;
- separate Dataset Governance Agent advisory runtime, followed by one cohesive
  Training Data Curator application command that owns its advisory outcomes
  and indivisible selected-plus-`curator_auto` composition;
- exact Dataset Candidate and Dataset Agent Timeline registry, redaction,
  cardinality, rollback, audit-noise, and zero-replay behavior;
- deterministic PostgreSQL, provider fake/spy, migration, current-guard race,
  anti-cheat, and full regression evidence.

## Non-goals

- HTTP/review UI or FT-016 dataset-field reads (D1);
- agent-output evidence wiring or any agent-labeled confirm path (D2/D5);
- export packaging, split assignment, full dataset registry, real fine-tuning,
  model evaluation, server upload/sync, scheduler/worker, or automatic trigger;
- generic MessageEnvelope/Safety/Bus/UI changes, provider/model/base URL/
  credentials/egress/network/live smoke, or production fake/fallback;
- batch backfill or startup reconciliation of historical evidence.

## Capability ownership and boundaries

Primary owner is **Dataset Governance**, code root
`backend/app/dataset_governance/`, registered in
[Boundary Map Modules](../../contracts/boundary-map.md#modules).

- Photo Intake, Plant Operations, and Task & Follow-Up retain their command/UoW
  authority and call only
  [Dataset Evidence Creation](../../contracts/boundary-map.md#dataset-evidence-creation).
- Task & Follow-Up alone composes
  [Follow-Up Evidence Association](../../contracts/boundary-map.md#follow-up-evidence-association)
  inside `record_outcome`; Dataset Governance derives targets and owns writes.
- Dataset Governance consumes Agent Runtime Core only through
  [Dataset Advisory Runtime Exception](../../contracts/boundary-map.md#dataset-advisory-runtime-exception).
- Timeline Audit owns append validation only. PostgreSQL Candidate rows remain
  mutable authority under
  [Timeline Append Boundary](../../contracts/boundary-map.md#timeline-append-boundary).
- Business orchestration stays in the owning services, never FastAPI handlers,
  `backend/app/main.py`, or a generic helper/composition root.

## Sequential task strategy

| Task | Independent result | Dependencies |
|---|---|---|
| TASK-047 | Aggregate, migration, and sole candidate-creation seam | terminal TASK-046 baseline |
| TASK-048 | Transition/trainability authority | TASK-047 |
| TASK-049 | Follow-up evidence association command | TASK-048 |
| TASK-050 | Photo Intake candidate creation | TASK-047 plus terminal FT-005 path |
| TASK-051 | Daily check-in candidate creation | TASK-047 plus terminal FT-004 path |
| TASK-052 | Manual measurement candidate creation | TASK-047 plus terminal FT-004 path |
| TASK-053 | Outcome candidate creation | TASK-047 plus terminal FT-012 path |
| TASK-054 | Outcome association composition | TASK-049 and TASK-053 |
| TASK-055 | Dataset Governance Agent advisory runtime | TASK-047 |
| TASK-057 | Training Data Curator runtime, advisory outcomes, and atomic selected gate through production multi-evidence state | TASK-048, TASK-050, TASK-054, TASK-055 |

Equal wave values express dependency readiness only; canonical execution is
sequential. Each task owns only its exact feature AC and integration delta;
dependency proof remains with the dependency.

## Expected advisory change surface

- new Dataset owner: `backend/app/dataset_governance/` with local
  `models.py`, `repository.py`, `contracts.py`, `service.py`,
  `runtime_contracts.py`, and `runtime.py` as evidence requires;
- one migration under `backend/migrations/versions/` and focused tests under
  `tests/backend/dataset_governance/`;
- narrow source-owner wiring in `backend/app/photo_intake/service.py`,
  `backend/app/plant_operations/service.py`, and
  `backend/app/task_follow_up/service.py`, with their existing tests;
- narrow provider composition/roster registration under
  `backend/app/agent_runtime/` only where AD-011 requires it;
- no hard task write boundary is inferred from these advisory paths.

## Tests, gates, and UAT

- focused Dataset aggregate/transition/association/runtime pytest by task;
- source-owner regressions separately for photo, operations, and task follow-up;
- PostgreSQL archive/revoke/candidate-version/concurrency plus append-failure
  and append-success/commit-failure probes on isolated rollback-safe state;
- migration upgrade/downgrade and dynamic linear-head compatibility;
- deterministic provider fake/spy success/error/unbound/no-fallback matrices;
- `node scripts/mb-lint.mjs`, `git diff --check`, and task-proportionate full
  deterministic regression;
- no HTTP/UI UAT exists in FT-014. Each T3 task followed normal
  `/verify` and `/red-verify`; the feature-completion
  `/red-verify --feature FT-014` gate ran and recorded
  `SEMANTIC_VERDICT: semantic-pass`.

## Governing sources and constraints

- Governing requirements: REQ-011 and REQ-019.
- REQ-003, REQ-010, and REQ-020 are non-owning normative constraints carried
  through ActorContext, Timeline, redaction, local-only, and lifecycle specs;
  they are not task claims.
- [AD-006](../../architecture/system-architecture.md#ad-006---dataset-trainability-is-evidence-gated-state)
  owns trainability authority; [AD-007](../../architecture/system-architecture.md#ad-007---archived-plant-is-a-global-operational-deny)
  owns archive/restore behavior; [AD-011](../../architecture/system-architecture.md#ad-011---dataset-agents-use-a-registered-advisory-only-runtime-route)
  owns the Dataset Agent exception.
- [Dataset Governance State](../../states/dataset-governance.md),
  [Dataset Governance Data](../../domains/dataset-governance.md),
  [Dataset Agents Runtime](../../contracts/dataset-agents-runtime.md),
  [Timeline Event](../../contracts/timeline-event.md), and
  [Dataset Verification](../../testing/dataset-governance.md) are direct
  canonical design/proof owners.
- [FT-014 clarification](../../../.protocols/FT-014/clarification.md) and
  [decision log](../../../.protocols/FT-014/decision-log.md) record the accepted
  production positive route and rebuild authority.

## Invariants

- New candidates and every association remain non-trainable until the sole
  transition authority confirms them under the exact policy.
- No caller/model/Timeline/manifest/UI/Bus value sets evidence association,
  lifecycle, quality, split, confirmation, or `can_train_on` directly.
- Every state-advancing write repeats current session/membership/Plant/grant
  and candidate version under canonical lock order; archive/restore never
  resumes work automatically.
- Timeline is audit/export only; append noise never repairs PostgreSQL state.
- Production remains unbound and fail-closed until the separate provider
  selection milestone.

## Handoff

Queue action: `rebuilt`, then fully executed to terminal `done` under Planning
Revision 3 APPROVE. W6 remediation (TASK-058/059/060) is also terminal `done`.
Feature `lifecycle` stays `implemented`; feature-level `SEMANTIC_VERDICT:
semantic-pass` is recorded. Feature-level `verified` and promotion remain
scheduler/owner-owned decisions after the applicable post-sync gates.
