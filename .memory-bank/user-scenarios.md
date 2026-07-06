---
description: Pre-PRD user scenarios for MVP v2 decomposition.
status: active
owner: product
last_updated: 2026-07-06
source_of_truth:
  - .memory-bank/prd.md
  - project_dossier_v2.md
---
# User Scenarios

## Primary Actors

- `Boss`: local Farm owner/admin. Manages local Accounts, role presets, Plant archive/restore, Plant access, admin audit, may create Plants, and may approve physical-action proposals for Farm Plants only through Safety Gate rules.
- `Engineer`: operational user who may create a Plant and otherwise works only with granted Plants. Runs check-ins, uploads photos, records measurements and observations, works tasks/follow-up, and approves physical-action proposals only when granted `plant_approve_actions`.
- `Consultant`: advisory/read/comment user for granted Plant context. Consultant does not create domain task/recommendation records and never approves physical actions in MVP.
- `Companion`: governance coordinator. Maintains typed Plant-scoped discussion state and proposals, but does not replace backend rules, Safety Gate approval, or human authority.
- Project owner / AI-first development operator: validates the product workflow, Memory Bank process, source-of-truth boundaries, and agent architecture.

## Core Scenarios

### 1. Boss Sets Up Local Farm Access

1. Boss opens the local app and uses or creates the single MVP Farm workspace.
2. Boss creates or confirms `tomato_001` as the initial Plant.
3. Boss adds at least one Engineer Account.
4. Boss assigns role preset and grants per-Plant access.
5. System records durable admin audit and later resolves ActorContext for each Farm/Plant route.

Decomposition implication: account/session/authz, Farm/Plant lifecycle, PlantAccessGrant, Boss Admin Surface, and admin audit are foundation slices, not optional UI decoration.

### 2. Engineer Performs Authorized Plant Operations

1. Engineer logs in or opens a local authorized session.
2. Engineer may create a Plant in the single Farm; the system atomically creates
   an active creator PlantAccessGrant with `plant_approve_actions=false`.
3. System resolves Account, Farm, role preset, PlantAccessGrant, and ActorContext.
4. Engineer selects only authorized Plants, initially `tomato_001` or a Plant
   created by that Engineer.
5. Engineer records observations, uploads a photo, and/or enters pH/EC measurements.
6. Backend persists runtime state, local photo artifacts, catalog refs, and timeline audit/export refs.
7. Real LLM/model-backed product agents process actual scoped Plant data and publish only through project-owned boundaries.
8. UI Feed displays human-facing cards, prompts, tasks, approvals, history, and storage warnings while remaining unavailable as agent working context.

Decomposition implication: daily operations, photo intake, runtime state, agent publication, UI Feed, and context hygiene must be cut with ActorContext and Plant authorization in mind.

### 3. Safety-Gated Recommendation Becomes Human-Performed Task

1. Product agent or advisor output implies a physical action.
2. Safety Gate blocks or routes the wording unless fresh evidence, Safety Gate pass, and authorized approval are present.
3. Boss or Engineer with `plant_approve_actions` approves or rejects the proposal.
4. Approval creates only a human-performed `action_task`, never automated actuation.
5. Follow-up outcome preserves evidence and audit trail.

Decomposition implication: Safety Gate, physical-action approval, task/action unlock, and follow-up must stay separate from governance decisions and UI presentation.

### 4. Companion Coordinates Plant-Scoped Governance

1. Companion tracks Plant-scoped issues in an explicit `IssueStack`.
2. Companion may raise `HumanAttentionNeeded`, create a `CompanionProposal`, and summarize discussion.
3. A valid human decision creates a `DecisionRecord`.
4. DecisionRecord may direct Plant-scoped workflow or safe task requests through backend rules.
5. Agents may consume only compact approved governance summary facts and refs, never raw proposal text, rationale, raw chat, UI markdown, or unapproved discussion.

Decomposition implication: Companion governance is a typed state/workflow slice and must not be merged with Safety Gate approval or raw chat/feed behavior.

## Out Of Scope Scenarios

- Production SaaS, hosted multi-tenant deployment, billing, subscriptions, enterprise identity, email delivery, hosted account recovery, or SaaS tenancy.
- Multi-Farm tenancy or multi-Farm membership.
- Automated physical actuation, pumps, dosing, pH/EC correction, light commands, autowatering, or autodosing.
- Broad commercial farm management beyond the bounded local Farm/Plant MVP.
- Sensor runtime dependency before real sensors exist.
- Full dataset registry, real fine-tuning, or trainability changes outside dataset governance.
- First-demo Consultant UI/path, although Consultant remains in MVP product scope.

## Architecture/Domain Implications

- Every Farm/Plant route and agent context builder needs ActorContext and backend authorization; frontend visibility is not authority.
- `tomato_001` is the initial Plant and migration seed, not a permanent product limit.
- PostgreSQL/read model remains runtime authority for mutable operational state unless a later active architecture spec replaces it.
- Timeline, photo files, and manifests are audit/export or local artifact layers, not mutable runtime authority.
- Agent Chat Bus is the agent-consumable working stream; UI Feed is human presentation only.
- Companion governance approval and Safety Gate approval are separate approval classes with different semantics.
- Archived Plant is a global operational deny: open tasks, approvals, and
  proposals remain retained but cannot transition, and restore never bypasses
  current authorization, freshness, Safety Gate, or governance checks.

## Review Status

- Status: ready_for_prd
- Reviewed sources: active PRD, Product Brief, Project Constitution, invariants, glossary, and MVP v2 dossier.
- Blocking gaps: none for `/prd` decomposition.
- Notes: `/spec-design` must later refine architecture, contracts, state machines, schemas, and verification strategy.
