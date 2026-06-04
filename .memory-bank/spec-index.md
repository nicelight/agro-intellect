---
description: Pure SDD spec registry and planned-spec index.
status: active
owner: architecture
last_updated: 2026-06-04
source_of_truth:
  - .memory-bank/constitution.md
  - .memory-bank/prd.md
  - .memory-bank/spec-backbone.md
---
# SDD Spec Index

## Purpose
- Keep a concise registry of existing and planned SDD specs.
- Read this index before creating new specs or doing serious T2/T3 work.
- Keep readiness, open design questions, backbone status, and routing handoffs in [.memory-bank/spec-backbone.md](spec-backbone.md).
- Feature `spec_design_status` lives in feature frontmatter, not in this index.

## Spec Registry
| Spec | Type | Path | Status | Owner command | Scope |
|---|---|---|---|---|---|
| Project Constitution | governance | [.memory-bank/constitution.md](constitution.md) | active | /constitution | Top governing policy. |
| Invariants | invariants | [.memory-bank/invariants.md](invariants.md) | active | /spec-init or /spec-design | Global MUST/NEVER rules. |
| Glossary | glossary | [.memory-bank/glossary.md](glossary.md) | active | /spec-init or /spec-design | Shared MVP v2 vocabulary. |
| User Scenarios | scenarios | [.memory-bank/user-scenarios.md](user-scenarios.md) | active | /spec-init | Primary actors, core scenarios, out-of-scope scenarios, and decomposition implications. |
| Core Domain | domain | [.memory-bank/domains/core-domain.md](domains/core-domain.md) | active | /spec-init | Main entities, roles, business rules, lifecycle hints, and decomposition constraints. |
| Runtime Data Model | domain | [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md) | active | /spec-design | Runtime authority, storage ownership, and shared entity groups. |
| System Architecture | architecture | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md) | active | /spec-design | Global architecture style, module boundaries, data flow, deployment, and handoff rules. |
| Contracts Index | contracts | [.memory-bank/contracts/index.md](contracts/index.md) | active | /spec-design | Router for active MVP v2 contract specs. |
| API Guidelines | contract | [.memory-bank/contracts/api-guidelines.md](contracts/api-guidelines.md) | active | /spec-design | Frontend/backend API, auth, errors, uploads, CORS, and OpenAPI generation policy. |
| Agent Harness Contract | contract | [.memory-bank/contracts/agent-harness.md](contracts/agent-harness.md) | active | /spec-design | Shared AgentHarness, AgentProfile, tool/action, permission, memory, trace, and eval rules. |
| Agent Chat Bus Contract | contract | [.memory-bank/contracts/agent-chat-bus.md](contracts/agent-chat-bus.md) | active | /spec-design | BusEventEnvelope and agent-consumable working event rules. |
| Message Envelope Contract | contract | [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md) | active | /spec-design | MessageEnvelope, runtime decisions, UI Feed projection, and presentation isolation. |
| Safety Gate Contract | contract | [.memory-bank/contracts/safety-gate.md](contracts/safety-gate.md) | active | /spec-design | Physical-action advice, Safety Gate decision, human approval, and action_task unlock rules. |
| Core Lifecycles | states | [.memory-bank/states/core-lifecycles.md](states/core-lifecycles.md) | active | /spec-design | Global lifecycle states and transition guardrails for shared entities. |
| Boundary Map | boundary_hints | [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md) | active | /spec-init | Preliminary boundary hints retained as framing evidence. |
| Lifecycle Map | lifecycle_hints | [.memory-bank/states/lifecycle-map.md](states/lifecycle-map.md) | active | /spec-init | Pre-PRD lifecycle hints retained as decomposition evidence. |
| Testing Index | testing | [.memory-bank/testing/index.md](testing/index.md) | active | /spec-design | Verification strategy, global test contract map, and harness eval requirements. |

## Planned Specs
| Area | Expected path | Needed by | Notes |
|---|---|---|---|
| feature_design | .memory-bank/tech-specs/FT-<NNN>-<slug>.md | /spec-improve | Feature-local specs only when needed before task decomposition. |
| generated_openapi | implementation-generated OpenAPI artifact | feature implementation | Generated from FastAPI/Pydantic once backend schemas exist; not hand-written before feature design. |

## Broken / Missing Links
- No known broken links recorded by `/spec-design`.

## Update Rules
- Keep this file as index/registry only: names, paths, statuses, owners, scopes, and broken links.
- Do not add global backbone status, backbone matrices, feature status maps, long hard rules, or open design question dumps here.
- Use [.memory-bank/spec-backbone.md](spec-backbone.md) for pre-PRD readiness, decomposition inputs, global backbone status, matrix, and handoffs.
- Use linked specs or ADRs for detailed decisions, rationale, contracts, state transitions, schemas, invariants, and testing rules.
