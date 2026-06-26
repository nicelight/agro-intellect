---
description: Pure SDD spec registry and planned-spec index.
status: active
owner: architecture
last_updated: 2026-06-26
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
| Boundary Map | boundary_hints | [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md) | active | /spec-init | Preliminary boundary hints only; no endpoints, schemas, or OpenAPI details. |
| Lifecycle Map | lifecycle_hints | [.memory-bank/states/lifecycle-map.md](states/lifecycle-map.md) | active | /spec-init | Lifecycle hints that affect epic/feature cuts. |
| Testing Index | testing | [.memory-bank/testing/index.md](testing/index.md) | active | /prd or /spec-design | Verification strategy and quality gates. |
| System Architecture | architecture | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md) | active | /spec-design | Global MVP v2 architecture style, source-of-truth hierarchy, module boundaries, data flow, storage, security/safety, testing, deployment, and open-question routing. |
| Foundation Dev Path | foundation_decision | [.memory-bank/foundation.md](foundation.md) | active | /spec-design | Required compact FT-000 executable baseline decision for task schema/protocol alignment, backend app/settings/database anchors, Linux Mint local bootstrap, PostgreSQL init, migrations, local runtime roots, and redaction baseline before product feature tasking. |
| Runtime Data Model | domain | [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md) | active | /spec-design | Global runtime authority layers, shared entities, invariants, and feature-local data-detail routing. |
| Contracts Index | contracts_index | [.memory-bank/contracts/index.md](contracts/index.md) | active | /spec-design | Router for active global contract documents. |
| API Guidelines | contract | [.memory-bank/contracts/api-guidelines.md](contracts/api-guidelines.md) | active | /spec-design | Global HTTP/API, ActorContext, authz, error, upload, CORS, and OpenAPI-generation guardrails. |
| Agent Chat Bus | contract | [.memory-bank/contracts/agent-chat-bus.md](contracts/agent-chat-bus.md) | active | /spec-design | Domain-owned agent-consumable event boundary and context hygiene rules. |
| MessageEnvelope | contract | [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md) | active | /spec-design | Structured publishable agent-output boundary after runtime decision handling. |
| FT-001 Local Accounts Sessions And ActorContext | feature_design | [.memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md](tech-specs/FT-001-local-accounts-sessions-actor-context.md) | active | /prd-to-tasks or /spec-improve repair | Current normative feature design for local identity, session lifecycle, ActorContext, role policy, auth errors, route contracts, and verification. |
| FT-002 Farm Plant Lifecycle And Access Grants | feature_design | [.memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md](tech-specs/FT-002-farm-plant-lifecycle-access-grants.md) | active | /prd-to-tasks or /spec-improve repair | Current normative feature design for single Farm seed, Plant lifecycle, PlantAccessGrant lifecycle, retained-history authorization, route contracts, audit handoff, and verification. |
| FT-003 Boss Admin Surface And Admin Audit | feature_design | [.memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md](tech-specs/FT-003-boss-admin-surface-admin-audit.md) | active | /prd-to-tasks or /spec-improve repair | Current normative feature design for Boss admin workflows, local invite semantics, AdminAuditRecord, admin route contracts, UI boundary, and verification. |

## Planned Specs
| Area | Expected path | Needed by | Notes |
|---|---|---|---|
| feature_design | .memory-bank/tech-specs/FT-<NNN>-<slug>.md | /prd-to-tasks or /spec-improve repair | Feature-local specs for features not yet registered above. `/prd-to-tasks` owns feature design before task slicing; `/spec-improve` is repair/advanced refresh. |
| generated_openapi | generated from backend schemas | implementation task / CI | Generated from FastAPI/Pydantic-style schemas after backend exists; no hand-written OpenAPI source during global backbone. |

## Broken / Missing Links
- None detected as of 2026-06-26.

## Update Rules
- Keep this file as index/registry only: names, paths, statuses, owners, scopes, and broken links.
- Do not add global backbone status, backbone matrices, feature status maps, long hard rules, or open design question dumps here.
- Use [.memory-bank/spec-backbone.md](spec-backbone.md) for pre-PRD readiness, decomposition inputs, global backbone status, matrix, and handoffs.
- Use linked specs or ADRs for detailed decisions, rationale, contracts, state transitions, schemas, invariants, and testing rules.
