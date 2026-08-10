---
description: Exact Dataset Candidate persistence, creation seam, transition authority transactions, and migration rules for FT-014.
status: active
type: data_spec
last_updated: 2026-08-10
source_of_truth:
  - .memory-bank/features/FT-014-dataset-governance-trainability.md
  - .memory-bank/states/dataset-governance.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/glossary.md
  - .protocols/FT-014/decision-log.md
---
# Dataset Governance Data

## Scope

Exact PostgreSQL persistence, creation seam, transition-authority
transactions, derived `can_train_on` recomputation, and migration rules for
the Dataset Governance module (`backend/app/dataset_governance/`). The global
lifecycle boundary, enum semantics, and forbidden trainability sources remain
owned by
[.memory-bank/states/dataset-governance.md](../states/dataset-governance.md);
this spec supplies the feature-local exact shape it delegates to FT-014.

## Out of scope

- Any HTTP boundary, review UI, or FT-016 dataset-fields read surface
  (operator decision D1; deferred to later planning);
- full dataset registry, export snapshots/packaging, real fine-tuning, ML
  training jobs, and model evaluation (Constitution VIII; decision D9);
- agent-output evidence wiring (D2) and provider invocation mechanics, which
  live in
  [.memory-bank/contracts/dataset-agents-runtime.md](../contracts/dataset-agents-runtime.md);
- Farm-level (Plant-less) candidates — every MVP evidence source is
  Plant-scoped, so `plant_id` is mandatory in this schema;
- hard delete, candidate merge/split tooling, and sensor-window refs (future
  sensor stage).

## Related specs

- [.memory-bank/states/dataset-governance.md](../states/dataset-governance.md):
  global lifecycle, transition table, strong-evidence policy, and forbidden
  sources.
- [.memory-bank/domains/runtime-data-model.md](runtime-data-model.md): shared
  native-UUID/non-cascading relational identity contract.
- [.memory-bank/domains/photo-artifacts.md](photo-artifacts.md): immutable
  Photo Intake `can_train_on=false` source assertion.
- [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md):
  append-only audit/export writer seam.
- [.memory-bank/contracts/dataset-agents-runtime.md](../contracts/dataset-agents-runtime.md):
  advisory curator/governance model results and the curator gate caller.

## Shared storage rules

- Product identifiers and FK columns use PostgreSQL native `uuid` via
  SQLAlchemy `Uuid(as_uuid=True)`, matching the cross-feature relational
  identity contract.
- Enum columns use the exact canonical value sets from
  [states/dataset-governance.md](../states/dataset-governance.md) and
  [glossary.md](../glossary.md); no additional values.
- Timestamps are timezone-aware UTC (`created_at`, `updated_at`).
- The table carries no secret, credential, absolute-path, raw provider, or raw
  agent-output columns; evidence refs are typed UUID references only.

## `dataset_candidates`

One row per Dataset Candidate governance record:

- `candidate_id` uuid PK, application-generated UUIDv4;
- `farm_id` uuid NOT NULL, FK -> Farm, `ON DELETE RESTRICT`;
- `plant_id` uuid NOT NULL, FK -> Plant, `ON DELETE RESTRICT`;
- `candidate_status` enum
  `candidate|needs_review|confirmed|rejected|excluded` NOT NULL, default
  `candidate`;
- `candidate_origin` enum `raw|agent_labeled` NOT NULL, default `raw`;
- `quality_tier` enum `standard|gold` NOT NULL, default `standard`;
- `split` enum `train|eval|holdout` NULL, default NULL (MVP assigns no split);
- `confirmation_source` enum
  `curator_auto|human_review|expert_review|batch_review` NULL, default NULL;
- `evidence_refs` JSONB array of typed ref objects NOT NULL with
  `CHECK (jsonb_array_length(evidence_refs) >= 1)`;
- `source_kind` enum
  `photo_catalog_item|daily_check_in|manual_measurement|follow_up_outcome`
  NOT NULL — the originating evidence flow that created the candidate;
- `source_ref` uuid NOT NULL — the originating evidence row identity;
- `curator_decision` enum `selected|deferred|rejected` NULL — advisory
  Training Data Curator result, never lifecycle or trainability authority;
- `curator_notes_ref` text NULL — pointer to internal curator notes;
- `curator_run_id` uuid NULL UNIQUE, `curator_command_sha256` char(64) NULL,
  and `curator_recorded_at` timestamptz NULL — all-or-none identity of the
  latest persisted Training Data Curator advisory result;
- `corrected` boolean NOT NULL, default false — human/review corrected label
  or metadata;
- `follow_up_seen` boolean NOT NULL, default false — a follow-up outcome
  evidence ref exists;
- `can_train_on` boolean NOT NULL, default false — stored derived value,
  recomputed only by the transition authority below;
- `record_version` integer NOT NULL, default 1 — incremented by every candidate
  advisory, evidence-association, or lifecycle mutation;
- `event_refs` JSONB array NOT NULL, default `[]` — ordered returned Timeline
  refs for candidate creation, evidence association, and lifecycle changes;
- `created_at`, `updated_at` timestamptz NOT NULL.

Integrity rules:

- Named normal unique constraint `uq_dataset_candidates_source_identity` on
  `(plant_id, source_kind, source_ref)` makes repeated creation-seam delivery
  for the same canonical source row idempotent. Source commands that create a
  new source-row UUID are new evidence, not retries of the same identity.
- `CHECK` enforces all-or-none
  `curator_run_id|curator_command_sha256|curator_recorded_at` and a lowercase
  64-hex command digest. A persisted curator run identifies exactly one
  candidate through the unique nullable `curator_run_id`.
- `CHECK` constraints forbid `quality_tier='gold'` unless
  `candidate_status='confirmed'` and
  `confirmation_source IN ('human_review','expert_review','batch_review')`,
  and forbid `can_train_on=true` unless `candidate_status='confirmed'` and
  `confirmation_source IS NOT NULL`. The service-level rules remain the
  authority; the checks are the last-line invariant.
- Relations are restrictive and non-cascading: Plant archive/restore never
  deletes or mutates candidate rows; archived-Plant candidates stay retained
  and readable, and advance only through a new authorized transition request
  that passes the current owning guards after restore.

### Evidence ref objects

Each `evidence_refs` item is exactly:

```json
{"kind": "photo|check_in|measurement|follow_up_outcome|review|observation", "ref": "<uuid>"}
```

- `kind` is closed; `ref` is the UUID of the referenced runtime record.
- Refs are validated service-side against existing, same-Farm/same-Plant
  records before any transition that could make data trainable; unresolvable
  or cross-Farm/Plant refs reject the transition.
- UI Feed rows, timeline snapshots, manifests, raw agent output, and raw
  Companion content are not valid evidence refs and are rejected by kind
  validation.

## Creation seam

One internal service method, e.g.
`DatasetGovernanceService.record_dataset_evidence(command)`, is the only
candidate-creation path. Wired callers (decision D2, same-UoW per D8):

| Source flow (owner) | `source_kind` | Initial `evidence_refs` |
|---|---|---|
| Photo Intake `accept_photo` (FT-005) | `photo_catalog_item` | `photo` |
| Plant Operations `create_check_in` (FT-004) | `daily_check_in` | `observation` |
| Plant Operations `create_manual_measurement` (FT-004) | `manual_measurement` | `measurement` |
| Task & Follow-Up `record_outcome` (FT-012) | `follow_up_outcome` | `follow_up_outcome` |

Rules:

- The seam runs inside the caller's unit of work; candidate insert and source
  mutation commit or roll back together.
- Callers pass only service-side identities (ActorContext, Plant, source row);
  no caller may pass `candidate_status`, `quality_tier`, `confirmation_source`,
  `can_train_on`, `split`, or curator fields.
- New rows always start `candidate`, `raw`, `standard`, `split=NULL`,
  `confirmation_source=NULL`, `can_train_on=false`; a `follow_up_outcome`
  source sets `follow_up_seen=true`.
- The source flow's current authorization/archive guards already passed; the
  seam revalidates the current Plant/Farm identity of the source row so
  unauthorized context cannot mix into a candidate.
- Creation appends one redacted `dataset_candidate_created` Timeline ref.
  The returned ref is appended to `event_refs` before the source owner's
  commit; append failure rolls back the candidate and source mutation, while
  append success followed by commit failure is non-authoritative audit noise.
- The Photo Intake immutable `can_train_on=false` catalog assertion is
  unchanged; the created candidate is evaluated only by Dataset Governance.

## Follow-up evidence association command

The internal `AssociateFollowUpEvidenceCommandV1` is the only production path
that adds evidence to an existing candidate in FT-014. It is invoked by
`TaskFollowUpService.record_outcome` inside that command's existing PostgreSQL
unit of work after the new Outcome identity and its already-authorized
`evidence_refs` are available.

The command receives only `schema_version=1`, service-side current
`ActorContext`, `plant_id`, the locked Outcome row, and its canonical ordered
source refs. It accepts no caller-selected `candidate_id`, arbitrary evidence
body, lifecycle/quality/split/confirmation/trainability field, curator field,
or policy result.

Rules:

- map only `photo_catalog_item|daily_checkin|manual_measurement` Outcome source
  refs to their exact Dataset source identities; `plant` and
  `plant_state_record` refs have no FT-014 source candidate and are ignored;
- reload/lock the current LocalSession, Account, Membership, active Plant,
  applicable grant, Outcome, source rows, and matching candidate rows in the
  project's canonical lock order; all identities must match one Farm/Plant;
- only `candidate|needs_review` rows are eligible; confirmed/terminal rows are
  retained unchanged and never enriched or reopened;
- append exactly
  `{"kind":"follow_up_outcome","ref":"<outcome_id>"}` when absent, derive
  `follow_up_seen=true`, increment `record_version`, update `updated_at`, and
  leave every lifecycle/quality/split/confirmation/curator/trainability field
  unchanged;
- append one `dataset_candidate_evidence_linked` Timeline ref per changed
  candidate and store it in `event_refs`; identical delivery changes no row and
  appends no event; and
- return `AssociateFollowUpEvidenceResultV1` with the ordered changed
  `candidate_id` values and unchanged-match count. Zero eligible matches is a
  successful no-op and does not alter the separate Outcome candidate.

Any association validation, Timeline append, or PostgreSQL failure rolls back
the entire `record_outcome` transaction. Timeline appends already written
before a later commit failure remain non-authoritative audit noise and cannot
repair candidate state.

## Transition authority transactions

One service transaction owns every lifecycle change; there is no other writer
of `candidate_status`, `quality_tier`, `confirmation_source`, or
`can_train_on`. The exact transition table and strong-evidence policy are
defined in
[states/dataset-governance.md](../states/dataset-governance.md#ft-014-transition-authority);
persistence-level rules:

- Every transition command carries the current ActorContext, `candidate_id`,
  target transition, expected current status, and expected `record_version`.
  It locks/rechecks the current LocalSession, Account, Membership, active
  Plant/grant, and candidate row in canonical order, so archive/revoke,
  concurrent advisory/association, or stale transitions conflict before write.
- Confirm transitions validate evidence refs (existence, same Farm/Plant,
  allowed kinds) inside the same transaction; `agent_labeled` rows reject
  every confirm transition in MVP (decision D5).
- `curator_auto` confirmation additionally requires exact equality between the
  command `curator_run_id|curator_command_sha256`, the locked persisted
  current-run identity, and `curator_decision='selected'`, plus the
  strong-evidence policy result. The policy evaluates canonical row state
  only, never model wording.
- Review confirmations (`human_review|expert_review|batch_review`) may set
  `quality_tier='gold'`; every other path rejects `gold`.
- `rejected` and `excluded` are terminal in MVP; `confirmed` rows may later be
  `excluded` (e.g. evidence invalidated) which recomputes
  `can_train_on=false`. No other reverse transitions exist.
- Every transition recomputes `can_train_on` (below), updates `updated_at`,
  increments `record_version`, and appends one redacted
  `dataset_candidate_reviewed` Timeline ref to `event_refs`; the transition
  and ref commit in one UoW. Append failure rolls the transition back; append
  success plus later commit failure is non-authoritative audit noise.

### Derived `can_train_on`

`can_train_on` is recomputed by the transition authority on every mutation
as exactly:

```text
candidate_status = 'confirmed'
AND evidence_refs is non-empty (validated)
AND confirmation_source IS NOT NULL
```

It is false in every other state. It is never caller-, request-, agent-,
manifest-, timeline-, or UI-writable; a supplied `can_train_on=true` in any
command or agent result is rejected and the value is recomputed from
canonical state.

## Curator/governance advisory writes

The dataset-agents runtime persists only `curator_decision`,
`curator_notes_ref`, and the all-or-none current-run identity through a
dedicated advisory seam. It locks the current authorization/Plant/grant and
candidate version after provider I/O. Deferred/rejected results commit only the
advisory fields and increment `record_version`; silence writes nothing.
Selected results are never left as a reusable stale selection: selected
advisory identity and `curator_auto` transition commit together, while policy,
audit, guard, or commit failure rolls both back. Advisory writes never change
evidence, lifecycle, quality, split, or trainability outside that atomic gate.
See
[contracts/dataset-agents-runtime.md](../contracts/dataset-agents-runtime.md).

## Migration sequence

- One additive Alembic revision `ft014_dataset_candidates`, parented on the
  linear head current at execution (`ft013_decision_effects` at planning
  time; the executor confirms the actual head at preflight — this spec does
  not pin a mutable exact head).
- Creates the enum types, `dataset_candidates` table, check constraints,
  normal source-identity uniqueness, unique curator-run identity, and indexes
  above; `downgrade` drops them in reverse.
- No existing table, enum, or Photo Intake assertion changes.

## Stable domain failures

- `dataset_candidate_not_found` — unknown `candidate_id`.
- `dataset_candidate_conflict` — stale expected status or concurrent
  transition.
- `dataset_transition_forbidden` — illegal transition, `agent_labeled`
  confirm, or `gold` without human/expert/batch review.
- `dataset_evidence_invalid` — empty, unresolvable, cross-Farm/Plant, or
  forbidden-kind evidence refs.
- `dataset_confirmation_policy_violation` — strong-evidence policy or
  curator-selection precondition failed for `curator_auto`.
- `dataset_evidence_association_conflict` — stale candidate version,
  unsupported/cross-scope derived link, or concurrent association conflict.
- `dataset_trainability_assign_forbidden` — caller/agent attempted to supply
  `can_train_on`, status, tier, split, or confirmation fields directly.

## Verification

See [.memory-bank/testing/dataset-governance.md](../testing/dataset-governance.md).
Tests must prove: default/enum shape; derivation and anti-assignment;
transition matrix including gold/curator_auto/`agent_labeled` guards;
evidence-ref validity and Plant scoping; same-UoW creation wiring and
idempotency; migration upgrade/downgrade and head compatibility; Timeline
cardinality; and that no MVP path performs export packaging, fine-tuning, or
server upload.
