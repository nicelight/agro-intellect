---
description: Pure SDD spec registry and planned-spec index.
status: active
owner: architecture
last_updated: 2026-06-29
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
| Foundation Runtime Substrate | architecture | [.memory-bank/architecture/foundation-runtime-substrate.md](architecture/foundation-runtime-substrate.md) | active | /foundation-to-tasks | Verified FT-000 backend runtime substrate: app factory, entrypoint, dependency direction, settings/database injection, and smoke route mounting. |
| Foundation Dev Path | foundation_decision | [.memory-bank/foundation.md](foundation.md) | active | /spec-design | Required compact FT-000 executable baseline decision for task schema/protocol alignment, backend app/settings/database anchors, Linux Mint local bootstrap, PostgreSQL init, migrations, local runtime roots, and redaction baseline before product feature tasking. |
| Domains Index | domains_index | [.memory-bank/domains/index.md](domains/index.md) | active | /foundation-to-tasks | Router for active domain/data specification documents. |
| Runtime Data Model | domain | [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md) | active | /spec-design | Global runtime authority layers, shared native-UUID identity/non-cascading relation rules, shared entities, invariants, and feature-local data-detail routing. |
| Foundation Data Substrate | domain | [.memory-bank/domains/foundation-data-substrate.md](domains/foundation-data-substrate.md) | active | /foundation-to-tasks | FT-000 DB/session/Alembic/runtime-root substrate that product features build on without defining product schemas. |
| Photo Artifacts | domain | [.memory-bank/domains/photo-artifacts.md](domains/photo-artifacts.md) | active | /spec-design | Global local photo artifact authority, identity, privacy, and cross-feature evidence refs. |
| Contracts Index | contracts_index | [.memory-bank/contracts/index.md](contracts/index.md) | active | /spec-design | Router for active global contract documents. |
| API Guidelines | contract | [.memory-bank/contracts/api-guidelines.md](contracts/api-guidelines.md) | active | /spec-design | Global HTTP/API, ActorContext, authz, error, upload, CORS, and OpenAPI-generation guardrails. |
| Foundation Smoke API | contract | [.memory-bank/contracts/foundation-smoke-api.md](contracts/foundation-smoke-api.md) | active | /foundation-to-tasks | Substrate-level `/health` and `/ready` route shape, status behavior, and redaction requirements. |
| Evidence Redaction | contract | [.memory-bank/contracts/evidence-redaction.md](contracts/evidence-redaction.md) | active | /foundation-to-tasks | Foundation evidence redaction rules for logs, scripts, tests, and handoff artifacts. |
| Agent Chat Bus | contract | [.memory-bank/contracts/agent-chat-bus.md](contracts/agent-chat-bus.md) | active | /spec-design | Domain-owned agent-consumable event boundary and context hygiene rules. |
| MessageEnvelope | contract | [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md) | active | /spec-design | Structured publishable agent-output boundary after runtime decision handling. |
| UI Feed | contract | [.memory-bank/contracts/ui-feed.md](contracts/ui-feed.md) | active | /spec-design | Human-facing presentation stream boundary; never runtime authority or agent working context. |
| Timeline Event | contract | [.memory-bank/contracts/timeline-event.md](contracts/timeline-event.md) | active | /spec-design | Append-only `timeline.jsonl` audit/export event boundary and replay limits. |
| States Index | states_index | [.memory-bank/states/index.md](states/index.md) | active | /spec-design | Router for active shared state/lifecycle specs. |
| Plant State Trust | state | [.memory-bank/states/plant-state-trust.md](states/plant-state-trust.md) | active | /spec-design | Global observation/hypothesis/conflict/confirmed Plant state promotion boundary. |
| Safety Action Lifecycle | state | [.memory-bank/states/safety-action-lifecycle.md](states/safety-action-lifecycle.md) | active | /spec-design | Global Safety Gate, human approval, action task, follow-up, and no-actuation boundary. |
| Companion Governance | state | [.memory-bank/states/companion-governance.md](states/companion-governance.md) | active | /spec-design | Global IssueStack, proposal supersede, DecisionRecord, and approved governance summary boundary. |
| Dataset Governance | state | [.memory-bank/states/dataset-governance.md](states/dataset-governance.md) | active | /spec-design | Global non-trainable default, evidence-ref, and trainability lifecycle boundary. |
| Foundation Test Harness | testing | [.memory-bank/testing/foundation-test-harness.md](testing/foundation-test-harness.md) | active | /foundation-to-tasks | FT-000 test command, smoke targets, fixture expectations, and evidence requirements. |
| Foundation Local Runtime Runbook | runbook | [.memory-bank/runbooks/foundation-local-runtime.md](runbooks/foundation-local-runtime.md) | active | /foundation-to-tasks | Local FT-000 setup/start/smoke command sequence and troubleshooting notes. |
| FT-001 Local Accounts Sessions And ActorContext | feature_design | [.memory-bank/tech-specs/FT-001-local-accounts-sessions-actor-context.md](tech-specs/FT-001-local-accounts-sessions-actor-context.md) | active | /prd-to-tasks or /spec-improve repair | Stable FT-001 feature hub and compatibility facade routing atomic data, security, API, ActorContext, and verification specs. |
| Local Identity And Session Data | domain | [.memory-bank/domains/local-identity-session-data.md](domains/local-identity-session-data.md) | active | /spec-improve FT-001 | Exact Account/FarmMembership/LocalSession schema, constraints, indexes, migration, and deferred Farm FK handoff. |
| Local Session Security | contract | [.memory-bank/contracts/local-session-security.md](contracts/local-session-security.md) | active | /spec-improve FT-001 | Argon2id credentials, opaque session tokens, lifecycle, browser cookie, and optional bearer transport. |
| Local Session API | contract | [.memory-bank/contracts/local-session-api.md](contracts/local-session-api.md) | active | /spec-improve FT-001 | Login/logout/me routes, activation handoff, stable auth errors, and no-leak failures. |
| ActorContext | contract | [.memory-bank/contracts/actor-context.md](contracts/actor-context.md) | active | /spec-improve FT-001 | Fixed role policy, ActorContext, PlantPermissionContext interface, protected entrypoints, and context-builder authorization. |
| FT-001 Access And Auth Verification | testing | [.memory-bank/testing/ft-001-access-auth.md](testing/ft-001-access-auth.md) | active | /spec-improve FT-001 | Cross-contract test coverage, task/evidence routing, and quality gates. |
| FT-002 Farm Plant Lifecycle And Access Grants | feature_design | [.memory-bank/tech-specs/FT-002-farm-plant-lifecycle-access-grants.md](tech-specs/FT-002-farm-plant-lifecycle-access-grants.md) | active | /prd-to-tasks or /spec-improve repair | Current normative feature design for single Farm seed/UUID authority, deferred FarmMembership FK closure, Plant lifecycle, PlantAccessGrant lifecycle, concrete PlantPermissionContext resolver semantics, retained-history authorization, route contracts, audit handoff, and verification. |
| FT-003 Boss Admin Surface And Admin Audit | feature_design | [.memory-bank/tech-specs/FT-003-boss-admin-surface-admin-audit.md](tech-specs/FT-003-boss-admin-surface-admin-audit.md) | active | /prd-to-tasks or /spec-improve repair | Current normative feature design for Boss admin workflows, local invite semantics, AdminAuditRecord, admin route contracts, UI boundary, and verification. |

## Planned Specs
| Area | Expected path | Needed by | Notes |
|---|---|---|---|
| feature_design | .memory-bank/tech-specs/FT-<NNN>-<slug>.md | /prd-to-tasks or /spec-improve repair | Feature-local specs for features not yet registered above. `/prd-to-tasks` owns feature design before task slicing; `/spec-improve` is repair/advanced refresh. |
| generated_openapi | generated from backend schemas | implementation task / CI | Generated from FastAPI/Pydantic-style schemas after backend exists; no hand-written OpenAPI source during global backbone. |

## Broken / Missing Links
- None detected as of 2026-06-29.

## Update Rules
- Keep this file as index/registry only: names, paths, statuses, owners, scopes, and broken links.
- Do not add global backbone status, backbone matrices, feature status maps, long hard rules, or open design question dumps here.
- Use [.memory-bank/spec-backbone.md](spec-backbone.md) for pre-PRD readiness, decomposition inputs, global backbone status, matrix, and handoffs.
- Use linked specs or ADRs for detailed decisions, rationale, contracts, state transitions, schemas, invariants, and testing rules.
