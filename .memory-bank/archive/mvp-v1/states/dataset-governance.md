---
description: Dataset lifecycle, provenance, split restrictions, and trainability rules.
status: active
owner: architecture
last_updated: 2026-05-31
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/spec-index.md
---
# Dataset Governance

## Dataset Status

Allowed `dataset.status` values:

- `raw`
- `agent_labeled`
- `needs_review`
- `confirmed`
- `rejected`
- `gold`
- `excluded`

## Separate Fields

The following are fields, not statuses:

- `dataset.split`: `train`, `eval`, `holdout`, or null;
- `dataset.curator_decision`: `selected`, `deferred`, or `rejected`;
- `dataset.confirmation_source`: null, `curator_auto`, `human`, `expert`, or `batch_review`;
- `dataset.evidence_refs`;
- `dataset.curator_notes_ref`;
- `dataset.corrected`;
- `dataset.follow_up_seen`;
- `can_train_on`.

## Trainability Rule

`can_train_on=true` is allowed only when:

```text
dataset.curator_decision = selected
AND dataset.split = train
AND dataset.evidence_refs is not empty
AND (
  dataset.status = confirmed
  AND dataset.confirmation_source in {curator_auto, human, expert, batch_review}
  OR
  dataset.status = gold
  AND dataset.confirmation_source in {human, expert, batch_review}
)
```

`dataset.split=eval` and `dataset.split=holdout` must never be used for fine-tuning/train.

## Gold and Curator Rules

- `gold` requires human, expert, or batch review approval.
- `curator_auto` may confirm ordinary train items only when strong `evidence_refs` exist.
- `curator_auto` cannot create `gold`.
- Raw, agent-labeled, and weak-evidence items are not trainable.

## Lifecycle Authority

`dataset.status` changes only through an explicit governance transition. A transition is valid only when the actor/source, required fields, evidence refs, and side effects below are satisfied.

PostgreSQL/read model owns the current mutable dataset status, split, curator fields, confirmation source, review refs, evidence refs, event refs, and `can_train_on`. Photo manifests and `timeline.jsonl` may preserve snapshots/evidence trails, but they do not define current mutable dataset state.

## Actors And Sources

- `agent`: may create hypotheses and request review; cannot confirm, select trainability, or create `gold`.
- `curator_auto`: may select/defer/reject ordinary items and confirm ordinary train items only with strong `evidence_refs`; cannot create `gold`.
- `user`: may create raw observations/photos and provide source material; does not by itself confirm dataset trainability unless recorded through a human review transition.
- `human`: may approve, correct, reject, confirm, or promote to `gold`.
- `expert`: same as `human`, intended for specialist label/review authority.
- `batch_review`: may confirm or promote reviewed batches when the batch review artifact is referenced.
- `system`: may initialize `raw`, exclude invalid/corrupt inputs, or force `needs_review` for conflicts according to deterministic validation rules.

Conflict, low confidence, rare valuable examples, gold candidates, and high-impact labels must route to `needs_review` unless a human, expert, or batch review has already resolved them.

## Transition Matrix

| From | To | Allowed actor/source | Required fields / refs | Side effects |
|---|---|---|---|---|
| new | `raw` | `system`, `user`, import workflow | subject ref, source/provenance, `created_at` | `can_train_on=false`; split and confirmation source remain null unless later selected. |
| `raw` | `agent_labeled` | `agent` through validated `MessageEnvelope` / domain adapter | `source_refs`, `model_version`, `prompt_version`, confidence or claim metadata, event ref | `can_train_on=false`; confirmation source remains null. |
| `raw` | `needs_review` | `system`, `curator_auto`, `human`, `expert`, `batch_review` | reason code and evidence/source refs | `can_train_on=false`; `curator_decision` should be `deferred` unless immediately rejected. |
| `raw` | `excluded` | `system`, `curator_auto`, `human`, `expert`, `batch_review` | exclusion reason and evidence/source refs | `can_train_on=false`; `curator_decision=rejected` when exclusion is a curator decision. |
| `agent_labeled` | `needs_review` | `system`, `curator_auto`, `human`, `expert`, `batch_review` | reason code, agent output ref, evidence/source refs | `can_train_on=false`; preserve original agent refs. |
| `agent_labeled` | `confirmed` | `curator_auto`, `human`, `expert`, `batch_review` | non-empty strong `evidence_refs`, `confirmation_source`, curator/review ref when available | Recompute `can_train_on` from the Trainability Rule; `curator_auto` allowed only for ordinary non-gold items. |
| `agent_labeled` | `excluded` | `system`, `curator_auto`, `human`, `expert`, `batch_review` | unsafe/noisy/invalid label reason and source refs | `can_train_on=false`; preserve original agent refs for audit. |
| `needs_review` | `confirmed` | `human`, `expert`, `batch_review`, `curator_auto` | review or curator decision ref, non-empty `evidence_refs`, `confirmation_source` | Recompute `can_train_on`; `curator_auto` is valid only when the review need is resolved by strong evidence and the item is ordinary. |
| `needs_review` | `rejected` | `human`, `expert`, `batch_review`, `curator_auto` | rejection reason, review/curator ref, event ref | `can_train_on=false`; `curator_decision=rejected`. |
| `needs_review` | `excluded` | `system`, `human`, `expert`, `batch_review`, `curator_auto` | exclusion reason and evidence/source refs | `can_train_on=false`; use for data quality, privacy, safety, corruption, or out-of-scope items. |
| `confirmed` | `gold` | `human`, `expert`, `batch_review` | review approval ref, quality rationale, non-empty `evidence_refs`, `confirmation_source` in allowed set | Recompute `can_train_on`; `curator_auto` is forbidden. |
| `confirmed` | `needs_review` | `system`, `curator_auto`, `human`, `expert`, `batch_review` | conflict/follow-up/correction reason and source refs | `can_train_on=false` until reconfirmed. |
| `confirmed` | `excluded` | `system`, `human`, `expert`, `batch_review`, `curator_auto` | exclusion reason and evidence/source refs | `can_train_on=false`; preserve previous confirmation refs for audit. |
| `gold` | `needs_review` | `system`, `human`, `expert`, `batch_review` | conflict/correction reason and source refs | `can_train_on=false` until review restores eligibility. |
| `gold` | `excluded` | `system`, `human`, `expert`, `batch_review` | exclusion reason and evidence/source refs | `can_train_on=false`; preserve previous gold review refs for audit. |

`rejected` and `excluded` are terminal for MVP training eligibility. Reconsidering those items requires a new dataset item/version with explicit source refs rather than silently reusing the old item.

## Forbidden Transitions And Combinations

- `raw -> confirmed` without a review or evidence-based curator transition is forbidden.
- `raw -> gold`, `agent_labeled -> gold`, `needs_review -> gold`, and `curator_auto -> gold` are forbidden.
- `rejected -> confirmed`, `rejected -> gold`, `excluded -> confirmed`, and `excluded -> gold` are forbidden for the same dataset item/version.
- `can_train_on=true` is forbidden for `raw`, `agent_labeled`, `needs_review`, `rejected`, and `excluded`.
- `can_train_on=true` is forbidden when `dataset.split` is `eval`, `holdout`, or null.
- `can_train_on=true` is forbidden when `dataset.curator_decision` is not `selected`.
- `can_train_on=true` is forbidden when `dataset.evidence_refs` is empty.
- `gold` with `dataset.confirmation_source=curator_auto` is forbidden.
- Agent output, UI Feed content, spoiler notes, stale export snapshots, and raw Agno output must not become trainable labels.

## Trainability Side Effects

Every transition must recompute `can_train_on` from the Trainability Rule.

- Entering `raw`, `agent_labeled`, `needs_review`, `rejected`, or `excluded` sets `can_train_on=false`.
- Entering `confirmed` may set `can_train_on=true` only when all trainability conditions pass.
- Entering `gold` may set `can_train_on=true` only when all trainability conditions pass and confirmation source is `human`, `expert`, or `batch_review`.
- Any conflict, correction request, contradictory follow-up, privacy concern, data corruption, or exclusion reason sets `can_train_on=false` until a later valid confirmation transition.

## Transition Audit Fields

Each dataset lifecycle transition must be traceable through PostgreSQL refs and timeline/event evidence where applicable:

- `transitioned_at`
- `actor_type`
- `actor_id` or `source_id`
- `from_status`
- `to_status`
- `reason_code`
- `evidence_refs`
- optional `review_id`
- optional `curator_notes_ref`
- optional `event_refs`

Dataset transitions that affect trainability must have enough refs to reproduce why `can_train_on` was allowed or denied.

## Provenance

Dataset and agent-report provenance must preserve source, `model_version`, `prompt_version`, reviewer role when reviewed, `created_at`, and outcome/evidence refs when available.

## Verification Targets

- Schema/unit tests cover allowed and forbidden lifecycle transitions.
- Policy tests prove `can_train_on=true` cannot be set for raw, agent-labeled, review-needed, rejected, excluded, eval, holdout, null-split, or weak-evidence items.
- Policy tests prove `gold` cannot be created by `curator_auto`.
- Policy tests prove conflicts or contradictory follow-up reset trainability until reconfirmed.
- Integration tests prove mutable dataset state is read from PostgreSQL/read model, not photo manifests or `timeline.jsonl`.
- Audit tests prove trainability-affecting transitions include actor, reason, evidence, and event/review refs where applicable.
