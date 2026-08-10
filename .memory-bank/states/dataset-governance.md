---
description: Global dataset governance and trainability lifecycle boundary for MVP v2.
status: active
type: state
last_updated: 2026-08-10
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/domains/runtime-data-model.md
---
# Dataset Governance

## Scope

Dataset Governance defines the global evidence and trainability boundary for
photo, measurement, follow-up, review, and agent-output evidence. It does not
create a full dataset registry or real fine-tuning path in MVP.

Exact persistence beyond the global fields below, endpoint schemas, and
UI behavior belong to `/feature-to-tasks FT-014`. The exact FT-014 transition
table and evidence policy are now fixed in
[FT-014 Transition Authority](#ft-014-transition-authority) below; exact
persistence lives in
[.memory-bank/domains/dataset-governance.md](../domains/dataset-governance.md),
and the dataset-agents runtime boundary lives in
[.memory-bank/contracts/dataset-agents-runtime.md](../contracts/dataset-agents-runtime.md).

## Scope Boundaries

- Defines: global non-trainable default, evidence-ref requirement, allowed
  trainability authority, forbidden sources, and verification requirements.
- Out of scope: full registry schema, ML training jobs, model evaluation,
  export packaging, or fine-tuning workflows.
- Related specs:
  - [.memory-bank/domains/dataset-governance.md](../domains/dataset-governance.md):
    exact Dataset Candidate persistence, creation seam, and transactions.
  - [.memory-bank/contracts/dataset-agents-runtime.md](../contracts/dataset-agents-runtime.md):
    advisory dataset-agents runtime and curator gate boundary.
  - [.memory-bank/testing/dataset-governance.md](../testing/dataset-governance.md):
    verification method and evidence.
  - [.memory-bank/domains/photo-artifacts.md](../domains/photo-artifacts.md):
    defines local photo evidence refs.
  - [.memory-bank/contracts/timeline-event.md](../contracts/timeline-event.md):
    defines audit/export event refs.
  - [.memory-bank/contracts/agent-chat-bus.md](../contracts/agent-chat-bus.md):
    defines agent-consumable evidence boundaries.

## Lifecycle Shape

Dataset candidates use one lifecycle field, `candidate_status`, with exactly:

- `candidate`
- `needs_review`
- `confirmed`
- `rejected`
- `excluded`

`candidate_origin` is exactly `raw|agent_labeled` and describes provenance,
not lifecycle state. `quality_tier` is exactly `standard|gold` and describes
quality, not lifecycle state.

Every Dataset Candidate governance record must carry:

- `farm_id`
- `plant_id` when Plant-scoped
- `evidence_refs`
- nullable `confirmation_source`:
  `curator_auto|human_review|expert_review|batch_review`
- `candidate_status`
- `candidate_origin`
- `quality_tier`
- derived `can_train_on=false` by default
- `created_at`
- `updated_at`

## Rules

- Dataset Governance is the sole authority that derives `can_train_on`.
  Commands, agents, source artifacts, manifests, timeline events, UI Feed, and
  imports cannot set it directly.
- `can_train_on` is true only when `candidate_status=confirmed`, the canonical
  FT-014 evidence policy accepts non-empty `evidence_refs`, and an allowed
  `confirmation_source` is recorded. It is false for every other state.
- New candidates start with `candidate_status=candidate`,
  `quality_tier=standard`, nullable `confirmation_source=null`, and derived
  `can_train_on=false`.
- `curator_auto` may confirm an ordinary candidate only under the exact FT-014
  strong-evidence policy. A `gold` designation additionally requires
  human, expert, or batch review and can never be granted by `curator_auto`.
- Candidate provenance (`raw|agent_labeled`), dataset split, curator output, or
  a `gold` designation alone never grants trainability.
- `photo_catalog_items.can_train_on=false` is an immutable Photo Intake
  assertion: accepting a photo never grants trainability. It is not a second
  mutable trainability authority; a later Dataset Candidate is evaluated only
  by Dataset Governance.
- Evidence refs are required before any future transition that could make data
  trainable.
- UI Feed, timeline snapshots, manifests, raw agent output, raw Companion
  content, and unreviewed model labels never grant trainability by themselves.
- Agent-labeled evidence remains non-trainable until a future explicit review
  path allows a transition.
- Full dataset registry, real fine-tuning, and production learning loops are
  out of MVP.
- Dataset/export context must stay Farm/Plant scoped and permission-aware.

## FT-014 Transition Authority

Accepted by operator decisions D1/D4/D5 (`.protocols/FT-014/decision-log.md`).
In MVP the transition authority is an internal backend service only; there is
no HTTP boundary or review UI. Exact transactions, locking, and failures live
in
[.memory-bank/domains/dataset-governance.md](../domains/dataset-governance.md).

### Transition table

| From | To | Authority | Conditions |
|---|---|---|---|
| `candidate` | `needs_review` | service review-request command | evidence refs remain non-empty |
| `candidate`, `needs_review` | `confirmed` | `human_review`, `expert_review`, or `batch_review` service command | evidence refs validate; `candidate_origin=raw` only in MVP (D5) |
| `candidate`, `needs_review` | `confirmed` | `curator_auto` | strong-evidence policy below plus persisted current-run `curator_decision=selected` |
| `candidate`, `needs_review` | `rejected` | any review command | terminal in MVP |
| `candidate`, `needs_review`, `confirmed` | `excluded` | any review command | terminal in MVP; recomputes `can_train_on=false` |

- Review confirmations may set `quality_tier=gold`; `curator_auto` and any
  unconfirmed path reject `gold`.
- MVP assigns no `split`; the field stays NULL.
- No other transitions exist; `rejected`/`excluded` have no outgoing
  transitions in MVP.

### Strong-evidence policy for `curator_auto`

`curator_auto` confirmation is permitted only when the canonical candidate
row satisfies all of:

- `candidate_origin=raw`;
- `quality_tier=standard`;
- at least two `evidence_refs` of at least two distinct kinds;
- at least one `follow_up_outcome` evidence ref (`follow_up_seen=true`);
- a persisted current-run `curator_decision=selected`.

The policy evaluates canonical row state only. When any condition fails, the
confirmation is rejected and the candidate keeps its current status.

### Production reachability

Positive `curator_auto` is required to be production-reachable in FT-014. The
sole route to its multi-evidence precondition is the internal
`associate_follow_up_evidence` command in
[Dataset Governance Data](../domains/dataset-governance.md#follow-up-evidence-association-command):
`record_follow_up_outcome` supplies an Outcome plus already-authorized source
refs, and Dataset Governance derives/locks matching source candidates before
appending the Outcome ref. No HTTP/UI/scheduler trigger and no caller-selected
candidate association exists.

Evidence association is not a lifecycle transition. It is allowed only for
`candidate|needs_review`, leaves `can_train_on=false`, and cannot confirm,
exclude, reject, set quality/split, or persist curator output. A later explicit
Training Data Curator invocation must persist the exact current run selection
and apply the `curator_auto` transition in one guarded transaction. Weak
evidence, stale/different run identity, post-I/O authority loss, audit failure,
or commit failure leaves neither a reusable selected advisory nor a lifecycle
change.

### MVP `agent_labeled` guard

MVP has no explicit review path for agent-labeled evidence, so
`agent_labeled` candidates cannot reach `confirmed`; every confirm transition
on them is rejected until a future review path allows it.

## Edge Cases And Errors

- Missing evidence refs block any trainability transition.
- A request or agent result that supplies `can_train_on=true` is rejected;
  trainability is recomputed from canonical governance state.
- `quality_tier=gold` on a non-confirmed candidate, or with
  `confirmation_source=curator_auto|null`, is rejected.
- Unauthorized Plant evidence must not be mixed into a dataset candidate.
- Follow-up association cannot enrich a confirmed/rejected/excluded candidate,
  accept a caller-selected candidate, or reuse a stale curator run.
- Raw model/provider output must not be stored as trainable fact.
- Server sync/upload wording must not appear because MVP sync status is
  `local_only`.

## Verification

Tests must prove:

- New dataset candidates default to `can_train_on=false`.
- Tests cover the exact `candidate_status` enum and prove that provenance and
  `gold` are not lifecycle states.
- Tests prove `can_train_on` is derived, cannot be assigned by a request or
  agent, and remains false when state, evidence, or confirmation is missing.
- Tests prove `curator_auto` cannot grant `gold` and that `gold` requires a
  confirmed candidate plus human/expert/batch review.
- Photo Intake tests continue to prove its immutable source assertion remains
  `can_train_on=false` without becoming governance authority.
- UI Feed, timeline, manifests, and raw agent output cannot set trainability.
- Evidence refs and Plant scope are preserved.
- Unauthorized context cannot mix into dataset/export records.
- No MVP path triggers real fine-tuning or server upload.
