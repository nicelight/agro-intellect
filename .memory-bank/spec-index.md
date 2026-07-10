---
description: Registry and discovery map for active subject-based SDD specifications.
status: active
last_updated: 2026-07-10
source_of_truth:
  - .memory-bank/constitution.md
  - .memory-bank/prd.md
  - .memory-bank/spec-backbone.md
---
# SDD Spec Index

## Purpose

- Register one active canonical path for each concrete design concern.
- Support registry-first discovery before specs are created or extended.
- Keep readiness and handoff state in `spec-backbone.md`; feature composition
  remains in feature `spec_design_links`.
- `Change route` names an allowed workflow, not a file owner.

## Spec Registry

| Type | Path | Status | Scope | Change route |
|---|---|---|---|---|
| governance | [.memory-bank/constitution.md](constitution.md) | active | Top project policy | `/constitution` |
| invariants | [.memory-bank/invariants.md](invariants.md) | active | Cross-cutting MUST/NEVER rules | `/spec-init` or `/spec-design` |
| glossary | [.memory-bank/glossary.md](glossary.md) | active | Shared vocabulary | `/spec-init` or `/spec-design` |
| scenarios | [.memory-bank/user-scenarios.md](user-scenarios.md) | active | Actors and scenario implications | `/spec-init` |
| domain | [.memory-bank/domains/core-domain.md](domains/core-domain.md) | active | PRD-level entities and rules | `/spec-init` |
| boundary_hints | [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md) | active | Preliminary decomposition boundaries | `/spec-init` or `/spec-design` |
| lifecycle_hints | [.memory-bank/states/lifecycle-map.md](states/lifecycle-map.md) | active | Preliminary lifecycle boundaries | `/spec-init` or `/spec-design` |
| architecture | [.memory-bank/architecture/system-architecture.md](architecture/system-architecture.md) | active | Global architecture and Architecture Spine | `/spec-design` |
| architecture | [.memory-bank/architecture/foundation-runtime-substrate.md](architecture/foundation-runtime-substrate.md) | active | Verified backend runtime substrate | `/foundation-to-tasks` or `/spec-design` |
| foundation_decision | [.memory-bank/foundation.md](foundation.md) | active | Foundation gate and pressure map | `/spec-design` |
| data_spec | [.memory-bank/domains/runtime-data-model.md](domains/runtime-data-model.md) | active | Global runtime authority and shared identity | `/spec-design` |
| data_spec | [.memory-bank/domains/foundation-data-substrate.md](domains/foundation-data-substrate.md) | active | DB/session/Alembic/runtime-root substrate | `/foundation-to-tasks` or `/spec-design` |
| data_spec | [.memory-bank/domains/plant-operations.md](domains/plant-operations.md) | active | Daily check-in, observation, manual pH/EC, and freshness persistence | `/prd-to-tasks` or `/spec-design` |
| data_spec | [.memory-bank/domains/photo-artifacts.md](domains/photo-artifacts.md) | active | Local photo artifact authority, catalog, layout, and capture manifests | `/spec-design` or `/prd-to-tasks` |
| data_spec | [.memory-bank/domains/identity/account-membership.md](domains/identity/account-membership.md) | active | Account and FarmMembership persistence | `/prd-to-tasks` or `/spec-design` |
| data_spec | [.memory-bank/domains/auth/session-storage.md](domains/auth/session-storage.md) | active | LocalSession digest-only persistence | `/prd-to-tasks` or `/spec-design` |
| data_spec | [.memory-bank/domains/farm/farm-plant-access-storage.md](domains/farm/farm-plant-access-storage.md) | active | Exact Farm/Plant/grant persistence, migration, bootstrap, and transaction rules | `/prd-to-tasks` or `/spec-design` |
| data_contract | [.memory-bank/domains/admin/admin-audit.md](domains/admin/admin-audit.md) | active | Durable admin audit record and transaction semantics | `/prd-to-tasks` or `/spec-design` |
| api_guidelines | [.memory-bank/contracts/api-guidelines.md](contracts/api-guidelines.md) | active | Global HTTP/auth/error/origin rules | `/spec-design` |
| api_contract | [.memory-bank/contracts/foundation-smoke-api.md](contracts/foundation-smoke-api.md) | active | `/health` and `/ready` substrate boundary | `/foundation-to-tasks` or `/spec-design` |
| evidence_contract | [.memory-bank/contracts/evidence-redaction.md](contracts/evidence-redaction.md) | active | Secret/evidence redaction | `/foundation-to-tasks` or `/spec-design` |
| event_contract | [.memory-bank/contracts/agent-chat-bus.md](contracts/agent-chat-bus.md) | active | Agent-consumable event boundary | `/spec-design` |
| agent_io_contract | [.memory-bank/contracts/message-envelope.md](contracts/message-envelope.md) | active | Structured publishable agent output | `/spec-design` |
| presentation_contract | [.memory-bank/contracts/ui-feed.md](contracts/ui-feed.md) | active | Human-facing non-authoritative projection | `/spec-design` |
| audit_contract | [.memory-bank/contracts/timeline-event.md](contracts/timeline-event.md) | active | Append-only timeline event, current event registry, and minimal append writer seam | `/spec-design` or `/prd-to-tasks` |
| security_contract | [.memory-bank/contracts/auth/session-security.md](contracts/auth/session-security.md) | active | Password/token/cookie/bearer security | `/prd-to-tasks` or `/spec-design` |
| api_contract | [.memory-bank/contracts/auth/session-http.md](contracts/auth/session-http.md) | active | Login/logout/current-session HTTP | `/prd-to-tasks` or `/spec-design` |
| interface_contract | [.memory-bank/contracts/access/actor-context.md](contracts/access/actor-context.md) | active | ActorContext and Plant permission resolution | `/prd-to-tasks` or `/spec-design` |
| api_contract | [.memory-bank/contracts/admin/boss-admin-http.md](contracts/admin/boss-admin-http.md) | active | Boss direct Account creation and admin HTTP boundary | `/prd-to-tasks` or `/spec-design` |
| api_contract | [.memory-bank/contracts/farm/plant-management-http.md](contracts/farm/plant-management-http.md) | active | Farm/Plant lifecycle and PlantAccessGrant HTTP boundary | `/prd-to-tasks` or `/spec-design` |
| api_contract | [.memory-bank/contracts/plant-operations-http.md](contracts/plant-operations-http.md) | active | Daily check-in and manual measurement HTTP boundary | `/prd-to-tasks` or `/spec-design` |
| api_contract | [.memory-bank/contracts/photo-intake-http.md](contracts/photo-intake-http.md) | active | Photo upload and catalog HTTP boundary | `/prd-to-tasks` or `/spec-design` |
| state_spec | [.memory-bank/states/plant-state-trust.md](states/plant-state-trust.md) | active | Plant evidence trust promotion | `/spec-design` |
| state_spec | [.memory-bank/states/safety-action-lifecycle.md](states/safety-action-lifecycle.md) | active | Safety/action approval lifecycle | `/spec-design` |
| state_spec | [.memory-bank/states/companion-governance.md](states/companion-governance.md) | active | Companion governance lifecycle | `/spec-design` |
| state_spec | [.memory-bank/states/dataset-governance.md](states/dataset-governance.md) | active | Dataset trainability lifecycle | `/spec-design` |
| state_spec | [.memory-bank/states/auth/session-lifecycle.md](states/auth/session-lifecycle.md) | active | Password session expiry/revocation | `/prd-to-tasks` or `/spec-design` |
| state_spec | [.memory-bank/states/plants/plant-and-access-lifecycle.md](states/plants/plant-and-access-lifecycle.md) | active | Plant/grant lifecycle and global archived-Plant operational guard | `/prd-to-tasks` or `/spec-design` |
| testing | [.memory-bank/testing/index.md](testing/index.md) | active | Testing document router | `/spec-design` |
| testing_strategy | [.memory-bank/testing/strategy.md](testing/strategy.md) | active | Global risk-based testing strategy | `/spec-design` |
| testing_spec | [.memory-bank/testing/foundation-test-harness.md](testing/foundation-test-harness.md) | active | Foundation executable harness | `/foundation-to-tasks` or `/spec-design` |
| testing_spec | [.memory-bank/testing/auth/session-and-access.md](testing/auth/session-and-access.md) | active | Identity/session/access verification | `/prd-to-tasks` or `/spec-design` |
| testing_spec | [.memory-bank/testing/admin/boss-admin-and-audit.md](testing/admin/boss-admin-and-audit.md) | active | Boss admin/audit verification | `/prd-to-tasks` or `/spec-design` |
| testing_spec | [.memory-bank/testing/farm/plant-lifecycle-and-access.md](testing/farm/plant-lifecycle-and-access.md) | active | Farm bootstrap, Plant lifecycle/access, audit, migration, and HTTP verification | `/prd-to-tasks` or `/spec-design` |
| testing_spec | [.memory-bank/testing/plant-operations.md](testing/plant-operations.md) | active | Check-in, manual measurement, and freshness verification | `/prd-to-tasks` or `/spec-design` |
| testing_spec | [.memory-bank/testing/photo-intake.md](testing/photo-intake.md) | active | Photo artifact, manifest, catalog, upload, and timeline-ref verification | `/prd-to-tasks` or `/spec-design` |
| runbook | [.memory-bank/runbooks/foundation-local-runtime.md](runbooks/foundation-local-runtime.md) | active | Local Foundation setup/start/smoke | `/foundation-to-tasks` or `/spec-design` |
| runbook | [.memory-bank/runbooks/first-boss-local-bootstrap.md](runbooks/first-boss-local-bootstrap.md) | active | First Boss one-shot local bootstrap command | `/prd-to-tasks` or `/spec-design` |

## Planned Specs

| Type | Expected path | Needed by | Notes |
|---|---|---|---|
| subject_spec | `.memory-bank/<family>/<subject>.md` | `/prd-to-tasks` | Create only after registry/folder discovery proves the concern is missing. |
| generated_openapi | generated from backend schemas | implementation/CI | Generated after schemas exist; not global source of truth. |

## Broken / Missing Links

- None detected during the 2026-06-30 subject-based migration.

## Update Rules

- One concrete concern has one active canonical path.
- Registry rows contain only type, path, status, scope, and change route.
- Do not store reverse usage, feature status/readiness, decision bodies,
  schemas, transitions, or file-owner metadata here.
- Features/tasks link the exact applicable canonical specs directly.
