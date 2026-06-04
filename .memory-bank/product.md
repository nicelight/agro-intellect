---
description: Product brief (C4 L1): what Agro Intellect MVP v2 is, for whom, and why.
status: draft
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/analysis/product-brief.md
  - .memory-bank/constitution.md
  - .memory-bank/invariants.md
---
# Product

## What This Is

Agro Intellect MVP v2 is a local-first Farm workspace for safe, traceable Plant
operations and a practical AI-first agentic development training ground. The product
starts with one local Farm, local Accounts, Boss/Engineer/Consultant role presets,
multiple Plants, and `tomato_001` as the initial Plant.

The first product surface is a Web App/PWA backed by a local modular monolith. Humans
perform daily Plant workflows, upload photos, record observations and pH/EC
measurements, review cautious model-backed agent outputs, handle Safety Gate prompts,
manage tasks and follow-up outcomes, and preserve local evidence for future dataset
governance.

## Core Value

The MVP gives a small team a bounded local Plant-operations system where human work,
agent assistance, evidence, approvals, and audit remain separated by explicit authority
boundaries. It is useful as a local tool and as a proving ground for future farm-scale
agentic architecture: ActorContext, per-Plant access, one shared AgentHarness,
permission-aware context, UI Feed isolation, Safety Gate, Companion governance, and
dataset evidence hygiene.

## Audience

- `Boss`: first local Account and Farm owner/admin. Manages personnel, roles, Plant
  lifecycle, per-Plant access, and admin audit; may approve physical-action proposals
  only through Safety Gate rules.
- `Engineer`: operational user for assigned Plants. Performs check-ins, photos,
  pH/EC, tasks, follow-up, and physical-action approvals only when granted
  `plant_approve_actions`.
- `Consultant`: advisory/read/comment user for granted Plant context. Does not create
  domain task/recommendation records or approve physical actions in MVP.
- Project owner / AI-first development operator: validates Memory Bank workflow,
  source-of-truth boundaries, agent architecture, and safety governance.

## Primary User Flow

1. A local user logs in or opens an authorized local session.
2. Backend resolves Account, Farm, role preset, PlantAccessGrant, and ActorContext.
3. User selects an authorized Plant, initially `tomato_001`.
4. User records observations, uploads photos, and/or enters pH/EC measurements.
5. Backend stores runtime state, photo artifacts, catalog rows, manifests, and audit refs.
6. The shared AgentHarness assembles permission-aware context from runtime state,
   approved evidence, approved governance summaries, and allowed scoped agent memory.
7. Real LLM/model-backed product agents produce concise outputs, clarify missing data,
   remain silent, or escalate through project-owned contracts.
8. UI Feed presents human-facing messages and tasks while staying unavailable as agent
   working context.
9. Safety Gate blocks or routes physical-action wording until fresh evidence, Safety
   Gate pass, authorized human approval, and task/action tracking exist.
10. Tasks and follow-up outcomes preserve evidence and audit trail.

## Constraints

- Tech stack direction: Python, FastAPI, Pydantic/schema validation, PostgreSQL/read
  model, local filesystem photo/artifact storage, JSONL timeline export, Web App/PWA.
- AI runtime direction: one project-owned provider-neutral AgentHarness control plane,
  Agno as execution layer only, real LLM-backed agents, real vision-capable model or
  real vision model integration for photo observation.
- Runtime authority: PostgreSQL/read model for mutable operational state unless a later
  active architecture spec replaces it.
- Audit/export: `timeline.jsonl`, photo files, and manifests are not mutable runtime
  authority.
- Deployment: loopback by default; optional LAN mode only with explicit auth/session,
  authorization, token protection, and CORS/origin controls.
- Sync/privacy: MVP data remains local/private by default with `sync.status=local_only`.
- Safety: no automated physical actuation; physical actions need Safety Gate and
  authorized human approval.
- Non-goals: production SaaS, hosted/cloud sync as an MVP requirement, billing,
  enterprise identity, multi-Farm tenancy, microservices, broad farm management,
  sensor runtime dependency, full dataset registry, real fine-tuning, or fake/stubbed
  product-agent runtime/demo outputs.
