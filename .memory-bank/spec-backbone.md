---
description: Pre-PRD spec framing, global SDD backbone state, and foundation routing.
status: active
---
# SDD Spec Backbone

## Pre-PRD Spec Status
- Status: ready_for_prd
- Last updated: 2026-06-26
- Notes: /spec-init refresh check completed against the updated command contract. Active PRD still has enough actor, scenario, domain, constraint, non-goal, boundary, lifecycle, and risk evidence for /prd decomposition. No pre-PRD blocker was found. Global architecture/backbone design was completed by /spec-design on 2026-06-14, refreshed for compact Foundation Dev Path routing on 2026-06-23, and brownfield-refreshed on 2026-06-26 against verified FT-000 code/evidence and current backend source.

## Decomposition Inputs
- User scenarios: [.memory-bank/user-scenarios.md](user-scenarios.md) captures Boss setup, Engineer Plant operations, Safety Gate/action task flow, and Companion governance scenarios.
- Domain model: [.memory-bank/domains/core-domain.md](domains/core-domain.md) captures Account, Farm, FarmMembership, ActorContext, Plant, PlantAccessGrant, admin audit, photo/runtime/audit, agent, safety, governance, and dataset entities.
- Constraints: [.memory-bank/prd.md](prd.md), [.memory-bank/invariants.md](invariants.md), and [.memory-bank/domains/core-domain.md](domains/core-domain.md) capture local-first, loopback default, one local Farm, PostgreSQL/read-model authority, UI Feed isolation, Safety Gate, real model-backed agent runtime, and no automated actuation.
- Non-goals: [.memory-bank/prd.md](prd.md) and [.memory-bank/user-scenarios.md](user-scenarios.md) capture no production SaaS, hosted/cloud sync as MVP requirement, billing, enterprise identity, multi-Farm tenancy, broad farm management, microservices, automated actuation, full dataset registry, or real fine-tuning.
- Risks: PRD/Product Brief risks are decomposition-relevant: authz enforced only in UI, governance approval confused with Safety Gate approval, Companion proposals leaking into agent context, agent fake/stub runtime paths, scope growth from Accounts/Farm/Admin.
- Boundary hints: [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md) captures preliminary boundaries for ActorContext, admin, Plant operations, photo artifacts, timeline, Bus, MessageEnvelope, UI Feed, Safety Gate, Companion governance, and dataset governance.
- Lifecycle hints: [.memory-bank/states/lifecycle-map.md](states/lifecycle-map.md) captures Account/FarmMembership/Plant/PlantAccessGrant, daily check-in, photo artifact, agent output, physical-action proposal, CompanionProposal, DecisionRecord, and dataset candidate lifecycles.

## Open Design Questions
- No global blocker remains after `/spec-design --all`.
- Foundation Dev Path is complete and verified; see [.memory-bank/foundation.md](foundation.md).
- Feature-level SDD design inside `/prd-to-tasks FT-<NNN>` must still define exact auth/session lifecycle, route schemas, DB migrations, event payloads, MessageEnvelope fields, Bus/UI projections, photo storage layout, state machines, freshness windows, action taxonomy, provider configuration, and UI route/view details before task slicing. Use standalone `/spec-improve FT-<NNN>` only for repair or advanced refresh without task generation.

## Backbone Area Matrix
| Area | Status | Authoritative source | Notes |
|---|---|---|---|
| architecture_style | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/constitution.md](constitution.md) | Local modular monolith; standard AI-first guardrails. |
| source_of_truth | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md), [.memory-bank/invariants.md](invariants.md), [.memory-bank/foundation.md](foundation.md) | Design precedence, runtime authority layers, and verified FT-000 brownfield executable baseline gate defined. |
| module_boundaries | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md) | Bounded modules defined inside one deployable monolith. |
| user_scenarios | authoritative | [.memory-bank/user-scenarios.md](user-scenarios.md), [.memory-bank/requirements.md](requirements.md) | Boss setup, Engineer operations, Safety Gate flow, and Companion governance covered. |
| constraints | authoritative | [.memory-bank/constitution.md](constitution.md), [.memory-bank/invariants.md](invariants.md), [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md) | Local-first, low-maintenance, safety, data authority, context hygiene, and no automated actuation. |
| non_goals | authoritative | [.memory-bank/prd.md](prd.md), [.memory-bank/requirements.md](requirements.md), [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md) | SaaS, hosted sync, enterprise identity, multi-Farm, microservices, full dataset registry, and actuation excluded. |
| domain_model | authoritative | [.memory-bank/domains/core-domain.md](domains/core-domain.md), [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md) | Global entities and runtime authority ownership defined; field detail routed to feature specs. |
| data_flow | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/foundation.md](foundation.md) | ActorContext -> state/artifacts/audit -> Bus/agents -> Safety/UI/tasks flow defined; Foundation proves only scaffold/bootstrap/DB readiness, not the full product event-agent path. |
| storage | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md), [.memory-bank/foundation.md](foundation.md) | PostgreSQL/read model, local filesystem artifacts, JSONL audit/export separation, and local bootstrap/runtime-root baseline defined. |
| api_contracts | authoritative | [.memory-bank/contracts/api-guidelines.md](contracts/api-guidelines.md) | HTTP/API style, ActorContext, authz, errors, upload, CORS, and OpenAPI-generation guardrails defined. |
| event_message_contracts | authoritative | [.memory-bank/contracts/agent-chat-bus.md](contracts/agent-chat-bus.md), [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md) | BusEventEnvelope and MessageEnvelope minimum boundaries defined; payload detail routed to feature specs. |
| agent_io_contracts | authoritative | [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md), [.memory-bank/contracts/agent-chat-bus.md](contracts/agent-chat-bus.md), [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md) | Runtime decision, adapter, consumability, and no-raw-output rules defined. |
| security_safety | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/invariants.md](invariants.md), [.memory-bank/contracts/api-guidelines.md](contracts/api-guidelines.md) | Backend authz, loopback/LAN controls, secret redaction, Safety Gate, and no automated actuation defined. |
| testing_strategy | authoritative | [.memory-bank/testing/index.md](testing/index.md), [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/foundation.md](foundation.md) | Unit/integration/e2e, anti-cheat test areas, and Foundation build/start/db/migration gates defined. |
| deployment | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/foundation.md](foundation.md) | Local loopback first demo; Linux Mint local bootstrap/PostgreSQL path; optional protected LAN later; no SaaS/server sync. |
| risks | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/prd.md](prd.md), [.memory-bank/analysis/product-brief.md](analysis/product-brief.md) | Key architecture risks recorded. |
| open_questions | authoritative | [.memory-bank/spec-backbone.md](spec-backbone.md), [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/foundation.md](foundation.md) | No global blocker; Foundation verified; feature-local details routed to `/prd-to-tasks`, with `/spec-improve` reserved for repair/advanced refresh. |

## Handoff To /prd
- Ready: yes
- Required reads: [.memory-bank/prd.md](prd.md), [.memory-bank/spec-index.md](spec-index.md), this file, [.memory-bank/user-scenarios.md](user-scenarios.md), [.memory-bank/domains/core-domain.md](domains/core-domain.md), [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md), [.memory-bank/states/lifecycle-map.md](states/lifecycle-map.md), [.memory-bank/invariants.md](invariants.md), and [.memory-bank/glossary.md](glossary.md).
- Stop conditions: PRD scope changes; Pre-PRD Spec Status becomes stale/blocked; new ambiguity appears around actors, Farm/Plant boundaries, Safety Gate authority, Companion governance authority, or real agent-runtime/demo requirements.

## Handoff To /spec-design
- Completed: yes, on 2026-06-14; refreshed on 2026-06-23 for compact Foundation Dev Path routing and on 2026-06-26 for brownfield-aware global/shared SDD alignment.
- Backbone areas decided: architecture_style, source_of_truth, module_boundaries, ActorContext/authz, Farm/Plant data authority, photo artifact storage, timeline audit/export, Agent Chat Bus, MessageEnvelope, UI Feed, Safety Gate, Companion governance, dataset governance, testing, deployment.
- Authoritative specs: see .memory-bank/spec-index.md Spec Registry.
- L1-L3 context: `/prd` completed active MVP v2 product, requirements, epics, and features on 2026-06-14; use [.memory-bank/requirements.md](requirements.md), [.memory-bank/epics/index.md](epics/index.md), and [.memory-bank/features/index.md](features/index.md) as decomposition inputs.

## Handoff To /foundation-to-tasks
- Required: complete.
- Foundation decision: [.memory-bank/foundation.md](foundation.md) records `Foundation Required: true`, `Foundation Requirement: REQ-000`, `Foundation Pseudo-Feature: FT-000`, and `Foundation Gate Task: TASK-004-T2-FT-000-W0`.
- Foundation scope: task schema/protocol alignment, backend scaffold anchors, Linux Mint local bootstrap, local PostgreSQL init, Alembic migration baseline, DB session/UoW baseline, local runtime roots, redaction baseline, and final foundation gate.
- Explicit non-scope: the old Bus -> Agent -> Message/UI -> Safety -> timeline/photo export critical path is not restored; those product boundaries remain in global contracts and feature-local specs.
- Next command: none for Foundation. This brownfield refresh preserves verified
  FT-000 closure and found no new executable baseline gap. `/prd-to-tasks
  FT-001` refresh has been run against the updated global specs/Foundation
  wording; run `/review-tasks-plan FT-001` before FT-001 execution.
- Stop conditions: Foundation gate task missing, not indexed, not `done`, or product tasks without direct/transitive dependency on the final foundation gate.

## Handoff To /prd-to-tasks And /spec-improve Repair
- Ready: yes.
- Required reads: [.memory-bank/spec-index.md](spec-index.md), this file, [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md), [.memory-bank/contracts/api-guidelines.md](contracts/api-guidelines.md), [.memory-bank/contracts/agent-chat-bus.md](contracts/agent-chat-bus.md), [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md), [.memory-bank/testing/index.md](testing/index.md), and the target feature file.
- Default route: `/prd-to-tasks FT-<NNN>` owns feature-level SDD design before task slicing and creates or refreshes task records/packets only inside that command.
- Repair route: standalone `/spec-improve FT-<NNN>` is for feature-design repair or advanced refresh without task generation.
- Stop conditions: PRD scope changes; a feature requires a global/shared decision not covered here; concrete feature design cannot truthfully define auth/session, route schemas, DB migrations, state machines, event payloads, freshness/action policy, provider configuration, or UI routes without contradicting verified code/baseline.

## Global Backbone Status
- Status: complete
- Mode: standard_ai_first
- Architecture artifact strategy: single-file
- Not applicable areas:
  - separate_handwritten_openapi_yaml: not_applicable - generated OpenAPI should come from backend FastAPI/Pydantic-style schemas after implementation exists.
  - microservices_or_distributed_deployment: not_applicable - MVP uses a local modular monolith.
  - automated_device_actuation: not_applicable - physical actions create only human-performed tasks in MVP.
  - production_saas_sync: not_applicable - MVP remains local-first with `local_only` sync status.
- Notes: Global AI-first architecture guardrails are complete for MVP v2
  feature-level design. Brownfield-aware refresh on 2026-06-26 confirmed the
  verified FT-000 executable baseline remains sufficient and preserved its
  closure. FT-001 task records, implementation plan, behavior specs, and
  packets were refreshed through `/prd-to-tasks FT-001`; run
  `/review-tasks-plan FT-001` before implementation. Feature-local specs still
  own detailed schemas, state machines, API endpoints, and task-ready
  verification evidence.
