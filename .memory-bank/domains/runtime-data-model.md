---
description: Runtime authority, storage ownership, and shared entity groups for MVP v2.
status: active
owner: domain
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/domains/core-domain.md
  - .memory-bank/invariants.md
---
# Runtime Data Model

## Purpose

This spec defines global runtime authority and shared entity groups for MVP v2. It is
not a database migration, ORM model list, or endpoint schema. Exact columns, indexes,
Pydantic schemas, migrations, and feature-local state transitions belong to
`/spec-improve FT-<NNN>` and task records.

## Authority Matrix

| Data Area | Runtime Authority | Audit / Artifact Layer | Not Authority |
|---|---|---|---|
| Accounts, sessions, roles, memberships | PostgreSQL/read model | AdminAuditRecord, security traces | UI role labels, client state |
| Plant lifecycle/access | PostgreSQL/read model | AdminAuditRecord, timeline refs | Plant selector visibility alone |
| Daily observations and measurements | PostgreSQL/read model | timeline refs, export snapshots | UI Feed, raw agent output |
| Photo metadata | PostgreSQL/read model photo catalog | local photo file, manifest, timeline refs | filename, manifest alone |
| Photo binary | local filesystem | sha256, catalog refs, capture manifest | model-visible image text |
| Mutable Plant state | PostgreSQL/read model | evidence refs, timeline refs | timeline replay, photo manifests, agent memory |
| Tasks, approvals, outcomes | PostgreSQL/read model | timeline refs, follow-up evidence refs | raw recommendation text |
| Agent memory | PostgreSQL/read model or dedicated local table under same authority | source refs, trace refs | hidden provider memory, UI Feed replay |
| Agent traces/evals | PostgreSQL/read model or append-only local trace store | redacted trace artifacts | hidden model reasoning |
| Companion governance | PostgreSQL/read model | proposal/decision audit refs | raw chat, UI markdown |
| Dataset lifecycle fields | PostgreSQL/read model | export snapshots, evidence refs | raw agent labels, UI Feed, manifests alone |
| Sync status | PostgreSQL/read model | local prompts/audit refs | upload UI copy |

## Entity Groups

### Access And Administration

- `Account`: local identity for login/session, authorization, attribution, and audit.
- `Farm`: single local workspace and data ownership boundary.
- `FarmMembership`: Account-to-Farm role and membership state.
- `PlantAccessGrant`: per-Plant visibility/work authorization plus optional
  `plant_approve_actions`.
- `ActorContext`: resolved request/runtime context containing Account, Farm,
  membership/role, Plant permissions, and session provenance.
- `AdminAuditRecord`: durable audit record for account, membership, role, Plant
  lifecycle, and access changes.

### Plant Operations And Runtime State

- `Plant`: Farm-managed crop/plant unit. `tomato_001` is the initial Plant.
- `CheckIn`: actor/Farm/Plant-scoped daily operation boundary.
- `Observation`: human-entered Plant note or structured observation.
- `ManualMeasurement`: pH/EC and future manually entered measurements.
- `PlantStateSnapshot` / read-model projection: current mutable state with trust labels
  and evidence refs.
- `PlantHistoryEntry`: read projection for authorized history view.

### Photos And Local Artifacts

- `PhotoCatalogItem`: accepted photo metadata and stable refs.
- `PhotoFile`: local original binary, addressed by catalog ref and `sha256`.
- `PhotoManifest`: adjacent JSON artifact with `initial_capture` or future
  `export_snapshot` kind.
- `DerivedPhotoArtifact`: optional thumbnails or analysis artifacts, never authority by
  themselves.

### Timeline And Audit

- `TimelineEvent`: append-only audit/export event with source refs and redacted payload.
- `AdminAuditRecord`: durable admin audit. It may reference timeline events but must not
  be replaced by UI rows.

### Agent Harness

- `AgentProfile`: single-competence product-agent definition inside shared
  `AgentHarness`.
- `AgentHarnessRun`: one invocation/run with context build, model calls, tool/action
  proposals, permission decisions, structured observations, traces, budgets, and final
  status.
- `ToolActionProposal`: model-proposed operation before schema validation and
  permission decision.
- `PermissionDecision`: allow, deny, ask_user, approval_required,
  require_stronger_auth, run_in_sandbox, or run_as_draft_only.
- `StructuredObservation`: bounded result returned to the model after success, denial,
  timeout, error, approval pause, or abort.
- `AgentMemoryRecord`: durable scoped memory item with source refs, trust/freshness
  metadata, and non-authority semantics.

### Publication

- `MessageEnvelope`: validated publishable agent output after runtime decision.
- `BusEventEnvelope`: agent-consumable working event wrapper.
- `UIFeedEvent`: human-facing projection wrapper, never agent working context.

### Safety And Task Loop

- `SafetyGateDecision`: fail-closed route/block/clear decision for physical-action
  wording.
- `Approval`: human approval/rejection record scoped to exact proposal/action.
- `Task`: check, measurement, follow-up, or approved human-performed action task.
- `Outcome`: follow-up result with evidence refs.

### Companion Governance

- `IssueStack`: explicit Plant-scoped issue state.
- `HumanAttentionNeeded`: typed marker for required/expected human reaction.
- `CompanionProposal`: human-visible proposal; no parallel pending proposal for the
  same Plant issue.
- `CompanionConclusion`: Companion resolution summary without binding authority by
  itself.
- `DecisionRecord`: typed governance decision, not Safety Gate approval and not Plant
  state evidence by itself.
- `ApprovedGovernanceSummary`: compact agent-consumable typed facts derived from a
  valid DecisionRecord.

### Dataset And Privacy

- `DatasetCandidate`: evidence-linked candidate with status/split/confirmation fields.
- `can_train_on`: computed/controlled trainability flag, false by default.
- `LocalStorageStatus`: local photo/dataset size and prompt acknowledgement state.
- `SyncStatus`: remains `local_only` in MVP.

## Identifier And Scope Rules

- Every persisted Farm/Plant record must include enough scope to filter by Farm, Plant,
  ActorContext, and PlantAccessGrant where relevant.
- Use stable IDs for records and evidence refs. Human labels and filenames are not
  authoritative IDs.
- Every mutable command must carry actor attribution.
- Every evidence-bearing record should store `source_refs` or linkable evidence refs
  where the owning feature requires them.
- Secret/auth material must be redacted before persistence in logs, timeline,
  manifests, Bus, UI Feed, screenshots, exports, or agent context.

## Retention Rules

- Plant archive never hard-deletes history, photos, tasks, outcomes, admin audit, or
  timeline evidence.
- Revoking PlantAccessGrant removes normal visibility and context retrieval for that
  actor without deleting retained audit/evidence.
- Superseded CompanionProposal records are retained but non-operative.
- Stale AgentMemoryRecord entries may remain retained but must be marked stale,
  superseded, or archived before retrieval rules can exclude or down-rank them.
- Dataset candidates remain non-trainable by default even when retained.

## Migration And Future Growth

- MVP starts with exactly one local Farm and `tomato_001` as initial Plant seed.
- Multi-Farm tenancy, server sync, InfluxDB, object storage, full dataset registry, and
  real fine-tuning require later PRD/spec promotion.
- A future architecture spec may replace or augment PostgreSQL/read-model authority
  only by explicitly updating [.memory-bank/spec-index.md](../spec-index.md),
  [.memory-bank/spec-backbone.md](../spec-backbone.md), and this document.
