---
description: Pre-PRD spec framing and global SDD backbone state.
status: active
---
# SDD Spec Backbone

## Pre-PRD Spec Status
- Status: ready_for_prd
- Last updated: 2026-06-03
- Notes: /spec-init completed. Active PRD has enough actor, scenario, domain, constraint, non-goal, boundary, lifecycle, and risk evidence for /prd decomposition. Architecture/backbone design is still owned by /spec-design after /prd.

## Decomposition Inputs
- User scenarios: [.memory-bank/user-scenarios.md](user-scenarios.md) captures Boss setup, Engineer Plant operations, Safety Gate/action task flow, and Companion governance scenarios.
- Domain model: [.memory-bank/domains/core-domain.md](domains/core-domain.md) captures Account, Farm, FarmMembership, ActorContext, Plant, PlantAccessGrant, admin audit, photo/runtime/audit, agent, safety, governance, and dataset entities.
- Constraints: [.memory-bank/prd.md](prd.md), [.memory-bank/invariants.md](invariants.md), and [.memory-bank/domains/core-domain.md](domains/core-domain.md) capture local-first, loopback default, one local Farm, PostgreSQL/read-model authority, UI Feed isolation, Safety Gate, real model-backed agent runtime, and no automated actuation.
- Non-goals: [.memory-bank/prd.md](prd.md) and [.memory-bank/user-scenarios.md](user-scenarios.md) capture no production SaaS, hosted/cloud sync as MVP requirement, billing, enterprise identity, multi-Farm tenancy, broad farm management, microservices, automated actuation, full dataset registry, or real fine-tuning.
- Risks: PRD/Product Brief risks are decomposition-relevant: authz enforced only in UI, governance approval confused with Safety Gate approval, Companion proposals leaking into agent context, agent fake/stub runtime paths, scope growth from Accounts/Farm/Admin.
- Boundary hints: [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md) captures preliminary boundaries for ActorContext, admin, Plant operations, photo artifacts, timeline, Bus, MessageEnvelope, UI Feed, Safety Gate, Companion governance, and dataset governance.
- Lifecycle hints: [.memory-bank/states/lifecycle-map.md](states/lifecycle-map.md) captures Account/FarmMembership/Plant/PlantAccessGrant, daily check-in, photo artifact, agent output, physical-action proposal, CompanionProposal, DecisionRecord, and dataset candidate lifecycles.

## Open Design Questions
- No blocker for /prd decomposition.
- /spec-design must later decide exact auth/session lifecycle, route/module grouping, event/envelope contracts, storage layout, state machines, freshness/action taxonomy, and verification strategy.

## Backbone Area Matrix
| Area | Status | Authoritative source | Notes |
|---|---|---|---|
| architecture_style | blocked | - | Decide in /spec-design after /prd. |
| source_of_truth | blocked | - | Decide in /spec-design after /prd. |
| module_boundaries | blocked | - | Decide in /spec-design after /prd. |
| user_scenarios | pre_prd_ready | .memory-bank/user-scenarios.md | Ready for /prd; refine architecture implications in /spec-design. |
| constraints | pre_prd_ready | .memory-bank/prd.md, .memory-bank/invariants.md | Ready for /prd; refine architecture implications in /spec-design. |
| non_goals | pre_prd_ready | .memory-bank/prd.md, .memory-bank/user-scenarios.md | Ready for /prd; refine architecture implications in /spec-design. |
| domain_model | pre_prd_ready | .memory-bank/domains/core-domain.md | Ready for /prd; refine shared design in /spec-design. |
| data_flow | blocked | - | Decide in /spec-design after /prd. |
| storage | blocked | - | Decide in /spec-design after /prd. |
| api_contracts | blocked | - | Decide authoritative/needed/not_applicable/blocked in /spec-design. |
| event_message_contracts | blocked | - | Decide authoritative/needed/not_applicable/blocked in /spec-design. |
| agent_io_contracts | blocked | - | Decide authoritative/needed/not_applicable/blocked in /spec-design. |
| security_safety | blocked | - | Decide in /spec-design after /prd. |
| testing_strategy | blocked | .memory-bank/testing/index.md | Decide in /spec-design after /prd. |
| deployment | blocked | - | Decide in /spec-design after /prd. |
| risks | pre_prd_ready | .memory-bank/prd.md, .memory-bank/analysis/product-brief.md | Ready for /prd; refine risk controls in /spec-design. |
| open_questions | pre_prd_ready | .memory-bank/spec-backbone.md | No /prd blocker; /spec-design questions remain. |

## Handoff To /prd
- Ready: yes
- Required reads: [.memory-bank/prd.md](prd.md), [.memory-bank/spec-index.md](spec-index.md), this file, [.memory-bank/user-scenarios.md](user-scenarios.md), [.memory-bank/domains/core-domain.md](domains/core-domain.md), [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md), [.memory-bank/states/lifecycle-map.md](states/lifecycle-map.md), [.memory-bank/invariants.md](invariants.md), and [.memory-bank/glossary.md](glossary.md).
- Stop conditions: PRD scope changes; Pre-PRD Spec Status becomes stale/blocked; new ambiguity appears around actors, Farm/Plant boundaries, Safety Gate authority, Companion governance authority, or real agent-runtime/demo requirements.

## Handoff To /spec-design
- Backbone areas to revisit: architecture_style, source_of_truth, module_boundaries, ActorContext/authz, Farm/Plant data authority, photo artifact storage, timeline audit/export, Agent Chat Bus, MessageEnvelope, UI Feed, Safety Gate, Companion governance, dataset governance, testing, deployment.
- Candidate specs: see .memory-bank/spec-index.md Planned Specs.

## Global Backbone Status
- Status: blocked
- Mode: standard_ai_first
- Architecture artifact strategy: single-file
- Not applicable areas:
  - TBD
- Notes: /spec-design has not completed the global AI-first architecture guardrails yet.
