---
description: Pre-PRD core domain framing for MVP v2 decomposition.
status: active
owner: domain
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/analysis/product-brief.md
  - .memory-bank/glossary.md
  - .memory-bank/invariants.md
---
# Core Domain

## Main Entities

- `Account`: local identity used for login/session, authorization, attribution, and audit.
- `Farm`: the single local MVP workspace and data-ownership boundary.
- `FarmMembership`: Account-to-Farm relationship carrying role preset and membership status.
- `ActorContext`: application/API boundary context with Account, Farm, role/membership, Plant permissions, and session/auth provenance.
- `Plant`: Farm-managed plant/crop unit. `tomato_001` is the initial Plant.
- `PlantAccessGrant`: explicit per-Plant visibility and work authorization.
- `AdminAuditRecord`: durable record for Account, role, Plant lifecycle, membership, and access changes.
- `PhotoCatalogItem`: accepted local photo metadata and refs backed by a local file and capture manifest.
- `TimelineEvent`: append-only audit/export event, not mutable runtime authority.
- `BusEventEnvelope`, `MessageEnvelope`, `UIFeedEvent`: high-level boundaries for agent working context and human-facing presentation.
- `AgentHarness`: shared project-owned control plane for all product agents.
- `AgentProfile`: single-competence product-agent definition inside the shared harness.
- `AgentMemoryRecord`: scoped, durable, source-ref backed long-term memory item for one product agent's Plant analysis.
- `Task`, `Approval`, `Outcome`: operational loop records for checks, measurements, approved human-performed actions, and follow-up.
- `IssueStack`, `CompanionProposal`, `CompanionConclusion`, `HumanAttentionNeeded`, `DecisionRecord`: Plant-scoped Companion governance records.
- Dataset governance fields: lifecycle status, evidence refs, confirmation source, split, and `can_train_on`.

## User Roles

- `Boss`: Farm owner/admin role. Owns personnel, role, Plant lifecycle, per-Plant access, admin audit, and may approve physical-action proposals only through Safety Gate rules.
- `Engineer`: operational role for assigned Plants. Performs check-ins, uploads photos, records measurements and observations, manages allowed tasks/follow-up, and may approve physical actions only with `plant_approve_actions`.
- `Consultant`: advisory/read/comment role for granted Plant context. No operational authority, governance approval authority, or physical-action approval authority by default.
- `Companion`: product agent role for governance coordination through typed state. Companion has no hidden authority and cannot authorize physical actions.

## Business Rules

- MVP has exactly one local Farm workspace.
- MVP supports multiple Plants; `tomato_001` is the initial Plant.
- Plant removal is archive/restore only; hard delete is out of MVP.
- Every Farm/Plant read, mutation, context-builder path, task, approval, and audit record must be actor-scoped through ActorContext.
- Backend authorization enforces Farm/Plant access; UI visibility controls are presentation only.
- MVP permission overrides are limited to `plant_approve_actions`; other permissions come from role presets and PlantAccessGrant.
- Product agents share one `AgentHarness`; separate ungoverned agent runtimes are out of MVP direction.
- Agent-specific capabilities are expressed as `AgentProfile` definitions with explicit context, tools, permissions, output contracts, risk boundaries, and memory scope.
- Agent long-term memory supports multi-week and multi-cycle Plant analysis, but it is non-authoritative unless promoted through owning runtime/state/governance rules with evidence and required human review.
- Agent memory retrieval must respect ActorContext, Farm/Plant scope, PlantAccessGrant, evidence provenance, freshness/trust semantics, Safety Gate boundaries, and dataset governance.
- Product-agent runtime/demo outputs must use real LLM/model-backed flows over actual scoped Plant data.
- UI Feed, raw chat, raw reasoning, spoiler notes, admin UI text, and unapproved proposals must not become agent working context.
- Physical-action wording requires fresh data, Safety Gate pass, authorized human approval, and task/action tracking.
- Governance DecisionRecord is not Safety Gate approval and cannot mutate Plant state or unlock physical action.
- Dataset items are non-trainable by default until dataset governance allows otherwise.
- MVP sync status remains `local_only`.

## Entity States

- `Account`: local active/invited/disabled style states need later exact spec; decomposition only requires local identity and audit attribution.
- `Farm`: single active local workspace; multi-Farm tenancy is out of MVP.
- `FarmMembership`: active/invited/disabled/removed style states need later exact spec; decomposition requires role and membership status.
- `Plant`: active, archived, restored history semantics. Archive removes from normal operations but retains history/audit/export access for authorized roles.
- `PlantAccessGrant`: granted/revoked semantics need later exact spec; decomposition requires per-Plant filtering and authorization.
- `AgentProfile`: defined/active/disabled or versioned style states need later exact spec; decomposition requires a stable way to bind agent competence, tools, context, and memory scope.
- `AgentMemoryRecord`: candidate/active/stale/superseded/archived style states need later exact spec; decomposition requires provenance, permission filtering, and non-authority semantics.
- `Task` / `Approval` / `Outcome`: operational loop states need later state spec; decomposition requires separation between check/measurement/follow-up and approved human-performed action tasks.
- `CompanionProposal`: pending, approved, rejected, superseded style states; no parallel pending proposals for the same Plant-scoped issue.
- `DecisionRecord`: binding governance record within backend rules only; not Plant-state evidence and not Safety Gate approval.
- Dataset governance: non-trainable by default; detailed lifecycle belongs to later specs.

## Lifecycles

- Local access lifecycle: Account -> FarmMembership -> role preset -> PlantAccessGrant -> ActorContext -> authorized route/context/action.
- Plant lifecycle: create -> active operations -> archive -> retained history/audit/export -> restore when authorized.
- Daily Plant operation lifecycle: select Plant -> check-in -> observation/photo/measurement -> persistence/audit -> agent publication boundary -> UI Feed display -> tasks/approvals/follow-up.
- Photo lifecycle: upload -> local file -> catalog item -> sha256 -> initial capture manifest -> timeline refs -> future export/dataset refs.
- Agent harness run lifecycle: ActorContext and source refs -> context build -> model execution -> tool/action proposal or output -> validation -> permission/approval decision -> structured observation -> trace/eval refs -> Bus/UI/domain routing when allowed.
- Agent memory lifecycle: evidence-backed candidate -> validation and provenance check -> scoped retrievable memory -> stale/superseded/archive handling -> later analysis context only when allowed.
- Physical-action lifecycle: agent/advisor wording -> Safety Gate route/block -> authorized human decision -> human-performed action task -> follow-up outcome.
- Companion governance lifecycle: issue detected -> current focus / human attention -> proposal -> decision -> compact approved governance summary -> allowed workflow effect.

## Domain Constraints

- Local-first and private by default.
- Loopback is the default first-demo exposure boundary; LAN mode is optional only with explicit controls.
- PostgreSQL/read model is mutable runtime authority unless replaced by later active architecture spec.
- Timeline is append-only audit/export only.
- Photo files and manifests are local artifacts, not mutable state authority.
- `agents-best-practices` is the guiding doctrine for the shared agent harness direction; `/spec-design` owns exact contracts, schemas, loop rules, memory rules, tools, permissions, traces, evals, and budgets.
- Agno is execution layer only, not source of truth, domain coordinator, Agent Chat Bus replacement, or domain authority.
- Secrets, sessions, tokens, credentials, `.env` values, and auth material must not enter logs, timeline, manifests, Bus, UI Feed, screenshots, exports, or agent context.

## Links To Contracts/States/Storage

- Boundary hints: [.memory-bank/contracts/boundary-map.md](../contracts/boundary-map.md).
- Lifecycle hints: [.memory-bank/states/lifecycle-map.md](../states/lifecycle-map.md).
- Global guardrails: [.memory-bank/invariants.md](../invariants.md).
- Vocabulary: [.memory-bank/glossary.md](../glossary.md).
- Product source: [.memory-bank/prd.md](../prd.md).
