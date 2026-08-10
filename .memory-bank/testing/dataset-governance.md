---
description: Verification method and evidence matrix for FT-014 Dataset Governance And Trainability.
status: active
type: testing_spec
last_updated: 2026-08-10
source_of_truth:
  - .memory-bank/states/dataset-governance.md
  - .memory-bank/domains/dataset-governance.md
  - .memory-bank/contracts/dataset-agents-runtime.md
  - .memory-bank/testing/strategy.md
---
# Dataset Governance Verification

## Scope

Verification for the FT-014 Dataset Governance aggregate, transition
authority, evidence-flow wiring, and provider-neutral dataset-agents runtime.
Global method stays in
[.memory-bank/testing/strategy.md](strategy.md); executor/provider mechanics
stay in
[.memory-bank/testing/agent-runtime.md](agent-runtime.md). There is no HTTP
surface in FT-014 (operator decision D1), so no API matrix exists.

## Aggregate, derivation, and transition matrix

- Migration/model tests prove the `dataset_candidates` table, native
  UUID/FK/enums, check constraints (non-empty `evidence_refs`; `gold` only
  for confirmed plus human/expert/batch review; `can_train_on=true` only for
  confirmed plus non-null `confirmation_source`), the named normal unique
  `(plant_id, source_kind, source_ref)` constraint, all-or-none/unique curator
  run identity, `record_version`, append-only `event_refs`, upgrade/downgrade, and
  compatibility with the linear migration head current at execution.
- Default tests prove new candidates start
  `candidate|raw|standard|split=NULL|confirmation_source=NULL|can_train_on=false`
  and that provenance and `gold` are not lifecycle states.
- Derivation/anti-assignment tests prove `can_train_on` is recomputed only by
  the transition authority and that any caller- or agent-supplied
  `can_train_on`, status, tier, split, or confirmation field is rejected
  (`dataset_trainability_assign_forbidden`).
- Transition tests cover the exact table in
  [states/dataset-governance.md](../states/dataset-governance.md#ft-014-transition-authority):
  legal transitions, terminal `rejected`/`excluded`, `confirmed -> excluded`
  recomputation, stale-status conflict (`dataset_candidate_conflict`), and
  row-lock concurrency.
- Evidence-gate tests prove transitions reject empty, unresolvable,
  cross-Farm/Plant, or forbidden-kind refs (`dataset_evidence_invalid`).
- Policy tests prove the strong-evidence gate: `curator_auto` confirms only
  raw/standard candidates with >=2 refs of >=2 distinct kinds,
  `follow_up_seen=true`, and a persisted current-run
  `curator_decision=selected`; every weaker combination is rejected
  (`dataset_confirmation_policy_violation`); `curator_auto` never grants
  `gold`; `gold` requires confirmed plus human/expert/batch review.
- Guard tests prove `agent_labeled` candidates reject every confirm
  transition in MVP (`dataset_transition_forbidden`).
- Timeline tests prove exactly one redacted `dataset_candidate_created` per
  creation and one `dataset_candidate_reviewed` per transition, with literal
  payload redaction, event-ref persistence, rollback on append failure, and
  non-authoritative noise when append succeeds before a failed DB commit.

## Follow-up evidence association matrix

- Command tests prove `AssociateFollowUpEvidenceCommandV1` derives targets only
  from the locked Outcome's already-authorized photo/check-in/measurement refs;
  caller-selected candidates and arbitrary evidence are structurally absent.
- PostgreSQL tests prove canonical lock ordering and current
  session/membership/active-Plant/grant/Outcome/source/candidate revalidation;
  archive, revoke, cross-scope, unsupported refs, stale version, and concurrent
  association fail closed without partial state.
- State tests prove only `candidate|needs_review` rows are eligible, the exact
  Outcome ref is added at most once, `follow_up_seen` and `record_version` are
  derived, lifecycle/quality/split/confirmation/curator/trainability remain
  unchanged, confirmed/terminal rows remain unchanged, and zero match is a
  successful no-op.
- Audit tests prove exactly one `dataset_candidate_evidence_linked` per changed
  candidate, no event for an idempotent no-op, whole-UoW rollback on append
  failure, and append-success/commit-failure noise with zero replay authority.

## Evidence-flow wiring matrix

- Integration tests prove `accept_photo`, `create_check_in`,
  `create_manual_measurement`, and `record_outcome` each create exactly one
  `raw` candidate with the typed initial evidence refs from
  [domains/dataset-governance.md](../domains/dataset-governance.md), inside
  the source flow's unit of work (candidate insert rolls back with source
  failure and vice versa).
- Retry/idempotency tests call the Dataset creation seam repeatedly for the
  same persisted source-row identity and prove one candidate through the named
  normal unique constraint. A new photo/check-in/measurement/Outcome UUID is
  correctly treated as new evidence rather than a duplicate retry.
- Scoping tests prove wrong-Farm/wrong-Plant or unauthorized context cannot
  create or mix into candidates, and that archived-Plant sources deny new
  candidates under the existing global operational guard.
- Compatibility tests prove the Photo Intake immutable
  `can_train_on=false` catalog assertion and existing FT-004/FT-005/FT-012
  public outcomes are unchanged.

## Dataset-agents runtime matrix

- Strict request tests prove exact `DatasetAgentCommandV1` and provider
  request fields, `command_sha256` fingerprint composition, and redaction
  (no secrets, paths, filenames, evidence bodies, UI/chat text).
- Result-validation tests prove unknown enums/extra fields and any
  lifecycle/tier/split/confirmation/`can_train_on` assignment attempt reject
  the model result (`invalid_model_result`).
- Advisory-persistence tests prove only `curator_decision` and
  `curator_notes_ref` plus the exact all-or-none current-run identity persist,
  that `silent` persists nothing, and that governance assessments persist
  nothing.
- Curator-gate tests prove selected-plus-policy-pass confirms via
  `curator_auto` with derived `can_train_on=true`, and that gold,
  `agent_labeled`, weak-evidence, deferred/rejected/silent, and stale-run
  selections never confirm. Selected advisory plus transition are atomic;
  policy/audit/guard/commit failure leaves no reusable selected run.
- Trigger tests prove only explicit `dataset_candidate_created` or internal
  `manual_review` invocations run the agents; page reads, startup, and domain
  events are not triggers.
- Executor tests prove deterministic fake/spy success/timeout/error paths and
  fail-closed unbound production with no fake/canned fallback.
- Outcome/audit tests prove every accepted explicit attempt returns the exact
  `DatasetAgentRuntimeOutcomeV1` branch and attempts one
  `dataset_agent_runtime_decided` append, including pre-I/O denial and unbound
  runtime; `audit_failed` returns no event/result and rolls back pending state.
- Concurrency tests prove post-I/O current session/membership/active-Plant/
  grant/candidate-version revalidation closes archive, revoke, and candidate
  mutation races before advisory/lifecycle writes.
- Anti-cheat/static tests prove no MessageEnvelope, Safety classification,
  Bus event, UI Feed row, or device effect is reachable from this runtime.

## Commands

- Focused:
  `.venv/bin/python -m pytest tests/backend/dataset_governance -m "not real_model" -q`
- Wiring regression:
  `.venv/bin/python -m pytest tests/backend/photo_intake tests/backend/plant_operations tests/backend/task_follow_up -m "not real_model" -q`
- Migration/head compatibility:
  `.venv/bin/python -m pytest tests/backend/test_foundation_database_contract.py tests/backend/dataset_governance/test_migration_models.py -q`
- Full deterministic regression:
  `.venv/bin/python -m pytest tests -m "not real_model" -q`
