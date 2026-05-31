---
description: Feature-local SDD tech spec for FT-009 dataset governance and trainability.
status: active
owner: architecture
last_updated: 2026-05-31
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/features/FT-009-dataset-governance-trainability.md
  - .memory-bank/spec-index.md
---
# FT-009 Dataset Governance and Trainability Tech Spec

## Scope

This spec closes the feature-local SDD design handoff for FT-009 before `/prd-to-tasks FT-009`.

FT-009 owns the MVP governance layer for future training/evaluation candidates:

- dataset item metadata boundary without a full dataset registry;
- transition command/service shape over the authoritative dataset lifecycle state spec;
- trainability recomputation and denial reasons;
- subject/evidence/provenance refs;
- curator decision handling;
- audit refs for lifecycle changes;
- API/service surfaces needed for task decomposition.

FT-009 does not own real fine-tuning, export packaging, server sync, model evaluation infrastructure, human review UI, photo intake, agent runtime adapters, or a separate Training Data Curator public contract.

## Normative Inputs

- [.memory-bank/states/dataset-governance.md](../states/dataset-governance.md): authoritative dataset lifecycle, actor/source rules, transition matrix, trainability rule, forbidden transitions, and audit fields.
- [.memory-bank/domains/runtime-data-model.md](../domains/runtime-data-model.md): `dataset_items`, human review refs, and PostgreSQL/read-model authority.
- [.memory-bank/domains/photo-artifacts.md](../domains/photo-artifacts.md): photo manifests/export snapshots are artifacts, not mutable dataset authority.
- [.memory-bank/contracts/message-envelope.md](../contracts/message-envelope.md): agent hypotheses default to `can_train_on=false`.
- [.memory-bank/tech-specs/FT-003-runtime-state-timeline-audit.md](FT-003-runtime-state-timeline-audit.md): runtime table boundary and timeline refs.
- [.memory-bank/tech-specs/FT-005-ui-feed-context-hygiene.md](FT-005-ui-feed-context-hygiene.md): UI Feed and spoiler notes are not facts, labels, or trainable data.
- [.memory-bank/testing/index.md](../testing/index.md): dataset governance policy and anti-cheat gates.
- [.memory-bank/invariants.md](../invariants.md): trainability, source-of-truth, and raw-output prohibitions.

## Design Decisions

### Dataset Item Boundary

FT-009 adds governance metadata for existing evidence subjects. It must not become a broad dataset registry.

Allowed MVP subject types:

| Subject type | Example subject ref |
|---|---|
| `photo` | `photo:<photo_id>` |
| `daily_observation` | `observation:<observation_id>` |
| `manual_measurement` | `measurement:<measurement_id>` |
| `agent_output` | `message:<message_id>` or `bus:<bus_event_id>` |
| `follow_up_outcome` | `task:<task_id>:outcome` |
| `export_candidate` | `export_candidate:<id>` |

Minimum dataset item fields:

| Field | Rule |
|---|---|
| `dataset_item_id` | Backend-generated stable ID. |
| `subject_type` / `subject_ref` | Required link to the governed evidence item. |
| `plant_id` | Required when plant-bound; MVP value `tomato_001`. |
| `status` | One value from `states/dataset-governance.md`. |
| `split` | `train`, `eval`, `holdout`, or null. |
| `curator_decision` | `selected`, `deferred`, or `rejected`. |
| `confirmation_source` | null, `curator_auto`, `human`, `expert`, or `batch_review`. |
| `evidence_refs` | List of domain evidence refs; required for trainability. |
| `curator_notes_ref` | Optional ref to curator notes; no raw chain-of-thought. |
| `corrected` | Boolean correction marker. |
| `follow_up_seen` | Boolean follow-up evidence marker. |
| `can_train_on` | Derived/stored result recomputed from the trainability rule. |
| `provenance` | Source/model/prompt/reviewer/timestamp fields when applicable. |
| `event_refs` | Timeline or domain event refs for transition audit. |

### Initial Creation

- New photo, observation, measurement, or follow-up evidence can initialize a dataset item as `raw` when the owning workflow needs governance metadata.
- Validated agent output can create or update an item to `agent_labeled` only through a `MessageEnvelope` / domain adapter path.
- Initial creation sets `can_train_on=false`.
- Split and confirmation source stay null unless a later valid transition sets them.

### Transition Service

All status/split/curator changes must use one governance transition service. Direct writes to `status`, `split`, `curator_decision`, `confirmation_source`, or `can_train_on` are forbidden outside that service.

Transition command shape:

| Field | Rule |
|---|---|
| `dataset_item_id` or `subject_ref` | Identifies the item. |
| `actor_type` | One actor/source allowed by `states/dataset-governance.md`. |
| `actor_id` / `source_id` | Stable actor/source ID. |
| `target_status` | Requested lifecycle status. |
| `split` | Optional requested split change. |
| `curator_decision` | Optional requested curator decision. |
| `confirmation_source` | Required when target status needs confirmation. |
| `reason_code` | Required machine-readable reason. |
| `evidence_refs` | Required when transition affects confirmation/trainability. |
| `review_id` | Required or optional according to actor/transition. |
| `curator_notes_ref` | Optional safe notes ref. |

The service validates the transition matrix, actor/source rules, forbidden combinations, and side effects from the dataset governance state spec.

### Trainability Recompute

Every transition recomputes `can_train_on`.

The result should include machine-readable denial reasons when false, such as:

- `status_not_trainable`;
- `split_not_train`;
- `curator_not_selected`;
- `missing_evidence_refs`;
- `confirmation_source_missing`;
- `gold_requires_human_expert_or_batch`;
- `agent_or_ui_content_not_trainable`;
- `conflict_or_correction_pending`.

`can_train_on=true` is allowed only by the rule in [.memory-bank/states/dataset-governance.md](../states/dataset-governance.md). The API and persistence layer must reject client-provided attempts to force this flag.

### Evidence Refs

Evidence refs must be stable domain refs, not presentation or execution artifacts.

Allowed evidence refs include:

- photo refs;
- observation refs;
- measurement refs;
- follow-up outcome refs;
- human review refs;
- approval/rejection refs where relevant;
- timeline event refs;
- validated MessageEnvelope/Bus refs only as provenance for agent-labeled status, not as sole confirmation evidence unless later review/follow-up supports it.

Forbidden as evidence for trainability:

- UI Feed events and spoiler notes;
- raw Agno output, provider messages, hidden reasoning, or prompt traces;
- stale export snapshots as current mutable authority;
- unreviewed raw agent hypotheses;
- local filenames/folders without catalog/runtime refs.

### Curator Rules

- `curator_auto` may select/defer/reject ordinary items and confirm ordinary train items only with strong evidence refs.
- For MVP, strong evidence means non-empty stable domain refs that are not UI-only, not raw model output, not stale export snapshot authority, and sufficient to reproduce the decision path.
- `curator_auto` cannot create `gold`.
- Conflict, low-confidence, rare valuable examples, gold candidates, and high-impact labels route to `needs_review` unless already resolved by human, expert, or batch review.
- A standalone Training Data Curator contract is not required for FT-009 decomposition. If future agent-runtime work needs a public curator output contract, create it through a later spec route.

### Authority And Export Boundary

- PostgreSQL/read model owns current dataset item state and `can_train_on`.
- Photo manifests and export snapshots may include dataset snapshots for export only.
- `timeline.jsonl` records transition audit/export evidence only.
- If export snapshot or timeline data conflicts with PostgreSQL dataset state, PostgreSQL wins for current state and the conflict should be reported as an integrity issue.

## API Surface

Minimum FT-009-owned API/service surface:

- `GET /api/dataset/items/{dataset_item_id}`
  - returns current dataset governance state from PostgreSQL/read model.
- `GET /api/dataset/items?subject_ref=...`
  - finds governance metadata for an evidence subject.
- `POST /api/dataset/items`
  - creates a raw governance item for an existing evidence subject when needed.
- `POST /api/dataset/items/{dataset_item_id}/transitions`
  - applies a validated governance transition and returns current state plus trainability denial/allow reasons.
- `GET /api/dataset/items/{dataset_item_id}/trainability`
  - returns computed `can_train_on` and reasons from current PostgreSQL state.

Exact route names may change in implementation, but task decomposition must preserve the single transition service, current-state authority, and trainability recomputation behavior.

## Verification Targets

Required before FT-009 can be marked implemented:

- `node scripts/mb-lint.mjs`
- `node scripts/mb-doctor.mjs`
- Schema tests for dataset item fields, subject refs, provenance, transition command fields, and transition audit fields.
- Policy tests for every allowed/forbidden transition in `states/dataset-governance.md`.
- Policy tests proving `can_train_on=true` cannot be client-forced and is recomputed after every transition.
- Trainability denial-reason tests for status, split, curator decision, missing evidence, missing confirmation source, gold restrictions, conflicts, and UI/raw-output exclusions.
- Integration tests proving current dataset state is read from PostgreSQL/read model, not photo manifests, export snapshots, UI Feed, or `timeline.jsonl`.
- MessageEnvelope integration tests proving agent outputs can create `agent_labeled` provenance but cannot become trainable by themselves.
- Audit tests proving trainability-affecting transitions include actor, reason, evidence, review/curator, and event refs where applicable.
- Anti-cheat tests proving eval/holdout, raw, agent-labeled, weak-evidence, UI-only, stale snapshot, and raw Agno-output items cannot become trainable.

## Gaps And Non-Goals

- No FT-009 blocker remains for `/prd-to-tasks FT-009`.
- Exact ORM names, Alembic revision names, Pydantic class names, route names, and fixture shapes belong to implementation tasks.
- Full dataset registry, object storage, real fine-tuning, model evaluation service, server sync, public Training Data Curator output contract, and export package generation are outside FT-009 MVP scope.
