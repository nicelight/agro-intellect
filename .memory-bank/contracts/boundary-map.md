---
description: Canonical module inventory, dependency graph, and inline ownership contracts for the MVP modular monolith.
status: active
last_updated: 2026-08-10
source_of_truth:
  - .memory-bank/architecture/system-architecture.md
  - .memory-bank/invariants.md
  - .memory-bank/spec-index.md
---
# Boundary Map

This file is the canonical detailed module/change-unit inventory and accepted
`Consumer -> Provider` topology. Parent architecture units remain in
[System Architecture](../architecture/system-architecture.md); subject specs
own exact payloads, states, persistence, errors, and verification matrices.
Code roots are discovery locations, not task hard write boundaries.

## Modules

| Module / Change Unit | Parent Architecture Unit | Code Root | Responsibility |
|---|---|---|---|
| Access & Admin | [Main Modules / Bounded Contexts](../architecture/system-architecture.md#main-modules-bounded-contexts) | `backend/app/access_admin/`; `backend/app/api/session.py`; `backend/app/api/admin.py`; `backend/app/api/plants.py` | Own Account, Farm, Membership, LocalSession, ActorContext, Plant lifecycle, PlantAccessGrant, and admin audit authority. |
| Plant Operations | [Main Modules / Bounded Contexts](../architecture/system-architecture.md#main-modules-bounded-contexts) | `backend/app/plant_operations/`; `backend/app/api/operations.py` | Own daily check-ins, observations, and manual pH/EC commands and rows. |
| Photo Intake | [Main Modules / Bounded Contexts](../architecture/system-architecture.md#main-modules-bounded-contexts) | `backend/app/photo_intake/`; `backend/app/api/photos.py` | Own accepted photo files, catalog identity, hash, capture manifest, and upload transaction. |
| Plant History | [Main Modules / Bounded Contexts](../architecture/system-architecture.md#main-modules-bounded-contexts) | `backend/app/plant_history/`; `backend/app/api/history.py` | Own Plant card/history projections and authorized retained-history reads. |
| Timeline Audit | [Main Modules / Bounded Contexts](../architecture/system-architecture.md#main-modules-bounded-contexts) | `backend/app/timeline/` | Own registered append-only `timeline.jsonl` validation and append refs; never mutable domain authority. |
| Agent Runtime Core | [Main Modules / Bounded Contexts](../architecture/system-architecture.md#main-modules-bounded-contexts) | `backend/app/agent_runtime/` | Own canonical roster metadata, provider binding composition, generic MessageEnvelope runtime, and registered advisory-only runtime rules. |
| Vision Observation | [Main Modules / Bounded Contexts](../architecture/system-architecture.md#main-modules-bounded-contexts) | `backend/app/vision_observation/` | Own strict real-photo observation request/result composition and observation handoff. |
| Plant State | [Main Modules / Bounded Contexts](../architecture/system-architecture.md#main-modules-bounded-contexts) | `backend/app/plant_state/`; `backend/app/api/plant_state.py` | Own Plant-state observations, assessments, conflicts, trust records, and review transitions. |
| Hydroponics Advisor | [Main Modules / Bounded Contexts](../architecture/system-architecture.md#main-modules-bounded-contexts) | `backend/app/hydroponics_advisor/` | Own advisor input freshness/missing-data policy and typed advisory result. |
| Agent Chat & UI Feed | [Main Modules / Bounded Contexts](../architecture/system-architecture.md#main-modules-bounded-contexts) | `backend/app/agent_chat/`; `backend/app/api/feed.py` | Own classified Bus publication, human Feed rows, protected Feed reads, and lazy roster-introduction materialization. |
| Safety Gate | [Main Modules / Bounded Contexts](../architecture/system-architecture.md#main-modules-bounded-contexts) | `backend/app/safety_gate/` | Own strict classification evidence, server-derived consumer route, and physical-action Safety routing. |
| Task & Follow-Up | [Main Modules / Bounded Contexts](../architecture/system-architecture.md#main-modules-bounded-contexts) | `backend/app/task_follow_up/`; `backend/app/api/task_follow_up.py` | Own the sole ordinary Task writer, Approval/Task/Outcome state, and follow-up transitions. |
| Companion Governance | [Main Modules / Bounded Contexts](../architecture/system-architecture.md#main-modules-bounded-contexts) | `backend/app/companion_governance/`; `backend/app/api/companion.py` | Own IssueStack, attention, proposal, conclusion, DecisionRecord, and allowed governance effects. |
| Dataset Governance | [Main Modules / Bounded Contexts](../architecture/system-architecture.md#main-modules-bounded-contexts) | `backend/app/dataset_governance/` | Own Dataset Candidate creation, evidence association, lifecycle, trainability derivation, and Dataset Agents advisory persistence. |
| Operator PWA | [Main Modules / Bounded Contexts](../architecture/system-architecture.md#main-modules-bounded-contexts) | `frontend/` | Own SvelteKit presentation and interaction only; backend modules retain authorization and mutable authority. |

## Dependency Graph

| Consumer | Provider | Contract |
|---|---|---|
| Plant Operations | Access & Admin | [ActorContext Gate](#actorcontext-gate) |
| Photo Intake | Access & Admin | [ActorContext Gate](#actorcontext-gate) |
| Plant History | Access & Admin | [ActorContext Gate](#actorcontext-gate) |
| Agent Chat & UI Feed | Access & Admin | [ActorContext Gate](#actorcontext-gate) |
| Task & Follow-Up | Access & Admin | [ActorContext Gate](#actorcontext-gate) |
| Companion Governance | Access & Admin | [ActorContext Gate](#actorcontext-gate) |
| Dataset Governance | Access & Admin | [ActorContext Gate](#actorcontext-gate) |
| Plant Operations | Timeline Audit | [Timeline Append Boundary](#timeline-append-boundary) |
| Photo Intake | Timeline Audit | [Timeline Append Boundary](#timeline-append-boundary) |
| Agent Runtime Core | Timeline Audit | [Timeline Append Boundary](#timeline-append-boundary) |
| Task & Follow-Up | Timeline Audit | [Timeline Append Boundary](#timeline-append-boundary) |
| Companion Governance | Timeline Audit | [Timeline Append Boundary](#timeline-append-boundary) |
| Dataset Governance | Timeline Audit | [Timeline Append Boundary](#timeline-append-boundary) |
| Vision Observation | Agent Runtime Core | [Registered Runtime Composition](#registered-runtime-composition) |
| Plant State | Agent Runtime Core | [Registered Runtime Composition](#registered-runtime-composition) |
| Hydroponics Advisor | Agent Runtime Core | [Registered Runtime Composition](#registered-runtime-composition) |
| Safety Gate | Agent Runtime Core | [Registered Runtime Composition](#registered-runtime-composition) |
| Task & Follow-Up | Agent Runtime Core | [Registered Runtime Composition](#registered-runtime-composition) |
| Companion Governance | Agent Runtime Core | [Registered Runtime Composition](#registered-runtime-composition) |
| Dataset Governance | Agent Runtime Core | [Dataset Advisory Runtime Exception](#dataset-advisory-runtime-exception) |
| Agent Chat & UI Feed | Safety Gate | [Classified Publication Route](#classified-publication-route) |
| Task & Follow-Up | Safety Gate | [Classified Publication Route](#classified-publication-route) |
| Companion Governance | Safety Gate | [Companion Governance Hold](#companion-governance-hold) |
| Companion Governance | Task & Follow-Up | [Approved Governance Task Effect](#approved-governance-task-effect) |
| Photo Intake | Dataset Governance | [Dataset Evidence Creation](#dataset-evidence-creation) |
| Plant Operations | Dataset Governance | [Dataset Evidence Creation](#dataset-evidence-creation) |
| Task & Follow-Up | Dataset Governance | [Dataset Evidence Creation](#dataset-evidence-creation) |
| Task & Follow-Up | Dataset Governance | [Follow-Up Evidence Association](#follow-up-evidence-association) |
| Operator PWA | Access & Admin | [Presentation Calls Backend Authority](#presentation-calls-backend-authority) |
| Operator PWA | Plant Operations | [Presentation Calls Backend Authority](#presentation-calls-backend-authority) |
| Operator PWA | Photo Intake | [Presentation Calls Backend Authority](#presentation-calls-backend-authority) |
| Operator PWA | Plant History | [Presentation Calls Backend Authority](#presentation-calls-backend-authority) |
| Operator PWA | Agent Chat & UI Feed | [Presentation Calls Backend Authority](#presentation-calls-backend-authority) |
| Operator PWA | Task & Follow-Up | [Presentation Calls Backend Authority](#presentation-calls-backend-authority) |
| Operator PWA | Companion Governance | [Presentation Calls Backend Authority](#presentation-calls-backend-authority) |

## Inline Contracts

### ActorContext Gate

Consumers call the Access & Admin ActorContext/Plant permission boundary and
must not duplicate its session, membership, role, grant, or archive rules.
State-advancing work repeats current guards at its owning write boundary. See
[ActorContext](access/actor-context.md#scope) and
[Plant And Access Lifecycle](../states/plants/plant-and-access-lifecycle.md#rules).

### Timeline Append Boundary

Producers use only registered event/source pairs and redacted summaries from
[Timeline Event](timeline-event.md#active-event-registry). The owning domain
mutation remains PostgreSQL authority; an append followed by commit failure is
non-authoritative audit noise, and Timeline replay never repairs state.

### Registered Runtime Composition

Competence modules reuse the provider factory, fail-closed binding,
pre/post-I/O authorization, redaction, sanitized audit, and generic
MessageEnvelope handoff from
[Agent Runtime Adapter](agent-runtime-adapter.md#invocation-flow). They must not
select providers, write neighbor state, or turn model output into authority.

### Dataset Advisory Runtime Exception

Only `dataset_governance` and `training_data_curator` use the registered
advisory-only exception defined by
[Dataset Agents Runtime](dataset-agents-runtime.md#registered-advisory-only-exception).
They reuse shared provider and current-guard infrastructure but return a strict
advisory outcome and never create MessageEnvelope, Safety, Bus, or UI Feed
effects. Dataset Governance alone may persist advisory fields or apply a
server-owned transition.

### Classified Publication Route

Consumers accept only a matching pending MessageEnvelope plus persisted
project-owned classification and the server-derived consumer route. They
repeat current authorization and Plant guards in the same transaction as their
write and never dispatch from model labels alone. See
[Safety Action Lifecycle](../states/safety-action-lifecycle.md#project-owned-classification-contract).

### Companion Governance Hold

Companion-classified output may enter only the guarded proposal boundary; it
cannot enter ordinary Bus/UI/Task consumers until an authorized human creates
a DecisionRecord. See
[Companion Runtime](companion-runtime.md#messageenvelope-and-classification).

### Approved Governance Task Effect

Companion Governance calls the sole Task & Follow-Up ordinary-task command
inside its caller-owned unit of work only for a valid approved DecisionRecord
effect. It never writes Task rows directly. See
[Task And Approval HTTP](task-approval-http.md#canonical-internal-ordinary-task-command).

### Dataset Evidence Creation

Source owners call the Dataset Governance creation seam inside their own unit
of work. The seam accepts service-side source identity only, creates a raw
non-trainable candidate idempotently, and never lets a source owner write
status, tier, confirmation, split, curator, or trainability fields. See
[Dataset Governance Data](../domains/dataset-governance.md#creation-seam).

### Follow-Up Evidence Association

Task & Follow-Up calls the Dataset-Governance-owned association command inside
`record_follow_up_outcome`. The command derives eligible target candidates from
the Outcome's already-authorized source refs, appends only the new Outcome ref,
and never accepts a caller-selected lifecycle or trainability result. See
[Dataset Governance Data](../domains/dataset-governance.md#follow-up-evidence-association-command).

### Presentation Calls Backend Authority

The Operator PWA may invoke registered HTTP/read boundaries and render their
results, but it never owns backend authorization, mutable domain state, agent
context, Safety approval, or dataset trainability. See
[API / Contract Boundaries](../architecture/system-architecture.md#api--contract-boundaries).
