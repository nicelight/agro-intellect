---
description: Pre-PRD spec framing and global SDD backbone state.
status: active
---
# SDD Spec Backbone

## Pre-PRD Spec Status
- Status: ready_for_prd
- Last updated: 2026-06-04
- Notes: /spec-init completed and synced with the shared `AgentHarness` direction from the active PRD/Product Brief. Active PRD has enough actor, scenario, domain, constraint, non-goal, boundary, lifecycle, and risk evidence for /prd decomposition. `/spec-design` has now completed the global architecture/backbone design.

## Decomposition Inputs
- User scenarios: [.memory-bank/user-scenarios.md](user-scenarios.md) captures Boss setup, Engineer Plant operations, shared harness context building, scoped agent memory, Safety Gate/action task flow, and Companion governance scenarios.
- Domain model: [.memory-bank/domains/core-domain.md](domains/core-domain.md) captures Account, Farm, FarmMembership, ActorContext, Plant, PlantAccessGrant, admin audit, photo/runtime/audit, AgentHarness, AgentProfile, AgentMemoryRecord, safety, governance, and dataset entities.
- Constraints: [.memory-bank/prd.md](prd.md), [.memory-bank/invariants.md](invariants.md), and [.memory-bank/domains/core-domain.md](domains/core-domain.md) capture local-first, loopback default, one local Farm, PostgreSQL/read-model authority, shared AgentHarness direction, scoped long-term agent memory, UI Feed isolation, Safety Gate, real model-backed agent runtime, and no automated actuation.
- Non-goals: [.memory-bank/prd.md](prd.md) and [.memory-bank/user-scenarios.md](user-scenarios.md) capture no production SaaS, hosted/cloud sync as MVP requirement, billing, enterprise identity, multi-Farm tenancy, broad farm management, microservices, automated actuation, full dataset registry, or real fine-tuning.
- Risks: PRD/Product Brief risks are decomposition-relevant: authz enforced only in UI, governance approval confused with Safety Gate approval, Companion proposals leaking into agent context, agent fake/stub runtime paths, unscoped/stale agent memory treated as authority, separate ungoverned agent runtimes, and scope growth from Accounts/Farm/Admin.
- Boundary hints: [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md) captures preliminary boundaries for ActorContext, admin, Plant operations, photo artifacts, timeline, context builder, AgentProfile, tool/action validation, AgentMemoryRecord, Bus, MessageEnvelope, UI Feed, Safety Gate, Companion governance, dataset governance, and harness trace/eval evidence.
- Lifecycle hints: [.memory-bank/states/lifecycle-map.md](states/lifecycle-map.md) captures Account/FarmMembership/Plant/PlantAccessGrant, daily check-in, photo artifact, AgentProfile, AgentHarnessRun, AgentMemoryRecord, agent output, physical-action proposal, CompanionProposal, DecisionRecord, and dataset candidate lifecycles.

## Open Design Questions
- No global `/spec-design` blocker remains.
- Feature-level `/spec-improve FT-001` through `FT-017` is complete. Remaining endpoint
  shapes, implementation schema names, UI flow details, eval fixture files, and launch
  gates belong to the existing feature-local tech specs, implementation plans, and task
  records.

## Backbone Area Matrix
| Area | Status | Authoritative source | Notes |
|---|---|---|---|
| architecture_style | authoritative | .memory-bank/architecture/system-architecture.md | Local modular monolith, standard AI-first backbone. |
| source_of_truth | authoritative | .memory-bank/architecture/system-architecture.md, .memory-bank/domains/runtime-data-model.md | Explicit precedence and runtime authority matrix. |
| module_boundaries | authoritative | .memory-bank/architecture/system-architecture.md | Main modules and bounded contexts defined. |
| user_scenarios | authoritative | .memory-bank/user-scenarios.md, .memory-bank/architecture/system-architecture.md | Scenario implications linked to architecture. |
| constraints | authoritative | .memory-bank/prd.md, .memory-bank/invariants.md, .memory-bank/architecture/system-architecture.md | Local-first, runtime authority, harness, safety, privacy. |
| non_goals | authoritative | .memory-bank/prd.md, .memory-bank/user-scenarios.md, .memory-bank/architecture/system-architecture.md | SaaS, multi-Farm, microservices, automated actuation, full dataset registry excluded. |
| domain_model | authoritative | .memory-bank/domains/core-domain.md, .memory-bank/domains/runtime-data-model.md, .memory-bank/states/core-lifecycles.md | Entities, authority, retention, and lifecycle guardrails. |
| data_flow | authoritative | .memory-bank/architecture/system-architecture.md | Core UI/API/runtime/photo/timeline/harness/Bus/Safety flow defined. |
| storage | authoritative | .memory-bank/architecture/system-architecture.md, .memory-bank/domains/runtime-data-model.md | PostgreSQL/read model, local files, manifests, timeline, trace refs. |
| api_contracts | authoritative | .memory-bank/contracts/api-guidelines.md | HTTP/API style, auth, errors, uploads, CORS, generated OpenAPI policy. |
| event_message_contracts | authoritative | .memory-bank/contracts/agent-chat-bus.md, .memory-bank/contracts/message-envelope.md | BusEventEnvelope, MessageEnvelope, runtime decision, UI Feed projection. |
| agent_io_contracts | authoritative | .memory-bank/contracts/agent-harness.md, .memory-bank/contracts/message-envelope.md, .memory-bank/contracts/safety-gate.md | AgentProfile, tool/action proposal, permission, observation, output, Safety Gate. |
| agent_harness | authoritative | .memory-bank/contracts/agent-harness.md, agents-best-practices | Shared harness loop, components, budgets, traces, evals, Agno boundary. |
| agent_memory | authoritative | .memory-bank/contracts/agent-harness.md, .memory-bank/domains/runtime-data-model.md, .memory-bank/states/core-lifecycles.md | Scoped source-ref backed memory, retrieval, lifecycle, non-authority. |
| security_safety | authoritative | .memory-bank/invariants.md, .memory-bank/contracts/safety-gate.md, .memory-bank/contracts/api-guidelines.md, .memory-bank/architecture/system-architecture.md | Authz, redaction, Safety Gate, LAN/CORS, no automated actuation. |
| testing_strategy | authoritative | .memory-bank/testing/index.md | Global test contract map and harness eval requirements. |
| deployment | authoritative | .memory-bank/architecture/system-architecture.md, .memory-bank/contracts/api-guidelines.md | Loopback default, explicit protected LAN, local_only sync. |
| risks | authoritative | .memory-bank/architecture/system-architecture.md, .memory-bank/testing/index.md, .memory-bank/analysis/product-brief.md | Risk surfaces and verification routes captured. |
| open_questions | authoritative | .memory-bank/spec-backbone.md | No global blocker; feature-local decisions routed to /spec-improve. |

## Handoff To /prd
- Ready: yes
- Required reads: [.memory-bank/prd.md](prd.md), [.memory-bank/spec-index.md](spec-index.md), this file, [.memory-bank/user-scenarios.md](user-scenarios.md), [.memory-bank/domains/core-domain.md](domains/core-domain.md), [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md), [.memory-bank/states/lifecycle-map.md](states/lifecycle-map.md), [.memory-bank/invariants.md](invariants.md), and [.memory-bank/glossary.md](glossary.md).
- Stop conditions: PRD scope changes; Pre-PRD Spec Status becomes stale/blocked; new ambiguity appears around actors, Farm/Plant boundaries, shared AgentHarness direction, AgentMemoryRecord authority, Safety Gate authority, Companion governance authority, or real agent-runtime/demo requirements.

## Completed /spec-design Inputs
- Governing direction: use the `agents-best-practices` skill as the harness doctrine while keeping Constitution and PRD as product/scope authority.
- Post-`/prd` L1-L3 artifacts: [.memory-bank/product.md](product.md), [.memory-bank/requirements.md](requirements.md), [.memory-bank/epics/index.md](epics/index.md), and [.memory-bank/features/index.md](features/index.md).
- Backbone areas to revisit: architecture_style, source_of_truth, module_boundaries, ActorContext/authz, Farm/Plant data authority, shared AgentHarness, AgentProfile, AgentMemoryRecord, context builder, tool/action validation, permission decisions, approval records, photo artifact storage, timeline audit/export, Agent Chat Bus, MessageEnvelope, UI Feed, Safety Gate, Companion governance, dataset governance, traces/evals, testing, deployment.
- Candidate specs: see .memory-bank/spec-index.md Planned Specs.

## Handoff To /spec-improve
- Status: complete for FT-001..FT-017.
- Required global reads for each feature:
  [.memory-bank/spec-index.md](spec-index.md),
  [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md),
  [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md),
  [.memory-bank/states/core-lifecycles.md](states/core-lifecycles.md),
  [.memory-bank/contracts/api-guidelines.md](contracts/api-guidelines.md),
  [.memory-bank/testing/index.md](testing/index.md), and feature-relevant contract specs.
- Stop conditions: PRD scope changes; a feature tries to weaken ActorContext,
  runtime authority, AgentHarness, UI Feed isolation, Safety Gate, governance
  separation, local privacy, secret redaction, or real model-backed runtime/demo
  requirements.
- Next route: use `.memory-bank/tasks/index.json` and indexed `TASK-*.task.json`
  records for `/execute`, or run a formal post-queue `/review` before `/autopilot`.

## Global Backbone Status
- Status: complete
- Mode: standard_ai_first
- Architecture artifact strategy: single-file
- Not applicable areas:
  - production_saas: not_applicable - explicit PRD non-goal; MVP deployment is local-first loopback/LAN only.
  - automated_actuation: not_applicable - explicit PRD non-goal; physical actions become human-performed tasks only.
  - multi_farm_tenancy: not_applicable - explicit PRD non-goal; MVP supports exactly one local Farm.
  - full_dataset_registry_and_fine_tuning: not_applicable - explicit PRD non-goal; MVP keeps dataset lifecycle guardrails only.
- Notes: /spec-design completed the global AI-first architecture guardrails.
  Feature-local `/spec-improve` is complete for FT-001..FT-017.
