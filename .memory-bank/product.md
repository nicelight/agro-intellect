---
description: Product brief (C4 L1): что это, для кого, core value, ограничения.
status: active
type: product
owner: product
last_updated: 2026-06-14
source_of_truth:
  - .memory-bank/prd.md
  - .memory-bank/constitution.md
  - .memory-bank/invariants.md
---
# Product

## What this is

Agro Intellect MVP v2 is a local-first Farm workspace and Web App/PWA for safe, traceable Plant operations with AI-assisted workflows. The MVP starts with one local Farm, local Accounts, Boss/Engineer/Consultant role presets, multiple Plants, and `tomato_001` as the initial Plant.

The system is also an AI-first agentic development training ground: product agents can observe, ask for missing data, publish cautious outputs, propose safe follow-up work, and support future dataset governance only through explicit project-owned boundaries.

## Core value

- Give humans a small useful Plant operations workspace with traceable evidence, audit, tasks, and follow-up outcomes.
- Prove the hard future-facing boundaries early: ActorContext, per-Plant authorization, admin audit, local artifact authority, Agent Chat Bus, MessageEnvelope, UI Feed isolation, Safety Gate, Companion governance, and dataset evidence hygiene.
- Keep physical-action advice fail-closed: no automated actuation and no immediate pH/EC/pump/light/dosing actions without fresh evidence, Safety Gate pass, and authorized human approval.

## Audience

- `Boss`: local Farm owner/admin who manages Accounts, roles, Plants, Plant access, admin audit, and may approve physical-action proposals only through Safety Gate rules.
- `Engineer`: operational user for assigned Plants who performs check-ins, uploads photos, records observations and pH/EC, handles tasks, and may approve physical actions only with per-Plant `plant_approve_actions`.
- `Consultant`: advisory/read/comment user for granted Plant context, without default operational authority, governance approval authority, or physical-action approval authority.
- Project owner / AI-first development operator: validates the Memory Bank workflow, source-of-truth boundaries, product-agent architecture, and safety governance.

## Primary user flow

1. User logs in or opens a local authorized session.
2. Backend resolves Account, Farm, FarmMembership, role preset, PlantAccessGrant, and ActorContext.
3. User selects an authorized Plant, initially `tomato_001`.
4. User runs a daily check-in, records observations, uploads photo evidence, and/or enters pH/EC measurements.
5. Backend persists mutable operational state in the PostgreSQL/read model, local photo artifacts/catalog entries, and append-only timeline audit/export refs.
6. Real model-backed product agents process only authorized, agent-consumable Plant context and publish through runtime decision, MessageEnvelope, and Agent Chat Bus boundaries.
7. UI Feed presents human-facing messages, cards, prompts, tasks, approvals, history, and local storage status without becoming agent context.
8. Safety Gate blocks or routes physical-action wording until fresh data, Safety Gate pass, authorized human approval, and task/action tracking exist.
9. Companion may coordinate Plant-scoped discussion through IssueStack, HumanAttentionNeeded, CompanionProposal, CompanionConclusion, and DecisionRecord, without replacing backend rules or Safety Gate approval.
10. Follow-up outcomes and dataset evidence remain traceable and non-trainable by default.

## Constraints
- Tech stack direction: local modular monolith, Python/FastAPI/Pydantic backend, PostgreSQL/read model runtime authority, local filesystem for photos/artifacts, JSONL timeline export, Web App/PWA frontend, Agno as agent execution layer only.
- Local-first and private by default. Default exposure is loopback; LAN mode may exist only when explicitly enabled with authentication, authorization, token/session protection, and CORS/origin controls.
- No production SaaS, hosted cloud sync as an MVP requirement, billing, enterprise identity, multi-Farm tenancy, microservices, broad farm management, full dataset registry, real fine-tuning, sensor runtime dependency, automated physical actuation, or fake/stubbed MVP runtime agent path.
- `timeline.jsonl`, photo files, manifests, UI Feed, raw chat, raw model reasoning, and unapproved Companion proposals are never mutable runtime authority.
