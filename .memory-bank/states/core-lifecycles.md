---
description: Global lifecycle states and transition guardrails for MVP v2 shared entities.
status: active
owner: architecture
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/requirements.md
  - .memory-bank/domains/runtime-data-model.md
  - .memory-bank/contracts/agent-harness.md
  - .memory-bank/contracts/safety-gate.md
---
# Core Lifecycles

## Purpose

This spec defines global lifecycle guardrails for shared MVP v2 entities. It avoids
feature-local drift before `/prd-to-tasks`. Exact field names, transition tables, UI
states, and migration details belong to feature-level `/spec-improve`.

## Access Lifecycle

| Entity | MVP States | Key Transitions | Guardrails |
|---|---|---|---|
| Account | `active`, `invited`, `disabled` | create/add/invite, activate, disable | Disabled Account cannot access Farm/Plant data; auth material is never logged/exported. |
| Farm | `active` | seed/create local Farm | Exactly one local Farm in MVP; no multi-Farm membership. |
| FarmMembership | `active`, `invited`, `disabled`, `removed` | assign role, change role, disable/remove | Membership state and role changes create AdminAuditRecord. |
| PlantAccessGrant | `granted`, `revoked` | grant, revoke, update `plant_approve_actions` | Revoked grant removes normal visibility/context retrieval without deleting audit/evidence. |
| ActorContext | `resolved`, `denied`, `expired` | resolve per request/run, expire session | Every protected route/context builder path must fail closed when context is not resolved. |

## Plant Lifecycle

| Entity | MVP States | Key Transitions | Guardrails |
|---|---|---|---|
| Plant | `active`, `archived` | create, archive, restore | Hard delete is absent; archive removes from normal operations but retains authorized history/evidence. |
| CheckIn | `started`, `completed`, `aborted` | start, add observation/photo/measurement, complete, abort | Actor/Farm/Plant scope required; archived Plants cannot start normal check-ins. |
| ManualMeasurement | `recorded`, `superseded`, `invalidated` | record, supersede/correct, invalidate | Freshness/trust labels must be explicit for advisor and Safety Gate use. |
| PlantStateValue | `confirmed_updated`, `confirmed_unchanged`, `assumed_unchanged`, `probable`, `unknown`, `conflict` | update from evidence/review/follow-up, carry forward, mark conflict | Agent hypothesis or memory cannot become confirmed without owning rules and human/follow-up evidence. |

## Photo And Timeline Lifecycle

| Entity | MVP States | Key Transitions | Guardrails |
|---|---|---|---|
| PhotoArtifact | `pending_validation`, `accepted`, `rejected`, `orphan_recovery` | upload, validate, write file, catalog, manifest, reject/recover | File failure must not create authoritative runtime state; secrets cannot enter manifests/filenames. |
| PhotoManifest | `initial_capture`, `export_snapshot` | create on upload, create future export snapshot | Manifest is local artifact, not mutable runtime authority. |
| TimelineEvent | `appended` | append once | Append-only audit/export; replay cannot overwrite runtime state. |

## Agent Harness Lifecycle

| Entity | MVP States | Key Transitions | Guardrails |
|---|---|---|---|
| AgentProfile | `defined`, `active`, `disabled`, `deprecated` | define, activate, disable, deprecate | Product agents are profiles inside shared harness; separate ungoverned harnesses forbidden. |
| AgentHarnessRun | `context_built`, `model_called`, `proposal_received`, `validated`, `permissioned`, `approval_paused`, `observed`, `finalized`, `stopped`, `failed` | run loop steps | Every proposal gets structured observation; budgets and permission decisions are enforced outside model. |
| ToolActionProposal | `received`, `invalid`, `denied`, `approval_required`, `allowed`, `executed`, `aborted` | validate, permission, execute/pause/deny | Unknown tools and invalid args return structured errors. |
| AgentMemoryRecord | `candidate`, `active`, `stale`, `superseded`, `archived`, `rejected` | create candidate, validate, activate, stale/supersede/archive | Memory is scoped/source-ref backed/non-authoritative; revoked access blocks retrieval. |
| AgentOutput | `speak`, `silent`, `clarify`, `escalate` | runtime decision | Raw provider output becomes publishable only after adapter validation. |

## Publication Lifecycle

| Entity | MVP States | Key Transitions | Guardrails |
|---|---|---|---|
| MessageEnvelope | `created`, `rejected`, `published_to_bus`, `projected_to_ui` | validate, publish, project | UI projection does not grant agent consumption. |
| BusEventEnvelope | `created`, `published`, `filtered` | publish, retrieve/filter | Bus is agent working context; UI Feed and unapproved proposals cannot enter. |
| UIFeedEvent | `projected`, `dismissed`, `archived` | project from backend/domain output, dismiss/archive | Presentation-only; `visible_to_agents=false`, `consumable_by_agents=false`. |

## Safety And Task Lifecycle

| Entity | MVP States | Key Transitions | Guardrails |
|---|---|---|---|
| PhysicalActionProposal | `blocked`, `missing_data`, `pending_approval`, `approved`, `rejected`, `expired` | Safety Gate route/block, approval/reject, expire | Fresh data is required but never sufficient; governance approval is not Safety approval. |
| Approval | `requested`, `approved`, `rejected`, `expired`, `revoked` | request, decide, expire/revoke | Approval is scoped to exact action and cannot authorize automated actuation. |
| Task | `open`, `in_progress`, `completed`, `cancelled`, `blocked` | create, start, complete, cancel/block | `action_task` only after Safety Gate pass plus authorized approval. |
| Outcome | `recorded`, `no_data`, `superseded` | record follow-up, mark no-data, supersede | No-data outcome cannot backfill success. |

## Companion Governance Lifecycle

| Entity | MVP States | Key Transitions | Guardrails |
|---|---|---|---|
| IssueStackItem | `open`, `current`, `closed`, `superseded` | open, focus, close/supersede | Plant-scoped in MVP. |
| HumanAttentionNeeded | `raised`, `acknowledged`, `resolved` | raise, acknowledge, resolve | Marker only; not approval. |
| CompanionProposal | `pending`, `approved`, `rejected`, `superseded` | create, supersede previous pending for same issue, decide | Superseded proposal cannot be approved or become agent fact. |
| DecisionRecord | `recorded` | create from valid human decision | May direct workflow/safe task requests through backend rules; cannot mutate Plant state or authorize physical actions. |
| ApprovedGovernanceSummary | `created`, `retrievable`, `revoked_or_filtered` | derive from DecisionRecord, retrieve/filter | Contains compact typed facts only; no raw proposal text/rationale/chat/UI markdown. |

## Dataset And Deployment Lifecycle

| Entity | MVP States | Key Transitions | Guardrails |
|---|---|---|---|
| DatasetCandidate | `raw`, `agent_labeled`, `needs_review`, `confirmed`, `rejected`, `gold`, `excluded` | create/update status through governance rules | Non-trainable by default; `gold` requires human/expert/batch review. |
| `can_train_on` | `false`, `true` | computed/changed only through dataset lifecycle | UI Feed, timeline, manifests, raw agent output never grant trainability by themselves. |
| LocalStoragePrompt | `not_shown`, `shown`, `acknowledged`, `dismissed` | show at 200 MB, acknowledge/dismiss | Does not imply upload/server availability and cannot change sync status. |
| SyncStatus | `local_only` | set/retain local only | `server_verified` is forbidden before later server-sync spec. |

## Cross-Cutting Transition Rules

- Every state-changing transition must be actor-attributed where a human/API action is
  involved.
- Every Plant-scoped transition must be Farm/Plant scoped.
- Authorization and permission checks happen before mutation.
- Audit refs must be created for admin, safety, task, governance, photo, runtime, and
  agent publication transitions where feature specs require them.
- Redaction happens before logs, timeline, manifests, Bus, UI Feed, screenshots,
  exports, or agent context.
- Feature specs may refine these states but must not weaken authority, safety, privacy,
  or context-isolation guardrails.
