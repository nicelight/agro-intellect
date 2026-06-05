---
description: Feature-local SDD tech spec for FT-016 dataset governance, trainability guardrails, and 200 MB local storage prompt.
status: active
feature_id: FT-016
owner: spec-improve
last_updated: 2026-06-05
source_of_truth:
  - .memory-bank/features/FT-016-dataset-governance-and-local-storage-prompt.md
  - .memory-bank/requirements.md
  - .memory-bank/invariants.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/states/core-lifecycles.md
  - .memory-bank/contracts/agent-harness.md
  - .memory-bank/tech-specs/FT-001-local-accounts-sessions-and-actor-context.md
  - .memory-bank/tech-specs/FT-002-farm-plant-lifecycle-and-plant-access-grant.md
  - .memory-bank/tech-specs/FT-005-photo-intake-catalog-and-capture-manifests.md
  - .memory-bank/tech-specs/FT-006-runtime-plant-state-history-and-timeline-audit.md
  - .memory-bank/tech-specs/FT-008-permission-aware-context-builder-and-agent-memory-record.md
  - .memory-bank/tech-specs/FT-009-message-envelope-agent-chat-bus-and-ui-feed-isolation.md
  - .memory-bank/tech-specs/FT-013-tasks-approvals-and-follow-up-outcomes.md
  - .memory-bank/tech-specs/FT-017-local-privacy-deployment-controls-and-secret-redaction.md
  - agents-best-practices
---
# FT-016 Dataset Governance And Local Storage Prompt Tech Spec

## Purpose

Define the minimum feature-local design needed before task decomposition for dataset
candidate governance fields, evidence refs, trainability guardrails, Dataset Governance
Agent boundaries, and the 200 MB local storage prompt.

This spec applies `agents-best-practices`: dataset actions are narrow typed proposals
or backend policy transitions, permissioned by ActorContext and Plant scope, traced,
bounded, and redacted. Dataset governance preserves future learning evidence without
turning the MVP into a full dataset registry, upload system, or fine-tuning product.

## Scope

In scope:

- DatasetCandidate metadata for existing evidence subjects;
- status, split, confirmation source, evidence refs, and `can_train_on` guardrails;
- transition and recomputation rules for trainability;
- Dataset Governance Agent and Training Data Curator boundaries;
- LocalStorageStatus measurement and 200 MB prompt behavior;
- privacy consistency with FT-017 `local_only`, no server upload, and redaction rules.

Out of scope:

- full dataset registry, real fine-tuning, object storage, server sync, remote backup,
  or production SaaS;
- broad labeling UI, expert review marketplace, or external dataset connectors;
- changing photo file/catalog/manifest authority owned by FT-005;
- changing sync/deployment/redaction rules owned by FT-017.

## Dataset Candidate Boundary

Dataset governance metadata attaches to existing evidence subjects such as accepted
photo refs, observations, manual measurements, outcomes, validated agent-labeled refs,
or review refs. It must not become a broad standalone dataset registry in MVP.

PostgreSQL/read model owns current dataset lifecycle fields. Photo manifests, timeline
events, export snapshots, UI Feed, Bus events, raw agent output, and AgentMemoryRecord
may provide refs but cannot grant trainability by themselves.

Minimum `DatasetCandidate` semantics:

```yaml
dataset_candidate_id: string
schema_version: string
created_at: datetime
updated_at: datetime
farm_id: string
plant_id: string
subject_ref: string
subject_type: photo | observation | measurement | outcome | agent_label | review
status: raw | agent_labeled | needs_review | confirmed | rejected | gold | excluded
split: train | eval | holdout | null
confirmation_source: curator_auto | human | expert | batch_review | null
curator_decision: selected | deferred | rejected | null
evidence_refs: []
source_refs: []
review_refs: []
follow_up_seen: boolean
corrected: boolean
can_train_on: boolean
trainability_reason_codes: []
trace_refs: []
redaction_status: redacted | no_sensitive_fields
```

Initial creation sets `status=raw`, `split=null`, `confirmation_source=null`,
`curator_decision=null`, and `can_train_on=false`.

## Dataset Lifecycle And Trainability

Allowed status semantics:

| Status | Meaning | Trainability |
|---|---|---|
| `raw` | Evidence subject exists but has no usable label/review yet. | Always false. |
| `agent_labeled` | Agent output labeled or described the subject through validated boundaries. | Always false by default. |
| `needs_review` | Candidate requires human/expert/batch or stronger evidence review. | Always false. |
| `confirmed` | Candidate has enough evidence or review for ordinary future use. | May become true only if all trainability conditions pass. |
| `rejected` | Candidate should not be used due to incorrectness or failed review. | Always false. |
| `gold` | High-quality reviewed example. | May become true only with human, expert, or batch review. |
| `excluded` | Candidate excluded for privacy, safety, corruption, scope, or quality. | Always false. |

`can_train_on=true` is allowed only when all conditions pass:

1. status is `confirmed` or `gold`;
2. split is `train`;
3. `curator_decision=selected`;
4. `evidence_refs` is non-empty and resolvable in authorized local evidence;
5. redaction succeeded;
6. no privacy/safety/exclusion reason is active;
7. for `gold`, `confirmation_source` is `human`, `expert`, or `batch_review`.

`curator_auto` may support ordinary `confirmed` train candidates only with strong
evidence refs. It cannot create `gold`.

Every dataset transition recomputes `can_train_on`. Direct client or agent writes to
force `can_train_on=true` are rejected.

## Forbidden Trainability Sources

The following never grant trainability by themselves:

- UI Feed, cards, spoiler notes, screenshots, or UI markdown;
- timeline snapshots or replay;
- photo manifests or export snapshots alone;
- raw agent output, hidden reasoning, provider memory, or Agno events;
- raw chat or unapproved governance discussion;
- AgentMemoryRecord;
- Bus events without authoritative dataset transition;
- storage prompt acknowledgement/dismissal;
- server/upload copy, because no server-sync stage exists in MVP.

If any transition is influenced by untrusted user/uploaded/provider content, it remains
trust-labeled as data and must be supported by explicit evidence refs.

## Dataset Governance Agent Boundary

The Dataset Governance Agent profile may:

- inspect authorized dataset candidate refs through the context builder;
- propose candidate status, split, curator decision, or review-needed transitions;
- produce trainability denial/allow reason summaries;
- stay silent when evidence is insufficient.

It must not:

- set `can_train_on=true` directly;
- read unauthorized Farm/Plant evidence;
- use UI Feed, raw chat, raw provider output, hidden reasoning, or unapproved governance
  content as dataset facts;
- imply upload, server sync, cloud backup, or real fine-tuning;
- override FT-017 local privacy and redaction.

Transition commits are backend policy actions with strict schemas and trace refs. Every
proposal receives one structured observation: success, denied, approval_required,
error, or aborted. Dataset policy blocks use the shared `denied` observation status
with a typed reason code, not a dataset-specific `blocked` observation status.

## Local Storage Status And 200 MB Prompt

`LocalStorageStatus` is a local runtime/read-model projection for prompt behavior.

Minimum semantics:

```yaml
storage_status_id: string
schema_version: string
measured_at: datetime
farm_id: string
photo_bytes: integer
dataset_artifact_bytes: integer
derived_artifact_bytes: integer
total_counted_bytes: integer
threshold_bytes: 209715200
prompt_state: not_shown | shown | acknowledged | dismissed
last_prompted_at: datetime | null
acknowledged_by_actor_ref: string | null
sync_status: local_only
trace_refs: []
redaction_status: redacted | no_sensitive_fields
```

Prompt rules:

- show the local storage prompt when counted local photo/dataset storage exceeds
  200 MB (`209715200` bytes);
- prompt copy may mention local disk usage and local cleanup/export choices only;
- prompt copy must not imply upload, cloud backup, server availability, remote sync, or
  server verification;
- acknowledge/dismiss changes only prompt state, never `sync.status`;
- prompt state does not affect trainability or evidence authority;
- storage measurement must not read or expose secrets/auth material.

## FT-017 Privacy Consistency

FT-017 remains the authoritative `/spec-improve` pass for local privacy, deployment
controls, `local_only` sync, and secret redaction.

FT-016 must preserve:

- `sync.status=local_only` as the only MVP sync value;
- `server_verified`, upload status, server copy, and remote backup fields absent;
- local artifacts private by default;
- redaction before logs, timeline, manifests, Bus, UI Feed, screenshots, exports,
  traces visible to agents, harness observations, and agent context;
- no `.env`, token, credential, API key, or auth material in dataset candidates,
  storage prompts, exports, or context packages.

No contradiction was found between this dataset/storage design and FT-017.

## API / Service Surface To Refine In Tasks

Task decomposition may define exact backend services and schemas for:

- create/find DatasetCandidate for an existing evidence subject;
- propose/apply dataset governance transition;
- recompute `can_train_on` and denial/allow reason codes;
- read authorized candidate state and redacted trace summaries;
- measure local photo/dataset storage;
- read/update local storage prompt acknowledgement/dismissal;
- run dataset governance and storage prompt eval fixtures.

Generated OpenAPI comes from implementation schemas later.

## Verification Targets

Required tests before FT-016 can be considered implemented:

- new DatasetCandidate defaults to non-trainable;
- `can_train_on=true` cannot be client-forced or agent-forced;
- trainability is recomputed after every transition;
- raw, agent_labeled, needs_review, rejected, excluded, eval, holdout, null split,
  weak-evidence, redaction-failed, and privacy-excluded candidates are non-trainable;
- `gold` requires human, expert, or batch review;
- UI Feed, timeline snapshots, manifests, raw agent output, AgentMemoryRecord, raw chat,
  and Bus events alone cannot grant trainability;
- unauthorized Farm/Plant evidence cannot enter another actor's dataset context;
- storage prompt appears when local counted storage exceeds 200 MB;
- acknowledge/dismiss does not change `sync.status`;
- storage prompt copy and state do not imply upload, cloud backup, server availability,
  remote sync, or `server_verified`;
- secret/auth material is redacted or rejected across dataset, storage, export, Bus/UI,
  trace, and agent context surfaces.

## Open Questions

No blocker for `/prd-to-tasks FT-016`. Exact route names, counted storage directories,
prompt display wording, review UI shape, reason-code enum spelling, and first-demo
storage measurement cadence can be chosen during task decomposition as long as
non-trainable defaults, evidence-ref requirements, local-only sync, no-upload wording,
and FT-017 redaction constraints hold.
