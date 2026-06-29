---
description: Pre-PRD spec framing, global SDD backbone state, and foundation routing.
status: active
---
# SDD Spec Backbone

## Pre-PRD Spec Status
- Status: ready_for_prd
- Last updated: 2026-06-26
- Notes: Active PRD contains enough actor, scenario, domain, constraint, non-goal, boundary, lifecycle, and risk evidence for `/prd` decomposition. No pre-PRD blocker remains.

## Decomposition Inputs
- User scenarios: [.memory-bank/user-scenarios.md](user-scenarios.md) captures Boss setup, Engineer Plant operations, Safety Gate/action task flow, and Companion governance scenarios.
- Domain model: [.memory-bank/domains/core-domain.md](domains/core-domain.md) captures Account, Farm, FarmMembership, ActorContext, Plant, PlantAccessGrant, admin audit, photo/runtime/audit, agent, safety, governance, and dataset entities.
- Constraints: [.memory-bank/prd.md](prd.md), [.memory-bank/invariants.md](invariants.md), and [.memory-bank/domains/core-domain.md](domains/core-domain.md) capture local-first, loopback default, one local Farm, PostgreSQL/read-model authority, UI Feed isolation, Safety Gate, real model-backed agent runtime, and no automated actuation.
- Non-goals: [.memory-bank/prd.md](prd.md) and [.memory-bank/user-scenarios.md](user-scenarios.md) capture no production SaaS, hosted/cloud sync as MVP requirement, billing, enterprise identity, multi-Farm tenancy, broad farm management, microservices, automated actuation, full dataset registry, or real fine-tuning.
- Risks: PRD/Product Brief risks are decomposition-relevant: authz enforced only in UI, governance approval confused with Safety Gate approval, Companion proposals leaking into agent context, agent fake/stub runtime paths, scope growth from Accounts/Farm/Admin.
- Boundary hints: [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md) captures preliminary boundaries for ActorContext, admin, Plant operations, photo artifacts, timeline, Bus, MessageEnvelope, UI Feed, Safety Gate, Companion governance, and dataset governance.
- Lifecycle hints: [.memory-bank/states/lifecycle-map.md](states/lifecycle-map.md) captures Account/FarmMembership/Plant/PlantAccessGrant, daily check-in, photo artifact, agent output, physical-action proposal, CompanionProposal, DecisionRecord, and dataset candidate lifecycles.

## Open Design Questions
- None at the global backbone level.

## Backbone Area Matrix
| Area | Status | Authoritative source | Notes |
|---|---|---|---|
| architecture_style | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/architecture/foundation-runtime-substrate.md](architecture/foundation-runtime-substrate.md), [.memory-bank/constitution.md](constitution.md) | Local modular monolith; standard architecture scaffold with AI-first guardrails; FT-000 runtime substrate defined. |
| source_of_truth | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md), [.memory-bank/domains/foundation-data-substrate.md](domains/foundation-data-substrate.md), [.memory-bank/invariants.md](invariants.md), [.memory-bank/foundation.md](foundation.md) | Design precedence, runtime authority layers, verified FT-000 brownfield executable baseline gate, and substrate data boundaries defined. |
| module_boundaries | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/architecture/foundation-runtime-substrate.md](architecture/foundation-runtime-substrate.md) | Bounded modules defined inside one deployable monolith; substrate dependency direction defined. |
| user_scenarios | authoritative | [.memory-bank/user-scenarios.md](user-scenarios.md), [.memory-bank/requirements.md](requirements.md) | Boss setup, Engineer operations, Safety Gate flow, and Companion governance covered. |
| constraints | authoritative | [.memory-bank/constitution.md](constitution.md), [.memory-bank/invariants.md](invariants.md), [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md) | Local-first, low-maintenance, safety, data authority, context hygiene, and no automated actuation. |
| non_goals | authoritative | [.memory-bank/prd.md](prd.md), [.memory-bank/requirements.md](requirements.md), [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md) | SaaS, hosted sync, enterprise identity, multi-Farm, microservices, full dataset registry, and actuation excluded. |
| domain_model | authoritative | [.memory-bank/domains/core-domain.md](domains/core-domain.md), [.memory-bank/domains/index.md](domains/index.md), [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md), [.memory-bank/domains/foundation-data-substrate.md](domains/foundation-data-substrate.md), [.memory-bank/domains/photo-artifacts.md](domains/photo-artifacts.md), [.memory-bank/states/index.md](states/index.md) | Global entities, shared native-UUID/non-cascading relation compatibility, foundation data substrate, photo artifact authority, shared lifecycle boundaries, and runtime authority ownership defined; exact field detail stays in feature specs. |
| data_flow | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/architecture/foundation-runtime-substrate.md](architecture/foundation-runtime-substrate.md), [.memory-bank/contracts/timeline-event.md](contracts/timeline-event.md), [.memory-bank/contracts/ui-feed.md](contracts/ui-feed.md), [.memory-bank/foundation.md](foundation.md) | ActorContext -> state/artifacts/audit -> Bus/agents -> Safety/UI/tasks flow defined; FT-000 runtime smoke flow defined; projection/audit layers cannot become runtime or agent authority. |
| storage | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md), [.memory-bank/domains/foundation-data-substrate.md](domains/foundation-data-substrate.md), [.memory-bank/domains/photo-artifacts.md](domains/photo-artifacts.md), [.memory-bank/contracts/timeline-event.md](contracts/timeline-event.md), [.memory-bank/foundation.md](foundation.md) | PostgreSQL/read model, shared UUID identity, non-cascading authority relations, DB/session/Alembic substrate, local filesystem artifacts, JSONL audit/export separation, and local bootstrap/runtime-root baseline defined. |
| api_contracts | authoritative | [.memory-bank/contracts/api-guidelines.md](contracts/api-guidelines.md), [.memory-bank/contracts/foundation-smoke-api.md](contracts/foundation-smoke-api.md) | HTTP/API guardrails plus concrete FT-000 `/health` and `/ready` smoke contract defined. |
| event_message_contracts | authoritative | [.memory-bank/contracts/agent-chat-bus.md](contracts/agent-chat-bus.md), [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md), [.memory-bank/contracts/ui-feed.md](contracts/ui-feed.md), [.memory-bank/contracts/timeline-event.md](contracts/timeline-event.md) | BusEventEnvelope, MessageEnvelope, UI Feed, and Timeline Event shared boundaries defined; payload detail routed to feature specs. |
| agent_io_contracts | authoritative | [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md), [.memory-bank/contracts/agent-chat-bus.md](contracts/agent-chat-bus.md), [.memory-bank/contracts/ui-feed.md](contracts/ui-feed.md), [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md) | Runtime decision, adapter, consumability, projection separation, and no-raw-output rules defined. |
| security_safety | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/invariants.md](invariants.md), [.memory-bank/contracts/api-guidelines.md](contracts/api-guidelines.md), [.memory-bank/contracts/evidence-redaction.md](contracts/evidence-redaction.md), [.memory-bank/states/safety-action-lifecycle.md](states/safety-action-lifecycle.md), [.memory-bank/states/companion-governance.md](states/companion-governance.md), [.memory-bank/states/dataset-governance.md](states/dataset-governance.md) | Backend authz, loopback/LAN controls, secret/evidence redaction, Safety Gate, governance separation, trainability default, and no automated actuation defined. |
| testing_strategy | authoritative | [.memory-bank/testing/index.md](testing/index.md), [.memory-bank/testing/foundation-test-harness.md](testing/foundation-test-harness.md), [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/foundation.md](foundation.md), [.memory-bank/states/index.md](states/index.md) | Unit/integration/e2e, anti-cheat test areas, shared state/contract checks, and Foundation build/start/db/migration/test harness gates defined. |
| deployment | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/runbooks/foundation-local-runtime.md](runbooks/foundation-local-runtime.md), [.memory-bank/foundation.md](foundation.md) | Local loopback first demo; Linux Mint local bootstrap/PostgreSQL path and runbook; optional protected LAN later; no SaaS/server sync. |
| risks | authoritative | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/prd.md](prd.md), [.memory-bank/analysis/product-brief.md](analysis/product-brief.md) | Key architecture risks recorded. |
| open_questions | authoritative | [.memory-bank/spec-backbone.md](spec-backbone.md), [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md), [.memory-bank/foundation.md](foundation.md) | No global blocker; feature-local details remain with their owning feature designs. |

## Handoff To /prd
- Ready: yes
- Required reads: [.memory-bank/prd.md](prd.md), [.memory-bank/spec-index.md](spec-index.md), this file, [.memory-bank/user-scenarios.md](user-scenarios.md), [.memory-bank/domains/core-domain.md](domains/core-domain.md), [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md), [.memory-bank/states/lifecycle-map.md](states/lifecycle-map.md), [.memory-bank/invariants.md](invariants.md), and [.memory-bank/glossary.md](glossary.md).
- Stop conditions: PRD scope changes; Pre-PRD Spec Status becomes stale/blocked; new ambiguity appears around actors, Farm/Plant boundaries, Safety Gate authority, Companion governance authority, or real agent-runtime/demo requirements.

## Handoff To /spec-design
- Global Backbone Status: complete.
- Backbone areas decided: architecture_style, source_of_truth, module_boundaries, ActorContext/authz, Farm/Plant data authority, photo artifact storage, timeline audit/export, Agent Chat Bus, MessageEnvelope, UI Feed, Plant state trust, Safety Gate/action lifecycle, Companion governance, dataset governance, testing, deployment.
- Authoritative specs: see .memory-bank/spec-index.md Spec Registry.
- L1-L3 context: [.memory-bank/requirements.md](requirements.md), [.memory-bank/epics/index.md](epics/index.md), and [.memory-bank/features/index.md](features/index.md).

## Handoff To /foundation-to-tasks
- Decision: required.
- Status: complete and verified; [.memory-bank/foundation.md](foundation.md) owns the current gate state and executable-baseline evidence.
- Downstream rule: product tasking must honor the Foundation gate recorded in the authoritative Foundation document.

## Handoff To /prd-to-tasks
- Ready: yes.
- Scope: feature-level SDD design and task slicing for the selected feature.
- Stop conditions: PRD scope changes, a new shared/global gap appears, or feature design conflicts with the authoritative global backbone; rerun `/spec-design` for shared/global decisions.

## Global Backbone Status
- Status: complete
- Mode: standard_architecture_scaffold
- Architecture artifact strategy: single-file
- Not applicable areas:
  - separate_handwritten_openapi_yaml: not_applicable - generated OpenAPI should come from backend FastAPI/Pydantic-style schemas after implementation exists.
  - microservices_or_distributed_deployment: not_applicable - MVP uses a local modular monolith.
  - automated_device_actuation: not_applicable - physical actions create only human-performed tasks in MVP.
  - production_saas_sync: not_applicable - MVP remains local-first with `local_only` sync status.
- Notes: All relevant global/shared areas have authoritative routes in the Backbone Area Matrix. Detailed feature schemas, state machines, API/event contracts, provider configuration, and UI behavior remain with their owning feature designs.
